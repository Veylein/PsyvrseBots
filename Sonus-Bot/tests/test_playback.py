import pytest
import asyncio

from src.commands.music.play import _select_audio_url, _yt_search


@pytest.mark.asyncio
async def test_select_audio_url_prefers_audio_format():
    info = {
        'formats': [
            {'format_id': '1', 'url': 'http://a', 'vcodec': 'none', 'acodec': 'aac', 'abr': 64},
            {'format_id': '2', 'url': 'http://b', 'vcodec': 'h264', 'acodec': 'aac', 'abr': 128},
        ]
    }
    assert _select_audio_url(info) == 'http://a'


@pytest.mark.asyncio
async def test_yt_search_returns_none_for_invalid():
    res = await _yt_search('this-is-unlikely-to-exist-12345', attempts=1, backoff=0.1)
    assert res is None
