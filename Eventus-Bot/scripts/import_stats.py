"""
Simple import/restore script for Eventus-Bot SQLite exports.

Usage:
  python scripts/import_stats.py --file backup.json [--dry-run]

This script merges exported JSON into the local `eventus.db` SQLite file.
Merge rules (safe defaults):
- Users: upsert by user_id, sum `activity_score` and keep latest `last_active`.
- Messages: insert messages that do not already exist (by message_id).
- Pings/rewards: insert if not duplicate (best-effort by id/timestamp).

This is intended as a local admin utility. For Postgres or remote DBs,
adjust the DB path/driver as needed.
"""

import argparse
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path


def parse_args():
    p = argparse.ArgumentParser(description="Import Eventus JSON export into SQLite DB")
    p.add_argument("--file", "-f", required=True, help="Path to JSON export file")
    p.add_argument("--db", default="Eventus-Bot/eventus.db", help="Path to SQLite DB file")
    p.add_argument("--dry-run", action="store_true", help="Show actions without applying them")
    return p.parse_args()


def load_export(path: Path):
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def ensure_tables(conn: sqlite3.Connection):
    # minimal checks - assume migrations/init already run
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys = ON")
    conn.commit()


def upsert_users(conn, users, dry_run=False):
    cur = conn.cursor()
    actions = []
    for u in users:
        user_id = u.get("user_id") or u.get("id")
        if user_id is None:
            continue
        score = u.get("activity_score", 0)
        last_active = u.get("last_active")
        if last_active:
            # normalize common formats
            try:
                last_active_ts = datetime.fromisoformat(last_active)
            except Exception:
                last_active_ts = None
        else:
            last_active_ts = None

        cur.execute("SELECT activity_score, last_active FROM users WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        if row is None:
            actions.append(("insert_user", user_id, score, last_active))
            if not dry_run:
                cur.execute(
                    "INSERT INTO users (user_id, activity_score, last_active) VALUES (?,?,?)",
                    (user_id, score, last_active),
                )
        else:
            new_score = (row[0] or 0) + score
            existing_last = row[1]
            latest_last = last_active if (not existing_last or (last_active and last_active > existing_last)) else existing_last
            actions.append(("update_user", user_id, new_score, latest_last))
            if not dry_run:
                cur.execute(
                    "UPDATE users SET activity_score = ?, last_active = ? WHERE user_id = ?",
                    (new_score, latest_last, user_id),
                )
    if not dry_run:
        conn.commit()
    return actions


def insert_messages(conn, messages, dry_run=False):
    cur = conn.cursor()
    actions = []
    for m in messages:
        mid = m.get("message_id") or m.get("id")
        if mid is None:
            continue
        cur.execute("SELECT 1 FROM messages WHERE message_id = ?", (mid,))
        if cur.fetchone():
            continue
        actions.append(("insert_message", mid))
        if not dry_run:
            cur.execute(
                "INSERT INTO messages (message_id, user_id, guild_id, channel_id, content, created_at) VALUES (?,?,?,?,?,?)",
                (
                    mid,
                    m.get("user_id"),
                    m.get("guild_id"),
                    m.get("channel_id"),
                    m.get("content"),
                    m.get("created_at"),
                ),
            )
    if not dry_run:
        conn.commit()
    return actions


def insert_generic_table(conn, table, items, key_field, dry_run=False):
    cur = conn.cursor()
    actions = []
    for it in items:
        key = it.get(key_field)
        if key is None:
            continue
        cur.execute(f"SELECT 1 FROM {table} WHERE {key_field} = ?", (key,))
        if cur.fetchone():
            continue
        actions.append(("insert", table, key))
        if not dry_run:
            # naive insertion: try to insert all fields that exist in DB table
            cols = list(it.keys())
            placeholders = ",".join("?" for _ in cols)
            sql = f"INSERT INTO {table} ({','.join(cols)}) VALUES ({placeholders})"
            try:
                cur.execute(sql, tuple(it[c] for c in cols))
            except Exception:
                # best-effort; skip rows that can't be inserted
                continue
    if not dry_run:
        conn.commit()
    return actions


def main():
    args = parse_args()
    path = Path(args.file)
    if not path.exists():
        print("Export file not found:", path)
        sys.exit(2)

    data = load_export(path)

    conn = sqlite3.connect(args.db)
    ensure_tables(conn)

    total_actions = []
    users = data.get("users") or []
    messages = data.get("messages") or []
    pings = data.get("pings") or []
    rewards = data.get("rewards") or []

    print(f"Loaded export: users={len(users)}, messages={len(messages)}, pings={len(pings)}, rewards={len(rewards)}")

    a = upsert_users(conn, users, dry_run=args.dry_run)
    total_actions.extend(a)

    a = insert_messages(conn, messages, dry_run=args.dry_run)
    total_actions.extend(a)

    # best-effort inserts for pings/rewards
    if pings:
        a = insert_generic_table(conn, "pings", pings, "ping_id", dry_run=args.dry_run)
        total_actions.extend(a)
    if rewards:
        a = insert_generic_table(conn, "rewards", rewards, "reward_id", dry_run=args.dry_run)
        total_actions.extend(a)

    # summary
    print("Actions:")
    counts = {}
    for act in total_actions:
        counts[act[0]] = counts.get(act[0], 0) + 1
    for k, v in counts.items():
        print(f" - {k}: {v}")

    if args.dry_run:
        print("Dry run complete — no changes applied.")
    else:
        print("Import complete — DB updated.")


if __name__ == "__main__":
    main()
