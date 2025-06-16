import os
import sys
import signal
from supabase import create_client, Client
import requests


def inject_secrets():
    print("Starting secret injection...")

    # Fetch secrets from Supabase
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SECRET_KEY"]

    def signal_handler(signum, frame):
        print(f"Received signal {signum}, exiting gracefully")
        sys.exit(1)

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Accept-Profile": "vault",  # This sets the schema
        "Content-Profile": "vault",
    }

    print("Fetching secrets from Supabase...")
    response = requests.get(f"{url}/rest/v1/decrypted_secrets", headers=headers)

    if response.status_code != 200:
        print(f"Failed to fetch secrets: {response.status_code}")
        print(f"Response: {response.text}")
        sys.exit(1)

    data = response.json()
    if not data:
        print("No secrets found")
        sys.exit(1)

    print(f"Found {len(data)} secrets")

    # Write to the correct location that matches the volume mount
    secrets_dir = "/app/secrets"
    env_file_path = os.path.join(secrets_dir, ".env")
    ready_file_path = os.path.join(secrets_dir, ".ready")

    # Ensure secrets directory exists
    os.makedirs(secrets_dir, exist_ok=True)

    try:
        print(f"Writing secrets to {env_file_path}...")

        with open(env_file_path, "w") as env_file:  # Use 'w' to overwrite
            for i, result in enumerate(data):
                secret_name = result.get("name", f"SECRET_{i}")
                secret_value = result.get("decrypted_secret", "")

                print(f"Writing secret: {secret_name}")
                env_file.write(f"{secret_name}={secret_value}\n")
                env_file.flush()

        # Create the ready file to signal completion
        with open(ready_file_path, "w") as ready_file:
            ready_file.write("secrets_loaded\n")

        print("All secrets written successfully!")
        print(f"Created ready signal file: {ready_file_path}")

    except Exception as e:
        print(f"Error writing secrets: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    inject_secrets()
    print("Secret injection completed. Container will now exit.")
