# PsyvrseBots

Consolidated workspace for several Discord bot projects and tools maintained by the Veylein/Psyvrse team.

This repository contains multiple independent bot projects (Conditor, Villicus, Ludus, Eventus, Pax, Sonus, and supporting tooling). The workspace is intended as a developer mono-repo for local development, testing, and deployment to Render or similar services.

## Included projects (top-level folders)

- `Conditor-Bot` — Server creation / provisioning bot (setup flow, planners, executor).
- `Villicus-main` — Villicus bot (entry: `main.py`).
- `Ludus-Bot` / `Ludus-main` — Game/economy related bot(s).
- `Eventus-main` — Events and announcements bot.
- `Sonus-main` — Audio/voice utilities.
- `Pax-main` — Misc utilities and helpers.

Each project has its own `requirements.txt`, scripts, and tests when available.

## Getting started (developer)

Prerequisites

- Python 3.10+ (this workspace sometimes builds with newer interpreters; tests were run locally with Python 3.11/3.12).
- `pip` for installing `requirements.txt` when working per-project.
- Git and a GitHub account with appropriate repo permissions.

Quick local run example (Conditor)

1. Create a virtual environment and install dependencies for `Conditor-Bot`:

```bash
python -m venv .venv
.
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
pip install -r Conditor-Bot/requirements.txt
```

2. Run Conditor locally (token secrets required for Discord connectivity):

```bash
cd Conditor-Bot
python main.py
# or, when running the package directly
python -m src.conditor
```

Notes
- Many services require a Discord bot token and optional guild IDs to run properly.
- Some services use SQLite files and expect migrations; if you see sqlite schema errors, run the project's migrations/seed scripts (where present) before starting.

## Running tests

Run pytest in a project folder that includes tests, for example:

```bash
cd Conditor-Bot
pip install -r requirements.txt
pytest
```

## Deployment (Render)

Each project can include a `render.yaml` manifest for Render services. Typical steps:

- Create a new Web Service in Render pointing at this repository (or a specific subfolder if you split projects into separate repos).
- Provide required environment variables (for example `CONDITOR_TOKEN`, `CONDITOR_GUILD_ID`) in Render's dashboard.
- Ensure the start command matches the project's `main.py` or `python -m` entrypoint.

## Contributing

- Work on feature branches and open pull requests against `main`.
- Keep commits focused and tests passing for changed components.
- When modifying subfolders that were previously gitlinks or submodules, prefer treating them as regular directories in this mono-repo to keep GitHub file viewable.

## Project goals / roadmap

- Improve the `/setup` UX in `Conditor-Bot` (single-questionnaire + quick presets).
- Add safety and auditability to plan execution (dry-run, approvals, logging).
- Add CI, tests, and deployment verification across services.

## Contact

For questions and issues, open an issue in the repository or contact the maintainer via the project GitHub account.

---
_This README is a living document — feel free to request more detailed per-project instructions._