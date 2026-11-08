# -*- mode: python ; coding: utf-8 -*-
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
    src_lower = src.lower().replace('\\', '/')
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
    hooksconfig={},
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
