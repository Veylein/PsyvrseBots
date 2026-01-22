import json
from pathlib import Path
from typing import Dict, Any

from src.logger import setup_logger

logger = setup_logger(__name__)

ROOT = Path(__file__).resolve().parents[2] / "data" / "guilds"
ROOT.mkdir(parents=True, exist_ok=True)

DEFAULTS: Dict[str, Any] = {
    "prefix": "S!",
    "color": "#1DB954",
}


def _path(guild_id: int) -> Path:
    return ROOT / f"{guild_id}.json"


def load(guild_id: int) -> Dict[str, Any]:
    p = _path(guild_id)
    if not p.exists():
        return DEFAULTS.copy()
    try:
        return {**DEFAULTS, **json.loads(p.read_text(encoding="utf-8"))}
    except Exception:
        logger.exception("Failed to load guild settings for %s", guild_id)
        return DEFAULTS.copy()


def save(guild_id: int, data: Dict[str, Any]) -> None:
    p = _path(guild_id)
    try:
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        logger.exception("Failed to save settings for %s", guild_id)


def set_prefix(guild_id: int, prefix: str) -> None:
    data = load(guild_id)
    data["prefix"] = prefix
    save(guild_id, data)


def set_color(guild_id: int, color: str) -> None:
    data = load(guild_id)
    data["color"] = color
    save(guild_id, data)
