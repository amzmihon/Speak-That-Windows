import os
import sys
import json
import subprocess
import urllib.request
import urllib.parse

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
        print("[!] Error: Could not get GitHub token.")
        sys.exit(1)

    owner = "amzmihon"
    repo = "Speak-That-Windows"
    tag = "v1.2.0"

    headers = {
        "Authorization": f"token {token}",
        "User-Agent": "SpeakThat-Release-Bot",
        "Accept": "application/vnd.github.v3+json"
    }

    # 1. Check if release already exists for tag
    get_rel_url = f"https://api.github.com/repos/{owner}/{repo}/releases/tags/{tag}"
    req = urllib.request.Request(get_rel_url, headers=headers)
    release = None
    try:
        with urllib.request.urlopen(req) as resp:
            release = json.loads(resp.read().decode())
            print(f"[*] Found existing release for {tag} (ID: {release['id']})")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(f"[*] Release for {tag} does not exist yet. Creating...")
        else:
            print(f"[!] Error checking release: {e}")
            sys.exit(1)

    release_body = """## 🗣️ SpeakThat v1.2.0 Release

SpeakThat is an instant, 100% offline text-to-speech desktop app for Windows. Highlight any text in your browser, PDF reader, IDE, or document and press `Ctrl+Shift+R` to hear it read aloud immediately.

---

### ✨ What's New in v1.2.0

- 🪟 **Microsoft WinUI 3 Fluent Design**: Hardware-accelerated rounded corners, semi-transparent frosted Acrylic backdrops, smooth floating pill HUD, and Segoe Fluent icons.
- ⚡ **100% Offline Paradee 8M ONNX Engine**: Distilled from Kokoro-82M, synthesizing natural human speech locally on CPU at ~20x real-time speed (zero cloud API calls, zero telemetry, 100% private).
- ⌨️ **Customizable System-Wide Shortcuts**: Live interactive hotkey recorder for both **Read Selection** (default: `Ctrl+Shift+R`) and **Stop Speech** (default: `Ctrl+Shift+X`).
- 🎨 **Configurable Pop-up HUD Styles**: Choose between **Default (440×74)**, **Small (310×54)**, **Tiny (154×46)**, or **No Pop-up** (silent keyboard shortcut mode).
- 🎛️ **Audition & Voice Manager**: Live audition test phrases, instant speed (0.5x–2.0x) and volume controls, and 4 neural voices (`Isabella`, `Heart`, `Puck`, `Fable`).
- ⚙️ **Automation & Clipboard Behavior**: Preserve clipboard history toggle, clipboard fallback on empty selection, minimize to tray on close, and start minimized on launch.
- 📦 **Dual Packaging**: Standalone GUI installer (`SpeakThat-Setup.exe`) and portable zero-install archive (`SpeakThat-v1.2-Windows-x64.zip`).
- ⚖️ **Open Source License**: Released under the permissive MIT License.

---

### 📥 Download & Installation

| File | Size | Description |
| :--- | :---: | :--- |
| **[`SpeakThat-Setup.exe`](https://github.com/amzmihon/Speak-That-Windows/releases/download/v1.2.0/SpeakThat-Setup.exe)** | **114.8 MB** | **Recommended.** Automated single-file Windows installer. Installs to `%LOCALAPPDATA%\\Programs\\SpeakThat` and creates Start Menu and Desktop shortcuts. |
| **[`SpeakThat-v1.2-Windows-x64.zip`](https://github.com/amzmihon/Speak-That-Windows/releases/download/v1.2.0/SpeakThat-v1.2-Windows-x64.zip)** | **105.5 MB** | **Portable Archive.** Extract anywhere (e.g. `C:\\SpeakThat` or USB) and double-click `SpeakThat.exe`. Includes `Install.bat`. |

#### ⚡ One-Command PowerShell Install
Open PowerShell and run:
```powershell
irm https://raw.githubusercontent.com/amzmihon/Speak-That-Windows/main/install.ps1 | iex
```

---

### 🖥️ System Requirements
- **OS**: Windows 10 (1809+) or Windows 11 (64-bit x64)
- **RAM**: 200 MB free RAM
- **CPU**: Standard x64 processor (no GPU required)
- **Network**: None (100% offline)
"""

    if not release:
        create_url = f"https://api.github.com/repos/{owner}/{repo}/releases"
        payload = {
            "tag_name": tag,
            "target_commitish": "main",
            "name": "SpeakThat v1.2.0 — WinUI 3 Fluent HUD, Offline Paradee 8M AI, & Customizable Hotkeys",
            "body": release_body,
            "draft": False,
            "prerelease": False
        }
        req = urllib.request.Request(
            create_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={**headers, "Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as resp:
            release = json.loads(resp.read().decode())
            print(f"[✓] Created release ID: {release['id']} ({release['html_url']})")

    # 2. Upload assets
    upload_url_template = release["upload_url"] # e.g. "https://uploads.github.com/repos/.../assets{?name,label}"
    base_upload_url = upload_url_template.split("{")[0]

    existing_assets = {a["name"]: a["id"] for a in release.get("assets", [])}

    assets_to_upload = [
        (r"E:\Speak-That-Windows\dist\SpeakThat-Setup.exe", "SpeakThat-Setup.exe", "application/vnd.microsoft.portable-executable"),
        (r"E:\Speak-That-Windows\dist\SpeakThat-v1.2-Windows-x64.zip", "SpeakThat-v1.2-Windows-x64.zip", "application/zip")
    ]

    for fpath, name, ctype in assets_to_upload:
        if not os.path.exists(fpath):
            print(f"[!] Warning: File {fpath} not found. Skipping.")
            continue

        fsize = os.path.getsize(fpath)
        fsize_mb = fsize / 1024 / 1024

        # Delete if asset already exists on release
        if name in existing_assets:
            print(f"[*] Asset {name} already exists. Deleting prior upload...")
            del_url = f"https://api.github.com/repos/{owner}/{repo}/releases/assets/{existing_assets[name]}"
            del_req = urllib.request.Request(del_url, headers=headers, method="DELETE")
            try:
                with urllib.request.urlopen(del_req) as dresp:
                    pass
                print(f"[✓] Deleted previous {name}")
            except Exception as e:
                print(f"[!] Warning deleting {name}: {e}")

        print(f"[*] Uploading {name} ({fsize_mb:.2f} MB)... Please wait.")
        target_url = f"{base_upload_url}?name={urllib.parse.quote(name)}"

        with open(fpath, "rb") as f:
            data = f.read()

        up_headers = {
            "Authorization": f"token {token}",
            "User-Agent": "SpeakThat-Release-Bot",
            "Content-Type": ctype,
            "Content-Length": str(fsize)
        }
        up_req = urllib.request.Request(target_url, data=data, headers=up_headers, method="POST")

        try:
            with urllib.request.urlopen(up_req) as up_resp:
                res_data = json.loads(up_resp.read().decode())
                print(f"[✓] Successfully uploaded {name}! (Download URL: {res_data.get('browser_download_url')})")
        except Exception as e:
            print(f"[!] Failed to upload {name}: {e}")
            sys.exit(1)

    print("\n[✓] Release creation and asset uploads completed successfully!")
    print(f"Release URL: {release.get('html_url')}")

if __name__ == "__main__":
    main()

