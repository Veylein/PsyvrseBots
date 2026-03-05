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
START_DELAY = int(os.environ.get("START_DELAY", 120))  # seconds between bot startups (bumped to 120s for safety)

BOT_ORDER = [ 
    "Ludus-Bot",
    "Pax-Bot",
    # "PsySource", # Disabled in launcher: Run as separate Web Service if needed
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
    # Special-case: prefer lightweight `start.py` for Pax to allow quick health startup
    try:
        if 'pax' in folder.name.lower():
            p_start = folder / 'start.py'
            if p_start.exists():
                return p_start
    except Exception:
        pass
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


async def launch_all_bots() -> list:
    """Start all bots in order. Returns list of started processes."""
    processes = []
    dir_folders = [f for f in BASE_DIR.iterdir() if f.is_dir()]

    def find_folder_by_name(target: str):
        t = target.lower()
        for f in dir_folders:
            if f.name.lower() == t:
                return f
        for f in dir_folders:
            if t in f.name.lower():
                return f
        return None

    started = set()

    # Start bots in the defined order
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

        # Check for very fast crash (first 10s only — likely a config/token error, not rate limit)
        check_delay = 10
        try:
            await asyncio.wait_for(proc.wait(), timeout=check_delay)
            print(f"[warning] {bot_name} exited within {check_delay}s (code {proc.returncode}). Continuing with remaining bots.")
        except asyncio.TimeoutError:
            # Still running — good
            pass
        except Exception as e:
            print(f"[error] Startup check error for {bot_name}: {e}")

        # Stagger startups to avoid rate-limit spikes
        msg_delay = max(0, START_DELAY - check_delay)
        if msg_delay > 0:
            await asyncio.sleep(msg_delay)

    # Start any extra directories not in BOT_ORDER
    for folder in dir_folders:
        name_l = folder.name.lower()
        if name_l in started:
            continue
        if folder.name.startswith('.') or name_l in ('.git', '.venv', 'venv', 'logs', 'scripts'):
            continue

        entry = find_entry(folder)
        if not entry:
            continue

        print(f"[info] Starting extra folder: {folder.name}")
        proc = await run_bot(folder, entry)
        processes.append(proc)
        started.add(name_l)
        await asyncio.sleep(START_DELAY)

    return processes


async def main():
    # Outer backoff loop — keeps launcher alive instead of exiting (which would
    # trigger an immediate platform restart and create a tight restart loop).
    BASE_BACKOFF = 300   # 5 minutes
    MAX_BACKOFF  = 3600  # 1 hour cap
    cycle = 0

    while True:
        if cycle > 0:
            backoff = min(BASE_BACKOFF * (2 ** (cycle - 1)), MAX_BACKOFF)
            print(f"\n[launcher] Cycle #{cycle}. Waiting {backoff}s before restarting bots...")
            await asyncio.sleep(backoff)

        cycle += 1
        print(f"\n[launcher] === Launch cycle #{cycle} ===")

        try:
            processes = await launch_all_bots()
        except Exception as e:
            print(f"[launcher] Fatal error during launch: {e}")
            continue

        if not processes:
            print("[launcher] No bots were started. Will retry after backoff.")
            continue

        print(f"\n[launcher] All bots launched ({len(processes)}). Monitoring...\n")

        try:
            await asyncio.gather(*(p.wait() for p in processes))
        except KeyboardInterrupt:
            print("\n[launcher] Shutdown signal received. Terminating bots...")
            for p in processes:
                try:
                    p.terminate()
                except Exception:
                    pass
            return

        print("\n[launcher] All bots have stopped. Entering backoff before next cycle...")


if __name__ == "__main__":
    asyncio.run(main())