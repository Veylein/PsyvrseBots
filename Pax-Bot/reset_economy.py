import json
import os

DATA_FILE = "chi_data.json"

def reset_economy():
    print(f"Resetting {DATA_FILE}...")
    with open(DATA_FILE, "w") as f:
        json.dump({}, f, indent=4)
    print("Economy reset complete.")

if __name__ == "__main__":
    reset_economy()
