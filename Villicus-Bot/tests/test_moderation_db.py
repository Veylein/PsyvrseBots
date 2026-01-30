import os
import sqlite3
from bot import moderation_cog as mc


def test_ensure_db_creates_file_and_table():
    # Ensure DB is created
    mc.ensure_db()
    assert os.path.exists(mc.DB_PATH)
    conn = sqlite3.connect(mc.DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='infractions'")
    row = cur.fetchone()
    conn.close()
    assert row is not None
