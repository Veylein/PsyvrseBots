from src.logger import setup_logger

logger = setup_logger(__name__)


def register(bot):
    @bot.event
    async def on_voice_state_update(member, before, after):
        # Track joins/leaves, auto-disconnect and reconnection logic for the bot.
        logger.debug("Voice state update for %s", getattr(member, "id", None))
        try:
            # only care about events affecting the bot itself
            if not getattr(bot, 'user', None) or member.id != bot.user.id:
                return

            # bot was disconnected from a channel unexpectedly
            try:
                before_chan = getattr(before, 'channel', None)
                after_chan = getattr(after, 'channel', None)
            except Exception:
                before_chan = None
                after_chan = None

            if before_chan and not after_chan:
                guild = before_chan.guild
                # determine if there is active or pending playback for this guild
                qmap = getattr(bot, 'sonus_queues', {}) or {}
                q = qmap.get(guild.id) if guild else None
                if not q:
                    q = getattr(bot, 'player', None)
                has_pending = False
                try:
                    if q:
                        if hasattr(q, 'all') and callable(q.all):
                            has_pending = bool(q.all())
                        else:
                            # attempt to coerce to list
                            has_pending = bool(list(q))
                except Exception:
                    has_pending = False

                now_playing = getattr(bot, 'sonus_now_playing', None)
                # only attempt reconnect if there's something to play or resume
                if has_pending or now_playing:
                    try:
                        import asyncio
                        from src.commands.music.play import _ensure_vc_connected

                        logger.info('Bot disconnected from voice in guild %s; attempting reconnect', getattr(guild, 'id', None))
                        # try a few times with small backoff
                        for attempt in range(3):
                            try:
                                vc = await _ensure_vc_connected(bot, guild, preferred_channel_id=before_chan.id if before_chan else None, attempts=2)
                                if vc:
                                    logger.info('Reconnected to voice in guild %s on attempt %d', getattr(guild, 'id', None), attempt + 1)
                                    break
                            except Exception:
                                logger.debug('Reconnect attempt %d failed for guild %s', attempt + 1, getattr(guild, 'id', None))
                            await asyncio.sleep(1 + attempt)
                    except Exception:
                        logger.exception('Failed during reconnection attempts')

        except Exception:
            logger.exception('Error handling voice state update')
