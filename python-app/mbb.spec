# -*- mode: python ; coding: utf-8 -*-
# MBB Dalamud Bridge - PyInstaller Specification
# Version: 1.0.0
# Build: 01232026-01

from PyInstaller.utils.hooks import collect_data_files, collect_submodules
import os

# Get the current directory
spec_root = os.path.abspath(SPECPATH)

# Collect all data files for google-generativeai
datas_google = collect_data_files('google.generativeai')

# Define additional data files to include
added_files = [
    # NPC Database
    ('NPC.json', '.'),

    # Environment template
    ('.env.example', '.'),

    # Fonts directory (all fonts)
    ('fonts', 'fonts'),

    # Assets directory (all images)
    ('assets', 'assets'),

    # UI components
    ('ui_components', 'ui_components'),
]

# Combine all data files
datas = added_files + datas_google

# Hidden imports - modules that PyInstaller might miss
hiddenimports = [
    # Core modules
    'tkinter',
    'tkinter.ttk',
    'tkinter.font',
    'tkinter.filedialog',
    'tkinter.messagebox',

    # Windows integration
    'win32com',
    'win32com.client',
    'win32gui',
    'win32con',
    'win32api',
    'win32process',
    'pywintypes',

    # Google AI
    'google',
    'google.generativeai',
    'google.generativeai.types',
    'google.ai',
    'google.ai.generativelanguage',

    # HTTP/Network
    'requests',
    'urllib3',
    'certifi',
    'charset_normalizer',

    # Image processing
    'PIL',
    'PIL.Image',
    'PIL.ImageTk',
    'PIL.ImageDraw',
    'PIL.ImageFont',

    # System
    'psutil',
    'keyboard',
    'dotenv',
    'json',
    'logging',
    'threading',
    'queue',
    'subprocess',

    # Theme
    'sv_ttk',

    # All Python app modules
    'advance_ui',
    'api_manager',
    'appearance',
    'asset_manager',
    'button_factory',
    'control_ui',
    'dalamud_bridge',
    'dalamud_immediate_handler',
    'dalamud_improvements',
    'dialogue_cache',
    'dialogue_simulator',
    'enhanced_name_detector',
    'font_manager',
    'loggings',
    'Manager',
    'npc_manager_card',
    'resource_utils',
    'settings',
    'text_corrector',
    'translated_ui',
    'translation_logger',
    'ui_components.bottom_bar',
    'ui_components.control_panel',
    'ui_components.header_bar',
]

# Analysis configuration
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
        # Exclude OCR modules (removed from project)
        'easyocr',
        'torch',
        'torchvision',
        'cv2',
        'opencv-python',

        # Exclude unnecessary modules
        'matplotlib',
        'numpy.distutils',
        'scipy',
        'IPython',
        'notebook',
        'pytest',
    ],
    noarchive=False,
    optimize=0,
)

# PYZ archive (compiled Python code)
pyz = PYZ(a.pure)

# EXE configuration
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
    console=False,  # No console window (GUI only)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/mbb_icon.png',  # Application icon
    version_file=None,
)

# COLLECT - bundle everything into one folder
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='MBB',
)

# Build configuration notes:
# - One-folder build (easier to package for distribution)
# - No console window (windowed mode for GUI)
# - UPX compression enabled
# - All assets bundled inside _internal folder
# - MBB.exe will be in dist/MBB/ folder
