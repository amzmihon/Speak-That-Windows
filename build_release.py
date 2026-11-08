"""Build script to create a standalone, redistributable Windows executable (.exe) and installer for SpeakThat.
"""

import os
import sys
import shutil
import subprocess
import zipfile

def build():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base_dir)

    print("===================================================")
    print("        SpeakThat Windows Release Builder          ")
    print("===================================================\n")

    # 1. Clean previous build artifacts
    for folder in ["build", "dist"]:
        if os.path.exists(folder):
            print(f"[*] Cleaning old {folder} directory...")
            try:
                shutil.rmtree(folder)
            except Exception as e:
                print(f"[!] Warning cleaning {folder}: {e}")

    # 2. Generate PyInstaller Spec
    spec_content = f'''# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

block_cipher = None

# Collect all package assets
ctk_datas = collect_data_files('customtkinter')
misaki_datas = collect_data_files('misaki')
spacy_datas = collect_data_files('spacy')
thinc_datas = collect_data_files('thinc')
en_datas = collect_data_files('en_core_web_sm')
espeak_datas = collect_data_files('espeakng_loader')
espeak_binaries = collect_dynamic_libs('espeakng_loader')
lt_datas = collect_data_files('language_tags')
ph_datas = collect_data_files('phonemizer')

onnx_binaries = collect_dynamic_libs('onnxruntime')
sd_binaries = collect_dynamic_libs('sounddevice')

raw_datas = [
    ('assets', 'assets'),
    ('speak_that/model', 'speak_that/model'),
] + ctk_datas + misaki_datas + spacy_datas + thinc_datas + en_datas + espeak_datas + lt_datas + ph_datas

# Filter out dead C/C++ source code, Cython headers, and non-English dictionaries
dead_exts = ('.cpp', '.h', '.hpp', '.c', '.pyx', '.pxd', '.pyi', '.dylib', '.ds_store')
datas = []
for src, dst in raw_datas:
    src_lower = src.lower().replace('\\\\', '/')
    filename = src_lower.split('/')[-1]
    
    # 1. Skip Cython C/C++ source code leftovers (spacy alone bundles ~75MB of .cpp files)
    if any(src_lower.endswith(ext) for ext in dead_exts):
        continue
    # 2. Skip non-English dictionaries in espeakng_loader (ru_dict is 8.14MB, cmn_dict is 1.49MB, etc.)
    if 'espeak-ng-data' in src_lower and '_dict' in filename:
        if not (filename.startswith('en') or filename.startswith('gmw')):
            continue
    # 3. Skip unit tests and doc trees
    if any(sub in src_lower for sub in ['/tests/', '/test/']):
        continue
        
    datas.append((src, dst))

binaries = onnx_binaries + sd_binaries + espeak_binaries

hiddenimports = [
    'customtkinter',
    'paradee',
    'misaki',
    'misaki.en',
    'misaki.espeak',
    'espeakng_loader',
    'language_tags',
    'phonemizer',
    'phonemizer.backend',
    'phonemizer.backend.espeak',
    'spacy',
    'en_core_web_sm',
    'sounddevice',
    '_sounddevice_data',
    'pystray',
    'pynput',
    'pynput.keyboard._win32',
    'pynput.mouse._win32',
    'pyperclip',
    'onnxruntime',
    'PIL',
    'PIL._imagingtk',
    'PIL.ImageTk',
]

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[
        'matplotlib', 'scipy', 'torch', 'torchaudio', 'torchvision', 'pandas', 'IPython', 'jupyter',
        'hf_xet', 'pytest', 'unittest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SpeakThat',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='SpeakThat',
)
'''

    spec_path = os.path.join(base_dir, "SpeakThat.spec")
    with open(spec_path, "w", encoding="utf-8") as f:
        f.write(spec_content)
    print(f"[*] Generated PyInstaller specification: {spec_path}")

    # 3. Execute PyInstaller
    print("[*] Running PyInstaller compiler (this may take 1-2 minutes)...")
    pyinstaller_exe = os.path.join(base_dir, ".venv", "Scripts", "pyinstaller.exe")
    if not os.path.exists(pyinstaller_exe):
        pyinstaller_exe = "pyinstaller"

    cmd = [pyinstaller_exe, "SpeakThat.spec", "--noconfirm", "--clean"]
    res = subprocess.run(cmd)

    if res.returncode != 0:
        print(f"[!] PyInstaller build failed with exit code {res.returncode}")
        sys.exit(res.returncode)

    dist_dir = os.path.join(base_dir, "dist", "SpeakThat")
    if not os.path.exists(dist_dir):
        print(f"[!] Build output directory not found: {dist_dir}")
        sys.exit(1)

    print(f"[+] Application successfully compiled to: {dist_dir}")

    # 4. Prune dead C/C++ source files, test caches, and non-English dicts from compiled distribution
    print("[*] Optimizing compiled distribution (pruning dead source files & unneeded dicts)...")
    pruned_count = 0
    pruned_bytes = 0
    dead_endings = ('.cpp', '.h', '.hpp', '.c', '.pyx', '.pxd', '.pyi', '.dylib', '.ds_store', '.pdb')
    for root, dirs, files in os.walk(dist_dir):
        for f in files:
            f_lower = f.lower()
            fp = os.path.join(root, f)
            should_remove = False

            # Remove leftover C/C++ source code
            if any(f_lower.endswith(ext) for ext in dead_endings):
                should_remove = True
            # Remove non-English dictionaries from espeak-ng-data (e.g., ru_dict is 8.1MB, cmn_dict is 1.5MB)
            elif 'espeak-ng-data' in root.lower() and '_dict' in f_lower:
                if not (f_lower.startswith('en') or f_lower.startswith('gmw')):
                    should_remove = True

            if should_remove:
                try:
                    fsize = os.path.getsize(fp)
                    os.remove(fp)
                    pruned_count += 1
                    pruned_bytes += fsize
                except Exception:
                    pass

    print(f"[✓] Optimization complete: Pruned {pruned_count} files ({pruned_bytes / 1024 / 1024:.2f} MB saved)!")

    # 5. Copy essential companion files into dist/SpeakThat
    for fname in ["config.json", "README.md", "assets"]:
        fpath = os.path.join(base_dir, fname)
        if os.path.exists(fpath):
            if os.path.isdir(fpath):
                dest_dir = os.path.join(dist_dir, fname)
                if os.path.exists(dest_dir):
                    shutil.rmtree(dest_dir)
                shutil.copytree(fpath, dest_dir)
            else:
                shutil.copy(fpath, os.path.join(dist_dir, fname))

    # 6. Create one-click installer script: dist/SpeakThat/install.bat
    install_bat_content = """@echo off
title SpeakThat Windows Installer
cd /d "%~dp0"
echo ===================================================
echo             SpeakThat Windows Setup                
echo ===================================================
echo.
echo Installing SpeakThat to user Programs folder...

set "TARGET_DIR=%LOCALAPPDATA%\\Programs\\SpeakThat"
if not exist "%TARGET_DIR%" mkdir "%TARGET_DIR%"

echo [*] Stopping running SpeakThat instances if any...
taskkill /F /IM SpeakThat.exe > nul 2>&1

echo [*] Copying application files to %TARGET_DIR%...
xcopy /E /I /Y /Q * "%TARGET_DIR%\\" > nul

echo [*] Creating Desktop and Start Menu Shortcuts...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ws = New-Object -ComObject WScript.Shell; ^
   $d = Join-Path ([Environment]::GetFolderPath('Desktop')) 'SpeakThat.lnk'; ^
   $s1 = $ws.CreateShortcut($d); ^
   $s1.TargetPath = '%TARGET_DIR%\\SpeakThat.exe'; ^
   $s1.WorkingDirectory = '%TARGET_DIR%'; ^
   $s1.IconLocation = '%TARGET_DIR%\\assets\\icon.ico'; ^
   $s1.Description = 'SpeakThat - Windows Text Reader'; ^
   $s1.Save(); ^
   $sm = Join-Path ([Environment]::GetFolderPath('StartMenu')) 'Programs\\SpeakThat.lnk'; ^
   $s2 = $ws.CreateShortcut($sm); ^
   $s2.TargetPath = '%TARGET_DIR%\\SpeakThat.exe'; ^
   $s2.WorkingDirectory = '%TARGET_DIR%'; ^
   $s2.IconLocation = '%TARGET_DIR%\\assets\\icon.ico'; ^
   $s2.Description = 'SpeakThat - Windows Text Reader'; ^
   $s2.Save();"

echo.
echo [✓] Installation complete!
echo     * Application installed to: %TARGET_DIR%
echo     * Desktop Shortcut created: 'SpeakThat'
echo     * Start Menu Shortcut created: 'SpeakThat'
echo.
echo Launching SpeakThat now...
start "" "%TARGET_DIR%\\SpeakThat.exe"
pause
"""
    with open(os.path.join(dist_dir, "Install.bat"), "w", encoding="utf-8") as f:
        f.write(install_bat_content)

    # 7. Create clean portable ZIP package: dist/SpeakThat-v1.2-Windows-x64.zip
    zip_output = os.path.join(base_dir, "dist", "SpeakThat-v1.2-Windows-x64.zip")
    print(f"[*] Packaging standalone ZIP release (max compression): {zip_output}...")
    with zipfile.ZipFile(zip_output, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
        for root, dirs, files in os.walk(dist_dir):
            for file in files:
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, os.path.dirname(dist_dir))
                zipf.write(abs_path, rel_path)

    zip_size_mb = os.path.getsize(zip_output) / 1024 / 1024
    print(f"[✓] Release package created: {zip_output} ({zip_size_mb:.2f} MB)")

    # 8. Compile Self-Extracting GUI Installer: dist/SpeakThat-Setup.exe
    print("[*] Compiling Standalone Graphical Installer (SpeakThat-Setup.exe)...")
    setup_cmd = [pyinstaller_exe, "SpeakThat-Setup.spec", "--noconfirm", "--clean"]
    res_setup = subprocess.run(setup_cmd)
    if res_setup.returncode == 0:
        setup_exe = os.path.join(base_dir, "dist", "SpeakThat-Setup.exe")
        if os.path.exists(setup_exe):
            setup_size = os.path.getsize(setup_exe) / 1024 / 1024
            print(f"[✓] Setup installer compiled: {setup_exe} ({setup_size:.2f} MB)")

    print("\n[✓] All release build steps completed successfully!")

if __name__ == "__main__":
    build()

