import os
import sys
import asyncio
import subprocess
from pathlib import Path

"""
Unified Discord Bot Launcher
Launch order (intentional, staggered):
1. Conditor  (core / setup)
2. Sonus     (audio)
3. Villicus  (moderation - primary)
4. Eventus   (activity / events)
5. Pax       (utility / misc)
6. Ludus     (games)

Each bot runs in its own subprocess with isolated env loading.
Bots are started one-by-one with a short delay to avoid rate-limit spikes.
"""

BASE_DIR = Path(__file__).parent.resolve()
START_DELAY = 6  # seconds between bot startups

BOT_ORDER = [
    "Conditor",
    "Sonus",
    "Villicus",
    "Eventus",
    "Pax",
    "Ludus",
]

ENTRY_CANDIDATES = [
    "main.py",
    "bot.py",
    "run.py",
    "start.py",
    "index.js",
]


def load_env(env_path: Path, env: dict) -> dict:
    if not env_path.exists():
        return env
    try:
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip("\"'")
    except Exception as e:
        print(f"[env] Failed to load {env_path}: {e}")
    return env


def find_entry(folder: Path) -> Path | None:
    for name in ENTRY_CANDIDATES:
        p = folder / name
        if p.exists():
            return p

    src = folder / "src"
    if src.exists():
        main_mod = src / "__main__.py"
        if main_mod.exists():
            return main_mod

    return None


async def run_bot(folder: Path, entry: Path):
    env = os.environ.copy()
    env = load_env(folder / ".env", env)

    # Force UTF-8 IO for subprocesses to avoid Windows encoding errors
    env.setdefault('PYTHONUTF8', '1')
    env.setdefault('PYTHONIOENCODING', 'utf-8')

    # Ensure Python subprocesses can import local packages by adding
    # the folder and its `src` subfolder to PYTHONPATH.
    pythonpath = env.get('PYTHONPATH', '')
    parts = []
    parts.append(str(folder))
    src_dir = folder / 'src'
    if src_dir.exists():
        parts.append(str(src_dir))
    if pythonpath:
        parts.append(pythonpath)
    env['PYTHONPATH'] = os.pathsep.join(parts)

    # If the entry is a Node.js script, run it with `node`
    if entry.suffix == '.js':
        cmd = ["node", str(entry.resolve())]
    else:
        cmd = [sys.executable, str(entry.resolve())]

    # Conditor REQUIRES --run (python-only).
    # Accept folder name variants like 'Conditor-Bot' by checking substring.
    if entry.suffix != '.js' and 'conditor' in folder.name.lower():
        cmd.append("--run")

    print(f"\n=== Starting {folder.name} ===")
    print("Command:", " ".join(cmd))

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=str(folder),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    async def stream():
        assert proc.stdout
        async for line in proc.stdout:
            # Decode bytes defensively and write to stdout.buffer using utf-8
            try:
                text = line.decode('utf-8')
            except Exception:
                text = line.decode('utf-8', 'replace')
            out = f"[{folder.name}] {text.rstrip()}\n".encode('utf-8', errors='replace')
            try:
                sys.stdout.buffer.write(out)
                sys.stdout.buffer.flush()
            except Exception:
                # Fallback to print if buffer isn't available
                print(out.decode('utf-8', 'replace'), end='')

    asyncio.create_task(stream())
    return proc


async def main():
    processes = []

    dir_folders = [f for f in BASE_DIR.iterdir() if f.is_dir()]

    def find_folder_by_name(target: str):
        t = target.lower()
        # exact match first
        for f in dir_folders:
            if f.name.lower() == t:
                return f
        # common suffix/prefix variants
        for f in dir_folders:
            if t in f.name.lower():
                return f
        # not found
        return None

    # Keep track of which folders we've already attempted to start
    started = set()

    # First, start the curated BOT_ORDER so important services come up first
    for bot_name in BOT_ORDER:
        folder = find_folder_by_name(bot_name)
        if not folder:
            print(f"[skip] {bot_name} not found")
            continue

        entry = find_entry(folder)
        if not entry:
            print(f"[skip] {bot_name}: no entry file in {folder.name}")
            continue

        proc = await run_bot(folder, entry)
        processes.append(proc)
        started.add(folder.name.lower())

        await asyncio.sleep(START_DELAY)

    # Then, scan all other directories and start any that have a valid entry but weren't in BOT_ORDER
    for folder in dir_folders:
        name_l = folder.name.lower()
        if name_l in started:
            continue
        # skip hidden or git/venv folders
        if folder.name.startswith('.') or folder.name.lower() in ('.git', '.venv', 'venv'):
            continue

        entry = find_entry(folder)
        if not entry:
            # nothing to start here
            continue

        print(f"[info] Starting extra folder: {folder.name}")
        proc = await run_bot(folder, entry)
        processes.append(proc)
        started.add(name_l)
        await asyncio.sleep(START_DELAY)

    if not processes:
        print("No bots were started.")
        return

    print("\nAll bots launched. Monitoring...\n")

    try:
        await asyncio.gather(*(p.wait() for p in processes))
    except KeyboardInterrupt:
        print("\nShutdown signal received. Terminating bots...")
        for p in processes:
            p.terminate()


if __name__ == "__main__":
    asyncio.run(main())