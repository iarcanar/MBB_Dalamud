"""
HotkeyPanel (PyQt6) — Frameless hotkey configuration matching MBB style
Replaces the old Tkinter SimplifiedHotkeyUI.
"""
import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGraphicsDropShadowEffect, QFrame, QLineEdit,
)
from PyQt6.QtGui import QColor, QFont, QKeyEvent
from PyQt6.QtCore import Qt, QPoint, QTimer

from pyqt_ui.styles import FONT_PRIMARY, FONT_MONO, derive_palette

log = logging.getLogger("mbb-qt")

WIDTH = 300
HEIGHT = 280

# ── Validation ──

VALID_KEYS = set("abcdefghijklmnopqrstuvwxyz0123456789")
VALID_FKEYS = {f"f{i}" for i in range(1, 13)}
VALID_MODIFIERS = {"ctrl", "alt", "shift"}


def is_valid_hotkey(hotkey: str) -> bool:
    parts = hotkey.lower().split("+")
    if len(parts) == 1:
        return parts[0] in VALID_KEYS or parts[0] in VALID_FKEYS
    if len(parts) > 1:
        modifiers = parts[:-1]
        key = parts[-1]
        return (all(m in VALID_MODIFIERS for m in modifiers)
                and (key in VALID_KEYS or key in VALID_FKEYS))
    return False


class HotkeyLineEdit(QLineEdit):
    """QLineEdit that captures key combos (Ctrl/Alt/Shift + key)."""

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        mods = event.modifiers()

        # Escape → revert
        if key == Qt.Key.Key_Escape:
            self.undo()
            self.clearFocus()
            return

        # Enter → confirm
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.clearFocus()
            return

        # Build combo string
        parts = []
        if mods & Qt.KeyboardModifier.ControlModifier:
            parts.append("ctrl")
        if mods & Qt.KeyboardModifier.AltModifier:
            parts.append("alt")
        if mods & Qt.KeyboardModifier.ShiftModifier:
            parts.append("shift")

        key_name = self._key_to_name(key)
        if key_name:
            parts.append(key_name)
            self.setText("+".join(parts))
        # Ignore modifier-only presses

    def _key_to_name(self, key):
        # F-keys
        if Qt.Key.Key_F1 <= key <= Qt.Key.Key_F12:
            return f"f{key - Qt.Key.Key_F1 + 1}"
        # Letters
        if Qt.Key.Key_A <= key <= Qt.Key.Key_Z:
            return chr(key).lower()
        # Numbers
        if Qt.Key.Key_0 <= key <= Qt.Key.Key_9:
            return chr(key)
        return None


class HotkeyPanel(QWidget):
    """Frameless hotkey settings panel."""

    def __init__(self, settings, update_callback, appearance_manager):
        super().__init__()
        self.settings = settings
        self.callback = update_callback
        self.am = appearance_manager
        self.old_pos = QPoint()

        self.bg = None
        self.shadow = None
        self._entries = {}
        self._status_label = None

        self._init_window()
        self._build_ui()
        self._apply_theme()
        self._load_current()

    def _init_window(self):
        self.setWindowTitle("Hotkey Settings")
        self.setFixedSize(WIDTH, HEIGHT)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)

        self.bg = QWidget()
        self.bg.setObjectName("hk_bg")
        outer.addWidget(self.bg)

        self.shadow = QGraphicsDropShadowEffect()
        self.shadow.setBlurRadius(20)
        self.shadow.setColor(QColor(0, 0, 0, 140))
        self.shadow.setOffset(0, 3)
        self.bg.setGraphicsEffect(self.shadow)

        main = QVBoxLayout(self.bg)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        # Header
        header = QWidget()
        header.setObjectName("hk_header")
        header.setFixedHeight(36)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(14, 0, 6, 0)

        title = QLabel("Hotkey Settings")
        title.setObjectName("hk_title")
        title.setFont(QFont(FONT_PRIMARY, 10, QFont.Weight.Bold))
        h_layout.addWidget(title)
        h_layout.addStretch()

        btn_close = QPushButton("\u2715")
        btn_close.setObjectName("hk_close")
        btn_close.setFixedSize(26, 26)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.clicked.connect(self.close)
        h_layout.addWidget(btn_close)

        main.addWidget(header)

        # Content
        content = QWidget()
        content.setObjectName("hk_content")
        c_layout = QVBoxLayout(content)
        c_layout.setContentsMargins(14, 12, 14, 14)
        c_layout.setSpacing(8)

        hotkeys = [
            ("toggle_ui", "Toggle UI:", "alt+l"),
            ("start_stop_translate", "Start/Stop:", "f9"),
            ("previous_dialog", "Previous:", "r-click"),
            ("previous_dialog_key", "Prev Key:", "f10"),
        ]

        for key, label, default in hotkeys:
            row = QHBoxLayout()
            row.setSpacing(8)
            lbl = QLabel(label)
            lbl.setObjectName("hk_label")
            lbl.setFont(QFont(FONT_PRIMARY, 9))
            lbl.setMinimumWidth(80)
            row.addWidget(lbl)

            entry = HotkeyLineEdit()
            entry.setObjectName("hk_entry")
            entry.setFont(QFont(FONT_MONO, 11))
            entry.setAlignment(Qt.AlignmentFlag.AlignCenter)
            entry.setMaximumWidth(140)
            row.addWidget(entry, stretch=1)

            c_layout.addLayout(row)
            self._entries[key] = entry

        c_layout.addStretch()

        # Buttons row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        btn_default = QPushButton("DEFAULT")
        btn_default.setObjectName("hk_btn")
        btn_default.setFont(QFont(FONT_PRIMARY, 9, QFont.Weight.Bold))
        btn_default.setFixedHeight(30)
        btn_default.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_default.clicked.connect(self._reset_defaults)
        btn_row.addWidget(btn_default)

        btn_save = QPushButton("SAVE")
        btn_save.setObjectName("hk_btn_save")
        btn_save.setFont(QFont(FONT_PRIMARY, 9, QFont.Weight.Bold))
        btn_save.setFixedHeight(30)
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.clicked.connect(self._save)
        btn_row.addWidget(btn_save)

        c_layout.addLayout(btn_row)

        # Status
        self._status_label = QLabel("")
        self._status_label.setObjectName("hk_status")
        self._status_label.setFont(QFont(FONT_PRIMARY, 8))
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        c_layout.addWidget(self._status_label)

        main.addWidget(content, stretch=1)

    # ── Data ──

    def _load_current(self):
        defaults = {
            "toggle_ui": "alt+l",
            "start_stop_translate": "f9",
            "previous_dialog": "r-click",
            "previous_dialog_key": "f10",
        }
        for key, entry in self._entries.items():
            val = self.settings.get_shortcut(key, defaults.get(key, ""))
            entry.setText(val)

    def _save(self):
        all_valid = True
        for key, entry in self._entries.items():
            val = entry.text().strip().lower()
            if key == "previous_dialog" and val == "r-click":
                continue
            if not is_valid_hotkey(val):
                all_valid = False
                break

        if not all_valid:
            self._show_status("Invalid hotkey detected", error=True)
            return

        for key, entry in self._entries.items():
            val = entry.text().strip().lower()
            self.settings.set_shortcut(key, val)

        if self.callback:
            self.callback()

        self._show_status("Saved!")

    def _reset_defaults(self):
        defaults = {
            "toggle_ui": "alt+l",
            "start_stop_translate": "f9",
            "previous_dialog": "r-click",
            "previous_dialog_key": "f10",
        }
        for key, entry in self._entries.items():
            entry.setText(defaults[key])
        self._show_status("Reset to defaults")

    def _show_status(self, text, error=False):
        if self._status_label:
            color = "#cc4444" if error else "#4CAF50"
            self._status_label.setStyleSheet(
                f"color: {color}; background: transparent;"
            )
            self._status_label.setText(text)
            QTimer.singleShot(2500, lambda: self._status_label.setText(""))

    # ── Theming ──

    def _apply_theme(self):
        primary = self.am.get_accent_color()
        secondary = self.am.get_theme_color("secondary", "#888888")
        p = derive_palette(primary, secondary)

        qss = f"""
            QWidget#hk_bg {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {p['bg']}, stop:1 {p['bg_deeper']});
                border-radius: 10px;
                border: 1px solid {p['border_subtle']};
            }}
            QWidget#hk_header {{
                background: {p['bg_titlebar']};
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }}
            QLabel#hk_title {{
                color: {p['text']};
                background: transparent;
            }}
            QPushButton#hk_close {{
                background: transparent;
                border: none; border-radius: 4px;
                color: {p['text_dim']}; font-size: 12px; font-weight: bold;
            }}
            QPushButton#hk_close:hover {{
                background: #cc4444; color: #ffffff;
            }}
            QWidget#hk_content {{
                background: transparent;
            }}
            QLabel#hk_label {{
                color: {p['text']};
                background: transparent;
            }}
            QLineEdit#hk_entry {{
                background: {p['bg_titlebar']};
                color: {p['accent']};
                border: 1px solid {p['border_subtle']};
                border-radius: 4px;
                padding: 4px 8px;
            }}
            QLineEdit#hk_entry:focus {{
                border: 1px solid {p['accent']};
            }}
            QPushButton#hk_btn {{
                background: {p['btn_bg']};
                color: {p['text']};
                border: 1px solid {p['border_subtle']};
                border-radius: 4px;
            }}
            QPushButton#hk_btn:hover {{
                background: {p['bg_medium']};
                border: 1px solid {p['border_active']};
            }}
            QPushButton#hk_btn_save {{
                background: {p['accent']};
                color: {p['toggled_text']};
                border: none;
                border-radius: 4px;
            }}
            QPushButton#hk_btn_save:hover {{
                background: {p['accent_light']};
            }}
            QLabel#hk_status {{
                background: transparent;
            }}
        """
        self.setStyleSheet(qss)

    # ── Drag ──

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPosition().toPoint()
