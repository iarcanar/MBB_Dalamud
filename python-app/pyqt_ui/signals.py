"""Thread-safe signal definitions for PyQt6 UI updates"""
from PyQt6.QtCore import QObject, pyqtSignal


class MBBSignals(QObject):
    """Signals for thread-safe communication between background threads and UI"""
    status_update = pyqtSignal(str)           # Status label text
    translation_state = pyqtSignal(bool)      # START/STOP state change
    theme_changed = pyqtSignal()              # Theme was updated
    swap_text_update = pyqtSignal(str)        # NPC database label
    info_update = pyqtSignal(str)             # Bottom info label
    button_state_update = pyqtSignal(str, bool)  # (button_key, is_active)
