import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional

from core.config import get_guild_settings


class HelpCog(commands.Cog):
    """Sleek help embed for prefix and slash usage."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _build_general_embed(self, prefix: str) -> discord.Embed:
        emb = discord.Embed(title="Villicus — Help", color=discord.Color.blurple())
        emb.description = (
            f"Prefix commands use `{prefix}` (example: `{prefix}warn @user`).\n"
            "Use the slash command preview for full argument help and required fields."
        )
        emb.add_field(name="Moderation", value="warn, mute, unmute, kick, ban, softban, massban, infractions", inline=False)
        emb.add_field(name="Admin", value="clear, slowmode, lock, unlock, clone, brick, demoji, emoji_lock", inline=False)
        emb.add_field(name="Staff", value="staff_setup, staff_promote, staff_demote, staff_perms", inline=False)
        emb.set_footer(text="Tip: try `/help <command>` for detailed info on a command.")
        return emb

    @commands.command(name='help')
    async def help_cmd(self, ctx: commands.Context, query: Optional[str] = None):
        prefix = get_guild_settings(ctx.guild.id).get('prefix', 'V!') if ctx.guild else 'V!'
        if not query:
            emb = self._build_general_embed(prefix)
            await ctx.send(embed=emb)
            return
        # find matching prefix command or slash command
        q = query.lower()
        # check prefix commands
        for cmd in self.bot.commands:
            if cmd.name == q:
                emb = discord.Embed(title=f'Help — {cmd.name}', color=discord.Color.green())
                emb.add_field(name='Usage', value=f"{prefix}{cmd.qualified_name} {cmd.signature}" or f"{prefix}{cmd.name}")
                emb.add_field(name='Help', value=cmd.help or '(no description)')
                await ctx.send(embed=emb)
                return
        # check slash commands
        for ac in self.bot.tree.walk_commands():
            if ac.name == q:
                emb = discord.Embed(title=f'Help — /{ac.name}', color=discord.Color.green())
                desc = ac.description or '(no description)'
                emb.add_field(name='Description', value=desc)
                # list parameters
                if hasattr(ac, 'parameters') and ac.parameters:
                    params = []
                    for p in ac.parameters:
                        params.append(f"{p.name}: {getattr(p, 'description', '')}")
                    emb.add_field(name='Parameters', value='\n'.join(params), inline=False)
                await ctx.send(embed=emb)
                return
        await ctx.send(f'No help found for `{query}`.')

    @app_commands.command(name='help', description='Show help for Villicus commands')
    @app_commands.describe(query='Command to get help for')
    async def help_slash(self, interaction: discord.Interaction, query: Optional[str] = None):
        await interaction.response.defer(ephemeral=True)
        prefix = get_guild_settings(interaction.guild.id).get('prefix', 'V!') if interaction.guild else 'V!'
        if not query:
            emb = self._build_general_embed(prefix)
            return await interaction.followup.send(embed=emb, ephemeral=True)
        q = query.lower()
        for cmd in self.bot.commands:
            if cmd.name == q:
                emb = discord.Embed(title=f'Help — {cmd.name}', color=discord.Color.green())
                emb.add_field(name='Usage', value=f"{prefix}{cmd.qualified_name} {cmd.signature}" or f"{prefix}{cmd.name}")
                emb.add_field(name='Help', value=cmd.help or '(no description)')
                return await interaction.followup.send(embed=emb, ephemeral=True)
        for ac in self.bot.tree.walk_commands():
            if ac.name == q:
                emb = discord.Embed(title=f'Help — /{ac.name}', color=discord.Color.green())
                desc = ac.description or '(no description)'
                emb.add_field(name='Description', value=desc)
                if hasattr(ac, 'parameters') and ac.parameters:
                    params = []
                    for p in ac.parameters:
                        params.append(f"{p.name}: {getattr(p, 'description', '')}")
                    emb.add_field(name='Parameters', value='\n'.join(params), inline=False)
                return await interaction.followup.send(embed=emb, ephemeral=True)
        await interaction.followup.send(f'No help found for `{query}`.', ephemeral=True)


async def setup(bot: commands.Bot):
    cog = HelpCog(bot)
    await bot.add_cog(cog)
    # register slash command onto tree (on_ready() will sync)
    try:
        bot.tree.add_command(app_commands.Command(name='help', description='Show help for Villicus commands', callback=cog.help_slash))
    except Exception:
        pass
