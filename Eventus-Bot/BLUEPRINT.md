# Ultimate Activity & Event Bot — Architecture Blueprint

**Purpose:** A complete blueprint for the "Ultimate Activity & Event" Discord bot — an open-source, free-to-run community engagement platform that automates activity tracking, event scheduling, rewards, channel management, and optional AI-driven topic suggestions and analytics.

**Scope of this document:** architecture, data model, commands & flows, components, deployment, security, testing, and a prioritized roadmap to implement the features described in the project plan.

**Core Vision:** Keep servers lively through automated recognition, scheduled events, smart reminders, and gamified rewards, while giving admins simple controls and transparency.

**1. High-Level Architecture**
- **Bot Core**: `eventus_render_mega.py` — bootstraps the bot, loads cogs, initializes DB.
- **Cogs (modular features)**: `cogs/activity.py`, `cogs/eventos.py`, `cogs/rewards.py`, `cogs/topicai.py`, `cogs/dashboard.py`, `cogs/momentum.py`, `cogs/owner.py`, `cogs/rules.py`.
- **Database**: SQLite for single-process / prototyping (`eventus.db`). Abstract DB access via helper functions; move to `aiosqlite` for async DB or PostgreSQL for production.
- **Scheduler / Background Tasks**: `discord.ext.tasks` for in-bot periodic jobs (ping_task, reward application, weekly analytics). For high scale, run dedicated worker processes and use Redis + APScheduler or Celery.
- **Optional Web Dashboard**: separate FastAPI/Flask service (optional) exposing admin UI and analytics; use JWT/OAuth for authentication.
- **AI Services**: external LLM or local model for topic suggestions; call via async HTTP client with rate-limits and caching.

**2. Data Model** (current + recommended extensions)
- `users` (user_id PRIMARY KEY): activity_score, momentum, streak, last_active, topic_influence, multi_channel_presence, username
- `events` (event_id PK): title, description, creator_id, start_time, end_time, rsvp_list (CSV or JSON), recurring, archived, channel_id, message_id
- `messages` (message_id PK): guild_id, channel_id, author_id, created_at, content (truncated), reaction_summary
- `pings` (ping_id PK): guild_id, channel_id, interval_minutes, top_n, last_sent, enabled
- `rewards` (reward_id PK): guild_id, role_id, criteria (string), tier, last_applied
- `analytics` (snapshot_id PK): created_at, data (JSON/text)
- `migrations` (migration_id PK): created_at, description, version — for safe schema evolution

Notes: prefer storing structured JSON (e.g., RSVPs as JSON array) rather than CSV for robustness; if moving to PostgreSQL, use JSONB columns.

**3. Command & API Surface**
- Prefix & Hybrid commands supported. Primary UX: slash commands + config via web dashboard (if provided).
- Activity Commands
  - `/aip [user]` or `E!aip`: show Activity Intelligence Profile
  - Internal listeners: `on_message`, `on_reaction_add` to update scores
- Ping Management (admins)
  - `/add_ping <channel> <interval_minutes> <top_n>` (E!add_ping) — schedule dynamic pings
  - `/list_pings`, `/remove_ping <id>`
- Events & RSVPs
  - `/create_event title description [--start --end --recurrence]` (E!create_event)
  - `/rsvp <event_id>`, `/remind_rsvp <event_id>`
  - `/archive_event`, `/create_event_thread`
- Rewards & Roles
  - `/add_reward <role> <tier> <criteria>` (admin), `/list_rewards`
  - automated daily/weekly reward application task
- Dashboard & Analytics
  - `/dashboard` returns weekly snapshot
  - `/export [json|csv|embed]` for owners
- Owner/Moderation
  - `/override`, `/purge_inactive`, `/tune`, `/silence`

Design note: implement both prefix and slash variants for migrations; prefer slash in UX and mark admin ops with `@commands.has_permissions(manage_guild=True)`.

**4. Activity Monitoring & Scoring**
- Listener points: `on_message`, `on_message_edit`, `on_reaction_add`, optionally voice state updates.
- Scoring model (initial): message base weight (1), reply (2), starter (3), reactions (1.5). Add decay function: hourly or daily decay (e.g., multiply activity_score by 0.98/day) to keep leaderboards fresh.
- Multi-channel presence: reward users who participate across multiple channels by counting unique channel IDs per period.
- Streaks: consecutive-day participation increments `streak`, reset after inactivity window.
- Persist top-N leaderboards per guild (cache in-memory + persist snapshot in DB for analytics).

**5. Dynamic Pings Workflow**
1. Admin configures ping via `add_ping` (channel, interval, top_n).
2. Background task queries `pings` table every minute/hour and determines which pings are due (compare last_sent + interval).
3. For due ping: query top `N` users in that guild by `activity_score`, format mentions, and post a configurable template message in target channel; update `last_sent`.
4. Respect per-user cooldowns (opt-out list) and role-level opt-outs (e.g., do not ping moderators or bots).

**6. Event Scheduler & Reminders**
- Use `events.recurring` to store recurrence rules (RFC5545/cron style or simplified: daily/weekly/monthly + interval).
- A background worker checks upcoming events and sends reminders at configurable intervals (e.g., 24h, 1h, 15m). Store scheduled reminders in DB.
- When an event is created: create event message, optionally create a thread and attach reaction-based RSVP or a slash-button RSVP UI (Buttons + Views in discord.py).
- RSVP management: store RSVPs as JSON refs in DB; provide `/remind_rsvp` to DM non-RSVPd users or post in announce channel.

**7. Role Rewards & Prizes**
- Reward assignment strategies:
  - Activity thresholds (e.g., activity_score >= X)
  - Event participation (e.g., attended Y events in last month)
  - Tournaments / winners via manual award commands
- Implementation: `rewards` table + daily job that evaluates criteria and assigns roles. Use safe eval or small DSL for `criteria` (e.g., `activity_score>=10 && momentum>=5`).
- Support tiering: tier 0..N and TTL for temporary roles (remove after TTL).

**8. Channel & Announcement Management**
- Automatic event channels/threads creation with templated names and permission presets.
- Announcement templates stored per-guild in `guilds` settings table; provide admin command to preview/edit templates.

**9. Permissions & Security**
- Use Discord's permission checks for admin commands: `manage_guild`, `manage_roles`, `manage_events`.
- Protect owner-only commands by checking `OWNER_IDS`.
- Limit DMing users (respect DND and privacy) and provide opt-out: store `opt_out` per user.
- Sanitize any user-provided strings; avoid arbitrary code execution when evaluating reward criteria.

**10. AI-Powered Topic Suggestions (Optional)**
- Analyze channel messages (sampled) to surface trending keywords; feed into an LLM for phrasing topics.
- Provide `/topic [category]` and scheduled topics; ensure rate limits and safety filters.

**11. Gamification & Leaderboards (Optional)**
- Points & streaks, badges, levels, seasonal leaderboards, and private channels unlocked by tier.
- Consider persistent Redis for ephemeral leaderboard caches and fast queries.

**12. Analytics Dashboard**
- Minimal: weekly `analytics` snapshots stored in DB and displayed by `cogs/dashboard.py`.
- Advanced: expose REST API endpoints (FastAPI) to fetch historical analytics; front-end can be static site or single-page app.

**13. Testing & CI**
- Unit tests for DB helpers and scoring logic (pytest). Mock Discord `Context` and `Member` where needed.
- Integration tests: test cogs' core commands via simulated bot client or separate test bot.
- Linting: `flake8`/`ruff` and formatting with `black`.
- CI: run tests on push, build artefacts, and optionally run a lint job.

**14. Deployment & Scaling**
- Development: run with `python eventus_render_mega.py` and env vars `TOKEN`, `CLIENT_ID`.
- Production: prefer containerized deployment (Docker). For large installations:
  - Use PostgreSQL and migrate DB schema.
  - Run multiple bot worker processes with Discord sharding.
  - Offload heavy tasks (reporting, AI inference) to separate worker services.

**15. Security, Privacy & Compliance**
- Comply with Discord TOS: avoid storing or exposing user tokens; do not DM users excessively; provide opt-out.
- Encrypt any sensitive data in transit; in DB keep only what you need. Provide a data retention policy and a way to delete user data (GDPR-style).

**16. Migration & Backwards Compatibility**
- Use a `migrations` table and write small migration scripts when altering schema.
- For small projects, a version-numbered migration runner is sufficient; for larger production, use Alembic or Django migrations when moving to a SQL server.

**17. Roadmap & Milestones (Recommended Implementation Plan)**
- Phase 0 (0–2 days): repo cleanup + DB init + blueprint (this document) — DONE
- Phase 1 (2–7 days): activity tracking (listeners, scoring), `E!aip`, `E!leaderboard`, `add_ping/list_pings/remove_ping`. (Core engagement)
- Phase 2 (1–2 weeks): Event creation, RSVP flow, scheduled reminders, thread/channel creation, `eventos` enhancements.
- Phase 3 (1–2 weeks): Rewards engine, role assignment, admin commands, opt-outs, TTL roles.
- Phase 4 (2–3 weeks): Dashboard, analytics snapshots, weekly reports, export features.
- Phase 5 (optional): AI topics integration, gamification features, web dashboard, scaling and multi-server packaging.

**18. Implementation Notes & Recommendations**
- Libraries: `discord.py` (or its maintained fork), `aiosqlite` for async DB, `APScheduler` or `discord.ext.tasks` for lightweight scheduling, `FastAPI` for web dashboard.
- Avoid heavy synchronous DB operations in event handlers — use `aiosqlite` or schedule DB writes on a background task.
- Use small, well-tested helper modules for scoring, criteria evaluation, and template rendering.

**19. Next Immediate Actions**
1. Harden `get_db()` to use `aiosqlite` or wrap writes in executor to avoid blocking the event loop.
2. Add migration table and a small migration runner to safely add `messages`, `pings`, `rewards` tables across existing DBs.
3. Implement opt-out list and per-user ping cooldown.
4. Add button-based RSVP via `discord.ui.View` to modernize RSVP UX.

---
This file is a living blueprint. Next I can:
- Create a `migrations/` folder and add a migration runner script.
- Replace sync sqlite connections with `aiosqlite` wrappers.
- Implement the remaining Phase 1–3 tasks in the repo with tests and CI.

File: BLUEPRINT.md — created automatically as the canonical implementation plan.
