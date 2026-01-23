"""
Resource Path Utilities for MBB Dalamud
Handles dynamic path resolution for both development and PyInstaller-packaged environments
"""

import os
import sys


def get_app_dir():
    """
    Get the application directory

    Returns the correct base directory for resources:
    - In development: Returns the script directory
    - In PyInstaller: Returns the executable directory

    Returns:
        str: Absolute path to application directory
    """
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller executable
        return os.path.dirname(sys.executable)
    else:
        # Running as Python script
        return os.path.dirname(os.path.abspath(__file__))


def resource_path(relative_path):
    """
    Get absolute path to resource file

    Works correctly in both development and PyInstaller environments.
    Handles both forward slashes and backslashes.

    Args:
        relative_path (str): Relative path from app directory (e.g., "fonts/Font.ttf")

    Returns:
        str: Absolute path to the resource

    Example:
        >>> resource_path("fonts/MyFont.ttf")
        'C:\MBB_Dalamud\python-app\fonts\MyFont.ttf'
    """
    # Normalize path separators
    relative_path = relative_path.replace('/', os.sep).replace('\\', os.sep)

    if getattr(sys, 'frozen', False):
        # PyInstaller: Check _MEIPASS first (for --onefile mode)
        if hasattr(sys, '_MEIPASS'):
            base_path = sys._MEIPASS
        else:
            # --onedir mode
            base_path = get_app_dir()
    else:
        # Development mode
        base_path = get_app_dir()

    return os.path.join(base_path, relative_path)


def resource_exists(relative_path):
    """
    Check if a resource file exists

    Args:
        relative_path (str): Relative path from app directory

    Returns:
        bool: True if resource exists, False otherwise
    """
    return os.path.exists(resource_path(relative_path))


def get_user_data_dir():
    """
    Get directory for user-specific data (settings, cache, etc.)

    Uses AppData on Windows, ~/.config on Linux/Mac

    Returns:
        str: Path to user data directory for MBB
    """
    if sys.platform == 'win32':
        # Windows: Use AppData\Local
        app_data = os.getenv('LOCALAPPDATA', os.path.expanduser('~'))
        user_dir = os.path.join(app_data, 'MBB_Dalamud')
    else:
        # Linux/Mac: Use ~/.config
        user_dir = os.path.join(os.path.expanduser('~'), '.config', 'mbb_dalamud')

    # Create directory if it doesn't exist
    os.makedirs(user_dir, exist_ok=True)

    return user_dir


def get_settings_path(filename='settings.json'):
    """
    Get path for settings file in user data directory

    Args:
        filename (str): Name of settings file

    Returns:
        str: Full path to settings file
    """
    return os.path.join(get_user_data_dir(), filename)


# Export main functions
__all__ = [
    'get_app_dir',
    'resource_path',
    'resource_exists',
    'get_user_data_dir',
    'get_settings_path'
]
