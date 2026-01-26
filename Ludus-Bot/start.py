"""Ludus-Bot startup script: loads .env, checks LUDUS_TOKEN, and launches bot.py as a subprocess."""
import os
import sys
import subprocess

try:
    import dotenv
except ImportError:
    print("Missing dependency: python-dotenv. Please install requirements.")
    sys.exit(1)

dotenv.load_dotenv()

if not os.environ.get('LUDUS_TOKEN'):
    print('LUDUS_TOKEN not set! Please add it to your .env file or environment variables.')
    sys.exit(1)

def main():
    # Always launch bot.py as a subprocess
    try:
        subprocess.run([sys.executable, 'bot.py'], check=True)
    except Exception as e:
        print(f"[Ludus-Bot] Failed to launch bot.py: {e}")

if __name__ == '__main__':
    main()
