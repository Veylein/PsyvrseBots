from discord import Embed
from discord.ext import commands
import discord
from src.utils.audit import log_action
import time

# per-user cooldown map for slash skip
_last_skip: dict[int, float] = {}
_skip_cooldown = 5.0


def register(bot):
    @bot.command(name="skip")
    async def _skip(ctx):
        try:
            vc = ctx.guild.voice_client
            if vc and vc.is_playing():
                vc.stop()
                await ctx.send(embed=Embed(description="⏭️ Skipping track"))
                await log_action(bot, ctx.author.id, 'skip', {})
                return

            player = getattr(bot, 'player', None)
            if player and hasattr(player, 'skip'):
                player.skip()
                await ctx.send(embed=Embed(description="⏭️ Skipping track (player)"))
                await log_action(bot, ctx.author.id, 'skip', {'via': 'player'})
                return

            await ctx.send("Could not skip: nothing is playing.")
        except Exception as exc:
            await ctx.send(f"Could not skip: {exc}")
            await log_action(bot, ctx.author.id, 'skip_failed', {'error': str(exc)})

    @bot.tree.command(name='skip')
    async def _skip_slash(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        perms = interaction.user.guild_permissions
        now = time.time()
        last = _last_skip.get(interaction.user.id, 0)
        if not perms.manage_guild and now - last < _skip_cooldown:
            rem = int(_skip_cooldown - (now - last))
            await interaction.followup.send(f'Skip is on cooldown. Try again in {rem}s.', ephemeral=True)
            return
        _last_skip[interaction.user.id] = now
        ctx = await commands.Context.from_interaction(interaction)
        await _skip(ctx)


    class SkipView(discord.ui.View):
        def __init__(self, bot):
            super().__init__(timeout=300)
            self.bot = bot

        @discord.ui.button(label='Skip', style=discord.ButtonStyle.secondary, custom_id='sonus_skip')
        async def skip_button(self, button: discord.ui.Button, interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=True)
            ctx = await commands.Context.from_interaction(interaction)
            await _skip(ctx)
