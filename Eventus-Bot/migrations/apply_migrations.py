#!/usr/bin/env python3
"""Simple SQLite migration runner for eventus.db

Usage: python migrations/apply_migrations.py
It will apply any .sql files in the migrations/ folder in filename order
and record applied migrations in the `migrations` table.
"""
import os
import glob
import sqlite3
from datetime import datetime

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DB_PATH = os.path.join(ROOT, 'eventus.db')


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


def record_applied(conn, filename):
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO migrations (filename, applied_at) VALUES (?, ?)", (filename, datetime.utcnow().isoformat()))
    conn.commit()


def main():
    sql_files = sorted(glob.glob(os.path.join(os.path.dirname(__file__), '*.sql')))
    if not sql_files:
        print("No migration files found.")
        return
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
                # Continue attempting remaining migrations; some migrations may depend on runtime-created tables.
                continue
    finally:
        conn.close()


if __name__ == '__main__':
    main()
