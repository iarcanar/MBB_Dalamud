"""
ControlPanel (PyQt6) - Status indicator, info rows, small stop/start button
Compact layout inspired by Claude Usage Widget info rows
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
)
from PyQt6.QtGui import QFont, QIcon, QPixmap
from PyQt6.QtCore import Qt, QTimer, QSize

from pyqt_ui.styles import (
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_DIM, SUCCESS_GREEN, STATUS_IDLE,
    FONT_PRIMARY, FONT_MONO,
)


class ControlPanel(QWidget):
    """Compact control panel: status dot + info rows + small stop button"""

    def __init__(self, callbacks: dict, appearance_manager):
        super().__init__()
        self.setObjectName("control_panel")
        self.callbacks = callbacks
        self.appearance = appearance_manager

        # Widget references
        self.btn_start_stop = None
        self.lbl_status_dot = None
        self.lbl_status = None
        self.lbl_npc_context = None
        self.lbl_info = None

        # Legacy compatibility
        self.lbl_swap = None
        self.btn_swap = None
        self.lbl_status_info = None

        self._is_translating = False
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 4)
        layout.setSpacing(6)

        # ── Row 1: Status indicator + small stop/start button ──
        status_row = QHBoxLayout()
        status_row.setSpacing(6)

        self.lbl_status_dot = QLabel("\u25cf")  # ●
        self.lbl_status_dot.setObjectName("status_dot")
        self.lbl_status_dot.setFont(QFont(FONT_PRIMARY, 12))
        self.lbl_status_dot.setFixedWidth(18)
        self.lbl_status_dot.setProperty("active", "false")
        status_row.addWidget(self.lbl_status_dot)

        self.lbl_status = QLabel("Ready")
        self.lbl_status.setObjectName("status")
        self.lbl_status.setFont(QFont(FONT_PRIMARY, 10))
        status_row.addWidget(self.lbl_status)

        status_row.addStretch()

        self.btn_start_stop = QPushButton("Start")
        self.btn_start_stop.setObjectName("btn_primary")
        self.btn_start_stop.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_start_stop.setFixedHeight(28)
        self.btn_start_stop.setProperty("active", "false")
        self.btn_start_stop.clicked.connect(
            self.callbacks.get("toggle_translation", lambda: None)
        )
        status_row.addWidget(self.btn_start_stop)

        layout.addLayout(status_row)

        layout.addSpacing(8)

        # ── Row 2: Game info + Zone Change button ──
        game_row = QHBoxLayout()
        game_row.setContentsMargins(0, 2, 0, 2)

        game_key = QLabel("Game")
        game_key.setObjectName("info_key")
        game_key.setFont(QFont(FONT_PRIMARY, 11))
        game_row.addWidget(game_key)

        self.lbl_npc_context = QLabel("---")
        self.lbl_npc_context.setObjectName("info_value")
        self.lbl_npc_context.setFont(QFont(FONT_PRIMARY, 11))
        game_row.addWidget(self.lbl_npc_context)

        game_row.addStretch()

        self.btn_zone_change = QPushButton("Zone Change")
        self.btn_zone_change.setObjectName("zone_btn")
        self.btn_zone_change.setToolTip("Manual Zone Change — ตัด context บทสนทนา")
        self.btn_zone_change.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_zone_change.setFixedHeight(18)
        self.btn_zone_change.setFont(QFont(FONT_MONO, 6))
        self.btn_zone_change.clicked.connect(
            self.callbacks.get("manual_zone_change", lambda: None)
        )
        game_row.addWidget(self.btn_zone_change)

        layout.addLayout(game_row)

        layout.addSpacing(2)

        # ── Status info (Model + Dalamud status) ──
        self.lbl_status_info = QLabel("")
        self.lbl_status_info.setObjectName("status_info")
        self.lbl_status_info.setFont(QFont(FONT_MONO, 8))
        self.lbl_status_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status_info.setWordWrap(True)
        layout.addWidget(self.lbl_status_info)

    def _make_info_row(self, label_text: str, value_text: str,
                       font_size: int = 10) -> dict:
        """Create a key-value info row like Claude widget's _info_row"""
        row = QHBoxLayout()
        row.setContentsMargins(0, 2, 0, 2)

        key = QLabel(label_text)
        key.setObjectName("info_key")
        key.setFont(QFont(FONT_PRIMARY, font_size))
        row.addWidget(key)

        row.addStretch()

        value = QLabel(value_text)
        value.setObjectName("info_value")
        value.setFont(QFont(FONT_PRIMARY, font_size))
        value.setAlignment(Qt.AlignmentFlag.AlignRight)
        row.addWidget(value)

        return {"layout": row, "value": value}

    # ── Public API (preserved for backward compatibility) ──

    def set_translating(self, is_translating: bool):
        self._is_translating = is_translating
        if self.btn_start_stop:
            self.btn_start_stop.setText("Stop" if is_translating else "Start")
            self.btn_start_stop.setProperty("active", "true" if is_translating else "false")
            self.btn_start_stop.style().unpolish(self.btn_start_stop)
            self.btn_start_stop.style().polish(self.btn_start_stop)
        if self.lbl_status_dot:
            self.lbl_status_dot.setProperty("active", "true" if is_translating else "false")
            self.lbl_status_dot.style().unpolish(self.lbl_status_dot)
            self.lbl_status_dot.style().polish(self.lbl_status_dot)
        if self.lbl_status:
            self.lbl_status.setText("ระบบ: ออนไลน์" if is_translating else "Ready")
            self.lbl_status.setProperty("active", "true" if is_translating else "false")
            self.lbl_status.style().unpolish(self.lbl_status)
            self.lbl_status.style().polish(self.lbl_status)

    def set_status(self, status: str):
        if self.lbl_status:
            self.lbl_status.setText(status)

    def set_swap_text(self, text: str):
        """Legacy API - updates the Game info value"""
        if self.lbl_npc_context:
            # Strip "ใช้: " prefix if present, show just the game name
            display = text.replace("ใช้: ", "") if text.startswith("ใช้: ") else text
            self.lbl_npc_context.setText(display)

    def set_status_info(self, text: str):
        if self.lbl_status_info:
            self.lbl_status_info.setText(text)

    def set_info(self, text: str):
        """No-op — Model info moved to control panel status_info"""
        pass

    def flash_zone_change(self):
        """Show brief zone change confirmation on status_info"""
        if self.lbl_status_info:
            self._saved_status_info = self.lbl_status_info.text()
            self.lbl_status_info.setText("⚡ Zone changed — context reset")
            QTimer.singleShot(2500, self._restore_status_info)

    def _restore_status_info(self):
        if self.lbl_status_info and hasattr(self, '_saved_status_info'):
            self.lbl_status_info.setText(self._saved_status_info)

    def update_theme(self, qss: str = ""):
        pass
