"""
UNO Game Module
Supports Classic, Flip, No Mercy and No Mercy+ variants
"""
from .classic import UnoCog

async def setup(bot):
    """Setup function for the cog"""
    await bot.add_cog(UnoCog(bot))
