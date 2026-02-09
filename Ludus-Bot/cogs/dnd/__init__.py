"""
INFINITY ADVENTURE - D&D System Package
Modular dimension system for interdimensional narrative RPG.
"""

from .dnd import InfinityAdventure

__all__ = ['InfinityAdventure']


async def setup(bot):
    """Required setup function for Discord.py cog loading"""
    await bot.add_cog(InfinityAdventure(bot))
