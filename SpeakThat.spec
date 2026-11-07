# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

block_cipher = None

# Collect all package assets
ctk_datas = collect_data_files('customtkinter')
misaki_datas = collect_data_files('misaki')
spacy_datas = collect_data_files('spacy')
en_datas = collect_data_files('en_core_web_sm')

onnx_binaries = collect_dynamic_libs('onnxruntime')
sd_binaries = collect_dynamic_libs('sounddevice')

datas = [
    ('assets', 'assets'),
    ('speak_that/model', 'speak_that/model'),
] + ctk_datas + misaki_datas + spacy_datas + en_datas

binaries = onnx_binaries + sd_binaries

hiddenimports = [
    'customtkinter',
    'paradee',
    'misaki',
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
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'scipy', 'torch', 'torchaudio', 'torchvision', 'pandas', 'IPython', 'jupyter'],
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
