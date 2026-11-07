"""Graphical Self-Extracting Installer for SpeakThat."""

import os
import sys
import time
import zipfile
import subprocess
import tkinter as tk
from tkinter import ttk

def install():
    root = tk.Tk()
    root.title("SpeakThat Setup")
    root.geometry("460x220")
    root.resizable(False, False)
    root.configure(bg="#12141C")

    # Center window
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    root.geometry(f"460x220+{(sw-460)//2}+{(sh-220)//2}")

    # Title label
    lbl_title = tk.Label(
        root,
        text="Installing SpeakThat v1.2",
        font=("Segoe UI", 14, "bold"),
        fg="#F8FAFC",
        bg="#12141C"
    )
    lbl_title.pack(pady=(20, 4))

    lbl_sub = tk.Label(
        root,
        text="Lightweight Windows Text Reader (Paradee 8M ONNX)",
        font=("Segoe UI", 9),
        fg="#818CF8",
        bg="#12141C"
    )
    lbl_sub.pack(pady=(0, 16))

    # Status label
    lbl_status = tk.Label(
        root,
        text="Extracting application files...",
        font=("Segoe UI", 9),
        fg="#94A3B8",
        bg="#12141C"
    )
    lbl_status.pack(pady=(0, 8))

    # Progress bar
    style = ttk.Style()
    style.theme_use('default')
    style.configure(
        "Custom.Horizontal.TProgressbar",
        troughcolor="#1A1D28",
        background="#6366F1",
        thickness=8
    )
    progress = ttk.Progressbar(
        root,
        style="Custom.Horizontal.TProgressbar",
        orient="horizontal",
        length=380,
        mode="determinate"
    )
    progress.pack(pady=(0, 20))

    def do_install():
        try:
            # 1. Target directory
            local_appdata = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
            target_dir = os.path.join(local_appdata, "Programs", "SpeakThat")
            os.makedirs(target_dir, exist_ok=True)

            # 2. Path to bundled or sibling zip
            base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
            zip_path = os.path.join(base_dir, "app_payload.zip")

            if not os.path.exists(zip_path):
                # Try sibling dist
                sibling_zip = os.path.join(os.path.dirname(base_dir), "SpeakThat-v1.2-Windows-x64.zip")
                if os.path.exists(sibling_zip):
                    zip_path = sibling_zip

            if os.path.exists(zip_path):
                with zipfile.ZipFile(zip_path, 'r') as zf:
                    members = zf.infolist()
                    total = len(members)
                    for i, m in enumerate(members):
                        zf.extract(m, target_dir)
                        if i % 15 == 0 or i == total - 1:
                            pct = int((i + 1) / total * 80)
                            progress['value'] = pct
                            lbl_status.configure(text=f"Extracting: {os.path.basename(m.filename)}")
                            root.update()

            # The actual app is inside target_dir\SpeakThat
            app_dir = os.path.join(target_dir, "SpeakThat") if os.path.exists(os.path.join(target_dir, "SpeakThat")) else target_dir
            exe_path = os.path.join(app_dir, "SpeakThat.exe")
            ico_path = os.path.join(app_dir, "assets", "icon.ico")

            # 3. Create Desktop & Start Menu Shortcuts via PowerShell
            lbl_status.configure(text="Creating desktop & start menu shortcuts...")
            progress['value'] = 90
            root.update()

            ps_cmd = f"""
$ws = New-Object -ComObject WScript.Shell
$desktop = [System.IO.Path]::Combine([Environment]::GetFolderPath('Desktop'), 'SpeakThat.lnk')
$s1 = $ws.CreateShortcut($desktop)
$s1.TargetPath = '{exe_path}'
$s1.IconLocation = '{ico_path}'
$s1.Description = 'SpeakThat - Windows Text Reader'
$s1.WorkingDirectory = '{app_dir}'
$s1.Save()

$startMenu = [System.IO.Path]::Combine([Environment]::GetFolderPath('StartMenu'), 'Programs', 'SpeakThat.lnk')
$s2 = $ws.CreateShortcut($startMenu)
$s2.TargetPath = '{exe_path}'
$s2.IconLocation = '{ico_path}'
$s2.Description = 'SpeakThat - Windows Text Reader'
$s2.WorkingDirectory = '{app_dir}'
$s2.Save()
"""
            subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_cmd], capture_output=True)

            progress['value'] = 100
            lbl_status.configure(text="Installation completed! Launching SpeakThat...", fg="#10B981")
            root.update()
            time.sleep(1.0)

            # 4. Launch app
            if os.path.exists(exe_path):
                subprocess.Popen([exe_path], cwd=app_dir)

            root.destroy()
        except Exception as e:
            lbl_status.configure(text=f"Error: {e}", fg="#EF4444")

    root.after(200, do_install)
    root.mainloop()

if __name__ == "__main__":
    install()
