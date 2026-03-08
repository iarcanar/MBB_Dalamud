import tkinter as tk
from PIL import ImageTk, Image
import os
import logging
from resource_utils import resource_path


class AssetManager:
    _icon_cache = {}

    @staticmethod
    def get_asset_path(file_name: str) -> str:
        """
        Finds the correct path for an asset file.
        Works in both development and PyInstaller environments.
        """
        # Try assets directory first (standard location)
        assets_path = resource_path(os.path.join("assets", file_name))
        print(f"[AssetManager] Checking assets path: {assets_path}")
        print(f"[AssetManager] Path exists: {os.path.exists(assets_path)}")
        if os.path.exists(assets_path):
            return assets_path

        # Fallback: try file name directly (for backward compatibility)
        direct_path = resource_path(file_name)
        print(f"[AssetManager] Checking direct path: {direct_path}")
        print(f"[AssetManager] Path exists: {os.path.exists(direct_path)}")
        if os.path.exists(direct_path):
            return direct_path

        raise FileNotFoundError(
            f"Asset '{file_name}' not found.\n"
            f"Searched paths:\n"
            f"  - {assets_path}\n"
            f"  - {direct_path}"
        )

    @staticmethod
    def load_icon(file_name: str, size: tuple = (20, 20)):
        """Loads an icon, resizes it, and caches it."""
        cache_key = (file_name, size)
        if cache_key in AssetManager._icon_cache:
            return AssetManager._icon_cache[cache_key]

        try:
            print(f"[AssetManager] Loading icon: {file_name}")
            path = AssetManager.get_asset_path(file_name)
            print(f"[AssetManager] Icon loaded successfully from: {path}")
            img = Image.open(path).resize(size, Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            AssetManager._icon_cache[cache_key] = photo
            return photo
        except Exception as e:
            print(f"[AssetManager] FAILED to load icon '{file_name}': {e}")
            logging.error(f"Failed to load icon '{file_name}': {e}")
            import traceback
            traceback.print_exc()
            # Return a blank image as a fallback
            blank_img = Image.new("RGBA", size, (0, 0, 0, 0))
            return ImageTk.PhotoImage(blank_img)
