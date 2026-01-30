Villicus — Local Setup
======================

This file contains minimal run instructions for local development.

Requirements
------------
- Python 3.11+
- `pip install -r requirements.txt` from `Villicus-Bot/`

Environment variables
---------------------
- `VILLICUS_TOKEN` — Bot token (required)
- `DEV_GUILD_ID` — Optional: a guild ID to register slash commands during development

Run
---
From repository root:

```bash
cd Villicus-Bot
python -m main
```

Tests
-----
Run the basic database test:

```bash
pip install pytest
pytest Villicus-Bot/tests -q
```

Notes
-----
- The bot auto-discovers cogs under `bot/` and will sync slash commands in `on_ready()`.
- Use `/config` to set up punishments, tickets, emoji locks, staff roles and giveaways.
