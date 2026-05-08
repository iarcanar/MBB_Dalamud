# -*- mode: python ; coding: utf-8 -*-
# MBB Dalamud Bridge - PyInstaller Specification
# Version: 1.8.4
# Build: 04032026-02 (rebuilt 2026-05-01 for v1.8.2 with PyQt6 + cleanup)
#
# Build command:
#   cd python-app
#   pyinstaller mbb.spec --clean --noconfirm --distpath ../dist_test
#
# Output: ../dist_test/MBB/MBB.exe + ../dist_test/MBB/_internal/

from PyInstaller.utils.hooks import collect_data_files, collect_submodules
import os
import sys

spec_root = os.path.abspath(SPECPATH)

# ============================================================
# DATA FILES (bundled into _internal/)
# ============================================================
# google.generativeai needs its data files (templates, schemas)
datas_google = collect_data_files('google.generativeai')

# Project data files - paths relative to spec_root (python-app/)
added_files = [
    # NPC database (lowercase per actual filename)
    # npc_file_utils looks next-to-exe FIRST, then _internal as fallback
    ('npc.json', '.'),

    # version.py — bundled as a data file so the updater can read __version__
    # without needing to import a Python module. Updater greps for the
    # __version__ = "..." line. Without this, the updater would see no local
    # version (PyInstaller normally compiles .py → .pyc inside the PYZ archive,
    # not as a loose file the updater can read).
    ('version.py', '.'),

    # .env template - users copy this to .env next to MBB.exe and fill in their key
    ('.env.example', '.'),

    # Assets (8MB) - icons, splash, logos
    ('assets', 'assets'),

    # Fonts (2.8MB) - Anuphan, FC Minimal, Caveat, Pacifico, Google Sans
    ('fonts', 'fonts'),

    # PyQt6 UI modules (Python source - PyInstaller compiles to .pyc in _internal/pyqt_ui/)
    ('pyqt_ui', 'pyqt_ui'),

    # Legacy ui_components (Tkinter helpers still used by some panels)
    ('ui_components', 'ui_components'),

    # NPC images (1.4MB) - bundled defaults; user can add more next to exe
    ('npc_images', 'npc_images'),
]

datas = added_files + datas_google

# ============================================================
# HIDDEN IMPORTS
# ============================================================
# PyInstaller's static analysis misses imports inside functions / dynamic imports
hiddenimports = [
    # ---- stdlib (rarely needed but cheap to include) ----
    'tkinter',
    'tkinter.ttk',
    'tkinter.font',
    'tkinter.filedialog',
    'tkinter.messagebox',
    'tkinter.colorchooser',

    # ---- Windows COM / Win32 ----
    'win32com',
    'win32com.client',
    'win32gui',
    'win32con',
    'win32api',
    'win32process',
    'win32pipe',
    'win32file',
    'pywintypes',

    # ---- Google Gemini SDK ----
    'google',
    'google.generativeai',
    'google.generativeai.types',
    'google.ai',
    'google.ai.generativelanguage',

    # ---- HTTP / Network ----
    'requests',
    'urllib3',
    'certifi',
    'charset_normalizer',
    'idna',

    # ---- Image processing ----
    'PIL',
    'PIL.Image',
    'PIL.ImageTk',
    'PIL.ImageDraw',
    'PIL.ImageFont',
    'PIL.ImageFilter',
    'PIL.ImageQt',  # PIL <-> Qt bridge

    # ---- System / OS ----
    'psutil',
    'keyboard',
    'dotenv',

    # ---- PyQt6 (core + extras) ----
    'PyQt6',
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'PyQt6.sip',

    # ---- MBB core modules (imported lazily / conditionally) ----
    'version',
    'api_key_manager',
    'api_manager',
    'appearance',
    'asset_manager',
    'button_factory',
    'conversation_logger',
    'dalamud_bridge',
    'dalamud_immediate_handler',
    'dialogue_cache',
    'enhanced_name_detector',
    'font_manager',
    'image_optimizer',
    'loggings',
    'Manager',
    'mini_ui',
    'model',
    'npc_data_manager',
    'npc_file_utils',
    'resource_utils',
    'settings',
    'simplified_hotkey_ui',
    'text_corrector',
    'translated_logs',  # legacy Tkinter version (unused but kept on disk)
    'translated_ui',
    'translation_logger',
    'translator_factory',
    'translator_gemini',
    'ui_config',

    # ---- ui_components (Tkinter helper widgets) ----
    'ui_components',
    'ui_components.bottom_bar',
    'ui_components.control_panel',
    'ui_components.header_bar',

    # ---- pyqt_ui (PyQt6 panels — actual UI used in v1.8.x) ----
    'pyqt_ui',
    'pyqt_ui.bottom_bar',
    'pyqt_ui.control_panel',
    'pyqt_ui.font_panel',
    'pyqt_ui.header_bar',
    'pyqt_ui.hotkey_panel',
    'pyqt_ui.main_window',
    'pyqt_ui.model_panel',
    'pyqt_ui.npc_manager_panel',
    'pyqt_ui.qt_font_manager',
    'pyqt_ui.settings_panel',
    'pyqt_ui.signals',
    'pyqt_ui.styles',
    'pyqt_ui.theme_panel',
    'pyqt_ui.translated_logs',
]

# ============================================================
# ANALYSIS
# ============================================================
a = Analysis(
    ['MBB.py'],
    pathex=[spec_root],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # ---- OCR era - permanently removed ----
        'easyocr',
        'torch',
        'torchvision',
        'cv2',
        'opencv-python',

        # ---- Heavy ML / sci packages we don't actually use ----
        'matplotlib',
        'numpy.distutils',
        'scipy',
        'IPython',
        'notebook',
        'pytest',

        # ---- sv_ttk no longer used (PyQt6 styling replaces it) ----
        'sv_ttk',

        # ---- Test / dev only ----
        'unittest',
    ],
    noarchive=False,
    optimize=0,
)

# ============================================================
# PYZ + EXE + COLLECT
# ============================================================
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='MBB',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # Console enabled for debugging - flip to False for prod release
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/mbb_icon.ico',
    version_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='MBB',
)

# ============================================================
# Post-build — promote user-editable data next to MBB.exe
# ============================================================
# Default PyInstaller layout buries everything in _internal/, but npc.json +
# npc_images are the files users actually want to find / edit / share. Put a
# copy at <DISTPATH>/MBB/<file> so they're discoverable without spelunking.
# The original copies stay in _internal/ as read-only fallback (npc_file_utils
# resolver already prefers next-to-exe → _internal as last resort).
import shutil

_dist_root = os.path.join(DISTPATH, 'MBB')
_npc_internal = os.path.join(_dist_root, '_internal', 'npc.json')
_npc_external = os.path.join(_dist_root, 'npc.json')
if os.path.exists(_npc_internal):
    try:
        shutil.copyfile(_npc_internal, _npc_external)
        print(f"[post-build] Promoted npc.json -> {_npc_external}")
    except Exception as e:
        print(f"[post-build] WARN: failed to copy npc.json: {e}")

_imgs_internal = os.path.join(_dist_root, '_internal', 'npc_images')
_imgs_external = os.path.join(_dist_root, 'npc_images')
if os.path.exists(_imgs_internal):
    try:
        shutil.copytree(_imgs_internal, _imgs_external, dirs_exist_ok=True)
        print(f"[post-build] Promoted npc_images/ -> {_imgs_external}")
    except Exception as e:
        print(f"[post-build] WARN: failed to copy npc_images: {e}")

# ============================================================
# Bundled Plugin — copy Dalamud DLL set into MBB/plugin/
# ============================================================
# v1.8.4+ ships the C# plugin INSIDE the same zip as the EXE so users only
# download one thing and only browse one path. The DLL must be built first
# (dotnet build -c Release) — if the source files aren't there, fail loudly
# so the dev notices instead of shipping an EXE without its plugin.
_plugin_src_dir = os.path.join(os.path.dirname(spec_root), 'DalamudMBBBridge', 'bin', 'Release')
_plugin_dst_dir = os.path.join(_dist_root, 'plugin')
_plugin_files = ['DalamudMBBBridge.dll', 'DalamudMBBBridge.json', 'icon.png']
if all(os.path.exists(os.path.join(_plugin_src_dir, f)) for f in _plugin_files):
    os.makedirs(_plugin_dst_dir, exist_ok=True)
    for fname in _plugin_files:
        try:
            shutil.copyfile(
                os.path.join(_plugin_src_dir, fname),
                os.path.join(_plugin_dst_dir, fname),
            )
        except Exception as e:
            print(f"[post-build] WARN: failed to copy plugin/{fname}: {e}")
    print(f"[post-build] Bundled Dalamud plugin -> {_plugin_dst_dir}")
else:
    missing = [f for f in _plugin_files
               if not os.path.exists(os.path.join(_plugin_src_dir, f))]
    raise SystemExit(
        f"\n[post-build] BUILD ABORTED — Dalamud plugin DLL not found.\n"
        f"[post-build] Missing in {_plugin_src_dir}:\n"
        f"[post-build]   {', '.join(missing)}\n\n"
        f"[post-build] Build the C# plugin first:\n"
        f"[post-build]   dotnet build DalamudMBBBridge/DalamudMBBBridge.csproj -c Release"
    )

# ============================================================
# Bundled Updater — copy MBB-Updater.exe (built separately) into MBB/
# ============================================================
# The standalone updater lives next to MBB.exe so users can double-click it
# anytime to pull the latest GitHub release. Updater is built by its own
# pyinstaller spec at updater/updater.spec — make sure to build that BEFORE
# this spec, otherwise the copy is skipped (with a warning) and the released
# MBB folder won't have the updater.
_updater_built = os.path.join(DISTPATH, 'MBB-Updater.exe')
_updater_dst = os.path.join(_dist_root, 'MBB-Updater.exe')
if os.path.exists(_updater_built):
    try:
        shutil.copyfile(_updater_built, _updater_dst)
        print(f"[post-build] Bundled MBB-Updater.exe -> {_updater_dst}")
    except Exception as e:
        print(f"[post-build] WARN: failed to copy updater: {e}")
else:
    print(f"[post-build] NOTE: {_updater_built} not found — skipped updater bundle")
    print(f"[post-build]       (build updater first: pyinstaller updater/updater.spec)")

# ============================================================
# Pre-deploy secrets scan — refuse to ship a build with leaked credentials
# ============================================================
# Catches: stray .env that was created by smoke-testing the EXE before
# packaging, accidentally bundled .key / .pem / *.env, content matching the
# Gemini API key shape, etc. Raising SystemExit aborts the entire build.
_secrets_scan = os.path.join(os.path.dirname(spec_root), 'scripts', 'check_no_secrets.py')
if os.path.exists(_secrets_scan):
    print(f"[post-build] Running secrets scan on {_dist_root}…")
    import subprocess
    rc = subprocess.call([sys.executable, _secrets_scan, _dist_root])
    if rc != 0:
        raise SystemExit(
            f"\n[post-build] BUILD ABORTED — secrets scanner exit={rc}\n"
            f"[post-build] DO NOT deploy this build until violations are fixed.\n"
            f"[post-build] Common cause: smoke-tested MBB.exe before packaging "
            f"(creates .env in MBB/ with your real key). Delete it + rebuild."
        )
    print(f"[post-build] secrets scan: clean ✓")
else:
    print(f"[post-build] WARN: secrets scanner not found at {_secrets_scan}")
    print(f"[post-build]       skipping pre-deploy security check")

# ============================================================
# Build Notes
# ============================================================
# - One-folder build (--onedir mode) - easier to package + asset edits
# - console=True for debugging - turn False for end-user release
# - UPX compression on (saves ~30% size)
# - All assets bundled in _internal/ with sys._MEIPASS resolution
# - npc.json bundled as _internal fallback; runtime prefers next-to-exe copy
# - PyQt6 fully bundled (was missing in pre-v1.7 build)
# - Output: ~28MB exe + ~330MB _internal = ~360MB total
# - Distribution zip should compress to ~80-100MB
