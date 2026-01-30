import os
import sqlite3
import tempfile
from bot import moderation_cog as mc


def test_export_infractions_csv_roundtrip(tmp_path):
    # Ensure DB exists and is clean
    if os.path.exists(mc.DB_PATH):
        os.remove(mc.DB_PATH)
    mc.ensure_db()
    # insert sample infractions
    conn = sqlite3.connect(mc.DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO infractions (user_id, moderator_id, action, reason, timestamp, duration_seconds, active) VALUES (?, ?, ?, ?, ?, ?, ?)", (111, 222, 'warn', 'Test reason', 1234567890, None, 1))
    cur.execute("INSERT INTO infractions (user_id, moderator_id, action, reason, timestamp, duration_seconds, active) VALUES (?, ?, ?, ?, ?, ?, ?)", (111, 333, 'mute', 'Muted for testing', 1234567900, 600, 1))
    conn.commit()
    conn.close()

    cog = mc.ModerationCog(bot=None)
    csv_bytes = cog._export_infractions_csv(111)
    assert csv_bytes
    csv_text = csv_bytes.decode('utf-8')
    assert 'warn' in csv_text
    assert 'Muted for testing' in csv_text
