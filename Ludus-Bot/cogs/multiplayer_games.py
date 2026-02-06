import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import random
from typing import Dict, List, Optional
from datetime import datetime

# ========================================
# MURDER MYSTERY LOBBY VIEW (v2 Components)
# ========================================

class MurderMysteryLobbyView(discord.ui.View):
    """Modern lobby with settings for Murder Mystery"""
    
    def __init__(self, cog, lobby_id):
        super().__init__(timeout=120.0)
        self.cog = cog
        self.lobby_id = lobby_id
    
    @discord.ui.button(label="Join Game", style=discord.ButtonStyle.green, emoji="✅", custom_id="mm_join")
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        game = self.cog.active_lobbies.get(self.lobby_id)
        if not game:
            await interaction.response.send_message("❌ Game no longer exists!", ephemeral=True)
            return
        
        if interaction.user.id in game["players"]:
            await interaction.response.send_message("❌ You're already in!", ephemeral=True)
            return
        
        if len(game["players"]) >= 10:
            await interaction.response.send_message("❌ Lobby full! (10/10)", ephemeral=True)
            return
        
        game["players"].append(interaction.user.id)
        await self.update_lobby_message(interaction)
        await interaction.response.send_message("✅ Joined!", ephemeral=True)
    
    @discord.ui.button(label="Leave", style=discord.ButtonStyle.gray, emoji="🚪", custom_id="mm_leave")
    async def leave_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        game = self.cog.active_lobbies.get(self.lobby_id)
        if not game:
            await interaction.response.send_message("❌ Game no longer exists!", ephemeral=True)
            return
        
        if interaction.user.id not in game["players"]:
            await interaction.response.send_message("❌ You're not in this game!", ephemeral=True)
            return
        
        if interaction.user.id == game["host"]:
            await interaction.response.send_message("❌ Host can't leave! Cancel game instead.", ephemeral=True)
            return
        
        game["players"].remove(interaction.user.id)
        await self.update_lobby_message(interaction)
        await interaction.response.send_message("✅ Left the game.", ephemeral=True)
    
    @discord.ui.button(label="Settings", style=discord.ButtonStyle.blurple, emoji="⚙️", custom_id="mm_settings")
    async def settings_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        game = self.cog.active_lobbies.get(self.lobby_id)
        if not game:
            await interaction.response.send_message("❌ Game no longer exists!", ephemeral=True)
            return
        
        if interaction.user.id != game["host"]:
            await interaction.response.send_message("❌ Only host can change settings!", ephemeral=True)
            return
        
        await interaction.response.send_modal(MurderMysterySettingsModal(self.cog, self.lobby_id))
    
    @discord.ui.button(label="Start Game", style=discord.ButtonStyle.red, emoji="▶️", custom_id="mm_start")
    async def start_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        game = self.cog.active_lobbies.get(self.lobby_id)
        if not game:
            await interaction.response.send_message("❌ Game no longer exists!", ephemeral=True)
            return
        
        if interaction.user.id != game["host"]:
            await interaction.response.send_message("❌ Only host can start!", ephemeral=True)
            return
        
        if len(game["players"]) < 4:
            await interaction.response.send_message("❌ Need at least 4 players!", ephemeral=True)
            return
        
        game["started"] = True
        await interaction.response.send_message("🎮 **Game Starting!** Assigning roles...", ephemeral=True)
        await self.cog.start_murder_mystery_game(interaction, self.lobby_id)
    
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger, emoji="❌", custom_id="mm_cancel")
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        game = self.cog.active_lobbies.get(self.lobby_id)
        if not game:
            await interaction.response.send_message("❌ Game no longer exists!", ephemeral=True)
            return
        
        if interaction.user.id != game["host"]:
            await interaction.response.send_message("❌ Only host can cancel!", ephemeral=True)
            return
        
        del self.cog.active_lobbies[self.lobby_id]
        await interaction.response.send_message("❌ **Game cancelled by host.**")
        await interaction.message.delete()
    
    async def update_lobby_message(self, interaction: discord.Interaction):
        """Update lobby embed"""
        game = self.cog.active_lobbies.get(self.lobby_id)
        if not game:
            return
        
        player_list = "\n".join([f"• <@{pid}>" for pid in game["players"]])
        
        embed = discord.Embed(
            title="🔪 MURDER MYSTERY LOBBY",
            description=f"**Host:** <@{game['host']}>\n\n"
                       f"**Players ({len(game['players'])}/10):**\n{player_list}\n\n"
                       "📋 **Game Settings:**\n"
                       f"• Tasks Required: **{game['tasks_required']}** per player\n"
                       f"• Round Duration: **{game['round_duration']}s**\n"
                       f"• Voting Duration: **{game['vote_duration']}s**\n"
                       f"• Sheriff Mode: **{'ON' if game['has_sheriff'] else 'OFF'}**\n\n"
                       "**How to Play:**\n"
                       "• 1 KILLER 🔪, 1 SHERIFF 👮 (optional), rest INNOCENT 😇\n"
                       "• Innocents complete tasks to win\n"
                       "• Killer eliminates players each round\n"
                       "• Vote to eject suspects\n"
                       "• Sheriff can eliminate someone (risky!)",
            color=discord.Color.dark_red()
        )
        embed.set_footer(text="Click Join to play • Host can Start when ready")
        
        await interaction.message.edit(embed=embed, view=self)

class MurderMysterySettingsModal(discord.ui.Modal, title="Murder Mystery Settings"):
    """Settings modal for lobby"""
    
    tasks_required = discord.ui.TextInput(
        label="Tasks Required (per player)",
        placeholder="5",
        default="5",
        min_length=1,
        max_length=2,
        required=True
    )
    
    round_duration = discord.ui.TextInput(
        label="Round Duration (seconds)",
        placeholder="90",
        default="90",
        min_length=2,
        max_length=3,
        required=True
    )
    
    vote_duration = discord.ui.TextInput(
        label="Voting Duration (seconds)",
        placeholder="45",
        default="45",
        min_length=2,
        max_length=3,
        required=True
    )
    
    sheriff_mode = discord.ui.TextInput(
        label="Sheriff Mode (yes/no)",
        placeholder="yes",
        default="yes",
        min_length=2,
        max_length=3,
        required=True
    )
    
    def __init__(self, cog, lobby_id):
        super().__init__()
        self.cog = cog
        self.lobby_id = lobby_id
    
    async def on_submit(self, interaction: discord.Interaction):
        game = self.cog.active_lobbies.get(self.lobby_id)
        if not game:
            await interaction.response.send_message("❌ Game no longer exists!", ephemeral=True)
            return
        
        try:
            tasks = int(self.tasks_required.value)
            round_dur = int(self.round_duration.value)
            vote_dur = int(self.vote_duration.value)
            sheriff = self.sheriff_mode.value.lower() in ["yes", "y", "true", "on"]
            
            if not (3 <= tasks <= 10):
                raise ValueError("Tasks must be 3-10")
            if not (30 <= round_dur <= 180):
                raise ValueError("Round duration must be 30-180s")
            if not (20 <= vote_dur <= 90):
                raise ValueError("Vote duration must be 20-90s")
            
            game["tasks_required"] = tasks
            game["round_duration"] = round_dur
            game["vote_duration"] = vote_dur
            game["has_sheriff"] = sheriff
            
            await interaction.response.send_message("✅ Settings updated!", ephemeral=True)
            
            # Update lobby display
            view = MurderMysteryLobbyView(self.cog, self.lobby_id)
            await view.update_lobby_message(interaction)
        
        except ValueError as e:
            await interaction.response.send_message(f"❌ Invalid settings: {e}", ephemeral=True)

class MultiplayerGames(commands.Cog):
    """Multiplayer social deduction and competitive games"""
    
    def __init__(self, bot):
        self.bot = bot
        self.active_lobbies = {}
        
    # Command group for multiplayer games
    multiplayer_group = app_commands.Group(name="multiplayer", description="Multiplayer social games")
    
    @multiplayer_group.command(name="clue", description="Play Clue! 2-6 players guess WHO, WHAT weapon, WHERE")
    async def clue_game(self, interaction: discord.Interaction):
        """Classic Clue board game - multiplayer"""
        
        # Check if lobby already exists
        lobby_id = f"clue_{interaction.channel.id}"
        if lobby_id in self.active_lobbies:
            await interaction.response.send_message("❌ A Clue game is already active in this channel!", ephemeral=True)
            return
        
        # Game data
        suspects = ["Colonel Mustard 👨‍✈️", "Miss Scarlet 💃", "Professor Plum 👨‍🏫", 
                   "Mrs. Peacock 👵", "Mr. Green 🧑‍💼", "Mrs. White 👩‍🍳"]
        weapons = ["Candlestick 🕯️", "Knife 🔪", "Lead Pipe 🔧", "Revolver 🔫", "Rope 🪢", "Wrench 🔩"]
        rooms = ["Kitchen 🍳", "Ballroom 💃", "Conservatory 🌿", "Dining Room 🍽️", 
                "Library 📚", "Lounge 🛋️", "Study 📖", "Hall 🚪", "Billiard Room 🎱"]
        
        # Create solution (hidden)
        solution = {
            "suspect": random.choice(suspects),
            "weapon": random.choice(weapons),
            "room": random.choice(rooms)
        }
        
        # Create lobby
        self.active_lobbies[lobby_id] = {
            "type": "clue",
            "host": interaction.user.id,
            "players": [interaction.user.id],
            "solution": solution,
            "suspects": suspects,
            "weapons": weapons,
            "rooms": rooms,
            "started": False,
            "guesses": {}
        }
        
        embed = discord.Embed(
            title="🎩 CLUE - Multiplayer Mystery!",
            description=f"**{interaction.user.mention} started a Clue game!**\n\n"
                       "📋 **How to Play:**\n"
                       "• 2-6 players try to solve: WHO did it, WHAT weapon, WHERE\n"
                       "• React with ✅ to join (30 seconds)\n"
                       "• Host reacts with ▶️ to start\n"
                       "• Take turns making accusations!\n\n"
                       f"**Players ({len(self.active_lobbies[lobby_id]['players'])}/6):**\n"
                       f"• {interaction.user.mention}",
            color=discord.Color.dark_red()
        )
        embed.set_footer(text="React ✅ to join • Host reacts ▶️ to start")
        
        await interaction.response.send_message(embed=embed)
        msg = await interaction.original_response()
        await msg.add_reaction("✅")
        await msg.add_reaction("▶️")
        
        def check_reaction(reaction, user):
            return (reaction.message.id == msg.id and 
                   not user.bot and 
                   str(reaction.emoji) in ["✅", "▶️"])
        
        # Lobby phase (30 seconds)
        try:
            while not self.active_lobbies[lobby_id]["started"]:
                reaction, user = await self.bot.wait_for('reaction_add', check=check_reaction, timeout=30.0)
                
                if str(reaction.emoji) == "✅" and user.id not in self.active_lobbies[lobby_id]["players"]:
                    if len(self.active_lobbies[lobby_id]["players"]) < 6:
                        self.active_lobbies[lobby_id]["players"].append(user.id)
                        
                        player_list = "\n".join([f"• <@{pid}>" for pid in self.active_lobbies[lobby_id]["players"]])
                        embed.description = (f"**{interaction.user.mention} started a Clue game!**\n\n"
                                           "📋 **How to Play:**\n"
                                           "• 2-6 players try to solve: WHO did it, WHAT weapon, WHERE\n"
                                           "• React with ✅ to join (30 seconds)\n"
                                           "• Host reacts with ▶️ to start\n"
                                           "• Take turns making accusations!\n\n"
                                           f"**Players ({len(self.active_lobbies[lobby_id]['players'])}/6):**\n"
                                           f"{player_list}")
                        await msg.edit(embed=embed)
                    else:
                        await interaction.followup.send(f"❌ {user.mention} Lobby full!", ephemeral=True)
                
                elif str(reaction.emoji) == "▶️" and user.id == self.active_lobbies[lobby_id]["host"]:
                    if len(self.active_lobbies[lobby_id]["players"]) >= 2:
                        self.active_lobbies[lobby_id]["started"] = True
                        break
                    else:
                        await interaction.followup.send("❌ Need at least 2 players!", ephemeral=True)
        
        except asyncio.TimeoutError:
            if len(self.active_lobbies[lobby_id]["players"]) >= 2:
                self.active_lobbies[lobby_id]["started"] = True
            else:
                await interaction.followup.send("❌ Game cancelled - not enough players!")
                del self.active_lobbies[lobby_id]
                return
        
        # Game starts!
        game_embed = discord.Embed(
            title="🎩 CLUE GAME - ACTIVE!",
            description="**The game has begun!**\n\n"
                       "💀 A murder has been committed!\n"
                       "🕵️ Figure out WHO, WHAT weapon, WHERE it happened\n\n"
                       "**To make an accusation, type:**\n"
                       "`[Suspect], [Weapon], [Room]`\n\n"
                       "**Example:** `Colonel Mustard, Knife, Kitchen`",
            color=discord.Color.red()
        )
        game_embed.add_field(name="👤 Suspects", value="\n".join([s.split()[0] + " " + s.split()[1] for s in suspects]), inline=True)
        game_embed.add_field(name="🔪 Weapons", value="\n".join([w.split()[0] for w in weapons]), inline=True)
        game_embed.add_field(name="🏠 Rooms", value="\n".join([r.split()[0] for r in rooms]), inline=True)
        
        player_mentions = " ".join([f"<@{pid}>" for pid in self.active_lobbies[lobby_id]["players"]])
        await interaction.followup.send(f"🎮 {player_mentions}", embed=game_embed)
        
        def check_message(m):
            return (m.channel.id == interaction.channel.id and 
                   m.author.id in self.active_lobbies[lobby_id]["players"] and
                   "," in m.content)
        
        # Game loop
        winner = None
        try:
            while lobby_id in self.active_lobbies and not winner:
                msg = await self.bot.wait_for('message', check=check_message, timeout=300.0)
                
                # Parse accusation
                parts = [p.strip() for p in msg.content.split(",")]
                if len(parts) != 3:
                    await msg.reply("❌ Format: `[Suspect], [Weapon], [Room]`", delete_after=5)
                    continue
                
                # Find matches (case insensitive, partial match)
                suspect_guess = None
                weapon_guess = None
                room_guess = None
                
                for s in suspects:
                    if parts[0].lower() in s.lower():
                        suspect_guess = s
                        break
                
                for w in weapons:
                    if parts[1].lower() in w.lower():
                        weapon_guess = w
                        break
                
                for r in rooms:
                    if parts[2].lower() in r.lower():
                        room_guess = r
                        break
                
                if not suspect_guess or not weapon_guess or not room_guess:
                    await msg.reply("❌ Invalid guess! Check spelling.", delete_after=5)
                    continue
                
                # Check if correct
                if (suspect_guess == solution["suspect"] and 
                    weapon_guess == solution["weapon"] and 
                    room_guess == solution["room"]):
                    
                    winner = msg.author
                    win_embed = discord.Embed(
                        title="🎉 CASE SOLVED!",
                        description=f"**{msg.author.mention} solved the mystery!**\n\n"
                                   f"👤 Murderer: **{solution['suspect']}**\n"
                                   f"🔪 Weapon: **{solution['weapon']}**\n"
                                   f"🏠 Location: **{solution['room']}**\n\n"
                                   "**+500 PsyCoins!** 🪙",
                        color=discord.Color.green()
                    )
                    await msg.reply(embed=win_embed)
                    
                    # Award coins
                    economy_cog = self.bot.get_cog("Economy")
                    if economy_cog:
                        economy_cog.add_coins(msg.author.id, 500, "clue_winner")
                    
                    del self.active_lobbies[lobby_id]
                    break
                else:
                    # Wrong guess
                    hints = []
                    if suspect_guess == solution["suspect"]:
                        hints.append("✅ Suspect correct!")
                    if weapon_guess == solution["weapon"]:
                        hints.append("✅ Weapon correct!")
                    if room_guess == solution["room"]:
                        hints.append("✅ Room correct!")
                    
                    if hints:
                        await msg.reply(f"🔍 **Close!** {' '.join(hints)}", delete_after=10)
                    else:
                        await msg.reply("❌ **All wrong!** Try again!", delete_after=10)
        
        except asyncio.TimeoutError:
            if lobby_id in self.active_lobbies:
                timeout_embed = discord.Embed(
                    title="⏰ Game Timeout",
                    description=f"**Solution:**\n"
                               f"👤 {solution['suspect']}\n"
                               f"🔪 {solution['weapon']}\n"
                               f"🏠 {solution['room']}",
                    color=discord.Color.orange()
                )
                await interaction.followup.send(embed=timeout_embed)
                del self.active_lobbies[lobby_id]
    
    @multiplayer_group.command(name="murdermystery", description="Among Us style! 4-10 players, find the killer!")
    async def murder_mystery(self, interaction: discord.Interaction):
        """Murder Mystery social deduction game - MODERN LOBBY v2"""
        
        lobby_id = f"murder_{interaction.channel.id}"
        if lobby_id in self.active_lobbies:
            await interaction.response.send_message("❌ A Murder Mystery game is already active!", ephemeral=True)
            return
        
        # Interactive task types
        task_templates = {
            "emoji_find": {
                "name": "🔍 Find the Emoji",
                "description": "Find the {target} emoji among decoys!",
                "type": "find"
            },
            "word_memory": {
                "name": "🧠 Memorize Words",
                "description": "Remember these words and type them back!",
                "type": "memory"
            },
            "math_quick": {
                "name": "🔢 Quick Math",
                "description": "Solve: {equation}",
                "type": "math"
            },
            "sort_numbers": {
                "name": "📊 Sort Numbers",
                "description": "Sort these numbers: {numbers}",
                "type": "sort"
            },
            "color_match": {
                "name": "🎨 Color Match",
                "description": "Which color is {color}? React with the emoji!",
                "type": "react"
            },
            "sequence": {
                "name": "🔄 Remember Sequence",
                "description": "Type this sequence: {sequence}",
                "type": "sequence"
            },
            "word_scramble": {
                "name": "🔤 Unscramble Word",
                "description": "Unscramble: {scrambled}",
                "type": "unscramble"
            },
            "pattern": {
                "name": "🧩 Complete Pattern",
                "description": "What comes next? {pattern}",
                "type": "pattern"
            }
        }
        
        # Create lobby with MODERN SETTINGS
        self.active_lobbies[lobby_id] = {
            "type": "murder",
            "host": interaction.user.id,
            "players": [interaction.user.id],
            "started": False,
            "killer": None,
            "sheriff": None,
            "alive": [],
            "dead": [],
            "tasks_done": {},
            "active_tasks": {},
            "tasks_required": 5,
            "round_duration": 90,
            "vote_duration": 45,
            "has_sheriff": True,
            "round": 0,
            "death_round": False,
            "killer_kills": {},
            "channel": interaction.channel.id,
            "task_templates": task_templates
        }
        
        # Send MODERN LOBBY
        player_list = f"• <@{interaction.user.id}>"
        
        embed = discord.Embed(
            title="🔪 MURDER MYSTERY LOBBY",
            description=f"**Host:** <@{interaction.user.id}>\n\n"
                       f"**Players (1/10):**\n{player_list}\n\n"
                       "📋 **Game Settings:**\n"
                       f"• Tasks Required: **5** per player\n"
                       f"• Round Duration: **90s**\n"
                       f"• Voting Duration: **45s**\n"
                       f"• Sheriff Mode: **ON**\n\n"
                       "**How to Play:**\n"
                       "• 1 KILLER 🔪, 1 SHERIFF 👮, rest INNOCENT 😇\n"
                       "• Innocents complete tasks to win\n"
                       "• Killer eliminates players each round\n"
                       "• Vote to eject suspects\n"
                       "• Sheriff can eliminate someone (risky!)",
            color=discord.Color.dark_red()
        )
        embed.set_footer(text="Click Join to play • Host can Start when ready")
        
        view = MurderMysteryLobbyView(self, lobby_id)
        await interaction.response.send_message(embed=embed, view=view)
    
    async def start_murder_mystery_game(self, interaction: discord.Interaction, lobby_id: str):
        """Start the murder mystery game after lobby phase"""
        game = self.active_lobbies.get(lobby_id)
        if not game:
            return
        
        # Assign roles
        players = game["players"].copy()
        random.shuffle(players)
        
        game["killer"] = players[0]
        game["sheriff"] = players[1] if game["has_sheriff"] and len(players) >= 4 else None
        game["alive"] = game["players"].copy()
        game["tasks_done"] = {pid: 0 for pid in game["players"] if pid != game["killer"]}
        
        # Send role DMs
        for player_id in game["players"]:
            try:
                user = await self.bot.fetch_user(player_id)
                if player_id == game["killer"]:
                    role_embed = discord.Embed(
                        title="🔪 YOU ARE THE KILLER!",
                        description="**Your mission:** Eliminate all innocents without being caught!\n\n"
                                   "**Your powers:**\n"
                                   "• Kill 1 player per round (use buttons in your ephemeral panel)\n"
                                   "• Fake tasks to blend in\n"
                                   "• Deceive and survive votes!\n\n"
                                   "**Win condition:** Outnumber or equal innocents",
                        color=discord.Color.red()
                    )
                    await user.send(embed=role_embed)
                elif player_id == game["sheriff"]:
                    role_embed = discord.Embed(
                        title="👮 YOU ARE THE SHERIFF!",
                        description="**Your mission:** Protect innocents and kill the killer!\n\n"
                                   "**Your powers:**\n"
                                   "• Use `/murderkill @user` to eliminate someone\n"
                                   "• ⚠️ WARNING: If you kill an innocent = DEATH ROUND!\n"
                                   "• Complete tasks like innocents\n\n"
                                   "**Win condition:** Find and eliminate the killer!",
                        color=discord.Color.blue()
                    )
                    await user.send(embed=role_embed)
                else:
                    role_embed = discord.Embed(
                        title="😇 YOU ARE INNOCENT!",
                        description="**Your mission:** Complete tasks and find the killer!\n\n"
                                   "**Your powers:**\n"
                                   "• Complete tasks (5 total) via your ephemeral panel\n"
                                   "• Vote to eject suspects\n"
                                   "• Discuss and deduce!\n\n"
                                   "**Win condition:** Complete all tasks OR vote out killer",
                        color=discord.Color.green()
                    )
                    await user.send(embed=role_embed)
            except:
                pass
        
        # Game start announcement
        channel = self.bot.get_channel(game["channel"])
        if not channel:
            return
        
        start_embed = discord.Embed(
            title="🎮 MURDER MYSTERY - GAME START!",
            description=f"**Roles assigned! Check your DMs.**\n\n"
                       f"👥 **{len(game['alive'])} players alive**\n"
                       f"🎯 **Tasks:** 0/{len(game['tasks_done']) * game['tasks_required']} completed\n"
                       f"🔪 **Killer:** Hidden among you...\n"
                       f"{'👮 **Sheriff:** One player can strike...' if game['has_sheriff'] else ''}\n\n"
                       f"**Round 1 begins!** You have {game['round_duration']} seconds.\n"
                       "Click the buttons that appear to interact!",
            color=discord.Color.gold()
        )
        await channel.send(embed=start_embed)
        
        # Start main game loop
        await self.run_murder_mystery_game(interaction, lobby_id)
        
        game["killer"] = players[0]
        game["sheriff"] = players[1] if len(players) >= 4 else None
        game["alive"] = game["players"].copy()
        game["tasks_done"] = {pid: 0 for pid in game["players"] if pid != game["killer"]}
        
        # Send role DMs
        for player_id in game["players"]:
            try:
                user = await self.bot.fetch_user(player_id)
                if player_id == game["killer"]:
                    role_embed = discord.Embed(
                        title="🔪 YOU ARE THE KILLER!",
                        description="**Your mission:** Eliminate all innocents without being caught!\n\n"
                                   "**Your powers:**\n"
                                   "• Kill 1 player per round (use buttons in your ephemeral panel)\n"
                                   "• Fake tasks to blend in\n"
                                   "• Deceive and survive votes!\n\n"
                                   "**Win condition:** Outnumber or equal innocents",
                        color=discord.Color.red()
                    )
                    await user.send(embed=role_embed)
                elif player_id == game["sheriff"]:
                    role_embed = discord.Embed(
                        title="👮 YOU ARE THE SHERIFF!",
                        description="**Your mission:** Protect innocents and kill the killer!\n\n"
                                   "**Your powers:**\n"
                                   "• Use `/murderkill @user` to eliminate someone\n"
                                   "• ⚠️ WARNING: If you kill an innocent = DEATH ROUND!\n"
                                   "• Complete tasks like innocents\n\n"
                                   "**Win condition:** Find and eliminate the killer!",
                        color=discord.Color.blue()
                    )
                    await user.send(embed=role_embed)
                else:
                    role_embed = discord.Embed(
                        title="😇 YOU ARE INNOCENT!",
                        description="**Your mission:** Complete tasks and find the killer!\n\n"
                                   "**Your powers:**\n"
                                   "• Complete tasks (5 total) via your ephemeral panel\n"
                                   "• Vote to eject suspects\n"
                                   "• Discuss and deduce!\n\n"
                                   "**Win condition:** Complete all tasks OR vote out killer",
                        color=discord.Color.green()
                    )
                    await user.send(embed=role_embed)
            except:
                pass
        
        # Game start
        start_embed = discord.Embed(
            title="🎮 MURDER MYSTERY - GAME START!",
            description=f"**Roles assigned! Check your DMs.**\n\n"
                       f"👥 **{len(game['alive'])} players alive**\n"
                       f"🎯 **Tasks:** 0/{len(game['tasks_done']) * 5} completed\n"
                       f"🔪 **Killer:** Hidden among you...\n"
                       f"👮 **Sheriff:** One player can strike...\n\n"
                       "**Round 1 begins!** You have 90 seconds.\n"
                       "Click the buttons that appear to interact!",
            color=discord.Color.gold()
        )
        await interaction.followup.send(embed=start_embed)
        
        # Main game loop
        await self.run_murder_mystery_game(interaction, lobby_id)
    
    async def run_murder_mystery_game(self, interaction, lobby_id):
        """Main game loop for murder mystery"""
        game = self.active_lobbies.get(lobby_id)
        if not game:
            return
        
        while lobby_id in self.active_lobbies:
            game = self.active_lobbies[lobby_id]
            game["round"] += 1
            
            # Check win conditions
            total_tasks = sum(game["tasks_done"].values())
            required_tasks = len(game["tasks_done"]) * game["tasks_required"]
            
            alive_innocents = len([p for p in game["alive"] if p != game["killer"]])
            
            # Innocents win by tasks
            if total_tasks >= required_tasks:
                win_embed = discord.Embed(
                    title="🎉 INNOCENTS WIN!",
                    description=f"**All tasks completed!**\n\n"
                               f"The killer was: <@{game['killer']}>\n"
                               f"The sheriff was: <@{game['sheriff']}>\n\n"
                               "**+400 PsyCoins to all innocents!**",
                    color=discord.Color.green()
                )
                await interaction.followup.send(embed=win_embed)
                del self.active_lobbies[lobby_id]
                return
            
            # Killer wins by numbers
            if game["killer"] not in game["alive"]:
                # Killer already ejected
                pass
            elif alive_innocents <= 1:
                win_embed = discord.Embed(
                    title="🔪 KILLER WINS!",
                    description=f"**The killer has won!**\n\n"
                               f"Killer: <@{game['killer']}>\n"
                               f"Sheriff: <@{game['sheriff']}>\n\n"
                               "**+500 PsyCoins to the killer!**",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=win_embed)
                del self.active_lobbies[lobby_id]
                return
            
            # Round phase - Send ephemeral panels
            round_embed = discord.Embed(
                title=f"🕐 ROUND {game['round']}" + (" - ☠️ DEATH ROUND!" if game["death_round"] else ""),
                description=f"{'⚠️ **DEATH ROUND ACTIVE!** Vote carefully!' if game['death_round'] else 'Complete tasks and stay alert!'}\n\n"
                           f"👥 **Alive:** {len(game['alive'])} players\n"
                           f"💀 **Dead:** {len(game['dead'])} players\n"
                           f"📊 **Tasks:** {total_tasks}/{required_tasks}\n\n"
                           f"**Check your ephemeral panels!** ({game['round_duration']} seconds)",
                color=discord.Color.red() if game["death_round"] else discord.Color.blue()
            )
            await interaction.followup.send(embed=round_embed)
            
            # Send ephemeral panels to all alive players
            await self.send_ephemeral_panels(interaction, lobby_id)
            
            # Wait for round duration (from settings)
            await asyncio.sleep(game['round_duration'])
            
            # Process killer's kill (if any)
            if game["killer"] in game["alive"] and lobby_id in self.active_lobbies:
                killer_target = game["killer_kills"].get(game["round"])
                if killer_target and killer_target in game["alive"]:
                    game["alive"].remove(killer_target)
                    game["dead"].append(killer_target)
                    
                    death_embed = discord.Embed(
                        title="💀 A BODY HAS BEEN FOUND!",
                        description=f"**<@{killer_target}> was killed!**\n\n"
                                   "The killer strikes again...",
                        color=discord.Color.dark_red()
                    )
                    await interaction.followup.send(embed=death_embed)
            
            # Voting phase
            await self.run_voting_phase(interaction, lobby_id)
    
    async def send_ephemeral_panels(self, interaction, lobby_id):
        """Send ephemeral action panels with INTERACTIVE TASKS to all players"""
        game = self.active_lobbies.get(lobby_id)
        if not game:
            return
        
        for player_id in game["alive"]:
            try:
                user = await self.bot.fetch_user(player_id)
                
                if player_id == game["killer"]:
                    # Killer panel - No real tasks, just fake task names
                    fake_tasks = ["🔧 Fix Wiring", "🗑️ Empty Trash", "📊 Download Data", "🚀 Start Reactor"]
                    fake_task = random.choice(fake_tasks)
                    
                    targets = [p for p in game["alive"] if p != player_id]
                    target_list = "\n".join([f"• <@{pid}>" for pid in targets[:5]])
                    
                    killer_embed = discord.Embed(
                        title="🔪 KILLER PANEL",
                        description=f"**Round {game['round']}**\n\n"
                                   f"**Choose your target:**\n{target_list}\n\n"
                                   f"**Fake task to blend in:** {fake_task}\n\n"
                                   f"In game channel, type: `kill @username`\n"
                                   f"Or pretend to complete tasks!",
                        color=discord.Color.red()
                    )
                    await user.send(embed=killer_embed)
                
                elif player_id == game["sheriff"]:
                    # Sheriff panel - Real tasks
                    task = await self.generate_interactive_task(user, player_id, game)
                    
                    suspects = [p for p in game["alive"] if p != player_id]
                    suspect_list = "\n".join([f"• <@{pid}>" for pid in suspects[:5]])
                    
                    sheriff_embed = discord.Embed(
                        title="👮 SHERIFF PANEL",
                        description=f"**Round {game['round']}**\n\n"
                                   f"**Your task:** {task['name']}\n"
                                   f"📋 {task['instruction']}\n\n"
                                   f"**Tasks done:** {game['tasks_done'].get(player_id, 0)}/5\n\n"
                                   f"⚠️ **SPECIAL POWER:**\n"
                                   f"Use `/murderkill @user` to eliminate\n"
                                   f"❗ Wrong kill = DEATH ROUND!\n\n"
                                   f"**Suspects:**\n{suspect_list}",
                        color=discord.Color.blue()
                    )
                    await user.send(embed=sheriff_embed)
                
                else:
                    # Innocent panel - Real tasks
                    task = await self.generate_interactive_task(user, player_id, game)
                    
                    tasks_completed = game["tasks_done"].get(player_id, 0)
                    
                    innocent_embed = discord.Embed(
                        title="😇 INNOCENT PANEL",
                        description=f"**Round {game['round']}**\n\n"
                                   f"**Your task:** {task['name']}\n"
                                   f"📋 {task['instruction']}\n\n"
                                   f"**Progress:** {tasks_completed}/5 tasks complete\n\n"
                                   f"Complete tasks to help innocents win!\n"
                                   f"Stay alert and find the killer!",
                        color=discord.Color.green()
                    )
                    await user.send(embed=innocent_embed)
            
            except:
                pass
    
    async def generate_interactive_task(self, user, player_id, game):
        """Generate a random interactive task for a player"""
        task_type = random.choice(list(game["task_templates"].keys()))
        template = game["task_templates"][task_type]
        
        task_data = {}
        instruction = ""
        
        if task_type == "emoji_find":
            # Find the target emoji among decoys
            emojis = ["🔴", "🟠", "🟡", "🟢", "🔵", "🟣", "⚫", "⚪", "🟤", "🔶", "🔷", "🔸", "🔹", "❤️", "🧡", "💛", "💚", "💙", "💜", "🖤"]
            target = random.choice(emojis)
            decoys = random.sample([e for e in emojis if e != target], 9)
            options = decoys + [target]
            random.shuffle(options)
            
            task_data = {
                "type": "emoji_find",
                "target": target,
                "options": options
            }
            instruction = f"Find {target} in this grid:\n" + " ".join(options) + f"\n\n**Reply with the position (1-10) in game channel!**"
        
        elif task_type == "word_memory":
            # Memorize words
            words = ["apple", "tiger", "cloud", "river", "mountain", "ocean", "forest", "thunder"]
            chosen = random.sample(words, 3)
            
            task_data = {
                "type": "word_memory",
                "words": chosen
            }
            instruction = f"**Memorize these words:**\n`{' '.join(chosen)}`\n\n(They'll disappear in 10 seconds, then type them back in game channel!)"
            
            # Auto-hide message after 10 seconds
            asyncio.create_task(self.delayed_hide_task(user, player_id, game, chosen))
        
        elif task_type == "math_quick":
            # Quick math
            num1 = random.randint(10, 50)
            num2 = random.randint(10, 50)
            operation = random.choice(["+", "-", "*"])
            
            if operation == "+":
                answer = num1 + num2
            elif operation == "-":
                answer = num1 - num2
            else:
                answer = num1 * num2
            
            task_data = {
                "type": "math",
                "equation": f"{num1} {operation} {num2}",
                "answer": answer
            }
            instruction = f"**Solve this equation:**\n`{num1} {operation} {num2} = ?`\n\n**Type the answer in game channel!**"
        
        elif task_type == "sort_numbers":
            # Sort numbers
            numbers = random.sample(range(1, 50), 5)
            sorted_nums = sorted(numbers)
            
            task_data = {
                "type": "sort",
                "numbers": numbers,
                "answer": sorted_nums
            }
            instruction = f"**Sort these numbers (low to high):**\n`{numbers}`\n\n**Type them sorted in game channel!**\nExample: 1 5 12 23 45"
        
        elif task_type == "sequence":
            # Remember sequence
            sequence = "".join(random.choices(["A", "B", "C", "D"], k=4))
            
            task_data = {
                "type": "sequence",
                "sequence": sequence
            }
            instruction = f"**Remember this sequence:**\n`{sequence}`\n\n**Type it back in game channel!**"
        
        elif task_type == "word_scramble":
            # Unscramble word
            words_dict = {
                "MYSTERY": ["M", "Y", "S", "T", "E", "R", "Y"],
                "KILLER": ["K", "I", "L", "L", "E", "R"],
                "INNOCENT": ["I", "N", "N", "O", "C", "E", "N", "T"],
                "DISCORD": ["D", "I", "S", "C", "O", "R", "D"],
                "GAMING": ["G", "A", "M", "I", "N", "G"]
            }
            word, letters = random.choice(list(words_dict.items()))
            scrambled_letters = letters.copy()
            random.shuffle(scrambled_letters)
            scrambled = "".join(scrambled_letters)
            
            task_data = {
                "type": "unscramble",
                "word": word,
                "scrambled": scrambled
            }
            instruction = f"**Unscramble this word:**\n`{scrambled}`\n\n**Type the word in game channel!**"
        
        elif task_type == "pattern":
            # Complete pattern
            patterns = [
                {"pattern": "2 4 6 8", "answer": "10"},
                {"pattern": "1 3 5 7", "answer": "9"},
                {"pattern": "5 10 15 20", "answer": "25"},
                {"pattern": "A B C D", "answer": "E"},
                {"pattern": "🔴 🟡 🔴 🟡", "answer": "🔴"}
            ]
            chosen_pattern = random.choice(patterns)
            
            task_data = {
                "type": "pattern",
                "pattern": chosen_pattern["pattern"],
                "answer": chosen_pattern["answer"]
            }
            instruction = f"**What comes next?**\n`{chosen_pattern['pattern']} ... ?`\n\n**Type the answer in game channel!**"
        
        else:
            # Fallback - color match
            colors = {"red": "🔴", "blue": "🔵", "green": "🟢", "yellow": "🟡", "purple": "🟣"}
            color_name, emoji = random.choice(list(colors.items()))
            
            task_data = {
                "type": "color",
                "color": color_name,
                "emoji": emoji
            }
            instruction = f"**Type the color name:**\n{emoji}\n\n**Type '{color_name}' in game channel!**"
        
        # Store task for validation
        game["active_tasks"][player_id] = task_data
        
        return {
            "name": template["name"],
            "instruction": instruction,
            "data": task_data
        }
    
    async def delayed_hide_task(self, user, player_id, game, words):
        """Hide memorization task after delay"""
        await asyncio.sleep(10)
        try:
            await user.send("⏰ **Time's up! Type the words you memorized in the game channel!**")
        except:
            pass
    
    async def run_voting_phase(self, interaction, lobby_id):
        """Run the voting phase"""
        game = self.active_lobbies.get(lobby_id)
        if not game:
            return
        
        alive_mentions = ", ".join([f"<@{pid}>" for pid in game["alive"]])
        
        vote_embed = discord.Embed(
            title="🗳️ VOTING TIME!",
            description=f"**Time to vote!**\n\n"
                       f"**Alive players:**\n{alive_mentions}\n\n"
                       f"Type `vote @user` to cast your vote!\n"
                       f"({game['vote_duration']} seconds)",
            color=discord.Color.gold()
        )
        vote_msg = await interaction.followup.send(embed=vote_embed)
        
        votes = {}
        
        def check_vote(m):
            return (m.channel.id == game["channel"] and 
                   m.author.id in game["alive"] and
                   m.content.lower().startswith("vote"))
        
        vote_end = asyncio.get_event_loop().time() + game['vote_duration']
        while asyncio.get_event_loop().time() < vote_end and lobby_id in self.active_lobbies:
            try:
                msg = await self.bot.wait_for('message', check=check_vote, timeout=max(0.1, vote_end - asyncio.get_event_loop().time()))
                if msg.mentions:
                    target = msg.mentions[0].id
                    if target in game["alive"]:
                        votes[msg.author.id] = target
                        await msg.add_reaction("✅")
            except asyncio.TimeoutError:
                break
        
        # Count votes
        if votes:
            vote_counts = {}
            for target in votes.values():
                vote_counts[target] = vote_counts.get(target, 0) + 1
            
            ejected = max(vote_counts, key=vote_counts.get)
            game["alive"].remove(ejected)
            game["dead"].append(ejected)
            
            was_killer = ejected == game["killer"]
            was_sheriff = ejected == game["sheriff"]
            
            result_embed = discord.Embed(
                title="📤 EJECTION RESULTS",
                description=f"**<@{ejected}> was ejected with {vote_counts[ejected]} votes!**\n\n"
                           f"They were: {'🔪 **THE KILLER!**' if was_killer else '👮 **THE SHERIFF!**' if was_sheriff else '😇 An innocent...'}",
                color=discord.Color.green() if was_killer else discord.Color.red()
            )
            await interaction.followup.send(embed=result_embed)
            
            if was_killer:
                win_embed = discord.Embed(
                    title="🎉 INNOCENTS WIN!",
                    description="**The killer has been caught!**\n\n**+400 PsyCoins to all innocents!**",
                    color=discord.Color.green()
                )
                await interaction.followup.send(embed=win_embed)
                del self.active_lobbies[lobby_id]
                return
        else:
            skip_embed = discord.Embed(
                title="⏭️ VOTE SKIPPED",
                description="No votes cast. The game continues...",
                color=discord.Color.orange()
            )
            await interaction.followup.send(embed=skip_embed)
    
    @app_commands.command(name="murderkill", description="[Sheriff only] Kill a suspect in Murder Mystery")
    async def murder_kill_command(self, interaction: discord.Interaction, target: discord.Member):
        """Sheriff kill command"""
        # Find active game
        lobby_id = f"murder_{interaction.channel.id}"
        game = self.active_lobbies.get(lobby_id)
        
        if not game:
            await interaction.response.send_message("❌ No Murder Mystery game active!", ephemeral=True)
            return
        
        if interaction.user.id != game["sheriff"]:
            await interaction.response.send_message("❌ Only the Sheriff can use this!", ephemeral=True)
            return
        
        if interaction.user.id not in game["alive"]:
            await interaction.response.send_message("❌ You are dead!", ephemeral=True)
            return
        
        if target.id not in game["alive"]:
            await interaction.response.send_message("❌ That player is not alive!", ephemeral=True)
            return
        
        # Sheriff kills
        game["alive"].remove(target.id)
        game["dead"].append(target.id)
        
        if target.id == game["killer"]:
            # Sheriff killed the killer - INNOCENTS WIN!
            await interaction.response.send_message(f"✅ You killed <@{target.id}>!", ephemeral=True)
            
            win_embed = discord.Embed(
                title="🎉 SHERIFF VICTORY!",
                description=f"**<@{interaction.user.id}> (Sheriff) killed the killer!**\n\n"
                           f"The killer was: <@{target.id}>\n\n"
                           "**+500 PsyCoins to Sheriff!**\n"
                           "**+300 PsyCoins to all innocents!**",
                color=discord.Color.gold()
            )
            await interaction.followup.send(embed=win_embed)
            del self.active_lobbies[lobby_id]
        else:
            # Sheriff killed an innocent - DEATH ROUND!
            await interaction.response.send_message(f"❌ You killed an innocent! DEATH ROUND activated!", ephemeral=True)
            
            game["death_round"] = True
            
            death_round_embed = discord.Embed(
                title="☠️ DEATH ROUND ACTIVATED!",
                description=f"**<@{interaction.user.id}> (Sheriff) killed innocent <@{target.id}>!**\n\n"
                           "⚠️ **DEATH ROUND:**\n"
                           "• One more round to find the killer\n"
                           "• If killer not found = KILLER WINS!\n"
                           "• Vote wisely!",
                color=discord.Color.dark_red()
            )
            await interaction.followup.send(embed=death_round_embed)
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Listen for task completions and killer actions - NOW WITH INTERACTIVE TASKS!"""
        if message.author.bot:
            return
        
        # Check if in active murder mystery game
        lobby_id = f"murder_{message.channel.id}"
        game = self.active_lobbies.get(lobby_id)
        
        if not game or not game.get("started"):
            return
        
        player_id = message.author.id
        
        # Killer kill command
        if message.content.lower().startswith("kill "):
            if player_id != game["killer"]:
                return
            
            if player_id not in game["alive"]:
                return
            
            if not message.mentions:
                await message.reply("❌ Mention someone to kill! `kill @user`", delete_after=5)
                return
            
            target = message.mentions[0]
            
            if target.id not in game["alive"]:
                await message.reply("❌ That player is not alive!", delete_after=5)
                return
            
            if target.id == player_id:
                await message.reply("❌ You can't kill yourself!", delete_after=5)
                return
            
            # Set kill target for this round
            game["killer_kills"][game["round"]] = target.id
            await message.delete()
            
            try:
                killer_user = await self.bot.fetch_user(player_id)
                await killer_user.send(f"🔪 **Target locked:** {target.display_name}\nThey will be eliminated at round end.")
            except:
                pass
            return
        
        # Interactive task validation
        if player_id not in game["alive"]:
            return
        
        if player_id == game["killer"]:
            return  # Killers don't do real tasks
        
        if player_id not in game["active_tasks"]:
            return  # No active task
        
        if game["tasks_done"].get(player_id, 0) >= 5:
            return  # Already completed all tasks
        
        task_data = game["active_tasks"][player_id]
        response = message.content.strip()
        is_correct = False
        
        # Validate based on task type
        if task_data["type"] == "emoji_find":
            try:
                position = int(response)
                if 1 <= position <= 10:
                    target_emoji = task_data["target"]
                    if task_data["options"][position - 1] == target_emoji:
                        is_correct = True
            except:
                pass
        
        elif task_data["type"] == "word_memory":
            # Check if all words are in response
            words = task_data["words"]
            response_lower = response.lower()
            if all(word in response_lower for word in words):
                is_correct = True
        
        elif task_data["type"] == "math":
            try:
                if int(response) == task_data["answer"]:
                    is_correct = True
            except:
                pass
        
        elif task_data["type"] == "sort":
            try:
                # Parse response numbers
                user_nums = [int(n) for n in response.split()]
                if user_nums == task_data["answer"]:
                    is_correct = True
            except:
                pass
        
        elif task_data["type"] == "sequence":
            if response.upper() == task_data["sequence"]:
                is_correct = True
        
        elif task_data["type"] == "unscramble":
            if response.upper() == task_data["word"]:
                is_correct = True
        
        elif task_data["type"] == "pattern":
            if response.upper() == task_data["answer"].upper():
                is_correct = True
        
        elif task_data["type"] == "color":
            if response.lower() == task_data["color"]:
                is_correct = True
        
        # Handle result
        if is_correct:
            game["tasks_done"][player_id] = game["tasks_done"].get(player_id, 0) + 1
            del game["active_tasks"][player_id]  # Remove completed task
            
            tasks_done = game["tasks_done"][player_id]
            total_tasks = sum(game["tasks_done"].values())
            required_tasks = len(game["tasks_done"]) * game["tasks_required"]
            
            await message.reply(
                f"✅ **Task complete!** ({tasks_done}/5)\n"
                f"🎯 Team progress: {total_tasks}/{required_tasks}",
                delete_after=10
            )
            await message.add_reaction("✅")
            
            # Check if all tasks done (instant win)
            if total_tasks >= required_tasks:
                win_embed = discord.Embed(
                    title="🎉 INNOCENTS WIN!",
                    description=f"**All tasks completed!**\n\n"
                               f"The killer was: <@{game['killer']}>\n"
                               f"The sheriff was: <@{game['sheriff']}>\n\n"
                               "**+400 PsyCoins to all innocents!**",
                    color=discord.Color.green()
                )
                channel = self.bot.get_channel(game["channel"])
                if channel:
                    await channel.send(embed=win_embed)
                del self.active_lobbies[lobby_id]
        else:
            await message.add_reaction("❌")

async def setup(bot):
    await bot.add_cog(MultiplayerGames(bot))
