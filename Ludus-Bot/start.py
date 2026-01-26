import sys
from pathlib import Path
import runpy

BASE = Path(__file__).parent
ENTRY_CANDIDATES = ("main.py", "bot.py", "run.py", "start.py")


def find_entry(folder: Path):
    for name in ENTRY_CANDIDATES:
        p = folder / name
        # avoid returning this wrapper script itself
        try:
            if p.exists() and p.resolve() != Path(__file__).resolve():
                return p
        except Exception:
            if p.exists() and p.name != Path(__file__).name:
                return p
    # fallback: look for any python file with 'bot' or 'main' in the name
    for p in folder.glob('*.py'):
        if 'bot' in p.name.lower() or 'main' in p.name.lower():
            return p
    return None


def main():
    entry = find_entry(BASE)
    if not entry:
        print("[Ludus-Bot] no runnable entry found in Ludus-Bot; nothing to start.")
        sys.exit(0)

    print(f"[Ludus-Bot] launching {entry.name}")
    runpy.run_path(str(entry), run_name='__main__')


if __name__ == '__main__':
    main()
