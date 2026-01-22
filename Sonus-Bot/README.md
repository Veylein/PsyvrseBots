# Sonus

Sonus is an audio operating system for Discord: a modular, data-driven platform for delivering high-quality, social music experiences inside Discord.

This repository contains a clean Python 3.11+ scaffold focused on separation of concerns: audio sources, effects pipeline, UI components, commands, and a replaceable data layer.

Goals
- Build a scalable audio-first system that feels premium and social.
- Keep every subsystem replaceable and data-driven (no hardcoded playlists or presets).
- Provide an async-first architecture suitable for long-running production deployments.

Quick Start
1. Create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

2. Set required environment variables (recommended via Render or your environment manager):

- `SONUS_TOKEN` — Discord bot token (required)
- `SONUS_ID` — Discord application ID (optional for some flows)
- `GUILD_ID`  — Development guild ID for command sync (optional but recommended)

3. Run the bot locally:

```bash
python main.py
```

Render
- `render.yaml` is configured to run Sonus as a worker on Render. Build and start commands from Render:

```yaml
buildCommand: pip install -r requirements.txt
startCommand: python main.py
```

Architecture Overview
- `src/bot.py` — application bootstrap and dynamic module registration (auto-loads `src.events` and `src.commands`).
- `src/events/` — event handlers (ready, interaction, voice state updates).
- `src/commands/` — prefix and slash command modules, organized into `music`, `playlist`, and `utility` groups.
- `src/audio/` — audio engine primitives: player, queue, effects, and source adapters (`youtube`, `spotify`, `soundcloud` stubs).
- `src/ui/` — embeds, buttons, and modals used across commands and views.
- `src/database/` — DB engine and models (stubbed using `asyncpg` and `pydantic`).
- `src/utils/` — helpers: loaders, validation, auditing, logging, and time utilities.
- `data/` — JSON-driven content for playlists, radios, EQ presets, and settings. Design principle: audio behavior is data-driven.

Important Commands
- Prefix owner-only commands (start with `S!`) — fast, silent system controls for owners.
- Slash commands — user-friendly UI for general users; registered on startup and synced to the dev guild when `GUILD_ID` is set.

Testing
- Minimal tests under `tests/` use `pytest`.

Notes & Next Steps
- Audio pipeline is intentionally scaffolded: production-quality encoding (ffmpeg → Opus at 48 kHz) and voice channel sinks need implementation.
- `src/utils/audit.py` logs owner actions to `data/audit.log` and posts short summaries to the audit channel.
- For better lyrics coverage, integrate Genius or a paid lyrics provider.

Contributing
- This repo is structured to accept focused, reviewable patches. Prefer feature branches and PRs. For large changes, open an issue with architecture notes.

License
- See the project `LICENSE` in the repository root (if present) or add one before public distribution.

If you want, I can now:
- Implement the production audio pipeline (yt-dlp → ffmpeg → Opus -> Discord VC),
- Wire the player to maintain `bot.sonus_now_playing`, or
- Add a small `S!audit tail` command to query recent audit lines.
Tell me which you'd like next.
