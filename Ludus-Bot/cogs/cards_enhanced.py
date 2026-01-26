import discord
from discord.ext import commands
from discord import app_commands
import random
from typing import Optional

from discord import app_commands
from discord.ui import View, Button
from cogs.minigames import PaginatedHelpView

class Cards(commands.Cog):
    """Card games with ephemeral messages for privacy"""

    def __init__(self, bot):
        self.bot = bot
        self.active_games = {}
        self.card_values = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        self.card_suits = ['♠️', '♥️', '♦️', '♣️']

    @app_commands.command(name="cardshelp", description="View all card game commands and info (paginated)")
    async def cardshelp_slash(self, interaction: discord.Interaction):
        commands_list = []
        for cmd in self.get_commands():
            if not cmd.hidden:
                name = f"/{cmd.name}" if hasattr(cmd, 'app_command') else f"L!{cmd.name}"
                desc = cmd.help or cmd.short_doc or "No description."
                commands_list.append((name, desc))
        category_name = "Card Games"
        category_desc = "Play a variety of card games! Use the buttons below to see all commands."
        view = PaginatedHelpView(interaction, commands_list, category_name, category_desc)
        await view.send()

    def create_deck(self):
        """Create a standard 52-card deck"""
        return [(value, suit) for value in self.card_values for suit in self.card_suits]

    def format_card(self, card):
        """Format a card for display"""
        return f"{card[0]}{card[1]}"

    def format_hand(self, hand):
        """Format a hand of cards"""
        return " ".join([self.format_card(card) for card in hand])
    
    # ==================== SLASH COMMAND CARD SELECTOR ====================
    
    @app_commands.command(name="cardsmenu", description="Choose a card game to play")
    async def cards_menu(self, interaction: discord.Interaction):
        """Select which card game you want to play"""
        
        view = CardGameSelector(self)
        
        embed = discord.Embed(
            title="🃏 Card Games Menu",
            description="Select a card game to play!\n\n"
                       "**Available Games:**\n"
                       "🃏 **Solitaire** - Classic single-player\n"
                       "♠️ **Spades** - Team-based trick game\n"
                       "8️⃣ **Crazy Eights** - Match suits or ranks\n"
                       "🎴 **Bullshit** - Bluff your way to victory\n\n"
                       "*Your cards will be shown privately!*",
            color=discord.Color.gold()
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    # ==================== SOLITAIRE ====================
    
    async def start_solitaire(self, interaction: discord.Interaction):
        """Start a game of Solitaire"""
        
        deck = self.create_deck()
        random.shuffle(deck)
        
        # Deal cards
        tableau = [deck[i:i+i+1] for i in range(7)]
        stock = deck[28:]
        
        game_id = f"solitaire_{interaction.user.id}"
        self.active_games[game_id] = {
            "type": "solitaire",
            "tableau": tableau,
            "stock": stock,
            "waste": [],
            "foundations": [[], [], [], []],
            "player": interaction.user.id
        }
        
        embed = discord.Embed(
            title="🃏 Solitaire",
            description=self.display_solitaire(game_id),
            color=discord.Color.blue()
        )
        embed.set_footer(text="Use buttons to interact with the game")
        
        view = SolitaireView(self, game_id)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
    
    def display_solitaire(self, game_id):
        """Display solitaire game state"""
        game = self.active_games.get(game_id)
        if not game:
            return "Game not found!"
        
        display = "**Stock:** "
        display += f"{len(game['stock'])} cards\n"
        display += "**Waste:** "
        display += self.format_card(game['waste'][-1]) if game['waste'] else "Empty"
        display += "\n\n**Foundations:**\n"
        
        for i, foundation in enumerate(game['foundations']):
            suit = self.card_suits[i]
            if foundation:
                display += f"{suit}: {self.format_card(foundation[-1])}\n"
            else:
                display += f"{suit}: Empty\n"
        
        display += "\n**Tableau:**\n"
        for i, pile in enumerate(game['tableau']):
            display += f"Pile {i+1}: "
            if pile:
                display += self.format_hand(pile)
            else:
                display += "Empty"
            display += "\n"
        
        return display
    
    # ==================== CRAZY EIGHTS ====================
    
    async def start_crazy_eights(self, interaction: discord.Interaction):
        """Start a game of Crazy Eights"""
        
        embed = discord.Embed(
            title="8️⃣ Crazy Eights",
            description="🎮 **Looking for opponent...**\n\n"
                       "Waiting for another player to join!\n"
                       "Use `/cardsmenu` and select Crazy Eights to join!",
            color=discord.Color.orange()
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        await interaction.channel.send(
            f"8️⃣ **{interaction.user.mention} wants to play Crazy Eights!**\n"
            f"Type `/cardsmenu` and select Crazy Eights to join!"
        )
    
    # ==================== SPADES ====================
    
    async def start_spades(self, interaction: discord.Interaction):
        """Start a game of Spades"""
        
        embed = discord.Embed(
            title="♠️ Spades",
            description="🎮 **Team-based card game**\n\n"
                       "Spades is a 4-player trick-taking game!\n"
                       "Looking for 3 more players...\n\n"
                       "Players use `/cardsmenu` to join!",
            color=discord.Color.dark_purple()
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        await interaction.channel.send(
            f"♠️ **{interaction.user.mention} wants to play Spades!**\n"
            f"Need 3 more players! Use `/cardsmenu` and select Spades to join!"
        )
    
    # ==================== BULLSHIT ====================
    
    async def start_bullshit(self, interaction: discord.Interaction):
        """Start a game of Bullshit"""
        
        embed = discord.Embed(
            title="🎴 Bullshit",
            description="🃏 **The Bluffing Card Game**\n\n"
                       "Lie about your cards and don't get caught!\n\n"
                       "**How to Play:**\n"
                       "• Play cards face-down claiming they're a certain rank\n"
                       "• Other players can call 'Bullshit!'\n"
                       "• If caught lying, you take all the cards\n"
                       "• If you were honest, the challenger takes them\n"
                       "• First to empty their hand wins!\n\n"
                       "Waiting for more players...",
            color=discord.Color.red()
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        await interaction.channel.send(
            f"🎴 **{interaction.user.mention} wants to play Bullshit!**\n"
            f"Need 2-6 players! Use `/cardsmenu` to join!"
        )

# ==================== UI COMPONENTS ====================

class CardGameSelector(discord.ui.View):
    """View for selecting card games"""
    
    def __init__(self, cog):
        super().__init__(timeout=300)
        self.cog = cog
    
    @discord.ui.button(label="🃏 Solitaire", style=discord.ButtonStyle.primary)
    async def solitaire_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await self.cog.start_solitaire(interaction)
    
    @discord.ui.button(label="♠️ Spades", style=discord.ButtonStyle.secondary)
    async def spades_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await self.cog.start_spades(interaction)
    
    @discord.ui.button(label="8️⃣ Crazy Eights", style=discord.ButtonStyle.success)
    async def crazy_eights_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await self.cog.start_crazy_eights(interaction)
    
    @discord.ui.button(label="🎴 Bullshit", style=discord.ButtonStyle.danger)
    async def bullshit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await self.cog.start_bullshit(interaction)

class SolitaireView(discord.ui.View):
    """Interactive buttons for Solitaire"""
    
    def __init__(self, cog, game_id):
        super().__init__(timeout=600)
        self.cog = cog
        self.game_id = game_id
    
    @discord.ui.button(label="Draw Card", style=discord.ButtonStyle.primary, emoji="🃏")
    async def draw_card(self, interaction: discord.Interaction, button: discord.ui.Button):
        game = self.cog.active_games.get(self.game_id)
        
        if game and game['stock']:
            card = game['stock'].pop()
            game['waste'].append(card)
            
            embed = discord.Embed(
                title="🃏 Solitaire",
                description=self.cog.display_solitaire(self.game_id),
                color=discord.Color.blue()
            )
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.send_message("❌ No more cards in stock!", ephemeral=True)
    
    @discord.ui.button(label="Reset Stock", style=discord.ButtonStyle.secondary, emoji="🔄")
    async def reset_stock(self, interaction: discord.Interaction, button: discord.ui.Button):
        game = self.cog.active_games.get(self.game_id)
        
        if game:
            game['stock'] = game['waste'][::-1]
            game['waste'] = []
            
            embed = discord.Embed(
                title="🃏 Solitaire",
                description=self.cog.display_solitaire(self.game_id),
                color=discord.Color.blue()
            )
            await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="New Game", style=discord.ButtonStyle.success, emoji="🆕")
    async def new_game(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if self.game_id in self.cog.active_games:
            del self.cog.active_games[self.game_id]
        await self.cog.start_solitaire(interaction)
    
    @discord.ui.button(label="Quit", style=discord.ButtonStyle.danger, emoji="❌")
    async def quit_game(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.game_id in self.cog.active_games:
            del self.cog.active_games[self.game_id]
        
        embed = discord.Embed(
            title="🃏 Game Ended",
            description="Thanks for playing Solitaire!",
            color=discord.Color.red()
        )
        await interaction.response.edit_message(embed=embed, view=None)

async def setup(bot):
    await bot.add_cog(Cards(bot))
