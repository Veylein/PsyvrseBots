import json
from pathlib import Path
from typing import Optional


def _find_project_root() -> Path:
    """Return the best guess for the project root containing `data/`.

    This is robust across environments where the package may be nested
    under `src/` or installed in different layouts. Preference order:
    - current working directory if it contains `data/`
    - two levels above this file (typical repo layout)
    - one level above this file
    - this file's parent
    """
    here = Path(__file__).resolve()
    candidates = [
        Path.cwd(),
        here.parents[2] if len(here.parents) > 2 else here.parent,
        here.parents[1] if len(here.parents) > 1 else here.parent,
        here.parent,
    ]

    for c in candidates:
        if (c / "data").exists():
            return c

    # fallback to repository root guess (two levels up)
    return candidates[1]


ROOT = _find_project_root()


def load_json(path: str):
    p = ROOT / path
    if not p.exists():
        # helpful error with attempted path
        raise FileNotFoundError(f"Required data file not found: {p}")
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)
