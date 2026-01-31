# Eventus-Bot — Quick Admin Guide

This file documents common admin tasks for local development: initializing the DB, running the importer script, and using the in-bot importer command.

Prerequisites
- Python 3.10+ and dependencies from `requirements.txt`.
- Optional: set `DATABASE_URL` to use Postgres instead of SQLite.

Initialize / migrate the database (SQLite)

```powershell
python migrations/run_init_db.py
```

This runs the async `init_db()` in `eventus_render_mega.py` and creates the required tables.

Importing JSON exports (file-based)

- Create an export using the bot's export commands (see `cogs/activity.py`).
- Merge the export into your local DB using the script (dry-run by default):

```powershell
python scripts/import_stats.py --file path/to/backup.json --dry-run
```

- To actually apply changes, omit `--dry-run`:

```powershell
python scripts/import_stats.py --file path/to/backup.json
```

Notes:
- The script uses safe merge rules: users are upserted (scores summed), messages are inserted if missing, and pings/rewards are upserted where possible.
- For Postgres (when `DATABASE_URL` is set) the script will attempt Postgres-friendly SQL. You may need to run migrations against the Postgres instance first.

In-bot importer (attachment, dry-run by default)

- Use the prefix command in server where the bot is present (admin only):
  - `E!import_stats` with a JSON file attached to the message — performs a dry-run
  - `E!import_stats --apply` with attachment — applies changes

- Slash command (admin only): `/import_stats` — attach file and set `apply` flag to true to write

Safety
- Imports are idempotent via upserts; however always run a dry-run first and review the planned actions before applying.

Next steps
- Add Postgres CI tests and more robust conflict resolution for complex merges.
# Eventus — Chat Engagement Bot

Eventus is a Discord bot designed to keep servers active by posting discussion topics, tracking activity, rewarding contributors, and providing configurable admin controls.

## Quick start

1. Create a Python 3.10+ virtualenv and install dependencies:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

2. Set environment variables (Windows example):

```powershell
$env:EVENTUS_TOKEN = "your_bot_token"
$env:DATABASE_URL = "postgres://user:pass@host/dbname" # optional, default uses SQLite
```

3. Initialize the database (SQLite or Postgres path supported):

- For SQLite (default):

```bash
python migrations/apply_migrations.py
# or in code the bot will auto-run init_db() on startup
```

- For Postgres: set `DATABASE_URL` and ensure the database exists. The code path attempts to use `asyncpg` when available.

4. Run the bot:

```bash
python start.py
```

## Configuration & DB

- Primary DB file (SQLite): `eventus.db` in the repo root.
- Tables created/used: `users`, `messages`, `events`, `pings`, `rewards`, `topic_settings`, `topic_opt_out`, `ignored_channels`, `ignored_roles`, `guilds`.
- If using Postgres, set `DATABASE_URL` to use `asyncpg` for async DB access.

## Core features and main commands

Topic system (auto-posting):
- `E!topic [category]` — drop a topic immediately.
- `E!set_topic_channel <#channel>` — set where topics auto-post.
- `E!set_topic_interval <minutes>` — configure interval.
- `E!add_topic <text>` / `E!list_topics` / `E!remove_topic <index>` — manage custom topics.
- `E!enable_topics` / `E!disable_topics` — toggle auto-posting.

Activity & leaderboards:
- `E!aip [user]` — Activity Intelligence Profile for a user.
- `E!server_stats` — top members, channels, recent activity.
- `E!leaderboard [top]` — top active users by score.

Pings & opt-out:
- `E!add_ping <#channel> [interval_minutes] [top_n]` — configure ping for top contributors.
- `E!list_pings`, `E!remove_ping <id>` — manage pings.
- `E!ping_optout` / `E!ping_optin` — users opt out/in of pinging.
- `E!list_optouts` — admin list of opted-out users.

Ignored channels/roles (admin):
- `E!ignore_channel <#channel>` / `E!unignore_channel <#channel>` / `E!list_ignored_channels`
- `E!ignore_role <role>` / `E!unignore_role <role>` / `E!list_ignored_roles`

Data export (admin):
- `E!export_stats` — export `users`, `events`, `pings`, `rewards`, `topic_settings`, `ignored_*` tables as JSON and upload to Discord.
- `E!export_messages [limit]` — export recent messages for the guild.

Admin-only commands require `Manage Server` permissions.

## Anti-spam & fairness

- A simple per-user rate limiter prevents counting more than a configurable number of messages per short window (default 6 messages / 60s). Messages are still stored but not scored if exceeding the limiter.
- Server admins can ignore channels or roles to prevent counting.
- Topics avoid posting repeated or near-duplicate prompts using simple token similarity checks.

## Migrations & maintenance

- SQL migrations are under `migrations/*.sql`. Use `migrations/apply_migrations.py` to apply any pending migrations to `eventus.db`.
- There is a helper `migrations/run_init_db.py` which will call the code-based `init_db()` function.

## Production notes

- For larger servers, use Postgres and set `DATABASE_URL`. Ensure `asyncpg` is installed (already in `requirements.txt`).
- Consider running the bot in a process manager (systemd/pm2) and monitoring logs.

## Development

- Cogs live in `cogs/` — `activity.py`, `topicai.py`, `eventos.py`, etc.
- Add or modify topics in `topicai.py` or via `E!add_topic`.
- Tests: a minimal `pytest` setup is included (see `requirements.txt`).

## Next recommended improvements

- Add full import/restore functionality with conflict resolution for JSON backups.
- Replace simple similarity checks with a lightweight embedding-based semantic check if available.
- Add a web dashboard for per-guild settings and visual leaderboards.

If you want, I can:
- Wire Postgres/asyncpg migrations and automatic migration runner.
- Add an import/restore command (careful with merges).
- Produce a short admin quickstart `README` for server operators.

Tell me which next step you'd like me to implement. (I can proceed autonomously.)
