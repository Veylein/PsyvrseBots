"""
🎨 Ludus Bot - Beautiful Embed Styling System
Professional, consistent, and visually stunning embeds
"""

import discord
from datetime import datetime
from typing import Optional, List, Dict, Any

# 🎨 Brand Colors
class Colors:
    """Ludus brand color palette"""
    # Primary Colors
    PRIMARY = 0x5865F2      # Discord Blurple
    SUCCESS = 0x57F287      # Vibrant Green
    WARNING = 0xFEE75C      # Bright Yellow
    ERROR = 0xED4245        # Vibrant Red
    INFO = 0x00D9FF         # Cyan Blue
    
    # Game Categories
    ECONOMY = 0xF1C40F      # Gold
    MINIGAMES = 0xE91E63    # Pink
    LEVELING = 0x9B59B6     # Purple
    MUSIC = 0x1DB954        # Spotify Green
    SOCIAL = 0x3498DB       # Sky Blue
    GAMBLING = 0xE74C3C     # Casino Red
    TCG = 0xFF6B6B          # Coral Red
    BOARD_GAMES = 0x95A5A6  # Cool Gray
    FISHING = 0x3498DB      # Ocean Blue
    PETS = 0xFF69B4         # Hot Pink
    QUESTS = 0xFFD700       # Golden
    
    # Tier Colors (for cards, items, etc)
    COMMON = 0x95A5A6       # Gray
    UNCOMMON = 0x2ECC71     # Green
    RARE = 0x3498DB         # Blue
    EPIC = 0x9B59B6         # Purple
    LEGENDARY = 0xF39C12    # Orange
    MYTHIC = 0xE91E63       # Pink
    DIVINE = 0xFFD700       # Gold

# 🎭 Emojis
class Emojis:
    """Beautiful emoji sets for consistent branding"""
    # Status
    SUCCESS = "✅"
    ERROR = "❌"
    WARNING = "⚠️"
    INFO = "ℹ️"
    LOADING = "⏳"
    SHIELD = "🛡️"
    TOOLS = "🛠️"
    LEVEL_UP = "⬆️"
    
    # Economy
    COIN = "🪙"
    BANK = "🏦"
    SHOP = "🛒"
    GIFT = "🎁"
    TREASURE = "💰"
    DIAMOND = "💎"
    
    # Games
    DICE = "🎲"
    CARDS = "🎴"
    TROPHY = "🏆"
    MEDAL = "🏅"
    STAR = "⭐"
    FIRE = "🔥"
    
    # Social
    CROWN = "👑"
    HEART = "❤️"
    PARTY = "🎉"
    SPARKLES = "✨"
    ROCKET = "🚀"
    
    # Music
    MUSIC = "🎵"
    NOTE = "🎶"
    HEADPHONES = "🎧"
    RADIO = "📻"
    MIC = "🎤"
    
    # Leveling
    LEVEL_UP = "📈"
    XP = "⚡"
    RANK = "📊"
    
    # Numbers (for rankings)
    NUMBERS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    MEDALS_RANK = ["🥇", "🥈", "🥉"]

class EmbedBuilder:
    """Beautiful embed creator with consistent styling"""
    
    @staticmethod
    def create(
        title: Optional[str] = None,
        description: Optional[str] = None,
        color: int = Colors.PRIMARY,
        author_name: Optional[str] = None,
        author_icon: Optional[str] = None,
        thumbnail: Optional[str] = None,
        image: Optional[str] = None,
        footer_text: Optional[str] = None,
        footer_icon: Optional[str] = None,
        timestamp: bool = False,
        fields: Optional[List[Dict[str, Any]]] = None
    ) -> discord.Embed:
        """
        Create a beautifully styled embed
        
        Args:
            title: Embed title with emoji
            description: Main content
            color: Color from Colors class
            author_name: Author name (usually bot name)
            author_icon: Author icon URL
            thumbnail: Small image URL (top right)
            image: Large image URL (bottom)
            footer_text: Footer text
            footer_icon: Footer icon URL
            timestamp: Add current timestamp
            fields: List of {name, value, inline} dicts
        """
        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=datetime.utcnow() if timestamp else None
        )
        
        if author_name:
            embed.set_author(name=author_name, icon_url=author_icon)
        
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
        
        if image:
            embed.set_image(url=image)
        
        if footer_text:
            embed.set_footer(text=footer_text, icon_url=footer_icon)
        
        if fields:
            for field in fields:
                embed.add_field(
                    name=field.get("name", "Field"),
                    value=field.get("value", "No value"),
                    inline=field.get("inline", False)
                )
        
        return embed
    
    @staticmethod
    def success(title: str, description: str, **kwargs) -> discord.Embed:
        """Create a success embed (green)"""
        return EmbedBuilder.create(
            title=f"{Emojis.SUCCESS} {title}",
            description=description,
            color=Colors.SUCCESS,
            **kwargs
        )
    
    @staticmethod
    def error(title: str, description: str, **kwargs) -> discord.Embed:
        """Create an error embed (red)"""
        return EmbedBuilder.create(
            title=f"{Emojis.ERROR} {title}",
            description=description,
            color=Colors.ERROR,
            **kwargs
        )
    
    @staticmethod
    def warning(title: str, description: str, **kwargs) -> discord.Embed:
        """Create a warning embed (yellow)"""
        return EmbedBuilder.create(
            title=f"{Emojis.WARNING} {title}",
            description=description,
            color=Colors.WARNING,
            **kwargs
        )
    
    @staticmethod
    def info(title: str, description: str, **kwargs) -> discord.Embed:
        """Create an info embed (cyan)"""
        return EmbedBuilder.create(
            title=f"{Emojis.INFO} {title}",
            description=description,
            color=Colors.INFO,
            **kwargs
        )
    
    @staticmethod
    def economy(title: str, description: str, **kwargs) -> discord.Embed:
        """Create an economy embed (gold)"""
        return EmbedBuilder.create(
            title=f"{Emojis.COIN} {title}",
            description=description,
            color=Colors.ECONOMY,
            **kwargs
        )
    
    @staticmethod
    def game(title: str, description: str, **kwargs) -> discord.Embed:
        """Create a game embed (pink)"""
        return EmbedBuilder.create(
            title=f"{Emojis.DICE} {title}",
            description=description,
            color=Colors.MINIGAMES,
            **kwargs
        )
    
    @staticmethod
    def leveling(title: str, description: str, **kwargs) -> discord.Embed:
        """Create a leveling embed (purple)"""
        return EmbedBuilder.create(
            title=f"{Emojis.LEVEL_UP} {title}",
            description=description,
            color=Colors.LEVELING,
            **kwargs
        )
    
    @staticmethod
    def music(title: str, description: str, **kwargs) -> discord.Embed:
        """Create a music embed (spotify green)"""
        return EmbedBuilder.create(
            title=f"{Emojis.MUSIC} {title}",
            description=description,
            color=Colors.MUSIC,
            **kwargs
        )
    
    @staticmethod
    def leaderboard(
        title: str,
        entries: List[Dict[str, Any]],
        user_field: str = "user",
        value_field: str = "value",
        **kwargs
    ) -> discord.Embed:
        """
        Create a beautiful leaderboard embed
        
        Args:
            title: Leaderboard title
            entries: List of dicts with user and value
            user_field: Key for user name
            value_field: Key for value to display
        """
        description = ""
        for i, entry in enumerate(entries[:10], 1):
            # Medal for top 3
            if i <= 3:
                rank = Emojis.MEDALS_RANK[i-1]
            else:
                rank = f"`#{i}`"
            
            user = entry.get(user_field, "Unknown")
            value = entry.get(value_field, 0)
            
            description += f"{rank} **{user}** — {value:,}\n"
        
        return EmbedBuilder.create(
            title=f"{Emojis.TROPHY} {title}",
            description=description or "No entries yet!",
            color=Colors.PRIMARY,
            timestamp=True,
            **kwargs
        )
    
    @staticmethod
    def profile(
        user: discord.Member,
        stats: Dict[str, Any],
        **kwargs
    ) -> discord.Embed:
        """
        Create a beautiful profile embed
        
        Args:
            user: Discord user
            stats: Dictionary of stats to display
        """
        embed = discord.Embed(
            title=f"{user.display_name}'s Profile",
            color=user.color if user.color != discord.Color.default() else Colors.PRIMARY,
            timestamp=datetime.utcnow()
        )
        
        embed.set_thumbnail(url=user.display_avatar.url)
        
        # Add stats as fields
        for name, value in stats.items():
            embed.add_field(name=name, value=value, inline=True)
        
        embed.set_footer(text=f"ID: {user.id}")
        
        return embed
    
    @staticmethod
    def progress_bar(percentage: float, length: int = 10, filled: str = "█", empty: str = "░") -> str:
        """
        Create a beautiful progress bar
        
        Args:
            percentage: Progress from 0 to 100
            length: Number of characters in bar
            filled: Character for filled portion
            empty: Character for empty portion
        
        Returns:
            Progress bar string like: ████████░░ 80%
        """
        filled_length = int(length * percentage / 100)
        bar = filled * filled_length + empty * (length - filled_length)
        return f"{bar} {percentage:.0f}%"
    
    @staticmethod
    def format_number(number: int) -> str:
        """Format large numbers with commas and suffixes"""
        if number >= 1_000_000_000:
            return f"{number / 1_000_000_000:.1f}B"
        elif number >= 1_000_000:
            return f"{number / 1_000_000:.1f}M"
        elif number >= 1_000:
            return f"{number / 1_000:.1f}K"
        else:
            return f"{number:,}"
    
    @staticmethod
    def tier_color(tier: str) -> int:
        """Get color for item tier"""
        tier_map = {
            "common": Colors.COMMON,
            "c": Colors.COMMON,
            "uncommon": Colors.UNCOMMON,
            "bronze": Colors.UNCOMMON,
            "b": Colors.UNCOMMON,
            "rare": Colors.RARE,
            "silver": Colors.RARE,
            "s": Colors.RARE,
            "epic": Colors.EPIC,
            "gold": Colors.EPIC,
            "g": Colors.EPIC,
            "legendary": Colors.LEGENDARY,
            "amber": Colors.LEGENDARY,
            "a": Colors.LEGENDARY,
            "mythic": Colors.MYTHIC,
            "platinum": Colors.MYTHIC,
            "p": Colors.MYTHIC,
            "divine": Colors.DIVINE,
            "x": Colors.DIVINE,
        }
        return tier_map.get(tier.lower(), Colors.PRIMARY)

# Quick access functions
def create_embed(*args, **kwargs):
    """Quick access to EmbedBuilder.create()"""
    return EmbedBuilder.create(*args, **kwargs)

def success_embed(*args, **kwargs):
    """Quick access to EmbedBuilder.success()"""
    return EmbedBuilder.success(*args, **kwargs)

def error_embed(*args, **kwargs):
    """Quick access to EmbedBuilder.error()"""
    return EmbedBuilder.error(*args, **kwargs)

def warning_embed(*args, **kwargs):
    """Quick access to EmbedBuilder.warning()"""
    return EmbedBuilder.warning(*args, **kwargs)

def info_embed(*args, **kwargs):
    """Quick access to EmbedBuilder.info()"""
    return EmbedBuilder.info(*args, **kwargs)
