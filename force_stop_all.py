import os
import requests

# Helper to get all servers
SERVERS = {}
for i in range(1, 60):
    repo_name = f"egygo2004/fb-otp-{i}" if i > 1 else "egygo2004/fb-otp"
    if i == 1: repo_name = "egygo2004/fb-otp"
    token = os.environ.get(f"SERVER_{i}_TOKEN")
    if token:
        SERVERS[str(i)] = {"repo": repo_name, "token": token}

def force_stop_all():
    print("🛑 Starting Emergency Stop for ALL Servers...")
    total_stopped = 0
    
    for server_id, config in SERVERS.items():
        repo = config['repo']
        token = config['token']
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        # Check active runs
        try:
            url = f"https://api.github.com/repos/{repo}/actions/runs?status=in_progress"
            resp = requests.get(url, headers=headers, timeout=10)
            
            if resp.status_code == 200:
                runs = resp.json().get('workflow_runs', [])
                queued_url = f"https://api.github.com/repos/{repo}/actions/runs?status=queued"
                queued_resp = requests.get(queued_url, headers=headers, timeout=10)
                if queued_resp.status_code == 200:
                    runs.extend(queued_resp.json().get('workflow_runs', []))
                
                if not runs:
                    print(f"✅ {repo}: No active runs.")
                    continue
                    
                print(f"⚠️ {repo}: Found {len(runs)} active runs. Cancelling...")
                
                for run in runs:
                    run_id = run['id']
                    cancel_url = f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/cancel"
                    cancel_resp = requests.post(cancel_url, headers=headers, timeout=10)
                    if cancel_resp.status_code in [200, 202, 204]:
                        print(f"   ⮑ Cancelled run {run_id}")
                        total_stopped += 1
                    else:
                        print(f"   ❌ Failed to cancel {run_id}: {cancel_resp.status_code}")
            else:
                print(f"❌ {repo}: API Error {resp.status_code}")
                
        except Exception as e:
            print(f"❌ {repo}: {e}")

    print(f"\n🏁 Emergency Stop Complete. Total cancelled: {total_stopped}")

if __name__ == "__main__":
    force_stop_all()
