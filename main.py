import os
import sys
import asyncio
import subprocess
from pathlib import Path

MAIN_FOLDER = Path(__file__).parent

def load_env_file(env_path: Path, base_env: dict):
    # Simple .env parser: KEY=VALUE, ignore comments and blank lines
    try:
        with env_path.open("r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                base_env[key] = val
    except Exception:
        pass
    return base_env

def find_bot_entry(folder: Path):
    # Prefer these entry scripts in order
    candidates = ["bot.py", "run.py", "main.py", "start.py", "delete_slash_commands.py"]
    for c in candidates:
        p = folder / c
        if p.exists():
            return p

    # Look for package-style entrypoints under src/**/__main__.py
    src = folder / "src"
    if src.exists():
        for p in src.rglob("__main__.py"):
            return p

    # fallback: any python file at repo root that looks like an entry
    for p in folder.glob("*.py"):
        if p.name.lower().startswith(("bot","main","start","run")):
            return p

    return None

async def run_subprocess(cmd, cwd, env):
    process = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=str(cwd),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )

    async def stream_output():
        assert process.stdout
        while True:
            line = await process.stdout.readline()
            if not line:
                break
            print(f"[{cwd.name}] {line.decode().rstrip()}")

    await stream_output()
    return await process.wait()

async def main():
    procs = []
    for folder in MAIN_FOLDER.iterdir():
        if not folder.is_dir():
            continue
        # detect bot folders by convention (-main) or presence of common entry files
        if not (folder.name.endswith("-main") or any((folder / f).exists() for f in ("bot.py","run.py","main.py","start.py","src"))):
            continue

        entry = find_bot_entry(folder)
        if not entry:
            print(f"Skipping {folder.name}: no entry script found")
            continue

        # Prepare environment, loading per-folder .env if present
        env = os.environ.copy()
        env_file = folder / ".env"
        if env_file.exists():
            env = load_env_file(env_file, env)

        # Build python command; use absolute path to the entry file when possible
        if entry.is_file():
            cmd = [sys.executable, str(entry.resolve())]
        else:
            # should not usually reach here, but handle defensively
            cmd = [sys.executable, str(entry)]

        print(f"Starting {folder.name} with command: {' '.join(cmd)} (cwd={folder})")
        procs.append(asyncio.create_task(run_subprocess(cmd, folder, env)))

    if not procs:
        print("No bot folders found to start.")
        return

    # wait for all to complete
    results = await asyncio.gather(*procs, return_exceptions=True)
    print("All bot processes exited.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Shutting down bots.")

