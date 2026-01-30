import asyncio
import importlib

import pytest


@pytest.mark.asyncio
async def test_resume_persisted_enqueues(tmp_path, monkeypatch):
    # point DB to temporary path
    dbpath = tmp_path / "enqueue.db"
    monkeypatch.setenv('SONUS_ENQUEUE_DB', str(dbpath))

    # prepare a saved enqueue state
    import src.utils.enqueue_store as es
    importlib.reload(es)
    es.save_enqueue_state(1234, {'items': ['http://example/stream'], 'added': 0, 'total': 1})

    # prepare fake play module with minimal API used by resume logic
    class FakePlay:
        def _ensure_guild_queue(self, bot, gid):
            return []

        async def _yt_search(self, q):
            return {'url': q, 'title': 't'}

        def _select_audio_url(self, e):
            return e.get('url')

        def _queue_add(self, q, track, gid):
            try:
                q.append(track)
            except Exception:
                pass

        async def _ensure_vc_connected(self, bot, guild):
            return None

        async def _play_next(self, bot, gid):
            return None

    import src.utils.enqueue_resume as er
    importlib.reload(er)
    # monkeypatch importlib used inside enqueue_resume to return our fake play
    monkeypatch.setattr(er.importlib, 'import_module', lambda name: FakePlay())

    class Bot:
        def __init__(self):
            self.sonus_enqueue_tasks = {}

        def get_guild(self, gid):
            return None

    bot = Bot()
    await er.resume_persisted_enqueues(bot)
    # allow scheduled tasks to run briefly
    await asyncio.sleep(0.05)

    states = es.load_all_enqueue_states()
    assert 1234 not in states
