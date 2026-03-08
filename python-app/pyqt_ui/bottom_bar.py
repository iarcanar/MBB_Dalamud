"""
BottomBar (PyQt6) - TUI/LOG/MINI toggles, NPC Manager, Theme, Settings, info
Compact monochrome layout — theme button moved here from header
"""
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
)
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtCore import Qt, QSize

from pyqt_ui.styles import (
    TEXT_SECONDARY, FONT_PRIMARY,
)


class BottomBar(QWidget):
    """Bottom toolbar: toggle buttons + utility buttons + info"""

    def __init__(self, callbacks: dict, appearance_manager,
                 button_state_manager, asset_path_func):
        """
        Args:
            callbacks: Dict with keys:
                'toggle_tui', 'toggle_log', 'toggle_mini',
                'toggle_npc_manager', 'toggle_theme', 'toggle_settings'
            appearance_manager: AppearanceManager for theme colors
            button_state_manager: ButtonStateManager for state tracking
            asset_path_func: Function to resolve asset paths
        """
        super().__init__()
        self.setObjectName("bottom_bar")
        self.callbacks = callbacks
        self.appearance = appearance_manager
        self.state_manager = button_state_manager
        self._asset_path = asset_path_func

        # Widget references
        self.btn_tui = None
        self.btn_log = None
        self.btn_mini = None
        self.btn_npc_manager = None
        self.btn_theme = None
        self.btn_settings = None

        self.setFixedHeight(100)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 16)
        layout.setSpacing(8)

        # ── Toggle buttons row ──
        toggle_row = QHBoxLayout()
        toggle_row.setSpacing(6)

        self.btn_tui = self._make_toggle_button("TUI")
        self.btn_tui.setToolTip("Translation display")
        self.btn_tui.clicked.connect(self._on_tui_click)
        toggle_row.addWidget(self.btn_tui)

        self.btn_log = self._make_toggle_button("LOG")
        self.btn_log.setToolTip("Translation history")
        self.btn_log.clicked.connect(self._on_log_click)
        toggle_row.addWidget(self.btn_log)

        self.btn_mini = self._make_toggle_button("MINI")
        self.btn_mini.setToolTip("Mini mode")
        self.btn_mini.clicked.connect(
            self.callbacks.get("toggle_mini", lambda: None)
        )
        toggle_row.addWidget(self.btn_mini)

        layout.addLayout(toggle_row)

        # ── Utility row: NPC Manager + Theme + Settings ──
        util_row = QHBoxLayout()
        util_row.setSpacing(6)

        self.btn_npc_manager = QPushButton("NPC Manager")
        self.btn_npc_manager.setObjectName("utility_btn")
        self.btn_npc_manager.setProperty("toggled", "false")
        self.btn_npc_manager.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_npc_manager.setToolTip("NPC Manager")
        self.btn_npc_manager.clicked.connect(
            self.callbacks.get("toggle_npc_manager", lambda: None)
        )
        util_row.addWidget(self.btn_npc_manager, stretch=1)

        # Theme button (moved from header)
        self.btn_theme = QPushButton()
        self.btn_theme.setObjectName("icon_btn")
        self.btn_theme.setFixedSize(30, 30)
        self.btn_theme.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_theme.setToolTip("Theme")
        theme_path = self._asset_path("assets/theme.png")
        if os.path.exists(theme_path):
            self.btn_theme.setIcon(QIcon(theme_path))
            self.btn_theme.setIconSize(QSize(18, 18))
        else:
            self.btn_theme.setText("\U0001f3a8")
        self.btn_theme.clicked.connect(
            self.callbacks.get("toggle_theme", lambda: None)
        )
        util_row.addWidget(self.btn_theme)

        # Settings button
        self.btn_settings = QPushButton()
        self.btn_settings.setObjectName("icon_btn")
        self.btn_settings.setFixedSize(30, 30)
        self.btn_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_settings.setToolTip("Settings")
        setting_path = self._asset_path("assets/setting.png")
        if os.path.exists(setting_path):
            self.btn_settings.setIcon(QIcon(setting_path))
            self.btn_settings.setIconSize(QSize(18, 18))
        else:
            self.btn_settings.setText("\u2699")
        self.btn_settings.clicked.connect(
            self.callbacks.get("toggle_settings", lambda: None)
        )
        util_row.addWidget(self.btn_settings)

        layout.addLayout(util_row)

    def _make_toggle_button(self, text: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setObjectName("toggle_btn")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setProperty("toggled", "false")
        btn.setMinimumHeight(32)
        return btn

    def _on_tui_click(self):
        callback = self.callbacks.get("toggle_tui")
        if callback:
            callback()

    def _on_log_click(self):
        callback = self.callbacks.get("toggle_log")
        if callback:
            callback()

    # ── Public API ──

    def set_info(self, text: str):
        """No-op — info moved to control_panel.set_status_info()"""
        pass

    def set_toggle_state(self, key: str, active: bool):
        btn_map = {
            "tui": self.btn_tui,
            "log": self.btn_log,
            "mini": self.btn_mini,
            "npc_manager": self.btn_npc_manager,
        }
        btn = btn_map.get(key)
        if btn:
            btn.setProperty("toggled", "true" if active else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def update_theme(self, qss: str = ""):
        pass
