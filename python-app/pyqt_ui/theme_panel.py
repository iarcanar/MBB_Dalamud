"""
ThemePanel (PyQt6) — Frameless theme manager matching MBB main window style
"""
import os
import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QGraphicsDropShadowEffect, QColorDialog, QGridLayout,
)
from PyQt6.QtGui import QColor, QFont, QIcon
from PyQt6.QtCore import Qt, QPoint, QTimer

from pyqt_ui.styles import (
    FONT_PRIMARY, FONT_MONO, derive_palette, _luminance,
)

log = logging.getLogger("mbb-qt")

WIDTH = 280
HEIGHT = 420


class ThemePanel(QWidget):
    """Frameless theme manager window — matches MBB main window design."""

    def __init__(self, appearance_manager, settings, on_theme_applied=None):
        super().__init__()
        self.am = appearance_manager
        self.settings = settings
        self._on_theme_applied = on_theme_applied
        self.old_pos = QPoint()

        # Current editing state
        self._selected_theme_id = None
        self._primary_color = "#1a1a1a"
        self._secondary_color = "#888888"

        # Widget refs
        self.bg = None
        self.shadow = None
        self._preset_buttons = {}
        self._primary_swatch = None
        self._secondary_swatch = None
        self._name_input = None
        self._status_label = None

        self._init_window()
        self._build_ui()
        self._load_current()

    def _init_window(self):
        self.setWindowTitle("Theme Manager")
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
        self.bg.setObjectName("theme_bg")
        outer.addWidget(self.bg)

        self.shadow = QGraphicsDropShadowEffect()
        self.shadow.setBlurRadius(20)
        self.shadow.setColor(QColor(0, 0, 0, 140))
        self.shadow.setOffset(0, 3)
        self.bg.setGraphicsEffect(self.shadow)

        main = QVBoxLayout(self.bg)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        # ── Header ──
        header = QWidget()
        header.setObjectName("theme_header")
        header.setFixedHeight(36)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(14, 0, 6, 0)
        h_layout.setSpacing(4)

        title = QLabel("Theme Manager")
        title.setObjectName("theme_title")
        title.setFont(QFont(FONT_PRIMARY, 10, QFont.Weight.Bold))
        h_layout.addWidget(title)
        h_layout.addStretch()

        btn_close = QPushButton("\u2715")
        btn_close.setObjectName("theme_close")
        btn_close.setFixedSize(26, 26)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.clicked.connect(self.close)
        h_layout.addWidget(btn_close)

        main.addWidget(header)

        # ── Content area ──
        content = QWidget()
        content.setObjectName("theme_content")
        c_layout = QVBoxLayout(content)
        c_layout.setContentsMargins(14, 12, 14, 14)
        c_layout.setSpacing(10)

        # Section: Preset themes
        sec_preset = QLabel("เลือกธีม")
        sec_preset.setObjectName("theme_section")
        sec_preset.setFont(QFont(FONT_PRIMARY, 9, QFont.Weight.Bold))
        c_layout.addWidget(sec_preset)

        grid = QGridLayout()
        grid.setSpacing(6)
        self._build_presets(grid)
        c_layout.addLayout(grid)

        # Section: Customize
        sec_custom = QLabel("ปรับแต่ง")
        sec_custom.setObjectName("theme_section")
        sec_custom.setFont(QFont(FONT_PRIMARY, 9, QFont.Weight.Bold))
        c_layout.addWidget(sec_custom)

        # Primary color row
        row_p = QHBoxLayout()
        row_p.setSpacing(8)
        lbl_p = QLabel("พื้นหลัง")
        lbl_p.setObjectName("theme_label")
        lbl_p.setFont(QFont(FONT_PRIMARY, 9))
        row_p.addWidget(lbl_p)
        row_p.addStretch()
        self._primary_swatch = QPushButton()
        self._primary_swatch.setObjectName("color_swatch")
        self._primary_swatch.setFixedSize(50, 24)
        self._primary_swatch.setCursor(Qt.CursorShape.PointingHandCursor)
        self._primary_swatch.setToolTip("เลือกสีพื้นหลัง")
        self._primary_swatch.clicked.connect(self._pick_primary)
        row_p.addWidget(self._primary_swatch)
        c_layout.addLayout(row_p)

        # Secondary color row
        row_s = QHBoxLayout()
        row_s.setSpacing(8)
        lbl_s = QLabel("ไฮไลท์")
        lbl_s.setObjectName("theme_label")
        lbl_s.setFont(QFont(FONT_PRIMARY, 9))
        row_s.addWidget(lbl_s)
        row_s.addStretch()
        self._secondary_swatch = QPushButton()
        self._secondary_swatch.setObjectName("color_swatch")
        self._secondary_swatch.setFixedSize(50, 24)
        self._secondary_swatch.setCursor(Qt.CursorShape.PointingHandCursor)
        self._secondary_swatch.setToolTip("เลือกสีไฮไลท์")
        self._secondary_swatch.clicked.connect(self._pick_secondary)
        row_s.addWidget(self._secondary_swatch)
        c_layout.addLayout(row_s)

        # Theme name row
        row_n = QHBoxLayout()
        row_n.setSpacing(8)
        lbl_n = QLabel("ชื่อธีม")
        lbl_n.setObjectName("theme_label")
        lbl_n.setFont(QFont(FONT_PRIMARY, 9))
        row_n.addWidget(lbl_n)
        self._name_input = QLineEdit()
        self._name_input.setObjectName("theme_input")
        self._name_input.setFont(QFont(FONT_PRIMARY, 9))
        self._name_input.setPlaceholderText("ชื่อธีม...")
        self._name_input.returnPressed.connect(self._apply)
        row_n.addWidget(self._name_input)
        c_layout.addLayout(row_n)

        # Apply button
        btn_apply = QPushButton("APPLY")
        btn_apply.setObjectName("theme_apply")
        btn_apply.setFont(QFont(FONT_PRIMARY, 10, QFont.Weight.Bold))
        btn_apply.setFixedHeight(34)
        btn_apply.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_apply.clicked.connect(self._apply)
        c_layout.addWidget(btn_apply)

        # Status label
        self._status_label = QLabel("")
        self._status_label.setObjectName("theme_status")
        self._status_label.setFont(QFont(FONT_PRIMARY, 8))
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        c_layout.addWidget(self._status_label)

        c_layout.addStretch()
        main.addWidget(content, stretch=1)

        self._apply_panel_theme()

    def _build_presets(self, grid: QGridLayout):
        """Build preset theme buttons from loaded themes."""
        themes = self.am.themes
        col = 0
        row = 0
        for theme_id in sorted(themes.keys()):
            data = themes[theme_id]
            name = data.get("name", theme_id)
            accent = data.get("accent", "#333333")
            secondary = data.get("secondary", "#888888")

            btn = QPushButton()
            btn.setObjectName("preset_btn")
            btn.setFixedSize(48, 36)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(name)
            # Two-tone: top half accent, bottom half secondary via gradient
            text_c = "#1a1a1a" if _luminance(accent) > 0.35 else "#ffffff"
            btn.setStyleSheet(
                f"QPushButton#preset_btn {{"
                f"  background: qlineargradient(x1:0,y1:0,x2:0,y2:1,"
                f"    stop:0 {accent}, stop:0.55 {accent},"
                f"    stop:0.55 {secondary}, stop:1 {secondary});"
                f"  border: 2px solid transparent;"
                f"  border-radius: 6px;"
                f"  color: {text_c}; font-size: 7pt;"
                f"}}"
                f"QPushButton#preset_btn:hover {{"
                f"  border: 2px solid #ffffff;"
                f"}}"
            )
            btn.clicked.connect(lambda checked, tid=theme_id: self._select_preset(tid))
            grid.addWidget(btn, row, col)
            self._preset_buttons[theme_id] = btn
            col += 1
            if col >= 5:
                col = 0
                row += 1

    def _select_preset(self, theme_id: str):
        """Select a preset theme and populate editors."""
        data = self.am.themes.get(theme_id)
        if not data:
            return
        self._selected_theme_id = theme_id
        self._primary_color = data.get("accent", "#1a1a1a")
        self._secondary_color = data.get("secondary", "#888888")
        self._name_input.setText(data.get("name", ""))
        self._update_swatches()
        self._highlight_selected()

    def _load_current(self):
        """Load current theme into editors."""
        tid = self.am.current_theme
        if tid and tid in self.am.themes:
            self._select_preset(tid)

    def _highlight_selected(self):
        """Update preset button borders to show selection."""
        for tid, btn in self._preset_buttons.items():
            data = self.am.themes.get(tid, {})
            accent = data.get("accent", "#333333")
            secondary = data.get("secondary", "#888888")
            text_c = "#1a1a1a" if _luminance(accent) > 0.35 else "#ffffff"
            selected = (tid == self._selected_theme_id)
            border = "#ffffff" if selected else "transparent"
            btn.setStyleSheet(
                f"QPushButton#preset_btn {{"
                f"  background: qlineargradient(x1:0,y1:0,x2:0,y2:1,"
                f"    stop:0 {accent}, stop:0.55 {accent},"
                f"    stop:0.55 {secondary}, stop:1 {secondary});"
                f"  border: 2px solid {border};"
                f"  border-radius: 6px;"
                f"  color: {text_c}; font-size: 7pt;"
                f"}}"
                f"QPushButton#preset_btn:hover {{"
                f"  border: 2px solid #ffffff;"
                f"}}"
            )

    def _update_swatches(self):
        """Update color swatch button backgrounds."""
        if self._primary_swatch:
            self._primary_swatch.setStyleSheet(
                f"QPushButton#color_swatch {{"
                f"  background: {self._primary_color};"
                f"  border: 1px solid #555555; border-radius: 4px;"
                f"}}"
                f"QPushButton#color_swatch:hover {{ border: 1px solid #ffffff; }}"
            )
        if self._secondary_swatch:
            self._secondary_swatch.setStyleSheet(
                f"QPushButton#color_swatch {{"
                f"  background: {self._secondary_color};"
                f"  border: 1px solid #555555; border-radius: 4px;"
                f"}}"
                f"QPushButton#color_swatch:hover {{ border: 1px solid #ffffff; }}"
            )

    def _pick_primary(self):
        color = QColorDialog.getColor(
            QColor(self._primary_color), self, "เลือกสีพื้นหลัง"
        )
        if color.isValid():
            self._primary_color = color.name()
            self._update_swatches()

    def _pick_secondary(self):
        color = QColorDialog.getColor(
            QColor(self._secondary_color), self, "เลือกสีไฮไลท์"
        )
        if color.isValid():
            self._secondary_color = color.name()
            self._update_swatches()

    def _apply(self):
        """Apply theme changes."""
        tid = self._selected_theme_id
        if not tid:
            self._show_status("เลือกธีมก่อน", error=True)
            return

        name = self._name_input.text().strip()
        if not name:
            name = self.am.themes.get(tid, {}).get("name", "Theme")

        success = self.am._update_theme(
            tid, name, self._primary_color, self._secondary_color
        )

        if success:
            self._show_status(f"บันทึก '{name}' แล้ว")
            self._apply_panel_theme()
            self._rebuild_presets()
        else:
            self._show_status("เกิดข้อผิดพลาด", error=True)

    def _rebuild_presets(self):
        """Rebuild preset buttons after theme data changes."""
        # Remove old buttons
        for btn in self._preset_buttons.values():
            btn.setParent(None)
            btn.deleteLater()
        self._preset_buttons.clear()

        # Find the grid layout and rebuild
        content = self.bg.findChild(QWidget, "theme_content")
        if content:
            layout = content.layout()
            # Find and remove old grid
            for i in range(layout.count()):
                item = layout.itemAt(i)
                if item and isinstance(item.layout(), QGridLayout):
                    grid = item.layout()
                    self._build_presets(grid)
                    self._highlight_selected()
                    return

    def _show_status(self, text: str, error=False):
        if self._status_label:
            color = "#cc4444" if error else "#4CAF50"
            self._status_label.setStyleSheet(f"color: {color}; background: transparent;")
            self._status_label.setText(text)
            QTimer.singleShot(3000, lambda: self._status_label.setText(""))

    # ── Theming ──

    def _apply_panel_theme(self):
        """Apply current theme colors to this panel."""
        primary = self.am.get_accent_color()
        secondary = self.am.get_theme_color("secondary", "#888888")
        p = derive_palette(primary, secondary)

        qss = f"""
            QWidget#theme_bg {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {p['bg']}, stop:1 {p['bg_deeper']});
                border-radius: 10px;
                border: 1px solid {p['border_subtle']};
            }}
            QWidget#theme_header {{
                background: {p['bg_titlebar']};
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }}
            QLabel#theme_title {{
                color: {p['text']};
                background: transparent;
            }}
            QPushButton#theme_close {{
                background: transparent;
                border: none; border-radius: 4px;
                color: {p['text_dim']}; font-size: 12px; font-weight: bold;
            }}
            QPushButton#theme_close:hover {{
                background: #cc4444; color: #ffffff;
            }}
            QWidget#theme_content {{
                background: transparent;
            }}
            QLabel#theme_section {{
                color: {p['text_dim']};
                background: transparent;
            }}
            QLabel#theme_label {{
                color: {p['text']};
                background: transparent;
            }}
            QLineEdit#theme_input {{
                background: {p['bg_titlebar']};
                color: {p['text']};
                border: 1px solid {p['border_subtle']};
                border-radius: 4px;
                padding: 4px 8px;
                font-family: '{FONT_PRIMARY}';
            }}
            QLineEdit#theme_input:focus {{
                border: 1px solid {p['border_active']};
            }}
            QPushButton#theme_apply {{
                background: {p['accent']};
                color: {p['toggled_text']};
                border: none;
                border-radius: 6px;
            }}
            QPushButton#theme_apply:hover {{
                background: {p['accent_light']};
            }}
            QLabel#theme_status {{
                background: transparent;
            }}
        """
        self.setStyleSheet(qss)
        self._update_swatches()

    # ── Drag Support ──

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPosition().toPoint()
