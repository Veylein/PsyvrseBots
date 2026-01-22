import os
import aiosqlite
import asyncio

DB_PATH = os.path.join(os.path.dirname(__file__), 'eventus.db')
DATABASE_URL = os.getenv('DATABASE_URL')
_asyncpg_pool = None

try:
    import asyncpg
except Exception:
    asyncpg = None

async def _ensure_pool():
    global _asyncpg_pool
    if DATABASE_URL and asyncpg and _asyncpg_pool is None:
        _asyncpg_pool = await asyncpg.create_pool(DATABASE_URL)

async def execute(query, params=(), commit=False):
    if DATABASE_URL and asyncpg:
        await _ensure_pool()
        async with _asyncpg_pool.acquire() as conn:
            await conn.execute(query, *params)
            return None
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(query, params)
            if commit:
                await db.commit()
            return cur

async def fetchone(query, params=()):
    if DATABASE_URL and asyncpg:
        await _ensure_pool()
        async with _asyncpg_pool.acquire() as conn:
            row = await conn.fetchrow(query, *params)
            return dict(row) if row else None
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(query, params)
            row = await cur.fetchone()
            await cur.close()
            return row

async def fetchall(query, params=()):
    if DATABASE_URL and asyncpg:
        await _ensure_pool()
        async with _asyncpg_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [dict(r) for r in rows]
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(query, params)
            rows = await cur.fetchall()
            await cur.close()
            return rows

async def executescript(script):
    # For sqlite: run executescript; for postgres: split and run sequentially
    if DATABASE_URL and asyncpg:
        await _ensure_pool()
        async with _asyncpg_pool.acquire() as conn:
            for stmt in script.split(';'):
                s = stmt.strip()
                if not s:
                    continue
                await conn.execute(s)
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.executescript(script)
            await db.commit()
