"""
NPC File Path Utility
Utility for managing and searching for NPC.json files in both development and production modes
"""

import os
import sys


def get_npc_file_path():
    """
    Search for NPC.json file with fallback strategy

    Priority:
    1. User-editable file (outside exe in production, current dir in dev)
    2. Bundled copy in _internal/ (production only)
    3. Default path for new file creation

    Returns:
        String: file path that found or should be used for creating new file
    """

    if hasattr(sys, "_MEIPASS"):
        # PRODUCTION MODE - PyInstaller executable
        exe_dir = os.path.dirname(sys.executable)
        print(f"[NPC File Utils] Production mode - executable dir: {exe_dir}")

        # Step 1: Try to find user-editable file (outside exe)
        for filename in ["NPC.json", "npc.json"]:
            user_path = os.path.join(exe_dir, filename)
            if os.path.exists(user_path):
                print(f"[NPC File Utils] Found user-editable file: {user_path}")
                return user_path

        # Step 2: Fallback to bundled copy in _internal/
        for filename in ["NPC.json", "npc.json"]:
            bundled_path = os.path.join(sys._MEIPASS, filename)
            if os.path.exists(bundled_path):
                print(f"[NPC File Utils] Using bundled copy: {bundled_path}")
                return bundled_path

        # Step 3: No file found - return default path (will be created)
        default_path = os.path.join(exe_dir, "NPC.json")
        print(f"[NPC File Utils] No file found, will use: {default_path}")
        return default_path

    else:
        # DEVELOPMENT MODE - running from source
        search_dir = os.path.abspath(".")
        print(f"[NPC File Utils] Development mode - searching in: {search_dir}")

        # Search for existing files (prefer lowercase in dev)
        for filename in ["npc.json", "NPC.json"]:
            full_path = os.path.join(search_dir, filename)
            if os.path.exists(full_path):
                print(f"[NPC File Utils] Found file: {full_path}")
                return full_path

        # No file found - return default path
        default_path = os.path.join(search_dir, "npc.json")
        print(f"[NPC File Utils] File not found, will use: {default_path}")
        return default_path


def get_game_info_from_npc_file():
    """
    Read current file and extract info from _game_info

    Returns:
        Dict: information or empty if file not found
    """
    import json

    npc_filepath = get_npc_file_path()
    try:
        with open(npc_filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Return if this field exists, if not return empty
        return data.get("_game_info", {})
    except (json.JSONDecodeError, IOError) as e:
        # Cannot read file

        # Return empty if error occurred or file doesn't exist
        return {}


def ensure_npc_file_exists():
    """
    Check if file exists or not, if not create initial file
    """
    import json

    npc_path = get_npc_file_path()
    if not os.path.exists(npc_path):
        # Create initial file
        default_data = {
            "main_characters": [],
            "side_characters": [],
            "monsters": [],
            "locations": [],
            "_game_info": {
                "game_name": "Unknown Game",
                "version": "1.0"
            }
        }
        try:
            with open(npc_path, "w", encoding="utf-8") as f:
                json.dump(default_data, f, indent=4, ensure_ascii=False)
            print(f"[NPC File Utils] Created initial file at: {npc_path}")
            return True
        except Exception as e:
            print(f"[NPC File Utils] Cannot create initial file: {e}")
            return False
    return True
