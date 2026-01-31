"""Run a simple smoke test for the importer using a temporary SQLite DB.

This script:
- creates a temp SQLite DB with minimal schema
- writes a small export JSON file
- runs the importer script with `--dry-run` and then without it against the temp DB
- verifies that rows were inserted

Run: python tests/run_importer_smoke.py
"""
import json
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path


SCHEMA_SQL = r"""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    activity_score INTEGER DEFAULT 0,
    momentum INTEGER DEFAULT 0,
    streak INTEGER DEFAULT 0,
    last_active TEXT,
    topic_influence REAL DEFAULT 0,
    multi_channel_presence TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS messages (
    message_id INTEGER PRIMARY KEY,
    guild_id INTEGER,
    channel_id INTEGER,
    user_id INTEGER,
    created_at TEXT,
    content TEXT
);
CREATE TABLE IF NOT EXISTS pings (
    ping_id INTEGER PRIMARY KEY,
    guild_id INTEGER,
    channel_id INTEGER,
    interval_minutes INTEGER DEFAULT 60,
    top_n INTEGER DEFAULT 3,
    last_sent TEXT
);
CREATE TABLE IF NOT EXISTS rewards (
    reward_id INTEGER PRIMARY KEY,
    guild_id INTEGER,
    role_id INTEGER,
    criteria TEXT,
    tier INTEGER DEFAULT 0
);
"""


def main():
    root = Path(__file__).parent.parent
    script = root / "scripts" / "import_stats.py"
    if not script.exists():
        print("Importer script not found at:", script)
        sys.exit(2)

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        db_path = td / "temp_eventus.db"
        # create sqlite schema
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.executescript(SCHEMA_SQL)
        conn.commit()
        conn.close()

        # create export json
        export = {
            "users": [{"user_id": 12345, "activity_score": 10, "last_active": "2026-01-01T00:00:00"}],
            "messages": [{"message_id": 111, "user_id": 12345, "guild_id": 1, "channel_id": 2, "content": "hello", "created_at": "2026-01-01T00:00:00"}],
            "pings": [{"ping_id": 1, "guild_id": 1, "channel_id": 2, "interval_minutes": 60, "top_n": 3}],
            "rewards": [{"reward_id": 1, "guild_id": 1, "role_id": 99, "criteria": "test", "tier": 1}],
        }
        export_path = td / "export.json"
        with export_path.open("w", encoding="utf-8") as fh:
            json.dump(export, fh)

        # dry-run
        print("Running dry-run...")
        r = subprocess.run([sys.executable, str(script), "--file", str(export_path), "--db", str(db_path), "--dry-run"], capture_output=True, text=True)
        print(r.stdout)
        if r.returncode != 0:
            print("Dry-run failed:", r.stderr)
            sys.exit(3)

        # apply
        print("Applying import...")
        r2 = subprocess.run([sys.executable, str(script), "--file", str(export_path), "--db", str(db_path)], capture_output=True, text=True)
        print(r2.stdout)
        if r2.returncode != 0:
            print("Apply failed:", r2.stderr)
            sys.exit(4)

        # verify
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT activity_score, last_active FROM users WHERE user_id = ?", (12345,))
        row = cur.fetchone()
        assert row is not None and row[0] == 10, "User not inserted or score mismatch"
        cur.execute("SELECT 1 FROM messages WHERE message_id = ?", (111,))
        assert cur.fetchone() is not None, "Message not inserted"
        cur.execute("SELECT 1 FROM pings WHERE ping_id = ?", (1,))
        assert cur.fetchone() is not None, "Ping not inserted"
        cur.execute("SELECT 1 FROM rewards WHERE reward_id = ?", (1,))
        assert cur.fetchone() is not None, "Reward not inserted"
        conn.close()

        print("Smoke test passed: importer inserted expected rows into temp DB.")


if __name__ == "__main__":
    main()
