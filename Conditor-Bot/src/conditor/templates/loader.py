import json
from pathlib import Path


def load_default_template():
    p = Path(__file__).parent / "bot_testing.json"
    if not p.exists():
        raise FileNotFoundError("Default template not found")
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)
