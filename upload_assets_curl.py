import os
import sys
import json
import subprocess
import urllib.request

def get_token():
    proc = subprocess.Popen(
        ["git", "credential", "fill"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    out, _ = proc.communicate("protocol=https\nhost=github.com\n")
    for line in out.splitlines():
        if line.startswith("password="):
            return line.split("=", 1)[1].strip()
    return None

def main():
    token = get_token()
    if not token:
        print("[!] Token not found.")
        sys.exit(1)

    owner = "amzmihon"
    repo = "Speak-That-Windows"
    release_id = "439346286"

    headers = {
        "Authorization": f"token {token}",
        "User-Agent": "SpeakThat-Release-Bot",
        "Accept": "application/vnd.github.v3+json"
    }

    # 1. Fetch current assets
    req = urllib.request.Request(f"https://api.github.com/repos/{owner}/{repo}/releases/{release_id}/assets", headers=headers)
    with urllib.request.urlopen(req) as resp:
        assets = json.loads(resp.read().decode())
    
    for a in assets:
        print(f"[*] Deleting existing/stale asset: {a['name']} (ID: {a['id']}, state: {a.get('state')})...")
        del_req = urllib.request.Request(f"https://api.github.com/repos/{owner}/{repo}/releases/assets/{a['id']}", headers=headers, method="DELETE")
        try:
            with urllib.request.urlopen(del_req) as dresp:
                pass
            print(f"[✓] Deleted {a['name']}")
        except Exception as e:
            print(f"[!] Warning deleting {a['name']}: {e}")

    # 2. Upload with curl
    files = [
        (r"E:\Speak-That-Windows\dist\SpeakThat-Setup.exe", "SpeakThat-Setup.exe", "application/octet-stream"),
        (r"E:\Speak-That-Windows\dist\SpeakThat-v1.2-Windows-x64.zip", "SpeakThat-v1.2-Windows-x64.zip", "application/zip")
    ]

    upload_url_base = f"https://uploads.github.com/repos/{owner}/{repo}/releases/{release_id}/assets"

    for fpath, fname, ctype in files:
        if not os.path.exists(fpath):
            print(f"[!] File not found: {fpath}")
            continue
        
        fsize = os.path.getsize(fpath)
        print(f"[*] Uploading {fname} ({fsize / 1024 / 1024:.2f} MB) via curl...")
        
        cmd = [
            "curl.exe",
            "-L",
            "--fail",
            "-X", "POST",
            "-H", f"Authorization: token {token}",
            "-H", f"Content-Type: {ctype}",
            "--data-binary", f"@{fpath}",
            f"{upload_url_base}?name={fname}"
        ]
        
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            print(f"[✓] Successfully uploaded {fname}!")
        else:
            print(f"[!] Curl upload failed for {fname} (exit {res.returncode}): {res.stderr}")
            sys.exit(1)

    print("\n[✓] All assets uploaded successfully!")

if __name__ == "__main__":
    main()

