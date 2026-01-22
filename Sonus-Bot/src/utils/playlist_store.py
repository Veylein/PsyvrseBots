import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.logger import setup_logger

logger = setup_logger(__name__)


ROOT = Path(__file__).resolve().parents[2] / "data" / "playlists"
ROOT.mkdir(parents=True, exist_ok=True)


def _slugify(name: str) -> str:
    return "-".join(name.lower().strip().split())


def _path_for(pid: str) -> Path:
    return ROOT / f"{pid}.json"


def list_playlists(owner_id: Optional[int] = None) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for p in ROOT.glob("*.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            if owner_id is None or data.get("owner_id") == owner_id:
                out.append(data)
        except Exception:
            logger.exception("Failed to read playlist file %s", p)
    return out


def get_playlist(pid: str) -> Optional[Dict[str, Any]]:
    p = _path_for(pid)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        logger.exception("Failed to load playlist %s", pid)
        return None


def create_playlist(name: str, owner_id: int) -> Dict[str, Any]:
    pid = _slugify(name)
    p = _path_for(pid)
    if p.exists():
        raise FileExistsError("Playlist already exists")
    data = {"id": pid, "name": name, "owner_id": owner_id, "tracks": []}
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


def save_playlist(data: Dict[str, Any]) -> None:
    pid = data.get("id")
    if not pid:
        raise ValueError("Playlist missing id")
    p = _path_for(pid)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def add_track(pid: str, owner_id: int, title: str, uri: str) -> Dict[str, Any]:
    pl = get_playlist(pid)
    if pl is None:
        raise FileNotFoundError("Playlist not found")
    if pl.get("owner_id") != owner_id:
        raise PermissionError("Not the playlist owner")
    track = {"title": title, "uri": uri}
    pl.setdefault("tracks", []).append(track)
    save_playlist(pl)
    return track


def remove_playlist(pid: str, owner_id: int) -> None:
    pl = get_playlist(pid)
    if pl is None:
        raise FileNotFoundError("Playlist not found")
    if pl.get("owner_id") != owner_id:
        raise PermissionError("Not the playlist owner")
    p = _path_for(pid)
    p.unlink()


def remove_track(pid: str, owner_id: int, index: int) -> Dict[str, Any]:
    pl = get_playlist(pid)
    if pl is None:
        raise FileNotFoundError("Playlist not found")
    if pl.get("owner_id") != owner_id:
        raise PermissionError("Not the playlist owner")
    tracks = pl.setdefault("tracks", [])
    if index < 0 or index >= len(tracks):
        raise IndexError("Track index out of range")
    removed = tracks.pop(index)
    save_playlist(pl)
    return removed
