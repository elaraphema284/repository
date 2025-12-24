import os
import requests
import base64
from nacl import public, encoding

# Configuration
SERVERS = {
    # Server 1 - 2
    "1": {"repo": "egygo2004/fb-otp", "token": os.environ.get("SERVER_1_TOKEN")},
    "2": {"repo": "egygo2004/fb-otp-2", "token": os.environ.get("SERVER_2_TOKEN")},
    
    # Server 11 - 50 (Generated Range)
    # Add logic here if you have dynamic server list or import from provision_server
}

# Add servers 11-50
for i in range(11, 51):
    env_token = os.environ.get(f"SERVER_{i}_TOKEN")
    if env_token:
        SERVERS[str(i)] = {
            "token": env_token,
            "repo": f"egygo2004/fb-otp-{i}",
            "name": f"Server {i}"
        }

def encrypt(public_key: str, secret_value: str) -> str:
    """Encrypt a Unicode string using the public key."""
    public_key = public.PublicKey(public_key.encode("utf-8"), encoding.Base64Encoder())
    sealed_box = public.SealedBox(public_key)
    encrypted = sealed_box.encrypt(secret_value.encode("utf-8"))
    return base64.b64encode(encrypted).decode("utf-8")

def update_secret(repo, token, secret_name, secret_value):
    """Update a GitHub Actions secret"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # 1. Get Public Key
    key_url = f"https://api.github.com/repos/{repo}/actions/secrets/public-key"
    resp = requests.get(key_url, headers=headers)
    if resp.status_code != 200:
        print(f"❌ {repo}: Failed to get key ({resp.status_code})")
        return False
    
    key_data = resp.json()
    key_id = key_data['key_id']
    key = key_data['key']
    
    # 2. Encrypt Value
    encrypted_value = encrypt(key, secret_value)
    
    # 3. Create/Update Secret
    secret_url = f"https://api.github.com/repos/{repo}/actions/secrets/{secret_name}"
    data = {
        "encrypted_value": encrypted_value,
        "key_id": key_id
    }
    
    put_resp = requests.put(secret_url, headers=headers, json=data)
    if put_resp.status_code in [201, 204]:
        print(f"✅ {repo}: Updated {secret_name}")
        return True
    else:
        print(f"❌ {repo}: Failed to update {secret_name} ({put_resp.status_code})")
        return False

def main():
    print("Batch Updating Secrets...")
    
    # Load secrets from Env or Input (hardcoded for this run based on user input)
    # USER provided:
    proton_user = "OOZ7czvUbQCuugpG"
    proton_pass = "IhKSZQGju85ZDTMNLC0NYD4yuQSzQc05"
    
    # Load Config from local file
    try:
        with open("wg-CA-FREE-14.conf", "rb") as f:
            valid_config = f.read()
            proton_config_b64 = base64.b64encode(valid_config).decode('utf-8')
            print("Loaded WireGuard config from file.")
    except Exception as e:
        print(f"Failed to read config file: {e}")
        proton_config_b64 = None

    if not proton_config_b64:
        print("PROTON_CONFIG_BASE64 not found. Skipping config update.")
    
    for key, server in SERVERS.items():
        if not server['token']:
            continue
            
        print(f"Processing {server.get('name', server['repo'])}...")
        update_secret(server['repo'], server['token'], "PROTON_USER", proton_user)
        update_secret(server['repo'], server['token'], "PROTON_PASS", proton_pass)
        
        if proton_config_b64:
            update_secret(server['repo'], server['token'], "PROTON_CONFIG_BASE64", proton_config_b64)

if __name__ == "__main__":
    main()
