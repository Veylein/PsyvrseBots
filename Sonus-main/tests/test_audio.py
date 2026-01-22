import pytest
from src.audio.queue import TrackQueue


def test_queue_add_pop():
    q = TrackQueue()
    q.add({"title":"t"})
    assert q.pop()["title"] == "t"
