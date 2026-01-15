# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Loba - Live OBS Subtitle Application
Build for macOS: pyinstaller loba.spec
"""

import sys
from pathlib import Path

block_cipher = None

# Get the project root directory
project_root = Path(SPECPATH)

# Data files to include
datas = [
    # UI assets (HTML, CSS, JS)
    (str(project_root / 'app' / 'ui' / 'overlay.html'), 'app/ui'),
    (str(project_root / 'app' / 'ui' / 'overlay.css'), 'app/ui'),
    (str(project_root / 'app' / 'ui' / 'overlay.js'), 'app/ui'),
    (str(project_root / 'app' / 'ui' / 'control.html'), 'app/ui'),
    # Models - Whisper
    (str(project_root / 'models' / 'ggml-small.en-q5_1.bin'), 'models'),
    # Models - Translation (MarianMT)
    (str(project_root / 'models' / 'opus-mt-en-pt-ct2'), 'models/opus-mt-en-pt-ct2'),
    # Models - Translation (M2M100)
    (str(project_root / 'models' / 'm2m100-en-pt-br-ct2'), 'models/m2m100-en-pt-br-ct2'),
]

# Binaries to include
binaries = [
    (str(project_root / 'bin' / 'whisper-cli'), 'bin'),
]

# Hidden imports that PyInstaller might miss
hiddenimports = [
    'ctranslate2',
    'sounddevice',
    'pynput',
    'pynput.keyboard',
    'pynput.keyboard._darwin',
    'aiohttp',
    'transformers',
    'sentencepiece',
    'numpy',
    'tkinter',
    '_tkinter',
]

a = Analysis(
    [str(project_root / 'main.py')],
    pathex=[str(project_root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='Loba',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # No console window for GUI app
    disable_windowed_traceback=False,
    argv_emulation=True,  # Important for macOS
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Loba',
)

# macOS App Bundle
app = BUNDLE(
    coll,
    name='Loba.app',
    icon=None,  # Add icon path here if you have one: 'assets/icon.icns'
    bundle_identifier='com.loba.subtitles',
    info_plist={
        'NSMicrophoneUsageDescription': 'Loba needs microphone access to capture speech for live subtitles.',
        'NSHighResolutionCapable': True,
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleName': 'Loba',
        'CFBundleDisplayName': 'Loba - Live Subtitles',
    },
)
