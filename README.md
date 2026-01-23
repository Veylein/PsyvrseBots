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

## Contact

For questions and issues, open an issue in the repository or contact the maintainer via the project GitHub account.

---
_This README is a living document — feel free to request more detailed per-project instructions._
