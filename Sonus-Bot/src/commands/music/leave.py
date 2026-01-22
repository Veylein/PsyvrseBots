import discord
from discord.ext import commands
from src.utils.audit import log_action


def register(bot: commands.Bot):
    @bot.command(name='leave')
    async def _leave(ctx: commands.Context):
        vc = ctx.guild.voice_client
        if not vc:
            await ctx.reply('Not connected.', mention_author=False)
            return
        try:
            channel_name = getattr(vc.channel, 'name', None)
            await vc.disconnect()
            await ctx.send('Left voice channel.')
            await log_action(bot, ctx.author.id, 'leave', {'channel': channel_name})
        except Exception as exc:
            await ctx.send(f'Failed to leave voice channel: {exc}')
            await log_action(bot, ctx.author.id, 'leave_failed', {'error': str(exc)})

    @bot.tree.command(name='leave')
    async def _leave_slash(interaction: discord.Interaction):
        await interaction.response.defer()
        ctx = await commands.Context.from_interaction(interaction)
        await _leave(ctx)
