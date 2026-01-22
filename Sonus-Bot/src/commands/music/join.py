import discord
from discord.ext import commands
from src.utils.audit import log_action


def register(bot: commands.Bot):
    @bot.command(name='join')
    async def _join(ctx: commands.Context):
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.reply('You are not in a voice channel.', mention_author=False)
            return
        channel = ctx.author.voice.channel
        vc = ctx.guild.voice_client
        try:
            if vc and vc.channel == channel:
                await ctx.send(f'Already connected to {channel.name}.')
            elif vc:
                await vc.move_to(channel)
                await ctx.send(f'Moved to {channel.name}')
            else:
                await channel.connect()
                await ctx.send(f'Joined {channel.name}')
            await log_action(bot, ctx.author.id, 'join', {'channel': channel.name})
        except Exception as exc:
            await ctx.send(f'Failed to join voice channel: {exc}')
            await log_action(bot, ctx.author.id, 'join_failed', {'channel': getattr(channel, 'name', None), 'error': str(exc)})

    @bot.tree.command(name='join')
    async def _join_slash(interaction: discord.Interaction):
        await interaction.response.defer()
        ctx = await commands.Context.from_interaction(interaction)
        await _join(ctx)
