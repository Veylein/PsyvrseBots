"""Diagnostic launcher to print presence of key environment variables
and then run the normal multi-bot `main.py` launcher. Intended for temporary
debugging on hosts like Render where environment visibility is limited.

Usage (Render start command):
    python diagnose_envs.py
"""
import os
import sys
import subprocess

KEYS = [
    "CONDITOR_TOKEN",
    "CONDITOR_GUILD_ID",
    "LUDUS_TOKEN",
    "VILLICUS_TOKEN",
    "PAX_TOKEN",
]

def mask(v: str) -> str:
    if not v:
        return "(missing)"
    if len(v) <= 6:
        return "(set)"
    return v[:3] + "..." + v[-3:]

def main():
    print("=== Environment diagnostic ===")
    for k in KEYS:
        v = os.environ.get(k)
        print(f"{k}: {mask(v)}")

    print("\nListing a few useful env vars available to the process:")
    for k in sorted([k for k in os.environ.keys() if any(x in k for x in ["TOKEN","GUILD","SECRET"])][:50]):
        print(f"  - {k}")

    # Now delegate to the existing main launcher
    cmd = [sys.executable, "main.py"]
    print(f"\nDelegating to: {' '.join(cmd)}")
    try:
        rc = subprocess.call(cmd)
        print(f"main.py exited with code {rc}")
        sys.exit(rc)
    except Exception as e:
        print(f"Failed to run main.py: {e}")
        raise

if __name__ == '__main__':
    main()
