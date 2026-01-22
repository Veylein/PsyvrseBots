import importlib
import asyncio
import inspect

import pytest

COGS = [
    'cogs.activity',
    'cogs.eventos',
    'cogs.topicai',
    'cogs.rewards',
    'cogs.dashboard',
    'cogs.owner',
    'cogs.momentum'
]

def test_import_modules():
    """Ensure all cog modules import without syntax errors and expose a setup coroutine."""
    for m in COGS:
        mod = importlib.import_module(m)
        assert hasattr(mod, 'setup'), f"Module {m} missing setup"
        assert inspect.iscoroutinefunction(mod.setup), f"setup in {m} should be async"


@pytest.mark.asyncio
async def test_db_async_api():
    """Verify async DB helper provides expected callables (non-blocking API)."""
    import db_async
    assert inspect.iscoroutinefunction(db_async.fetchone)
    assert inspect.iscoroutinefunction(db_async.fetchall)
    assert inspect.iscoroutinefunction(db_async.execute)


@pytest.mark.asyncio
async def test_llm_absent_or_callable():
    """LLM client should be importable; if API key missing functions return None rather than raise."""
    try:
        import llm
    except Exception:
        pytest.skip("LLM helper not importable")
    # If API key is not configured, polish_text should return None when awaited
    if not getattr(llm, 'OPENAI_API_KEY', None):
        out = await llm.polish_text('Test')
        assert out is None
    else:
        # If key present, ensure coroutine exists
        assert inspect.iscoroutinefunction(llm.polish_text)
