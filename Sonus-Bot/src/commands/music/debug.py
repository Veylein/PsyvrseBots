import asyncio
from typing import Optional

import discord
from discord.ext import commands
import yt_dlp

from src.commands.music.play import YTDL_OPTS
from src.logger import setup_logger

logger = setup_logger(__name__)


def register(bot: commands.Bot):
    # Avoid defining `audiotest` if it already exists (play.py also defines it)
    if bot.get_command('audiotest') is None:
        @bot.command(name='audiotest')
        async def _audiotest(ctx: commands.Context, *, query: str):
            """Test yt-dlp extraction and FFmpeg probe for a URL or query."""
            await ctx.send('Testing extraction...')
            loop = asyncio.get_running_loop()

            def run_extract(q):
                try:
                    with yt_dlp.YoutubeDL(YTDL_OPTS) as ytdl:
                        return ytdl.extract_info(q, download=False)
                except Exception as e:
                    return {'_extract_error': str(e)}

            info = await loop.run_in_executor(None, run_extract, query)
            if not info:
                await ctx.send('Extraction returned no data.')
                return
            if isinstance(info, dict) and info.get('_extract_error'):
                await ctx.send(f"Extraction error: {info.get('_extract_error')}")
                logger.error('audiotest extract error for %s: %s', query, info.get('_extract_error'))
                return

            title = info.get('title') or info.get('id')
            formats = len(info.get('formats') or [])
            webpage = info.get('webpage_url')
            await ctx.send(f'Extracted: {title} — {formats} formats — webpage: {webpage}')

            # try to select audio url
            def select_audio(info):
                if info.get('url'):
                    return info['url']
                formats = info.get('formats') or []
                audio_only = [f for f in formats if (not f.get('vcodec') or f.get('vcodec') == 'none') and f.get('acodec') and f.get('acodec') != 'none']
                if audio_only:
                    audio_only.sort(key=lambda f: (f.get('abr') or 0, f.get('tbr') or 0), reverse=True)
                    return audio_only[0].get('url')
                for f in formats:
                    if f.get('url'):
                        return f.get('url')
                return None

            source_url = select_audio(info)
            if not source_url:
                await ctx.send('Could not pick an audio URL from formats.')
                return

            await ctx.send('Probing ffmpeg...')
            try:
                src = discord.FFmpegOpusAudio.from_probe(source_url, before_options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', options='-vn')
                await ctx.send('FFmpeg probe succeeded (source created).')
                logger.info('audiotest probe succeeded for %s', query)
                try:
                    src.cleanup()
                except Exception:
                    pass
            except Exception as e:
                await ctx.send(f'FFmpeg probe failed: {e}')
                logger.exception('audiotest ffmpeg probe failed for %s', query)

    if bot.tree.get_command('audiotest') is None:
        @bot.tree.command(name='audiotest')
        async def _audiotest_slash(interaction: discord.Interaction, query: str):
            await interaction.response.defer()
            ctx = await commands.Context.from_interaction(interaction)
            await _audiotest(ctx, query=query)

    @bot.command(name='postlogs')
    async def _postlogs(ctx: commands.Context, lines: int = 200):
        """Post recent logs to the configured dev audit channel."""
        logger_root = setup_logger()
        ring = getattr(logger_root, '_ring_handler', None)
        if not ring:
            await ctx.send('No in-memory logs available.')
            return
        recent = ring.recent(lines)
        text = "\n".join(recent) or "(no logs)"
        try:
            dev_channel_id = 1462019773755035731
            ch = ctx.bot.get_channel(dev_channel_id)
            if ch:
                # send as file if too long
                from io import StringIO
                bio = StringIO(text)
                bio.seek(0)
                await ch.send(content=f'Log dump from {ctx.author}:', file=discord.File(bio, filename='sonus_logs.txt'))
                await ctx.send('Posted logs to dev channel.')
            else:
                await ctx.send('Dev channel not found in this bot instance.')
        except Exception as e:
            logger.exception('Failed to post logs: %s', e)
            await ctx.send(f'Failed to post logs: {e}')

    @bot.tree.command(name='postlogs')
    async def _postlogs_slash(interaction: discord.Interaction, lines: int = 200):
        await interaction.response.defer()
        ctx = await commands.Context.from_interaction(interaction)
        await _postlogs(ctx, lines=lines)
