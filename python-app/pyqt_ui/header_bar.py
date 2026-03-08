"""
HeaderBar (PyQt6) - Version, glass/pin/close buttons
Clean monochrome design — logo is overlay in main_window
"""
import os
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtGui import QPixmap, QIcon, QFont
from PyQt6.QtCore import Qt, QSize

from pyqt_ui.styles import (
    BG_MEDIUM, TEXT_PRIMARY, TEXT_SECONDARY,
    ERROR_RED, FONT_PRIMARY, FONT_MONO,
)

# Logo overflow size (used by main_window for overlay positioning)
LOGO_SIZE = 72


class HeaderBar(QWidget):
    """Header bar: version + glass/pin/close buttons (logo is separate overlay)"""

    def __init__(self, callbacks: dict, appearance_manager, asset_path_func):
        """
        Args:
            callbacks: Dict with keys: 'toggle_topmost', 'toggle_glass', 'exit_program'
            appearance_manager: AppearanceManager for theme colors
            asset_path_func: Function to resolve asset paths (resource_path)
        """
        super().__init__()
        self.callbacks = callbacks
        self.appearance = appearance_manager
        self._asset_path = asset_path_func
        self._is_pinned = False
        self._is_glass = False

        self.setObjectName("header")
        self.setFixedHeight(44)

        # Widget references
        self.lbl_version = None
        self.btn_glass = None
        self.btn_pin = None
        self.btn_close = None

        self._build()

    def _build(self):
        layout = QHBoxLayout(self)
        # Left margin accounts for the overlay logo (LOGO_SIZE + gap)
        layout.setContentsMargins(LOGO_SIZE + 6, 0, 4, 0)
        layout.setSpacing(6)

        # Version label (no "MBB" text — the logo icon already shows it)
        self.lbl_version = QLabel("")
        self.lbl_version.setObjectName("version")
        self.lbl_version.setFont(QFont(FONT_PRIMARY, 7))
        layout.addWidget(self.lbl_version)

        layout.addStretch()

        # Glass mode button
        self.btn_glass = self._make_header_button()
        self.btn_glass.setText("\u25cf")  # ● filled circle
        self.btn_glass.setToolTip("Glass mode")
        self.btn_glass.clicked.connect(self._on_glass_click)
        layout.addWidget(self.btn_glass)

        # Pin button
        self.btn_pin = self._make_header_button()
        self._update_pin_icon()
        self.btn_pin.setToolTip("Pin")
        self.btn_pin.clicked.connect(
            self.callbacks.get("toggle_topmost", lambda: None)
        )
        layout.addWidget(self.btn_pin)

        # Close button
        self.btn_close = QPushButton("\u2715")
        self.btn_close.setObjectName("btn_close")
        self.btn_close.setFixedSize(30, 30)
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.setToolTip("Close")
        self.btn_close.clicked.connect(
            self.callbacks.get("exit_program", lambda: None)
        )
        layout.addWidget(self.btn_close)

    def _make_header_button(self) -> QPushButton:
        btn = QPushButton()
        btn.setObjectName("header_btn")
        btn.setFixedSize(30, 30)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        return btn

    def _update_pin_icon(self):
        icon_name = "assets/pin.png" if self._is_pinned else "assets/unpin.png"
        icon_path = self._asset_path(icon_name)
        if os.path.exists(icon_path):
            self.btn_pin.setIcon(QIcon(icon_path))
            self.btn_pin.setIconSize(QSize(18, 18))
            self.btn_pin.setText("")
        else:
            self.btn_pin.setText("\U0001f4cc" if self._is_pinned else "\U0001f4cd")

    def _on_glass_click(self):
        callback = self.callbacks.get("toggle_glass")
        if callback:
            callback()

    # ── Public API ──

    def set_version(self, version: str):
        if self.lbl_version:
            self.lbl_version.setText(f"v{version}")

    def update_pin_state(self, is_pinned: bool):
        self._is_pinned = is_pinned
        self._update_pin_icon()
        tip = "Pinned (click to unpin)" if is_pinned else "Pin"
        if self.btn_pin:
            self.btn_pin.setToolTip(tip)

    def update_glass_state(self, is_glass: bool):
        self._is_glass = is_glass
        if self.btn_glass:
            self.btn_glass.setText("\u25cb" if is_glass else "\u25cf")
            tip = "Glass mode ON" if is_glass else "Glass mode"
            self.btn_glass.setToolTip(tip)

    def update_theme(self, qss: str = ""):
        pass
