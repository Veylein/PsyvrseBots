import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_settings_json_exists():
    p = ROOT / "data" / "settings.json"
    assert p.exists()
    data = json.loads(p.read_text(encoding='utf-8'))
    assert "default_volume" in data
