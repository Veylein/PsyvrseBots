from collections import deque
from typing import Any, Dict, List, Optional


class TrackQueue:
    """A lightweight FIFO queue for track dicts used by the bot.

    This keeps a minimal API: `enqueue`/`add`, `dequeue`/`pop`, `all`, and `__len__`.
    """

    def __init__(self) -> None:
        self._items: deque[Dict[str, Any]] = deque()

    def enqueue(self, item: Dict[str, Any]) -> None:
        self._items.append(item)

    add = enqueue

    def dequeue(self) -> Optional[Dict[str, Any]]:
        if not self._items:
            return None
        return self._items.popleft()

    pop = dequeue

    def all(self) -> List[Dict[str, Any]]:
        return list(self._items)

    def __len__(self) -> int:
        return len(self._items)
 