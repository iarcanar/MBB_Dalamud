# -*- mode: python ; coding: utf-8 -*-
# MBB Updater — PyInstaller spec (onefile mode)
#
# Build:
#   cd updater
#   pyinstaller updater.spec --clean --noconfirm --distpath ../dist_test
#
# Output: ../dist_test/MBB-Updater.exe
# Then python-app/mbb.spec post-build copies it into ../dist_test/MBB/.

import os

spec_root = os.path.abspath(SPECPATH)
mbb_root = os.path.abspath(os.path.join(spec_root, '..'))
assets_dir = os.path.join(mbb_root, 'python-app', 'assets')
icon_path = os.path.join(assets_dir, 'mbb_icon.ico')

# Bundle the header logo + ico so the UI looks consistent with the main app
_datas = []
for fname in ('mbb_meteor.png', 'mbb_icon.ico'):
    _src = os.path.join(assets_dir, fname)
    if os.path.exists(_src):
        # ('.' = MEIPASS root in onefile — _resolve_asset() looks here first)
        _datas.append((_src, '.'))

a = Analysis(
    ['updater.py'],
    pathex=[spec_root],
    binaries=[],
    datas=_datas,
    hiddenimports=[
        # We use psutil to detect/kill running MBB.exe before extraction.
        'psutil',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Keep the updater small — it's a single-purpose tool. Strip everything
        # the main MBB needs but the updater doesn't.
        'PyQt6', 'PyQt6.sip',
        'numpy', 'pandas', 'scipy',
        'PIL', 'PIL.Image',
        'google', 'google.generativeai',
        'matplotlib',
        'IPython',
        'cv2',
        'pytest', 'unittest',
        # We use stdlib urllib instead of requests
        'requests',
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

# Onefile mode: pass binaries + datas directly to EXE() without a COLLECT step.
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='MBB-Updater',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,             # GUI app — no cmd window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path if os.path.exists(icon_path) else None,
)
