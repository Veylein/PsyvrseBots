import discord
from discord import Embed
from discord.ext import commands
from src.utils.audit import log_action


def register(bot):
    @bot.command(name="pause")
    async def _pause(ctx):
        try:
            vc = ctx.guild.voice_client
            if vc and vc.is_playing():
                vc.pause()
                await ctx.send(embed=Embed(description="⏸️ Paused"))
                await log_action(bot, ctx.author.id, 'pause', {})
                return

            # fallback to bot player
            player = getattr(bot, 'player', None)
            if player and hasattr(player, 'pause'):
                player.pause()
                await ctx.send(embed=Embed(description="⏸️ Paused (player)"))
                await log_action(bot, ctx.author.id, 'pause', {'via': 'player'})
                return

            await ctx.send("Could not pause: nothing is playing.")
        except Exception as exc:
            await ctx.send(f"Could not pause: {exc}")
            await log_action(bot, ctx.author.id, 'pause_failed', {'error': str(exc)})

    @bot.tree.command(name='pause')
    async def _pause_slash(interaction: discord.Interaction):
        await interaction.response.defer()
        ctx = await commands.Context.from_interaction(interaction)
        await _pause(ctx)
