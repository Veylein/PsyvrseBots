"""
utils/stat_hooks.py
===================
Fire-and-forget helpers for recording game results into data/users/{id}.json.

Import in any cog:
    from utils.stat_hooks import us_inc, us_mg, us_touch

All functions are safe to call from sync code – they schedule an asyncio Task
and immediately return without blocking.

us_touch(user_id, username=None)
    Ensure the user file exists / refresh last_active.

us_inc(user_id, stat_name, amount=1, username=None)
    Increment any stat counter (e.g. 'blackjack_wins', 'achievements_unlocked').

us_mg(user_id, game_name, result, coins=0, username=None)
    Record a minigame result ('win' | 'loss' | 'draw').
    Updates minigames.by_game.{game_name} and stats.minigames_played/won.
"""

from __future__ import annotations

import asyncio
from typing import Optional

try:
    from utils.user_storage import (
        touch_user        as _touch,
        increment_stat    as _inc,
        record_minigame_result as _mg,
        set_stat          as _set,
    )
    _available = True
except Exception:
    _touch = _inc = _mg = _set = None
    _available = False


def _task(coro):
    """Schedule a coroutine as an asyncio Task if a loop is running."""
    if coro is None:
        return
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(coro)
    except RuntimeError:
        pass  # no running loop – skip silently


def us_touch(user_id: int, username: Optional[str] = None) -> None:
    """Ensure user file exists + refresh last_active. Safe to call anywhere."""
    if not _available:
        return
    try:
        _task(_touch(int(user_id), username))
    except Exception:
        pass


def us_inc(user_id: int, stat_name: str,
           amount: int = 1, username: Optional[str] = None) -> None:
    """Increment a stat counter in data/users/{id}.json. Safe to call anywhere."""
    if not _available:
        return
    try:
        _task(_inc(int(user_id), stat_name, amount, username))
    except Exception:
        pass


def us_mg(user_id: int, game_name: str, result: str,
          coins: int = 0, username: Optional[str] = None) -> None:
    """
    Record a minigame/game result in data/users/{id}.json.
    result: 'win' | 'loss' | 'draw'
    """
    if not _available:
        return
    try:
        _task(_mg(int(user_id), game_name, result, coins, username))
    except Exception:
        pass


def us_set(user_id: int, stat_name: str,
           value: int, username: Optional[str] = None) -> None:
    """Set a stat to an absolute value in data/users/{id}.json. Safe to call anywhere."""
    if not _available or _set is None:
        return
    try:
        _task(_set(int(user_id), stat_name, value, username))
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Challenge event hook  (requires bot to be registered via us_set_bot)
# ---------------------------------------------------------------------------

_bot_ref = None


def us_set_bot(bot) -> None:
    """Register the bot instance so us_challenge can find the GameChallenges cog.
    Call this once in bot.py after the bot object is created:
        from utils.stat_hooks import us_set_bot
        us_set_bot(bot)
    """
    global _bot_ref
    _bot_ref = bot


def us_challenge(
    user_id: int,
    event_type: str,
    amount: int = 1,
    game_name: Optional[str] = None,
) -> None:
    """Notify the GameChallenges cog of a game event so it can update challenge progress.

    Parameters
    ----------
    user_id    : Discord user ID
    event_type : one of game_win, coin_earn, game_played, word_game_win,
                 math_game_win, social_game, board_game_win, puzzle_win,
                 trivia_correct, speed_win
    amount     : points / count to add (default 1)
    game_name  : required for event_type="game_played" (play_variety tracking)

    Usage in any cog::

        from utils.stat_hooks import us_challenge
        us_challenge(ctx.author.id, "game_win")
    """
    if _bot_ref is None:
        return
    try:
        cog = _bot_ref.get_cog("GameChallenges")
        if cog is not None:
            cog.record_game_event(int(user_id), event_type, amount, game_name)
    except Exception:
        pass
