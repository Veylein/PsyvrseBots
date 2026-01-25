Conditor-Bot
=================

Conditor is a deterministic Discord server architect: it creates full server layouts from descriptive JSON templates and user input (via modals).

Key files:
- `main.py` — entrypoint
- `src/conditor/modals.py` — modal flow (15 fields)
- `src/conditor/parser.py` — deterministic template -> plan generator
- `src/conditor/creator.py` — executes plan against a Guild with rollback
- `src/conditor/templates/` — templates and schema

Run locally:

```bash
cd Conditor-Bot
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
set CONDITOR_TOKEN=<your-bot-token>
python main.py
```
