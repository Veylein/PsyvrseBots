import discord
from discord.ext import commands

class HelpCog(commands.Cog):
    """Provides help commands for users."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="help")
    async def help(self, ctx, command_name: str = None):
        """Show help for a specific command or all commands."""
        if command_name:
            command = self.bot.get_command(command_name)
            if command:
                embed = discord.Embed(title=f"Help: {command_name}")
                embed.add_field(name="Description", value=command.help or "No description available.")
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"Command '{command_name}' not found.")
        else:
            embed = discord.Embed(title="Available Commands")
            for command in self.bot.commands:
                embed.add_field(name=f"!{command.name}", value=command.help or "No description available.", inline=False)
            await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(HelpCog(bot))
