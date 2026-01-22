import asyncio
from collections import deque
from typing import Optional


class Player:
    def __init__(self):
        self._q = deque()
        self.current: Optional[dict] = None
        self._playing = False
        self._paused = False
        self._skip_requested = False

    def enqueue(self, item: dict):
        self._q.append(item)

    def dequeue(self) -> Optional[dict]:
        return self._q.popleft() if self._q else None

    def peek(self) -> Optional[dict]:
        return self._q[0] if self._q else None

    def all(self):
        return list(self._q)

    def is_playing(self) -> bool:
        return self._playing and not self._paused

    def pause(self):
        self._paused = True

    def resume(self):
        self._paused = False

    def skip(self):
        self._skip_requested = True

    def clear(self):
        self._q.clear()

    async def play_loop(self, bot):
        # simple background loop that simulates playback and updates bot state
        while True:
            if not self._q:
                self.current = None
                self._playing = False
                # clear now_playing on bot
                try:
                    bot.sonus_now_playing = None
                except Exception:
                    pass
                await asyncio.sleep(1)
                continue

            track = self.dequeue()
            self.current = track
            self._playing = True
            self._paused = False
            self._skip_requested = False

            # expose now playing metadata to bot for other commands
            try:
                bot.sonus_now_playing = track
            except Exception:
                pass

            # simulate playing by sleeping for track duration (fallback 5s)
            duration = track.get("duration", 5)
            elapsed = 0.0
            interval = 0.5
            while elapsed < duration:
                if self._skip_requested:
                    break
                if self._paused:
                    await asyncio.sleep(interval)
                    continue
                await asyncio.sleep(interval)
                elapsed += interval

            # finished track or skipped
            self._skip_requested = False
            self.current = None
            # loop continues to next track
