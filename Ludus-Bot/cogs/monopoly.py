import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import random
from typing import Dict, List, Optional, Literal
import json
import os

try:
    from .tcg import manager as tcg_manager
    from .psyvrse_tcg import CARD_DATABASE
except Exception:
    tcg_manager = None
    CARD_DATABASE = {}

class MonopolyGame:
    """Complete Monopoly game state management"""
    
    def __init__(self, channel_id, players):
        self.channel_id = channel_id
        self.players = players  # List of player IDs
        self.current_turn = 0
        self.round_num = 1
        self.active = True
        
        # Player data
        self.player_money = {pid: 1500 for pid in players}
        self.player_position = {pid: 0 for pid in players}
        self.player_in_jail = {pid: False for pid in players}
        self.player_jail_turns = {pid: 0 for pid in players}
        self.player_get_out_jail_cards = {pid: 0 for pid in players}
        self.player_bankrupt = {pid: False for pid in players}
        self.player_properties = {pid: [] for pid in players}
        self.player_pieces = {}  # pid -> emoji piece
        
        # Property ownership
        self.property_owners = {}  # property_id -> player_id
        self.property_houses = {}  # property_id -> house count (0-5, 5=hotel)
        self.property_mortgaged = {}  # property_id -> bool
        
        # Game state
        self.last_roll = None
        self.doubles_count = 0
        self.trade_offers = []
        self.auction_active = None
        
        # BANK POOL - Collects taxes and loans
        self.bank_pool = 0
        
        # Initialize properties
        self.properties = self._init_properties()
        self.chance_cards = self._init_chance_cards()
        self.community_chest_cards = self._init_community_chest_cards()
        random.shuffle(self.chance_cards)
        random.shuffle(self.community_chest_cards)
    
    def _init_properties(self):
        """Initialize all 28 properties + railroads + utilities"""
        return {
            # Brown properties
            1: {"name": "Mediterranean Avenue", "color": "brown", "price": 60, "rent": [2, 10, 30, 90, 160, 250], "house_cost": 50},
            3: {"name": "Baltic Avenue", "color": "brown", "price": 60, "rent": [4, 20, 60, 180, 320, 450], "house_cost": 50},
            
            # Light Blue
            6: {"name": "Oriental Avenue", "color": "lightblue", "price": 100, "rent": [6, 30, 90, 270, 400, 550], "house_cost": 50},
            8: {"name": "Vermont Avenue", "color": "lightblue", "price": 100, "rent": [6, 30, 90, 270, 400, 550], "house_cost": 50},
            9: {"name": "Connecticut Avenue", "color": "lightblue", "price": 120, "rent": [8, 40, 100, 300, 450, 600], "house_cost": 50},
            
            # Pink
            11: {"name": "St. Charles Place", "color": "pink", "price": 140, "rent": [10, 50, 150, 450, 625, 750], "house_cost": 100},
            13: {"name": "States Avenue", "color": "pink", "price": 140, "rent": [10, 50, 150, 450, 625, 750], "house_cost": 100},
            14: {"name": "Virginia Avenue", "color": "pink", "price": 160, "rent": [12, 60, 180, 500, 700, 900], "house_cost": 100},
            
            # Orange
            16: {"name": "St. James Place", "color": "orange", "price": 180, "rent": [14, 70, 200, 550, 750, 950], "house_cost": 100},
            18: {"name": "Tennessee Avenue", "color": "orange", "price": 180, "rent": [14, 70, 200, 550, 750, 950], "house_cost": 100},
            19: {"name": "New York Avenue", "color": "orange", "price": 200, "rent": [16, 80, 220, 600, 800, 1000], "house_cost": 100},
            
            # Red
            21: {"name": "Kentucky Avenue", "color": "red", "price": 220, "rent": [18, 90, 250, 700, 875, 1050], "house_cost": 150},
            23: {"name": "Indiana Avenue", "color": "red", "price": 220, "rent": [18, 90, 250, 700, 875, 1050], "house_cost": 150},
            24: {"name": "Illinois Avenue", "color": "red", "price": 240, "rent": [20, 100, 300, 750, 925, 1100], "house_cost": 150},
            
            # Yellow
            26: {"name": "Atlantic Avenue", "color": "yellow", "price": 260, "rent": [22, 110, 330, 800, 975, 1150], "house_cost": 150},
            27: {"name": "Ventnor Avenue", "color": "yellow", "price": 260, "rent": [22, 110, 330, 800, 975, 1150], "house_cost": 150},
            29: {"name": "Marvin Gardens", "color": "yellow", "price": 280, "rent": [24, 120, 360, 850, 1025, 1200], "house_cost": 150},
            
            # Green
            31: {"name": "Pacific Avenue", "color": "green", "price": 300, "rent": [26, 130, 390, 900, 1100, 1275], "house_cost": 200},
            32: {"name": "North Carolina Avenue", "color": "green", "price": 300, "rent": [26, 130, 390, 900, 1100, 1275], "house_cost": 200},
            34: {"name": "Pennsylvania Avenue", "color": "green", "price": 320, "rent": [28, 150, 450, 1000, 1200, 1400], "house_cost": 200},
            
            # Dark Blue
            37: {"name": "Park Place", "color": "darkblue", "price": 350, "rent": [35, 175, 500, 1100, 1300, 1500], "house_cost": 200},
            39: {"name": "Boardwalk", "color": "darkblue", "price": 400, "rent": [50, 200, 600, 1400, 1700, 2000], "house_cost": 200},
            
            # Railroads
            5: {"name": "Reading Railroad", "type": "railroad", "price": 200, "rent": [25, 50, 100, 200]},
            15: {"name": "Pennsylvania Railroad", "type": "railroad", "price": 200, "rent": [25, 50, 100, 200]},
            25: {"name": "B&O Railroad", "type": "railroad", "price": 200, "rent": [25, 50, 100, 200]},
            35: {"name": "Short Line Railroad", "type": "railroad", "price": 200, "rent": [25, 50, 100, 200]},
            
            # Utilities
            12: {"name": "Electric Company", "type": "utility", "price": 150},
            28: {"name": "Water Works", "type": "utility", "price": 150},
        }
    
    def _init_chance_cards(self):
        """Initialize MEGA Chance cards (? spaces)"""
        return [
            # Movement cards
            {"type": "move", "target": 0, "text": "🎯 Advance to GO! Collect $200"},
            {"type": "move", "target": 24, "text": "🎯 Advance to Illinois Avenue"},
            {"type": "move", "target": 11, "text": "🎯 Advance to St. Charles Place"},
            {"type": "move_nearest", "target_type": "railroad", "text": "🚂 Advance to nearest Railroad, pay 2x rent"},
            {"type": "move_nearest", "target_type": "utility", "text": "💡 Advance to nearest Utility"},
            {"type": "move", "target": -3, "relative": True, "text": "⬅️ Go Back 3 Spaces"},
            {"type": "move", "target": 5, "text": "🚂 Take a trip to Reading Railroad"},
            
            # Jail cards
            {"type": "jail", "text": "👮 Go to Jail! Do not pass GO, do not collect $200"},
            {"type": "jail_free", "text": "🔑 Get Out of Jail FREE card! (Keep this)"},
            
            # Money cards
            {"type": "money", "amount": 50, "text": "💰 Bank dividend! Collect $50"},
            {"type": "money", "amount": 150, "text": "💰 Building loan matures! Collect $150"},
            {"type": "money", "amount": -15, "text": "🚔 Speeding fine! Pay $15"},
            
            # Tax/Loan cards
            {"type": "tax", "amount": 50, "text": "💸 Property tax! Pay $50 to BANK"},
            {"type": "tax", "amount": 100, "text": "💸 Luxury tax! Pay $100 to BANK"},
            {"type": "loan", "amount": 200, "text": "🏦 Take out a $200 loan from BANK (pay back when you land on Bank)"},
            {"type": "tax_refund", "text": "💵 TAX REFUND! Get $200 from BANK POOL"},
            {"type": "tax_evasion", "text": "🕶️ TAX EVASION! Exempt from next tax"},
            
            # Special cards
            {"type": "pay_all", "amount": 50, "text": "🎩 Chairman of the Board! Pay each player $50"},
            {"type": "collect_all", "amount": 30, "text": "🎂 It's your birthday! Collect $30 from each player"},
            {"type": "repairs", "house": 25, "hotel": 100, "text": "🔧 General repairs: $25 per house, $100 per hotel to BANK"},
            
            # RARE CARDS (Very powerful)
            {"type": "double_money", "text": "💎 JACKPOT! Double your current money! (RARE)"},
            {"type": "steal_property", "text": "🎰 MEGA WIN! Steal a random property from another player! (RARE)"},
            {"type": "free_property", "text": "🏆 FREE PROPERTY! Get any unowned property for FREE! (RARE)"},
        ]
    
    def _init_community_chest_cards(self):
        """Initialize MEGA Community Chest cards (📦 spaces)"""
        return [
            # Movement
            {"type": "move", "target": 0, "text": "▶️ Advance to GO! Collect $200"},
            
            # Money gains
            {"type": "money", "amount": 200, "text": "💰 Bank error in your favor! Collect $200"},
            {"type": "money", "amount": 100, "text": "💰 Life insurance matures! Collect $100"},
            {"type": "money", "amount": 50, "text": "💰 Stock sale profit! Collect $50"},
            {"type": "money", "amount": 25, "text": "💰 Consultancy fee! Collect $25"},
            {"type": "money", "amount": 10, "text": "🏆 Beauty contest 2nd place! Collect $10"},
            {"type": "money", "amount": 100, "text": "💰 You inherit $100!"},
            {"type": "money", "amount": 20, "text": "💰 Holiday fund matures! Collect $20"},
            
            # Money losses
            {"type": "money", "amount": -50, "text": "💸 Doctor's fees! Pay $50"},
            {"type": "money", "amount": -100, "text": "💸 Hospital fees! Pay $100"},
            {"type": "money", "amount": -50, "text": "💸 School fees! Pay $50"},
            
            # Tax/Loan
            {"type": "tax", "amount": 75, "text": "💸 Income tax! Pay $75 to BANK"},
            {"type": "loan", "amount": 300, "text": "🏦 Emergency loan! Borrow $300 from BANK"},
            {"type": "tax_refund", "text": "💵 IRS ERROR! Collect $300 from BANK POOL"},
            
            # Jail
            {"type": "jail", "text": "👮 Go to Jail! Do not pass GO"},
            {"type": "jail_free", "text": "🔑 Get Out of Jail FREE card! (Keep this)"},
            
            # Special
            {"type": "collect_all", "amount": 50, "text": "🎭 Grand Opera Night! Collect $50 from each player"},
            {"type": "repairs", "house": 40, "hotel": 115, "text": "🔧 Street repairs: $40 per house, $115 per hotel to BANK"},
            
            # RARE CARDS
            {"type": "double_money", "text": "💎 LOTTERY WIN! Double your money! (RARE)"},
            {"type": "bank_robbery", "text": "🏴‍☠️ BANK HEIST! Steal entire BANK POOL! (RARE)"},
            {"type": "property_upgrade", "text": "🏗️ FREE UPGRADE! Add a house to one property for FREE! (RARE)"},
        ]
    
    def get_current_player(self):
        """Get current player ID"""
        active_players = [pid for pid in self.players if not self.player_bankrupt[pid]]
        if not active_players:
            return None
        return active_players[self.current_turn % len(active_players)]
    
    def next_turn(self):
        """Move to next player's turn"""
        active_players = [pid for pid in self.players if not self.player_bankrupt[pid]]
        if len(active_players) <= 1:
            self.active = False
            return
        
        self.current_turn += 1
        if self.current_turn % len(active_players) == 0:
            self.round_num += 1
        self.doubles_count = 0

class Monopoly(commands.Cog):
    """Full Monopoly board game with all classic mechanics"""
    
    def __init__(self, bot):
        self.bot = bot
        self.active_games = {}  # channel_id -> MonopolyGame
        
        # Full board layout (0-39)
        self.board_layout = [
            "GO! 💰", "Mediterranean Ave", "Community Chest 📦", "Baltic Ave", "Income Tax 💸",
            "Reading Railroad", "Oriental Ave", "Chance ❓", "Vermont Ave", "Connecticut Ave",
            "Jail/Visiting 🔒", "St. Charles Place", "Electric Company", "States Ave", "Virginia Ave",
            "Pennsylvania RR", "St. James Place", "Community Chest 📦", "Tennessee Ave", "New York Ave",
            "BANK 🏦", "Kentucky Ave", "Chance ❓", "Indiana Ave", "Illinois Ave",
            "B&O Railroad", "Atlantic Ave", "Ventnor Ave", "Water Works", "Marvin Gardens",
            "GO TO JAIL 👮", "Pacific Ave", "North Carolina Ave", "Community Chest 📦", "Pennsylvania Ave",
            "Short Line RR", "Chance ❓", "Park Place", "Luxury Tax 💸", "Boardwalk"
        ]
        
        # Space type emojis
        self.space_emojis = {
            "property": "🏠",
            "railroad": "🚂",
            "utility": "💡",
            "go": "▶️",
            "jail": "🔒",
            "parking": "🅿️",
            "chance": "❓",
            "chest": "📦",
            "tax": "💸",
            "gotojail": "👮"
        }
    
    @app_commands.command(name="monopoly", description="Play Monopoly board game")
    @app_commands.describe(
        action="What do you want to do?",
        user="User to view (for status action)"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="🎮 Start Game", value="start"),
        app_commands.Choice(name="🎲 Roll Dice", value="roll"),
        app_commands.Choice(name="🏠 Buy Property", value="buy"),
        app_commands.Choice(name="✅ End Turn", value="endturn"),
        app_commands.Choice(name="📊 View Status", value="status"),
        app_commands.Choice(name="🗺️ View Board", value="board"),
        app_commands.Choice(name="🏘️ My Properties", value="properties"),
        app_commands.Choice(name="🛑 End Game", value="end"),
    ])
    async def monopoly(self, interaction: discord.Interaction, action: str, user: Optional[discord.Member] = None):
        """Single Monopoly command with action choices"""
        
        if action == "start":
            await self.start_game(interaction)
        elif action == "roll":
            await self.roll_dice(interaction)
        elif action == "buy":
            await self.buy_property(interaction)
        elif action == "endturn":
            await self.end_turn(interaction)
        elif action == "status":
            await self.view_status(interaction, user)
        elif action == "board":
            await self.view_board(interaction)
        elif action == "properties":
            await self.view_properties(interaction)
        elif action == "end":
            await self.force_end_game(interaction)
    
    @app_commands.command(name="monopolyboard", description="Preview the Monopoly board layout")
    async def monopolyboard_slash(self, interaction: discord.Interaction):
        """Show a preview of the Monopoly board without starting a game"""
        try:
            await self._show_board_preview(interaction)
        except Exception as e:
            print(f"Error in monopolyboard: {e}")
            await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)
    
    @commands.command(name="monopolyboard", aliases=["mboard", "monopolyhelp"])
    async def monopolyboard_prefix(self, ctx: commands.Context):
        """Show a preview of the Monopoly board without starting a game"""
        await self._show_board_preview(ctx, is_slash=False)
    
    async def _show_board_preview(self, ctx_or_interaction, is_slash=True):
        """Helper function to show board preview"""
        # Create a demo board embed
        embed = discord.Embed(
            title="🎲 MONOPOLY BOARD PREVIEW",
            description="**Classic Monopoly Board Layout**\n\n"
                       "The board has 40 spaces arranged in a square:\n"
                       "• **4 Corners:** <:GO:1442963964819538062> GO, <:Jail:1442965311518150676> Jail, <:Free_Parking:1442963738062880879> Free Parking/Bank, <:GoToJail:1442965655405203529> Go To Jail\n"
                       "• **22 Properties** in 8 color groups (can build 🏠🏨)\n"
                       "• **4 Railroads** <:Train:1442963532827201546> (rent multiplies)\n"
                       "• **2 Utilities** ⚡💧 (rent based on dice)\n"
                       "• **2 Tax Spaces** 💸 (pay to Bank Pool)\n"
                       "• **3 Chance** ❓ and **3 Community Chest** 📦 spaces\n\n"
                       "When you play, you'll pick a piece (🎩🚗🐕🚢 etc) and it will move around the board!",
            color=discord.Color.gold()
        )
        
        # Property groups
        embed.add_field(
            name="🎨 Color Groups",
            value="🟤 **Brown:** Mediterranean, Baltic\n"
                  "🔵 **Light Blue:** Oriental, Vermont, Connecticut\n"
                  "💗 **Pink:** St. Charles, States, Virginia\n"
                  "🟠 **Orange:** St. James, Tennessee, New York\n"
                  "🔴 **Red:** Kentucky, Indiana, Illinois\n"
                  "🟡 **Yellow:** Atlantic, Ventnor, Marvin Gardens\n"
                  "🟢 **Green:** Pacific, N. Carolina, Pennsylvania\n"
                  "🔷 **Dark Blue:** Park Place, Boardwalk",
            inline=False
        )
        
        embed.add_field(
            name="💰 Special Mechanics",
            value="🏦 **Bank Pool:** All taxes go here. Land on <:Free_Parking:1442963738062880879> with doubles to win!\n"
                  "🎴 **Cards:** 45 total cards including RARE effects (💎 Double Money, 🏴‍☠️ Bank Robbery)\n"
                  "🏠 **Building:** Build houses → hotels for higher rent\n"
                  "🔒 **Jail:** 3 ways out: doubles, Get Out card, or $50 fine",
            inline=False
        )
        
        # Visual board layout (simplified for Discord limits)
        board_visual = (
            "```\n"
            "       BANK-21-22-23-24-25-26-27-28-29-30-JAIL\n"
            "    20 |                                        |\n"
            "    19 |         🎲 MONOPOLY BOARD 🎲          | 31\n"
            "    18 |                                        | 32\n"
            "    17 |    Players move clockwise around       | 33\n"
            "    16 |    Pick: 🎩🚗🐕🚢⚓🎸🦠🧲          | 34\n"
            "    15 |    Roll dice, buy properties,          | 35\n"
            "    14 |    build houses & hotels!              | 36\n"
            "    13 |                                        | 37\n"
            "    12 |                                        | 38\n"
            "       |                                        |\n"
            "       JAIL-10-09-08-07-06-05-04-03-02-01-GO💰\n"
            "```"
        )
        
        embed.add_field(
            name="📋 The Monopoly Board:",
            value=board_visual,
            inline=False
        )
        
        embed.set_footer(text="Use /monopoly start or L!monopoly start to begin a game!")
        
        try:
            if is_slash:
                await ctx_or_interaction.response.send_message(embed=embed)
            else:
                await ctx_or_interaction.send(embed=embed)
        except Exception as e:
            print(f"Error sending monopoly board: {e}")
            if is_slash and not ctx_or_interaction.response.is_done():
                await ctx_or_interaction.response.send_message("❌ Error displaying board", ephemeral=True)

    
    async def start_game(self, interaction: discord.Interaction):
        """Start a Monopoly game! 2-6 players"""
        
        if interaction.channel_id in self.active_games:
            await interaction.response.send_message("❌ A Monopoly game is already running here!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        # Lobby phase
        embed = discord.Embed(
            title="🎩 MONOPOLY GAME!",
            description=f"**{interaction.user.mention} wants to play Monopoly!**\n\n"
                       "🏠 **Classic Features:**\n"
                       "• 28 properties + railroads + utilities\n"
                       "• Build houses & hotels\n"
                       "• Chance & Community Chest cards\n"
                       "• Jail, auctions, trading, mortgages\n"
                       "• Rent collection & bankruptcy\n"
                       "• Doubles & passing GO ($200)\n\n"
                       "💰 **Winner gets their Monopoly money × 0.5 as PsyCoins!**\n\n"
                       f"**Players (1/6):**\n• {interaction.user.mention}\n\n"
                       "React ✅ to join (60 seconds) • Host ▶️ to start (min 2 players)",
            color=discord.Color.green()
        )
        
        msg = await interaction.followup.send(embed=embed)
        await msg.add_reaction("✅")
        await msg.add_reaction("▶️")
        
        players = [interaction.user.id]
        
        def check_reaction(reaction, user):
            return (reaction.message.id == msg.id and 
                   not user.bot and 
                   str(reaction.emoji) in ["✅", "▶️"])
        
        start_game = False
        try:
            while not start_game:
                reaction, user = await self.bot.wait_for('reaction_add', check=check_reaction, timeout=60.0)
                
                if str(reaction.emoji) == "✅" and user.id not in players:
                    if len(players) < 6:
                        players.append(user.id)
                        player_list = "\n".join([f"• <@{pid}>" for pid in players])
                        embed.description = (f"**{interaction.user.mention} wants to play Monopoly!**\n\n"
                                           "🏠 **Classic Features:**\n"
                                           "• 28 properties + railroads + utilities\n"
                                           "• Build houses & hotels\n"
                                           "• Chance & Community Chest cards\n"
                                           "• Jail, auctions, trading, mortgages\n"
                                           "• Rent collection & bankruptcy\n"
                                           "• Doubles & passing GO ($200)\n\n"
                                           "💰 **Winner gets their Monopoly money × 0.5 as PsyCoins!**\n\n"
                                           f"**Players ({len(players)}/6):**\n{player_list}\n\n"
                                           "React ✅ to join • Host ▶️ to start (min 2 players)")
                        await msg.edit(embed=embed)
                
                elif str(reaction.emoji) == "▶️" and user.id == interaction.user.id:
                    if len(players) >= 2:
                        start_game = True
                    else:
                        await interaction.channel.send("❌ Need at least 2 players!", delete_after=5)
        
        except asyncio.TimeoutError:
            if len(players) >= 2:
                start_game = True
            else:
                await interaction.channel.send("❌ Game cancelled - not enough players!")
                return
        
        # Create game
        game = MonopolyGame(interaction.channel_id, players)
        self.active_games[interaction.channel_id] = game
        
        # Piece selection phase
        available_pieces = ["🎩", "🚗", "🐕", "🚢", "🎸", "👢", "🐈", "🦖", "🏎️", "🚀", "🎪", "⚓"]
        piece_select_embed = discord.Embed(
            title="🎭 SELECT YOUR PIECE!",
            description="Each player, choose your game piece by reacting:\n\n"
                       "🎩 Top Hat • 🚗 Car • 🐕 Dog • 🚢 Ship\n"
                       "🎸 Guitar • 👢 Boot • 🐈 Cat • 🦖 Dino\n"
                       "🏎️ Race Car • 🚀 Rocket • 🎪 Tent • ⚓ Anchor\n\n"
                       f"**Waiting for pieces:**\n" + "\n".join([f"• <@{pid}>" for pid in players]),
            color=discord.Color.purple()
        )
        
        piece_msg = await interaction.channel.send(embed=piece_select_embed)
        for piece in available_pieces:
            await piece_msg.add_reaction(piece)
        
        # Wait for each player to pick
        picked_pieces = {}
        
        def check_piece(reaction, user):
            return (reaction.message.id == piece_msg.id and 
                   user.id in players and 
                   user.id not in picked_pieces and
                   str(reaction.emoji) in available_pieces and
                   str(reaction.emoji) not in picked_pieces.values())
        
        try:
            while len(picked_pieces) < len(players):
                reaction, user = await self.bot.wait_for('reaction_add', check=check_piece, timeout=45.0)
                picked_pieces[user.id] = str(reaction.emoji)
                available_pieces.remove(str(reaction.emoji))
                
                # Update embed
                waiting = [f"• <@{pid}>" for pid in players if pid not in picked_pieces]
                chosen = [f"• <@{pid}> → {picked_pieces[pid]}" for pid in picked_pieces]
                
                piece_select_embed.description = (
                    "Each player, choose your game piece by reacting:\n\n"
                    "🎩 Top Hat • 🚗 Car • 🐕 Dog • 🚢 Ship\n"
                    "🎸 Guitar • 👢 Boot • 🐈 Cat • 🦖 Dino\n"
                    "🏎️ Race Car • 🚀 Rocket • 🎪 Tent • ⚓ Anchor\n\n"
                    f"**Chosen pieces:**\n" + "\n".join(chosen) +
                    ("\n\n**Waiting for:**\n" + "\n".join(waiting) if waiting else "")
                )
                await piece_msg.edit(embed=piece_select_embed)
        
        except asyncio.TimeoutError:
            # Auto-assign remaining pieces
            for pid in players:
                if pid not in picked_pieces:
                    picked_pieces[pid] = available_pieces.pop(0)
        
        # Assign pieces to game
        game.player_pieces = picked_pieces
        
        # Show starting board
        board_embed = await self.create_board_embed(game)
        await interaction.channel.send(embed=board_embed)
        
        player_mentions = ", ".join([f"<@{pid}>" for pid in players])
        start_embed = discord.Embed(
            title="🎩 MONOPOLY - GAME START!",
            description=f"**Players:** {player_mentions}\n\n"
                       f"**Starting money:** $1,500 each\n"
                       f"**Turn order:** {' → '.join([f'<@{pid}>' for pid in players])}\n\n"
                       "**Commands:**\n"
                       "`/monopoly roll` - Roll dice\n"
                       "`/monopoly buy` - Buy property\n"
                       "`/monopoly build <property>` - Build house/hotel\n"
                       "`/monopoly mortgage <property>` - Mortgage property\n"
                       "`/monopoly trade @user` - Start trade\n"
                       "`/monopoly endturn` - End your turn\n"
                       "`/monopoly status` - View your assets\n"
                       "`/monopoly board` - View board state\n\n"
                       f"**<@{game.get_current_player()}>'s turn!** Use `/monopoly roll` to start!",
            color=discord.Color.gold()
        )
        await interaction.channel.send(embed=start_embed)
    
    def generate_board_display(self, game: MonopolyGame, highlight_player: int = None) -> str:
        """Generate visual board with player positions"""
        # Create board sections
        top_row = list(range(20, 31))  # Free Parking to Go To Jail
        right_col = list(range(11, 20))  # Between corners
        bottom_row = list(range(0, 11))  # GO to Jail
        left_col = list(range(31, 40))  # Between corners
        
        board_lines = []
        
        # Top row (reversed for display)
        top_line = "```"
        for pos in reversed(top_row):
            players_here = [p for p in game.players if game.player_position[p] == pos and not game.player_bankrupt[p]]
            if players_here:
                top_line += f"[{len(players_here)}]"
            else:
                top_line += f"[{pos:2d}]"
        board_lines.append(top_line)
        
        # Middle rows (left and right columns)
        for i in range(9):
            left_pos = left_col[i] if i < len(left_col) else None
            right_pos = right_col[8-i] if i < len(right_col) else None
            
            line = ""
            
            # Left column
            if left_pos is not None:
                players_here = [p for p in game.players if game.player_position[p] == left_pos and not game.player_bankrupt[p]]
                if players_here:
                    line += f"[{len(players_here)}]"
                else:
                    line += f"[{left_pos:2d}]"
            else:
                line += "    "
            
            # Middle spacing
            line += " " * (len(top_row) * 4 - 8)
            
            # Right column
            if right_pos is not None:
                players_here = [p for p in game.players if game.player_position[p] == right_pos and not game.player_bankrupt[p]]
                if players_here:
                    line += f"[{len(players_here)}]"
                else:
                    line += f"[{right_pos:2d}]"
            
            board_lines.append(line)
        
        # Bottom row
        bottom_line = ""
        for pos in bottom_row:
            players_here = [p for p in game.players if game.player_position[p] == pos and not game.player_bankrupt[p]]
            if players_here:
                bottom_line += f"[{len(players_here)}]"
            else:
                bottom_line += f"[{pos:2d}]"
        board_lines.append(bottom_line + "```")
        
        return "\n".join(board_lines)
    
    def generate_player_summary(self, game: MonopolyGame) -> str:
        """Generate player position and status summary"""
        lines = []
        for player_id in game.players:
            if game.player_bankrupt[player_id]:
                continue
            
            pos = game.player_position[player_id]
            space_name = self.board_layout[pos]
            money = game.player_money[player_id]
            props = len(game.player_properties[player_id])
            
            status = ""
            if game.player_in_jail[player_id]:
                status = "🔒 JAIL"
            elif pos == 0:
                status = "▶️ GO"
            elif pos == 10:
                status = "👁️ Visiting"
            elif pos == 20:
                status = "🅿️ Parking"
            elif pos == 30:
                status = "👮 Go to Jail"
            else:
                status = f"📍 {space_name}"
            
            is_current = (player_id == game.get_current_player())
            turn_marker = "👉 " if is_current else "   "
            
            lines.append(f"{turn_marker}<@{player_id}> | ${money:,} | {props} props | {status}")
        
        return "\n".join(lines)

    async def roll_dice(self, interaction: discord.Interaction):
        """Roll the dice and move"""
        game = self.active_games.get(interaction.channel_id)
        if not game or not game.active:
            await interaction.response.send_message("❌ No active Monopoly game!", ephemeral=True)
            return
        
        if interaction.user.id != game.get_current_player():
            await interaction.response.send_message("❌ Not your turn!", ephemeral=True)
            return
        
        await interaction.response.defer()
        player_id = interaction.user.id
        
        # Check if in jail
        if game.player_in_jail[player_id]:
            await self.handle_jail_turn(interaction, game, player_id)
            return
        
        # Roll dice
        die1 = random.randint(1, 6)
        die2 = random.randint(1, 6)
        total = die1 + die2
        is_doubles = die1 == die2
        
        game.last_roll = (die1, die2)
        
        if is_doubles:
            game.doubles_count += 1
            if game.doubles_count == 3:
                # Go to jail on 3rd double
                game.player_position[player_id] = 10
                game.player_in_jail[player_id] = True
                game.player_jail_turns[player_id] = 0
                game.doubles_count = 0
                
                # Show board with pieces
                board_embed = await self.create_board_embed(game)
                
                embed = discord.Embed(
                    title="🎲 MONOPOLY - THREE DOUBLES!",
                    description=f"**{interaction.user.mention} rolled {die1} + {die2} = {total}**\n<:GoToJail:1442965655405203529> **Three doubles! Go to Jail!**",
                    color=discord.Color.red()
                )
                
                await interaction.followup.send(embed=embed)
                await interaction.channel.send(embed=board_embed)
                
                game.next_turn()
                await self.announce_next_turn(interaction.channel, game)
                return
        
        # Move player
        old_pos = game.player_position[player_id]
        new_pos = (old_pos + total) % 40
        passed_go = new_pos < old_pos
        game.player_position[player_id] = new_pos
        
        # Get space info
        space_name = self.board_layout[new_pos]
        
        # Handle passing GO
        if passed_go:
            game.player_money[player_id] += 200
        
        # Create roll result embed
        doubles_text = " 🎲 **DOUBLES!**" if is_doubles else ""
        embed = discord.Embed(
            title=f"🎲 MONOPOLY - Roll Result",
            description=f"**{interaction.user.mention} rolled {die1} + {die2} = {total}**{doubles_text}\n"
                       f"📍 **Landed on: {space_name}** (Space {new_pos})",
            color=discord.Color.green() if is_doubles else discord.Color.blue()
        )
        
        if passed_go:
            embed.description += f"\n💰 **Passed GO! +$200** (Balance: ${game.player_money[player_id]:,})"
        
        # Show visual board with pieces
        board_embed = await self.create_board_embed(game)
        await interaction.followup.send(embed=embed)
        await interaction.channel.send(embed=board_embed)
        
        # Handle landing on space (but DON'T end turn yet)
        await self.handle_space_landing(interaction.channel, game, player_id, new_pos)
        
        # IMPORTANT: Only end turn if NOT doubles and NOT on a buyable property
        prop = game.properties.get(new_pos)
        can_buy = prop and new_pos not in game.property_owners
        
        if is_doubles:
            # Rolled doubles - can roll again
            await interaction.channel.send(f"**{interaction.user.mention}, you rolled doubles!**\n"
                                          f"• Roll again: `/monopoly roll`\n"
                                          f"• End turn: `/monopoly endturn`" +
                                          (f"\n• Buy property: `/monopoly buy`" if can_buy else ""))
        elif can_buy:
            # On buyable property - give option to buy before ending turn
            await interaction.channel.send(f"**{interaction.user.mention}**, you can:\n"
                                          f"• Buy this property: `/monopoly buy`\n"
                                          f"• End turn: `/monopoly endturn`")
        else:
            # Auto-end turn if nothing to do
            game.next_turn()
            await self.announce_next_turn(interaction.channel, game)
    
    async def handle_space_landing(self, channel, game, player_id, position):
        """Handle landing on a space with MEGA features"""
        # Check if it's a property
        if position in game.properties:
            prop = game.properties[position]
            owner = game.property_owners.get(position)
            
            if owner is None:
                # Unowned property - offer to buy
                embed = discord.Embed(
                    title=f"🏠 {prop['name']}",
                    description=f"**Price:** ${prop['price']:,}\n"
                               f"**Rent:** ${prop['rent'][0]:,}\n\n"
                               f"Use `/monopoly buy` to purchase or pass",
                    color=discord.Color.blue()
                )
                await channel.send(f"<@{player_id}>", embed=embed)
            
            elif owner != player_id and not game.property_mortgaged.get(position, False):
                # Pay rent
                rent = self.calculate_rent(game, position, owner)
                if game.player_money[player_id] >= rent:
                    game.player_money[player_id] -= rent
                    game.player_money[owner] += rent
                    await channel.send(f"💸 **<@{player_id}> paid ${rent:,} rent to <@{owner}>**")
                else:
                    await channel.send(f"❌ **<@{player_id}> cannot afford ${rent:,} rent! Bankruptcy!**")
                    await self.handle_bankruptcy(channel, game, player_id, owner)
        
        # Special spaces
        elif position == 0:
            # GO!
            await channel.send(f"<:GO:1442963964819538062> **Landed on GO! <@{player_id}> collects $200!**")
        
        elif position == 2 or position == 17 or position == 33:
            # Community Chest
            await self.draw_community_chest(channel, game, player_id)
        
        elif position == 7 or position == 22 or position == 36:
            # Chance
            await self.draw_chance(channel, game, player_id)
        
        elif position == 4:
            # Income Tax - Goes to BANK
            tax = 200
            game.player_money[player_id] -= tax
            game.bank_pool += tax
            await channel.send(f"💸 **Income Tax! <@{player_id}> pays $200 to BANK**\n🏦 Bank Pool: ${game.bank_pool:,}")
        
        elif position == 38:
            # Luxury Tax - Goes to BANK
            tax = 100
            game.player_money[player_id] -= tax
            game.bank_pool += tax
            await channel.send(f"💸 **Luxury Tax! <@{player_id}> pays $100 to BANK**\n🏦 Bank Pool: ${game.bank_pool:,}")
        
        elif position == 30:
            # Go To Jail
            game.player_position[player_id] = 10
            game.player_in_jail[player_id] = True
            game.player_jail_turns[player_id] = 0
            await channel.send(f"<:GoToJail:1442965655405203529> **GO TO JAIL! <@{player_id}> is sent directly to jail!**")
        
        elif position == 10:
            # Jail/Visiting
            if game.player_in_jail[player_id]:
                await channel.send(f"<:Jail:1442965311518150676> **<@{player_id}> is in JAIL!**")
            else:
                await channel.send(f"<:Jail:1442965311518150676> **Just Visiting Jail**")
        
        elif position == 20:
            # BANK - Special mechanic!
            if game.last_roll and game.last_roll[0] == game.last_roll[1]:
                # Rolled doubles - WIN THE BANK POOL!
                winnings = game.bank_pool
                game.player_money[player_id] += winnings
                game.bank_pool = 0
                await channel.send(f"<:Free_Parking:1442963738062880879> **BANK JACKPOT! <@{player_id}> rolled DOUBLES and wins ${winnings:,} from the Bank Pool!** 💰💰💰")
            else:
                await channel.send(f"<:Free_Parking:1442963738062880879> **Landed on BANK** (Bank Pool: ${game.bank_pool:,})\n"
                                  f"💡 Roll doubles next time to WIN the entire pool!")
    
    def calculate_rent(self, game, position, owner):
        """Calculate rent for a property"""
        prop = game.properties[position]
        
        # Railroad
        if prop.get("type") == "railroad":
            railroads_owned = sum(1 for pos in [5, 15, 25, 35] if game.property_owners.get(pos) == owner)
            return prop["rent"][railroads_owned - 1]
        
        # Utility
        if prop.get("type") == "utility":
            utilities_owned = sum(1 for pos in [12, 28] if game.property_owners.get(pos) == owner)
            if game.last_roll:
                dice_total = sum(game.last_roll)
                return dice_total * (4 if utilities_owned == 1 else 10)
            return 0
        
        # Regular property
        houses = game.property_houses.get(position, 0)
        return prop["rent"][houses]
    
    async def draw_chance(self, channel, game, player_id):
        """Draw a MEGA Chance card"""
        if not game.chance_cards:
            game.chance_cards = self._init_chance_cards()
            random.shuffle(game.chance_cards)
        
        card = game.chance_cards.pop(0)
        
        # Determine rarity
        is_rare = card["type"] in ["double_money", "steal_property", "free_property", "bank_robbery", "property_upgrade"]
        
        embed = discord.Embed(
            title="❓ CHANCE CARD" if not is_rare else "💎 RARE CHANCE CARD!",
            description=card['text'],
            color=discord.Color.gold() if is_rare else discord.Color.blue()
        )
        
        await channel.send(f"<@{player_id}>", embed=embed)
        await self.process_card(channel, game, player_id, card)
        
        # Don't return rare cards to deck
        if not is_rare:
            game.chance_cards.append(card)
    
    async def draw_community_chest(self, channel, game, player_id):
        """Draw a MEGA Community Chest card"""
        if not game.community_chest_cards:
            game.community_chest_cards = self._init_community_chest_cards()
            random.shuffle(game.community_chest_cards)
        
        card = game.community_chest_cards.pop(0)
        
        # Determine rarity
        is_rare = card["type"] in ["double_money", "steal_property", "free_property", "bank_robbery", "property_upgrade"]
        
        embed = discord.Embed(
            title="📦 COMMUNITY CHEST" if not is_rare else "💎 RARE COMMUNITY CHEST!",
            description=card['text'],
            color=discord.Color.gold() if is_rare else discord.Color.green()
        )
        
        await channel.send(f"<@{player_id}>", embed=embed)
        await self.process_card(channel, game, player_id, card)
        
        # Don't return rare cards to deck
        if not is_rare:
            game.community_chest_cards.append(card)
    
    async def process_card(self, channel, game, player_id, card):
        """Process a MEGA card action"""
        card_type = card["type"]
        
        # Basic money
        if card_type == "money":
            game.player_money[player_id] += card["amount"]
            if card["amount"] > 0:
                await channel.send(f"💰 <@{player_id}> gains ${abs(card['amount']):,}! (Balance: ${game.player_money[player_id]:,})")
            else:
                await channel.send(f"💸 <@{player_id}> pays ${abs(card['amount']):,}! (Balance: ${game.player_money[player_id]:,})")
        
        # Tax (goes to BANK POOL)
        elif card_type == "tax":
            tax = card["amount"]
            game.player_money[player_id] -= tax
            game.bank_pool += tax
            await channel.send(f"💸 <@{player_id}> pays ${tax:,} to BANK! 🏦 Bank Pool: ${game.bank_pool:,}")
        
        # Loan (from BANK POOL)
        elif card_type == "loan":
            loan = card["amount"]
            game.player_money[player_id] += loan
            game.bank_pool -= loan
            await channel.send(f"🏦 <@{player_id}> borrows ${loan:,} from BANK! (Balance: ${game.player_money[player_id]:,})")
        
        # Tax Refund (from BANK POOL)
        elif card_type == "tax_refund":
            refund = min(game.bank_pool, 300)  # Max $300 or whatever is in pool
            game.player_money[player_id] += refund
            game.bank_pool -= refund
            await channel.send(f"💵 <@{player_id}> gets ${refund:,} tax refund from BANK! 🏦 Bank Pool: ${game.bank_pool:,}")
        
        # Tax Evasion (immunity marker - would need to track separately)
        elif card_type == "tax_evasion":
            await channel.send(f"🕶️ <@{player_id}> gets tax evasion! (Next tax is free)")
        
        # DOUBLE MONEY (RARE!)
        elif card_type == "double_money":
            original = game.player_money[player_id]
            game.player_money[player_id] *= 2
            await channel.send(f"💎 **JACKPOT!** <@{player_id}> doubles their money! ${original:,} → ${game.player_money[player_id]:,}! 🎰🎰🎰")
        
        # BANK ROBBERY (RARE!)
        elif card_type == "bank_robbery":
            stolen = game.bank_pool
            game.player_money[player_id] += stolen
            game.bank_pool = 0
            await channel.send(f"🏴‍☠️ **BANK HEIST!** <@{player_id}> steals ${stolen:,} from the Bank! 💰💰💰")
        
        # STEAL PROPERTY (RARE!)
        elif card_type == "steal_property":
            # Find all properties owned by other players
            all_props = []
            for other_id in game.players:
                if other_id != player_id and not game.player_bankrupt[other_id]:
                    all_props.extend([(prop_id, other_id) for prop_id in game.player_properties[other_id]])
            
            if all_props:
                prop_id, victim_id = random.choice(all_props)
                prop = game.properties[prop_id]
                
                # Transfer property
                game.property_owners[prop_id] = player_id
                game.player_properties[victim_id].remove(prop_id)
                game.player_properties[player_id].append(prop_id)
                
                await channel.send(f"🎰 **MEGA WIN!** <@{player_id}> steals **{prop['name']}** from <@{victim_id}>! 🏆")
            else:
                await channel.send(f"😢 No properties to steal! <@{player_id}> gets $500 consolation prize")
                game.player_money[player_id] += 500
        
        # FREE PROPERTY (RARE!)
        elif card_type == "free_property":
            unowned = [pos for pos in game.properties.keys() if pos not in game.property_owners]
            if unowned:
                prop_id = random.choice(unowned)
                prop = game.properties[prop_id]
                
                game.property_owners[prop_id] = player_id
                game.player_properties[player_id].append(prop_id)
                
                await channel.send(f"🏆 **FREE PROPERTY!** <@{player_id}> gets **{prop['name']}** for FREE! (Worth ${prop['price']:,})")
            else:
                await channel.send(f"😢 No unowned properties! <@{player_id}> gets $1000 consolation prize")
                game.player_money[player_id] += 1000
        
        # PROPERTY UPGRADE (RARE!)
        elif card_type == "property_upgrade":
            if game.player_properties[player_id]:
                prop_id = random.choice(game.player_properties[player_id])
                prop = game.properties[prop_id]
                
                if "color" in prop:  # Only properties can have houses
                    current_houses = game.property_houses.get(prop_id, 0)
                    if current_houses < 5:
                        game.property_houses[prop_id] = current_houses + 1
                        house_name = "🏨 HOTEL" if current_houses == 4 else "🏠 HOUSE"
                        await channel.send(f"🏗️ **FREE UPGRADE!** <@{player_id}> adds a {house_name} to **{prop['name']}** for FREE!")
                    else:
                        await channel.send(f"Property maxed! <@{player_id}> gets $500 consolation")
                        game.player_money[player_id] += 500
                else:
                    await channel.send(f"Can't upgrade! <@{player_id}> gets $500 consolation")
                    game.player_money[player_id] += 500
            else:
                await channel.send(f"No properties! <@{player_id}> gets $500 consolation")
                game.player_money[player_id] += 500
        
        # Jail
        elif card_type == "jail":
            game.player_position[player_id] = 10
            game.player_in_jail[player_id] = True
            game.player_jail_turns[player_id] = 0
            await channel.send(f"<:GoToJail:1442965655405203529> <@{player_id}> goes to JAIL!")
        
        # Get Out of Jail Free
        elif card_type == "jail_free":
            game.player_get_out_jail_cards[player_id] += 1
            await channel.send(f"🔑 <@{player_id}> keeps this card!")
        
        # Movement
        elif card_type == "move":
            if card.get("relative"):
                new_pos = (game.player_position[player_id] + card["target"]) % 40
            else:
                new_pos = card["target"]
            
            passed_go = new_pos < game.player_position[player_id] and not card.get("relative")
            game.player_position[player_id] = new_pos
            
            if passed_go:
                game.player_money[player_id] += 200
                await channel.send(f"<:GO:1442963964819538062> Passed GO! Collect $200")
            
            await channel.send(f"🎯 Moving to **{self.board_layout[new_pos]}**...")
            await self.handle_space_landing(channel, game, player_id, new_pos)
        
        # Pay/Collect from all players
        elif card_type == "pay_all":
            amount = card["amount"]
            for other_id in game.players:
                if other_id != player_id and not game.player_bankrupt[other_id]:
                    game.player_money[player_id] -= amount
                    game.player_money[other_id] += amount
            total = amount * (len([p for p in game.players if not game.player_bankrupt[p]]) - 1)
            await channel.send(f"💸 <@{player_id}> pays ${total:,} total to all players")
        
        elif card_type == "collect_all":
            amount = card["amount"]
            for other_id in game.players:
                if other_id != player_id and not game.player_bankrupt[other_id]:
                    game.player_money[player_id] += amount
                    game.player_money[other_id] -= amount
            total = amount * (len([p for p in game.players if not game.player_bankrupt[p]]) - 1)
            await channel.send(f"💰 <@{player_id}> collects ${total:,} from all players!")
        
        # Repairs (to BANK)
        elif card_type == "repairs":
            house_cost = card["house"]
            hotel_cost = card["hotel"]
            total_cost = 0
            
            for prop_id in game.player_properties[player_id]:
                houses = game.property_houses.get(prop_id, 0)
                if houses == 5:
                    total_cost += hotel_cost
                elif houses > 0:
                    total_cost += houses * house_cost
            
            if total_cost > 0:
                game.player_money[player_id] -= total_cost
                game.bank_pool += total_cost
                await channel.send(f"🔧 <@{player_id}> pays ${total_cost:,} repairs to BANK! 🏦 Bank Pool: ${game.bank_pool:,}")
    
    async def handle_jail_turn(self, interaction, game, player_id):
        """Handle a turn while in jail"""
        game.player_jail_turns[player_id] += 1
        
        # Roll for doubles
        die1 = random.randint(1, 6)
        die2 = random.randint(1, 6)
        
        if die1 == die2:
            game.player_in_jail[player_id] = False
            game.player_jail_turns[player_id] = 0
            await interaction.followup.send(f"🎲 **Rolled {die1} + {die2} = DOUBLES! Out of jail!**")
            game.player_position[player_id] = 10 + die1 + die2
            await self.handle_space_landing(interaction.channel, game, player_id, game.player_position[player_id])
        elif game.player_jail_turns[player_id] >= 3:
            # Must pay $50
            game.player_money[player_id] -= 50
            game.bank_pool += 50
            game.player_in_jail[player_id] = False
            game.player_jail_turns[player_id] = 0
            await interaction.followup.send(f"💸 **3 turns in jail! Paid $50 fine to BANK! Now free!**\n🏦 Bank Pool: ${game.bank_pool:,}")
        else:
            await interaction.followup.send(f"🎲 **Rolled {die1} + {die2}. Still in jail. ({game.player_jail_turns[player_id]}/3 turns)**\nRoll doubles, use Get Out of Jail Free card, or wait for turn 3 ($50 fine)")
    
    async def handle_bankruptcy(self, channel, game, player_id, creditor_id):
        """Handle player bankruptcy"""
        game.player_bankrupt[player_id] = True
        
        # Transfer all properties to creditor
        for prop_id in game.player_properties[player_id]:
            game.property_owners[prop_id] = creditor_id
            game.player_properties[creditor_id].append(prop_id)
        
        game.player_properties[player_id] = []
        game.player_money[player_id] = 0
        
        await channel.send(f"💀 **<@{player_id}> is BANKRUPT! All assets go to <@{creditor_id}>**")
        
        # Check win condition
        active_players = [pid for pid in game.players if not game.player_bankrupt[pid]]
        if len(active_players) == 1:
            await self.end_game(channel, game, active_players[0])
    
    async def end_game(self, channel, game, winner_id):
        """End the game and award prizes"""
        game.active = False
        
        winner_money = game.player_money[winner_id]
        psycoins = int(winner_money * 0.5)
        
        # Award PsyCoins
        economy_cog = self.bot.get_cog("Economy")
        if economy_cog:
            economy_cog.add_coins(winner_id, psycoins, "monopoly_win")
        
        embed = discord.Embed(
            title="🏆 MONOPOLY - GAME OVER!",
            description=f"**WINNER: <@{winner_id}>**\n\n"
                       f"💰 **Final Monopoly Money:** ${winner_money:,}\n"
                       f"🪙 **PsyCoins Earned:** {psycoins:,} (×0.5)\n\n"
                       f"**Final Standings:**",
            color=discord.Color.gold()
        )
        
        for pid in game.players:
            status = "💀 Bankrupt" if game.player_bankrupt[pid] else f"${game.player_money[pid]:,}"
            embed.add_field(name=f"<@{pid}>", value=status, inline=True)
        
        await channel.send(embed=embed)
        # Chance to award TCG card(s) for difficult category (monopoly)
        if tcg_manager:
            try:
                awarded = tcg_manager.award_for_game_event(str(winner_id), 'difficult')
                if awarded:
                    names = [CARD_DATABASE.get(c, {}).get('name', c) for c in awarded]
                    await channel.send(f"🏆 Bonus TCG reward for the winner: {', '.join(names)}")
            except Exception:
                pass
        del self.active_games[channel.id]
    
    async def announce_next_turn(self, channel, game):
        """Announce next player's turn"""
        if not game.active:
            return
        
        current = game.get_current_player()
        if current:
            await channel.send(f"**<@{current}>'s turn!** Use `/monopoly roll` to roll dice")
    
    async def buy_property(self, interaction: discord.Interaction):
        """Buy the property you're standing on"""
        game = self.active_games.get(interaction.channel_id)
        if not game or interaction.user.id != game.get_current_player():
            await interaction.response.send_message("❌ Not your turn or no active game!", ephemeral=True)
            return
        
        player_id = interaction.user.id
        position = game.player_position[player_id]
        
        if position not in game.properties:
            await interaction.response.send_message("❌ Not a purchasable property!", ephemeral=True)
            return
        
        if game.property_owners.get(position) is not None:
            await interaction.response.send_message("❌ Property already owned!", ephemeral=True)
            return
        
        prop = game.properties[position]
        price = prop["price"]
        
        if game.player_money[player_id] < price:
            await interaction.response.send_message(f"❌ Not enough money! Need ${price}", ephemeral=True)
            return
        
        # Buy the property
        game.player_money[player_id] -= price
        game.property_owners[position] = player_id
        game.player_properties[player_id].append(position)
        
        # Show updated board
        board_display = self.generate_board_display(game, player_id)
        player_summary = self.generate_player_summary(game)
        
        embed = discord.Embed(
            title="🏠 PROPERTY PURCHASED!",
            description=f"✅ **<@{player_id}> bought {prop['name']} for ${price:,}!**\n"
                       f"💰 Balance: ${game.player_money[player_id]:,}\n"
                       f"🏠 Properties owned: {len(game.player_properties[player_id])}",
            color=discord.Color.green()
        )
        embed.add_field(name="🗺️ Board", value=board_display, inline=False)
        embed.add_field(name="👥 Players", value=player_summary, inline=False)
        
        await interaction.response.send_message(embed=embed)
        
        # Check if player rolled doubles (don't end turn)
        if game.doubles_count > 0:
            await interaction.channel.send(f"**{interaction.user.mention}**, you rolled doubles earlier!\n"
                                          f"• Roll again: `/monopoly roll`\n"
                                          f"• End turn: `/monopoly endturn`")
        else:
            # End turn after buying (if not doubles)
            await interaction.channel.send(f"**Turn ending...**")
            game.next_turn()
            await self.announce_next_turn(interaction.channel, game)
        await interaction.response.send_message(f"✅ **<@{player_id}> bought {prop['name']} for ${price}!** (Balance: ${game.player_money[player_id]})")
    
    async def end_turn(self, interaction: discord.Interaction):
        """End your turn"""
        game = self.active_games.get(interaction.channel_id)
        if not game or interaction.user.id != game.get_current_player():
            await interaction.response.send_message("❌ Not your turn!", ephemeral=True)
            return
        
        await interaction.response.send_message(f"✅ Ending turn...")
        game.next_turn()
        await self.announce_next_turn(interaction.channel, game)
    
    async def force_end_game(self, interaction: discord.Interaction):
        """Force end the current Monopoly game"""
        game = self.active_games.get(interaction.channel_id)
        if not game:
            await interaction.response.send_message("❌ No active Monopoly game in this channel!", ephemeral=True)
            return
        
        # Check if user is in the game or is admin
        if interaction.user.id not in game.players and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Only players in the game or admins can end it!", ephemeral=True)
            return
        
        # Calculate winner (player with most money)
        winner_id = max(game.player_money.items(), key=lambda x: x[1])[0]
        winner_money = game.player_money[winner_id]
        
        # Award PsyCoins
        psycoins = int(winner_money * 0.5)
        economy_cog = self.bot.get_cog("Economy")
        if economy_cog:
            economy_cog.add_coins(winner_id, psycoins, "monopoly_win")
        
        embed = discord.Embed(
            title="🛑 MONOPOLY - GAME ENDED!",
            description=f"**Game ended by <@{interaction.user.id}>**\n\n"
                       f"🏆 **Winner (Most Money):** <@{winner_id}>\n"
                       f"💰 **Final Money:** ${winner_money:,}\n"
                       f"🪙 **PsyCoins Earned:** {psycoins:,}\n\n"
                       f"Thanks for playing!",
            color=discord.Color.red()
        )
        
        # Show final standings
        standings = sorted(game.player_money.items(), key=lambda x: x[1], reverse=True)
        standings_text = ""
        for i, (pid, money) in enumerate(standings, 1):
            medal = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else f"{i}."
            standings_text += f"{medal} <@{pid}>: ${money:,}\n"
        
        embed.add_field(name="📊 Final Standings", value=standings_text, inline=False)
        
        await interaction.response.send_message(embed=embed)
        del self.active_games[interaction.channel_id]
    
    async def view_status(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        """View player status and full board"""
        game = self.active_games.get(interaction.channel_id)
        if not game:
            await interaction.response.send_message("❌ No active Monopoly game!", ephemeral=True)
            return
        
        target = user or interaction.user
        if target.id not in game.players:
            await interaction.response.send_message("❌ That user is not in this game!", ephemeral=True)
            return
        
        player_id = target.id
        position = game.player_position[player_id]
        space_name = self.board_layout[position]
        
        # Generate board and player summary
        board_display = self.generate_board_display(game, player_id)
        player_summary = self.generate_player_summary(game)
        
        # Build properties list
        properties_text = ""
        if game.player_properties[player_id]:
            for prop_id in sorted(game.player_properties[player_id]):
                prop = game.properties[prop_id]
                houses = game.property_houses.get(prop_id, 0)
                house_text = ""
                if houses == 5:
                    house_text = " 🏨"
                elif houses > 0:
                    house_text = f" {'🏠' * houses}"
                mortgaged = " 🔒" if game.property_mortgaged.get(prop_id) else ""
                properties_text += f"• {prop['name']}{house_text}{mortgaged}\n"
        else:
            properties_text = "No properties owned"
        
        # Calculate distances to key locations
        distance_to_go = (40 - position) if position > 0 else 0
        distance_to_jail = (10 - position) if position < 10 else (50 - position)
        distance_to_parking = (20 - position) if position < 20 else (60 - position)
        
        # Build status embed
        embed = discord.Embed(
            title=f"🎮 MONOPOLY - {target.display_name}'s Status",
            description=f"**Position:** Space {position} - {space_name}\n"
                       f"**Money:** ${game.player_money[player_id]:,}\n"
                       f"**Properties:** {len(game.player_properties[player_id])}\n"
                       f"**Status:** {'🔒 In Jail' if game.player_in_jail[player_id] else '✅ Active'}",
            color=discord.Color.gold() if player_id == game.get_current_player() else discord.Color.blue()
        )
        
        # Add board display
        embed.add_field(name="🗺️ Full Board", value=board_display, inline=False)
        
        # Add all players
        embed.add_field(name="👥 All Players", value=player_summary, inline=False)
        
        # Add properties owned
        if len(properties_text) < 1024:
            embed.add_field(name="🏠 Properties Owned", value=properties_text, inline=False)
        else:
            embed.add_field(name="🏠 Properties Owned", value=properties_text[:1020] + "...", inline=False)
        
        # Add distances
        embed.add_field(
            name="📍 Distances",
            value=f"▶️ To GO: {distance_to_go} spaces\n"
                  f"🔒 To Jail: {distance_to_jail} spaces\n"
                  f"🅿️ To Parking: {distance_to_parking} spaces",
            inline=True
        )
        
        # Add net worth
        net_worth = game.player_money[player_id]
        for prop_id in game.player_properties[player_id]:
            if not game.property_mortgaged.get(prop_id):
                net_worth += game.properties[prop_id]["price"]
        
        embed.add_field(
            name="💎 Net Worth",
            value=f"${net_worth:,}",
            inline=True
        )
        
        embed.set_footer(text=f"Round {game.round_num} • Use /monopoly to play")
        
        await interaction.response.send_message(embed=embed)
    
    async def view_board(self, interaction: discord.Interaction):
        """View the full Monopoly board with all players"""
        game = self.active_games.get(interaction.channel_id)
        if not game:
            await interaction.response.send_message("❌ No active Monopoly game!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        board_embed = await self.create_board_embed(game)
        await interaction.followup.send(embed=board_embed)
    
    async def view_properties(self, interaction: discord.Interaction):
        """View all your properties in detail"""
        game = self.active_games.get(interaction.channel_id)
        if not game:
            await interaction.response.send_message("❌ No active Monopoly game!", ephemeral=True)
            return
        
        player_id = interaction.user.id
        if player_id not in game.players:
            await interaction.response.send_message("❌ You're not in this game!", ephemeral=True)
            return
        
        if not game.player_properties[player_id]:
            await interaction.response.send_message("❌ You don't own any properties yet!", ephemeral=True)
            return
        
        # Group properties by color
        color_groups = {}
        railroads = []
        utilities = []
        
        for prop_id in game.player_properties[player_id]:
            prop = game.properties[prop_id]
            if prop.get("type") == "railroad":
                railroads.append((prop_id, prop))
            elif prop.get("type") == "utility":
                utilities.append((prop_id, prop))
            else:
                color = prop.get("color", "Other")
                if color not in color_groups:
                    color_groups[color] = []
                color_groups[color].append((prop_id, prop))
        
        # Calculate total value
        total_value = 0
        total_income = 0
        
        embed = discord.Embed(
            title=f"{game.player_pieces.get(player_id, '🎩')} YOUR PROPERTIES",
            description=f"**<@{player_id}>** owns {len(game.player_properties[player_id])} properties\n"
                       f"💰 Cash on hand: ${game.player_money[player_id]:,}\n",
            color=discord.Color.green()
        )
        
        # Add color groups
        for color, props in sorted(color_groups.items()):
            props_text = ""
            for prop_id, prop in props:
                houses = game.property_houses.get(prop_id, 0)
                mortgaged = game.property_mortgaged.get(prop_id, False)
                
                house_display = ""
                if mortgaged:
                    house_display = " 🔒 MORTGAGED"
                elif houses == 5:
                    house_display = " 🏨 HOTEL"
                elif houses > 0:
                    house_display = f" {'🏠' * houses}"
                
                rent = prop["rent"][houses] if not mortgaged else 0
                value = prop["price"] if not mortgaged else prop["price"] // 2
                
                props_text += f"**{prop['name']}** ${prop['price']:,}{house_display}\n"
                props_text += f"  💵 Rent: ${rent:,} | Value: ${value:,}\n"
                
                total_value += value
                total_income += rent
            
            # Color emoji
            color_emoji = {
                "Brown": "🟤", "Light Blue": "🔵", "Pink": "💗",
                "Orange": "🟠", "Red": "🔴", "Yellow": "🟡",
                "Green": "🟢", "Dark Blue": "🔷"
            }.get(color, "⬜")
            
            embed.add_field(
                name=f"{color_emoji} {color}",
                value=props_text,
                inline=False
            )
        
        # Add railroads
        if railroads:
            rail_text = ""
            for prop_id, prop in railroads:
                mortgaged = game.property_mortgaged.get(prop_id, False)
                status = " 🔒" if mortgaged else ""
                rail_count = sum(1 for p in [5, 15, 25, 35] if game.property_owners.get(p) == player_id)
                rent = prop["rent"][rail_count - 1] if not mortgaged else 0
                
                rail_text += f"**{prop['name']}**{status}\n"
                rail_text += f"  💵 Rent: ${rent:,} ({rail_count} owned)\n"
                
                total_value += prop["price"] if not mortgaged else prop["price"] // 2
                total_income += rent
            
            embed.add_field(name="🚂 Railroads", value=rail_text, inline=False)
        
        # Add utilities
        if utilities:
            util_text = ""
            for prop_id, prop in utilities:
                mortgaged = game.property_mortgaged.get(prop_id, False)
                status = " 🔒" if mortgaged else ""
                util_count = sum(1 for p in [12, 28] if game.property_owners.get(p) == player_id)
                
                util_text += f"**{prop['name']}**{status}\n"
                util_text += f"  💵 Rent: {4 if util_count == 1 else 10}× dice roll\n"
                
                total_value += prop["price"] if not mortgaged else prop["price"] // 2
            
            embed.add_field(name="⚡ Utilities", value=util_text, inline=False)
        
        # Summary
        net_worth = game.player_money[player_id] + total_value
        embed.add_field(
            name="📊 Portfolio Summary",
            value=f"**Property Value:** ${total_value:,}\n"
                  f"**Potential Income:** ${total_income:,}/turn\n"
                  f"**Net Worth:** ${net_worth:,}",
            inline=False
        )
        
        embed.set_footer(text=f"Round {game.round_num} | Position: {self.board_layout[game.player_position[player_id]]}")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def create_board_embed(self, game: MonopolyGame) -> discord.Embed:
        """Create a visual board embed with player pieces"""
        # Build the board visually
        board_lines = []
        
        # Top row (20-30, reversed)
        top_row = "┌─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┐\n"
        top_spaces = ""
        top_pieces = ""
        
        for pos in range(30, 19, -1):
            space_num = f"{pos:02d}"
            players_here = [game.player_pieces.get(p, '🎩') for p in game.players 
                          if game.player_position[p] == pos and not game.player_bankrupt[p]]
            piece_display = ''.join(players_here[:3]) if players_here else "   "
            
            top_spaces += f"│ {space_num} "
            top_pieces += f"│{piece_display:^5}"
        
        top_spaces += "│\n"
        top_pieces += "│\n"
        
        board_lines.append(top_row + top_spaces + top_pieces)
        board_lines.append("├─────┼" + "─────┼" * 9 + "─────┤\n")
        
        # Middle rows (39-31 on left, 11-19 on right)
        for i in range(9):
            left_pos = 39 - i
            right_pos = 11 + i
            
            left_players = [game.player_pieces.get(p, '🎩') for p in game.players 
                          if game.player_position[p] == left_pos and not game.player_bankrupt[p]]
            right_players = [game.player_pieces.get(p, '🎩') for p in game.players 
                           if game.player_position[p] == right_pos and not game.player_bankrupt[p]]
            
            left_piece = ''.join(left_players[:3]) if left_players else "   "
            right_piece = ''.join(right_players[:3]) if right_players else "   "
            
            line = f"│ {left_pos:02d} │" + "     │" * 9 + f" {right_pos:02d} │\n"
            pieces = f"│{left_piece:^5}│" + "     │" * 9 + f"{right_piece:^5}│\n"
            
            board_lines.append(line + pieces)
            if i < 8:
                board_lines.append("├─────┤" + "     │" * 9 + "├─────┤\n")
        
        # Bottom row (0-10)
        board_lines.append("├─────┼" + "─────┼" * 9 + "─────┤\n")
        
        bottom_spaces = ""
        bottom_pieces = ""
        
        for pos in range(0, 11):
            space_num = f"{pos:02d}"
            players_here = [game.player_pieces.get(p, '🎩') for p in game.players 
                          if game.player_position[p] == pos and not game.player_bankrupt[p]]
            piece_display = ''.join(players_here[:3]) if players_here else "   "
            
            bottom_spaces += f"│ {space_num} "
            bottom_pieces += f"│{piece_display:^5}"
        
        bottom_spaces += "│\n"
        bottom_pieces += "│\n"
        bottom_row = "└─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┘"
        
        board_lines.append(bottom_spaces + bottom_pieces + bottom_row)
        
        board_display = "```\n" + ''.join(board_lines) + "\n```"
        
        # Player legend
        player_list = []
        for pid in game.players:
            if game.player_bankrupt[pid]:
                continue
            piece = game.player_pieces.get(pid, '🎩')
            pos = game.player_position[pid]
            space = self.board_layout[pos]
            money = game.player_money[pid]
            props = len(game.player_properties[pid])
            
            status = ""
            if game.player_in_jail[pid]:
                status = " 🔒"
            elif pid == game.get_current_player():
                status = " 👈 **TURN**"
            
            player_list.append(f"{piece} <@{pid}> - ${money:,} | {props} props | {space}{status}")
        
        embed = discord.Embed(
            title="🎲 MONOPOLY BOARD",
            description=board_display + "\n**Players:**\n" + "\n".join(player_list),
            color=discord.Color.gold()
        )
        
        # Add bank pool info
        embed.add_field(
            name="🏦 Bank Pool",
            value=f"${game.bank_pool:,}\n💡 Land on <:Free_Parking:1442963738062880879> with doubles to win!",
            inline=False
        )
        
        embed.set_footer(text=f"Round {game.round_num} | Use /monopoly board to view anytime")
        
        return embed

async def setup(bot):
    await bot.add_cog(Monopoly(bot))
