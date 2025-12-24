
import os
import sys
import requests
import base64
import subprocess
from time import sleep

# --- CONFIG ---
TOKEN = sys.argv[1] if len(sys.argv) > 1 else ""
REPO_NAME = "server-21-worker"  # User requested repo name
TELEGRAM_TOKEN = "7205135297:AAEKFDTNZBj0c1I23Ri_a_PjCuWn_KUiYyY"
TELEGRAM_CHAT_ID = "664193835"

HEADER = {
    "Authorization": f"token {TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

def log(msg):
    print(f"[INFO] {msg}")

def check_user():
    r = requests.get("https://api.github.com/user", headers=HEADER)
    if r.status_code == 200:
        user = r.json()['login']
        log(f"Authenticated as: {user}")
        return user
    else:
        print(f"[ERROR] Invalid Token! Status: {r.status_code}")
        sys.exit(1)

def create_repo():
    log(f"Creating repo: {REPO_NAME}...")
    data = {
        "name": REPO_NAME,
        "private": True,
        "auto_init": True  # Auto init with README to mimic human
    }
    r = requests.post("https://api.github.com/user/repos", headers=HEADER, json=data)
    if r.status_code == 201:
        log("Repo created successfully (with README).")
        log("Waiting 10s for GitHub propagation...")
        sleep(10)
        return True
    elif r.status_code == 422:
        log("Repo already exists. Configuring existing repo...")
        return True
    else:
        print(f"[ERROR] Failed to create repo: {r.text}")
        sys.exit(1)

def enable_actions(user):
    log("Enabling GitHub Actions...")
    # Enable Actions for the repo (PUT /repos/:owner/:repo/actions/permissions)
    url = f"https://api.github.com/repos/{user}/{REPO_NAME}/actions/permissions"
    data = {"enabled": True, "allowed_actions": "all"}
    r = requests.put(url, headers=HEADER, json=data)
    if r.status_code == 204:
        log("GitHub Actions enabled.")
    else:
        log(f"Warning: Failed to enable actions: {r.text}")

def get_public_key(user):
    url = f"https://api.github.com/repos/{user}/{REPO_NAME}/actions/secrets/public-key"
    r = requests.get(url, headers=HEADER)
    if r.status_code == 200:
        return r.json()
    else:
        print(f"Failed to get public key: {r.text}")
        sys.exit(1)

def encrypt_secret(public_key, secret_value):
    import nacl
    from nacl import public, encoding
    
    public_key_bytes = base64.b64decode(public_key)
    sealed_box = public.SealedBox(public.PublicKey(public_key_bytes))
    encrypted = sealed_box.encrypt(secret_value.encode("utf-8"))
    return base64.b64encode(encrypted).decode("utf-8")

def add_secret(user, key_data, secret_name, secret_value):
    try:
        import nacl
    except ImportError:
        print("PyNaCl not installed. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pynacl"])
        import nacl

    encrypted_value = encrypt_secret(key_data['key'], secret_value)
    
    url = f"https://api.github.com/repos/{user}/{REPO_NAME}/actions/secrets/{secret_name}"
    data = {
        "encrypted_value": encrypted_value,
        "key_id": key_data['key_id']
    }
    r = requests.put(url, headers=HEADER, json=data)
    if r.status_code in [201, 204]:
        log(f"Secret {secret_name} added.")
    else:
        print(f"Failed to add secret {secret_name}: {r.text}")

def push_code(user):
    log("Pushing code to new repo...")
    remote_url = f"https://{TOKEN}@github.com/{user}/{REPO_NAME}.git"
    
    # 1. Create Orphan Branch
    subprocess.run(f"git checkout --orphan clean_deploy_{REPO_NAME}", shell=True, check=False)
    subprocess.run("git reset", shell=True) # Unstage all
    
    # 2. Add specific files
    files = [".github", "fb_otp_browser.py", "requirements.txt"]
    for f in files:
        subprocess.run(f"git add {f}", shell=True)
    
    # 3. Commit
    subprocess.run('git commit -m "Feat: Add worker automation"', shell=True)
    
    # 4. Push (Safe Force)
    log("Waiting 5s before push...")
    sleep(5)
    subprocess.run(f"git push {remote_url} clean_deploy_{REPO_NAME}:main -f", shell=True)
    
    # 5. Cleanup
    subprocess.run("git checkout master", shell=True)
    subprocess.run(f"git branch -D clean_deploy_{REPO_NAME}", shell=True)
    log("Code pushed successfully.")

def main():
    if not TOKEN:
        print("Usage: python provision_server.py <GITHUB_TOKEN>")
        sys.exit(1)
        
    user = check_user()
    create_repo()
    enable_actions(user)
    
    key_data = get_public_key(user)
    add_secret(user, key_data, "TELEGRAM_TOKEN", TELEGRAM_TOKEN)
    add_secret(user, key_data, "TELEGRAM_CHAT_ID", TELEGRAM_CHAT_ID)
    
    push_code(user)
    
    print(f"\n{'-'*30}")
    print(f"[SUCCESS] Server 21 Deployment Complete!")
    print(f"Repo: {user}/{REPO_NAME}")
    print(f"Branch: main")
    print(f"Token: {TOKEN}")
    print(f"{'-'*30}\n")
    print("Next Step: Run header 'heroku config:set SERVER_21_...'")       

if __name__ == "__main__":
    main()
