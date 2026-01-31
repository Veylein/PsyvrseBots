#!/usr/bin/env python3
"""Simple SQLite migration runner for eventus.db

Usage: python migrations/apply_migrations.py
It will apply any .sql files in the migrations/ folder in filename order
and record applied migrations in the `migrations` table.
"""
import os
import glob
import sqlite3
import asyncio
from datetime import datetime

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DB_PATH = os.path.join(ROOT, 'eventus.db')
DATABASE_URL = os.getenv('DATABASE_URL')

try:
    import asyncpg
except Exception:
    asyncpg = None


def ensure_migrations_table(conn):
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS migrations (
        filename TEXT PRIMARY KEY,
        applied_at TEXT
    )
    """)
    conn.commit()


def get_applied(conn):
    c = conn.cursor()
    c.execute("SELECT filename FROM migrations")
    return {r[0] for r in c.fetchall()}


def apply_sql_file(conn, path):
    with open(path, 'r', encoding='utf-8') as f:
        sql = f.read()
    conn.executescript(sql)


async def apply_sql_file_async(pool, path):
    with open(path, 'r', encoding='utf-8') as f:
        sql = f.read()
    # Split statements naively on ';' but preserve multi-statement blocks
    stmts = [s.strip() for s in sql.split(';') if s.strip()]
    async with pool.acquire() as conn:
        for s in stmts:
            try:
                await conn.execute(s)
            except Exception as e:
                # try single statement execution which may include $$ blocks
                try:
                    await conn.execute(s + ';')
                except Exception:
                    raise


def record_applied(conn, filename):
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO migrations (filename, applied_at) VALUES (?, ?)", (filename, datetime.utcnow().isoformat()))
    conn.commit()


def main():
    sql_files = sorted(glob.glob(os.path.join(os.path.dirname(__file__), '*.sql')))
    if not sql_files:
        print("No migration files found.")
        return
    if DATABASE_URL and asyncpg:
        async def run_async():
            pool = await asyncpg.create_pool(DATABASE_URL)
            # ensure migrations table exists (create a simple one if not present)
            async with pool.acquire() as conn:
                await conn.execute("""
                CREATE TABLE IF NOT EXISTS migrations (
                    filename TEXT PRIMARY KEY,
                    applied_at TEXT
                )
                """)
            # get applied
            async with pool.acquire() as conn:
                rows = await conn.fetch("SELECT filename FROM migrations")
                applied = {r['filename'] for r in rows}
            for path in sql_files:
                name = os.path.basename(path)
                if name in applied:
                    print(f"Skipping already applied: {name}")
                    continue
                print(f"Applying migration to Postgres: {name}")
                try:
                    await apply_sql_file_async(pool, path)
                    async with pool.acquire() as conn:
                        await conn.execute("INSERT INTO migrations (filename, applied_at) VALUES ($1, $2)", name, datetime.utcnow().isoformat())
                    print(f"Applied: {name}")
                except Exception as e:
                    print(f"Failed to apply {name}: {e}")
                    continue
            await pool.close()

        asyncio.run(run_async())
    else:
        conn = sqlite3.connect(DB_PATH)
        try:
            ensure_migrations_table(conn)
            applied = get_applied(conn)
            for path in sql_files:
                name = os.path.basename(path)
                if name in applied:
                    print(f"Skipping already applied: {name}")
                    continue
                print(f"Applying migration: {name}")
                try:
                    apply_sql_file(conn, path)
                    record_applied(conn, name)
                    print(f"Applied: {name}")
                except Exception as e:
                    print(f"Failed to apply {name}: {e}")
                    continue
        finally:
            conn.close()


if __name__ == '__main__':
    main()
