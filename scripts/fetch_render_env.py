import os
import sys
import json
import urllib.request
import urllib.parse
from pathlib import Path

RENDER_API_KEY = os.environ.get("RENDER_API_KEY")
SERVICE_NAME_FILTER = "ludus-bot"

def fetch_services(api_key):
    url = "https://api.render.com/v1/services?limit=50"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        print(f"Error fetching services: {e}")
        return []
    except Exception as e:
        print(f"Unexpected error: {e}")
        return []

def fetch_env_vars(api_key, service_id):
    url = f"https://api.render.com/v1/services/{service_id}/env-vars?limit=50"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        print(f"Error fetching env vars for {service_id}: {e}")
        return []

def main():
    global RENDER_API_KEY
    if not RENDER_API_KEY:
        print("Please enter your Render API Key (will be hidden):")
        # In standardized Python input(), we can't hide it easily cross-platform
        # without getpass, but getpass works well.
        import getpass
        try:
            RENDER_API_KEY = getpass.getpass("Render API Key: ")
        except Exception:
             RENDER_API_KEY = input("Render API Key: ")
        
        if not RENDER_API_KEY:
            print("No API Key provided. Exiting.")
            sys.exit(1)

    print(f"Fetching services looking for '{SERVICE_NAME_FILTER}'...")
    services_data = fetch_services(RENDER_API_KEY)
    
    target_service = None
    for service in services_data:
        # Check both name and slug just in case
        s_name = service.get("service", {}).get("name", "")
        s_slug = service.get("service", {}).get("slug", "")
        
        # Render API v1 structure is list of objects, each object has 'service' key? 
        # Actually API v1 returns list of service objects directly if using GET /services
        # Note: The response is actually a list of objects.
        
        # Let's handle both v1 direct list and wrapped list
        # Response is actually a list of Service objects directly.
        name = service.get("name", "")
        slug = service.get("slug", "")
        s_id = service.get("id", "")
        
        if SERVICE_NAME_FILTER.lower() in name.lower() or SERVICE_NAME_FILTER.lower() in slug.lower():
            target_service = service
            print(f"Found service: {name} ({s_id})")
            break
    
    if not target_service:
        print(f"Service '{SERVICE_NAME_FILTER}' not found.")
        sys.exit(1)

    service_id = target_service["id"]
    print(f"Fetching environment variables for {service_id}...")
    env_vars = fetch_env_vars(RENDER_API_KEY, service_id)
    
    if not env_vars:
        print("No environment variables found or error occurred.")
        sys.exit(1)

    # Prepare .env content
    env_lines = []
    print("\nVariables found:")
    for item in env_vars:
        key = item.get("envVar", {}).get("key")
        value = item.get("envVar", {}).get("value")
        
        if not key:
             # Try direct structure if API differs
             key = item.get("key")
             value = item.get("value")

        if key:
            print(f" - {key}")
            env_lines.append(f"{key}={value}")

    # Write to Ludus-Bot/.env
    output_path = Path("Ludus-Bot/.env")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(env_lines))
    
    print(f"\nSuccessfully wrote {len(env_lines)} variables to {output_path}")

if __name__ == "__main__":
    main()
