"""
FontPanel (PyQt6) — Frameless font selection matching MBB style.
Uses QtFontManager for proper Qt font registration and discovery.
"""
import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGraphicsDropShadowEffect, QListWidget, QListWidgetItem,
    QAbstractItemView, QSizeGrip,
)
from PyQt6.QtGui import QColor, QFont, QFontDatabase
from PyQt6.QtCore import Qt, QPoint, QTimer

from pyqt_ui.styles import FONT_PRIMARY, FONT_MONO, derive_palette

log = logging.getLogger("mbb-qt")

WIDTH = 340
MIN_HEIGHT = 400
DEFAULT_HEIGHT = 520

PREVIEW_LINE1 = "ตัวอย่างข้อความภาษาไทย"
PREVIEW_LINE2 = "Sample English ABC 123"


class FontPanel(QWidget):
    """Frameless font selection panel with resize support."""

    def __init__(self, settings, qt_font_manager, appearance_manager, main_app=None):
        super().__init__()
        self.settings = settings
        self.qfm = qt_font_manager          # QtFontManager instance
        self.am = appearance_manager
        self.main_app = main_app
        self.old_pos = QPoint()
        self._dragging = False

        self.bg = None
        self.shadow = None
        self._grip = None
        self._font_list = None
        self._size_value = 24
        self._size_label = None
        self._preview_line1 = None
        self._preview_line2 = None
        self._preview_text_color = "#e0e0e0"
        self._status_label = None
        self._target_mode = "both"   # "tui" | "logs" | "both"
        self._target_btns: dict = {}  # label -> QPushButton

        self._init_window()
        self._build_ui()
        self._apply_theme()
        self._load_current()

    def _init_window(self):
        self.setWindowTitle("Font Settings")
        self.setMinimumSize(WIDTH, MIN_HEIGHT)
        self.resize(WIDTH, DEFAULT_HEIGHT)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)

        self.bg = QWidget()
        self.bg.setObjectName("font_bg")
        outer.addWidget(self.bg)

        self.shadow = QGraphicsDropShadowEffect()
        self.shadow.setBlurRadius(20)
        self.shadow.setColor(QColor(0, 0, 0, 140))
        self.shadow.setOffset(0, 3)
        self.bg.setGraphicsEffect(self.shadow)

        main = QVBoxLayout(self.bg)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        # ── Header (drag zone) ──
        header = QWidget()
        header.setObjectName("font_header")
        header.setFixedHeight(36)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(14, 0, 6, 0)

        title = QLabel("Font Settings")
        title.setObjectName("font_title")
        title.setFont(QFont(FONT_PRIMARY, 10, QFont.Weight.Bold))
        h_layout.addWidget(title)
        h_layout.addStretch()

        btn_close = QPushButton("\u2715")
        btn_close.setObjectName("font_close")
        btn_close.setFixedSize(26, 26)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.clicked.connect(self.close)
        h_layout.addWidget(btn_close)

        main.addWidget(header)

        # ── Content ──
        content = QWidget()
        content.setObjectName("font_content")
        c = QVBoxLayout(content)
        c.setContentsMargins(14, 10, 14, 14)
        c.setSpacing(8)

        # Font Family
        sec_family = QLabel("Font Family")
        sec_family.setObjectName("font_section")
        sec_family.setFont(QFont(FONT_PRIMARY, 9, QFont.Weight.Bold))
        c.addWidget(sec_family)

        self._font_list = QListWidget()
        self._font_list.setObjectName("font_list")
        self._font_list.setFont(QFont(FONT_PRIMARY, 10))
        self._font_list.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self._font_list.setMinimumHeight(120)
        self._font_list.currentItemChanged.connect(self._on_font_changed)
        self._font_list.itemClicked.connect(self._on_font_clicked)
        c.addWidget(self._font_list, stretch=1)

        # ── Size Control ──
        c.addSpacing(4)
        sec_size = QLabel("Size")
        sec_size.setObjectName("font_section")
        sec_size.setFont(QFont(FONT_PRIMARY, 9, QFont.Weight.Bold))
        c.addWidget(sec_size)

        size_row = QHBoxLayout()
        size_row.setSpacing(0)
        size_row.setContentsMargins(0, 0, 0, 0)

        btn_minus = QPushButton("\u2212")
        btn_minus.setObjectName("font_size_btn")
        btn_minus.setFixedSize(44, 40)
        btn_minus.setFont(QFont(FONT_PRIMARY, 16, QFont.Weight.Bold))
        btn_minus.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_minus.clicked.connect(self._dec_size)
        size_row.addWidget(btn_minus)

        self._size_label = QLabel(str(self._size_value))
        self._size_label.setObjectName("font_size_display")
        self._size_label.setFont(QFont(FONT_MONO, 18, QFont.Weight.Bold))
        self._size_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._size_label.setFixedHeight(40)
        size_row.addWidget(self._size_label, stretch=1)

        btn_plus = QPushButton("+")
        btn_plus.setObjectName("font_size_btn")
        btn_plus.setFixedSize(44, 40)
        btn_plus.setFont(QFont(FONT_PRIMARY, 16, QFont.Weight.Bold))
        btn_plus.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_plus.clicked.connect(self._inc_size)
        size_row.addWidget(btn_plus)

        c.addLayout(size_row)

        # ── Target ──
        c.addSpacing(4)
        sec_target = QLabel("Apply To")
        sec_target.setObjectName("font_section")
        sec_target.setFont(QFont(FONT_PRIMARY, 9, QFont.Weight.Bold))
        c.addWidget(sec_target)

        target_row = QHBoxLayout()
        target_row.setSpacing(6)
        target_row.setContentsMargins(0, 0, 0, 0)

        for key, label in [("tui", "TUI"), ("logs", "TUI Log"), ("both", "Both")]:
            btn = QPushButton(label)
            btn.setObjectName("font_target_btn")
            btn.setCheckable(True)
            btn.setFixedHeight(30)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, k=key: self._set_target(k))
            target_row.addWidget(btn)
            self._target_btns[key] = btn

        c.addLayout(target_row)

        # ── Preview ──
        c.addSpacing(4)
        sec_preview = QLabel("Preview")
        sec_preview.setObjectName("font_section")
        sec_preview.setFont(QFont(FONT_PRIMARY, 9, QFont.Weight.Bold))
        c.addWidget(sec_preview)

        preview_box = QWidget()
        preview_box.setObjectName("font_preview_box")
        pv = QVBoxLayout(preview_box)
        pv.setContentsMargins(12, 6, 12, 6)
        pv.setSpacing(0)

        self._preview_line1 = QLabel(PREVIEW_LINE1)
        self._preview_line1.setObjectName("font_preview_text")
        self._preview_line1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview_line1.setWordWrap(True)
        pv.addWidget(self._preview_line1)

        self._preview_line2 = QLabel(PREVIEW_LINE2)
        self._preview_line2.setObjectName("font_preview_text")
        self._preview_line2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview_line2.setWordWrap(True)
        pv.addWidget(self._preview_line2)

        preview_box.setMinimumHeight(90)
        c.addWidget(preview_box, stretch=1)

        # ── Footer ──
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self._status_label = QLabel("")
        self._status_label.setObjectName("font_status")
        self._status_label.setFont(QFont(FONT_PRIMARY, 8))
        btn_row.addWidget(self._status_label, stretch=1)

        btn_apply = QPushButton("APPLY")
        btn_apply.setObjectName("font_apply")
        btn_apply.setFont(QFont(FONT_PRIMARY, 9, QFont.Weight.Bold))
        btn_apply.setFixedHeight(32)
        btn_apply.setFixedWidth(80)
        btn_apply.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_apply.clicked.connect(self._on_apply)
        btn_row.addWidget(btn_apply)

        c.addLayout(btn_row)

        main.addWidget(content, stretch=1)

        # ── Resize Grip ──
        self._grip = QSizeGrip(self)
        self._grip.setObjectName("font_grip")
        self._grip.setFixedSize(16, 16)

    # ── Size Controls ──

    def _set_target(self, key: str):
        """Toggle target mode and load font/size for that target."""
        self._target_mode = key
        for k, btn in self._target_btns.items():
            btn.setChecked(k == key)
        self.settings.set("font_target_mode", key)

        # Load font settings for the selected target
        font_name, font_size = self._get_font_for_target(key)
        self._size_value = font_size
        self._size_label.setText(str(self._size_value))

        # Select the font in the list (block signals to avoid double preview update)
        self._font_list.blockSignals(True)
        items = self._font_list.findItems(font_name, Qt.MatchFlag.MatchExactly)
        if not items and self.qfm:
            resolved = self.qfm.resolve_family(font_name)
            items = self._font_list.findItems(resolved, Qt.MatchFlag.MatchExactly)
        if items:
            self._font_list.setCurrentItem(items[0])
            self._font_list.scrollToItem(items[0])
        self._font_list.blockSignals(False)

        self._update_preview()

    def reload_target(self):
        """Reload target mode from settings (called when panel is re-shown)."""
        saved_target = self.settings.get("font_target_mode", "both")
        self._set_target(saved_target if saved_target in self._target_btns else "both")

    def _get_font_for_target(self, key: str):
        """Return (font_name, font_size) for the given target key."""
        if key == "logs":
            logs_ui = self.settings.get("logs_ui") or {}
            return (
                logs_ui.get("font_family", "Anuphan"),
                int(logs_ui.get("font_size", 16)),
            )
        else:
            # "tui" or "both" — use TUI settings
            return (
                self.settings.get("font", "Anuphan"),
                int(self.settings.get("font_size", 24)),
            )

    def _dec_size(self):
        if self._size_value > 8:
            self._size_value -= 1
            self._size_label.setText(str(self._size_value))
            self._update_preview()

    def _inc_size(self):
        if self._size_value < 72:
            self._size_value += 1
            self._size_label.setText(str(self._size_value))
            self._update_preview()

    # ── Data ──

    def _load_current(self):
        """Populate font list from QtFontManager and select current font."""
        if self.qfm:
            fonts = self.qfm.get_available_fonts()
        else:
            fonts = sorted(QFontDatabase.families())

        self._font_list.clear()
        for name in fonts:
            self._font_list.addItem(QListWidgetItem(name))

        # โหลด target mode — _set_target จะ load font/size ให้อัตโนมัติ
        saved_target = self.settings.get("font_target_mode", "both")
        self._set_target(saved_target if saved_target in self._target_btns else "both")

    def _on_font_changed(self, current, previous):
        if current:
            self._update_preview_for(current.text())

    def _on_font_clicked(self, item):
        if item:
            self._update_preview_for(item.text())

    def _update_preview_for(self, font_name):
        """Update preview labels — must use setStyleSheet because the parent
        stylesheet overrides setFont() in Qt."""
        preview_size = min(self._size_value, 32)

        resolved = self.qfm.resolve_family(font_name) if self.qfm else font_name
        text_color = self._preview_text_color or "#e0e0e0"

        qss = (
            f"font-family: '{resolved}';"
            f"font-size: {preview_size}pt;"
            f"color: {text_color};"
            f"background: transparent;"
        )
        self._preview_line1.setStyleSheet(qss)
        self._preview_line2.setStyleSheet(qss)

    def _update_preview(self):
        """Update preview from current list selection (for size changes)."""
        item = self._font_list.currentItem()
        font_name = item.text() if item else FONT_PRIMARY
        self._update_preview_for(font_name)

    def _on_apply(self):
        item = self._font_list.currentItem()
        if not item:
            self._show_status("Select a font first", error=True)
            return

        font_name = item.text()
        font_size = self._size_value

        if not self.main_app or not hasattr(self.main_app, "apply_font_with_target"):
            self._show_status("No app connection", error=True)
            return

        self.main_app.apply_font_with_target({
            "font": font_name,
            "font_size": font_size,
            "target": self._target_mode,
        })

        target_label = {"tui": "TUI", "logs": "TUI Log", "both": "Both"}.get(self._target_mode, "")
        self._show_status(f"Applied: {font_name} {font_size}px → {target_label}")

    def _show_status(self, text, error=False):
        if self._status_label:
            color = "#cc4444" if error else "#4CAF50"
            self._status_label.setStyleSheet(
                f"color: {color}; background: transparent;"
            )
            self._status_label.setText(text)
            QTimer.singleShot(
                3000,
                lambda: self._status_label.setText("") if self._status_label else None,
            )

    # ── Theming ──

    def _apply_theme(self):
        primary = self.am.get_accent_color()
        secondary = self.am.get_theme_color("secondary", "#888888")
        p = derive_palette(primary, secondary)
        self._preview_text_color = p['text']

        qss = f"""
            QWidget#font_bg {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {p['bg']}, stop:1 {p['bg_deeper']});
                border-radius: 10px;
                border: 1px solid {p['border_subtle']};
            }}
            QWidget#font_header {{
                background: {p['bg_titlebar']};
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }}
            QLabel#font_title {{
                color: {p['text']};
                background: transparent;
            }}
            QPushButton#font_close {{
                background: transparent;
                border: none; border-radius: 4px;
                color: {p['text_dim']}; font-size: 12px; font-weight: bold;
            }}
            QPushButton#font_close:hover {{
                background: #cc4444; color: #ffffff;
            }}
            QWidget#font_content {{
                background: transparent;
            }}
            QLabel#font_section {{
                color: {p['text_dim']};
                background: transparent;
            }}
            QListWidget#font_list {{
                background: {p['bg_titlebar']};
                color: {p['text']};
                border: 1px solid {p['border_subtle']};
                border-radius: 6px;
                padding: 4px;
                outline: none;
            }}
            QListWidget#font_list::item {{
                padding: 4px 8px;
                border-radius: 4px;
            }}
            QListWidget#font_list::item:selected {{
                background: {p['accent']};
                color: {p['toggled_text']};
            }}
            QListWidget#font_list::item:hover {{
                background: {p['bg_medium']};
            }}
            QPushButton#font_size_btn {{
                background: {p['btn_bg']};
                color: {p['text']};
                border: 1px solid {p['border_subtle']};
                border-radius: 6px;
            }}
            QPushButton#font_size_btn:hover {{
                background: {p['bg_medium']};
                border: 1px solid {p['border_active']};
            }}
            QPushButton#font_size_btn:pressed {{
                background: {p['accent']};
                color: {p['toggled_text']};
            }}
            QLabel#font_size_display {{
                color: {p['accent']};
                background: {p['bg_titlebar']};
                border: 1px solid {p['border_subtle']};
                border-radius: 6px;
                margin: 0px 6px;
            }}
            QWidget#font_preview_box {{
                background: {p['bg_titlebar']};
                border: 1px solid {p['border_subtle']};
                border-radius: 6px;
            }}
            QPushButton#font_target_btn {{
                background: {p['btn_bg']};
                color: {p['text_dim']};
                border: 1px solid {p['border_subtle']};
                border-radius: 6px;
                font-size: 9pt;
            }}
            QPushButton#font_target_btn:hover {{
                background: {p['bg_medium']};
                color: {p['text']};
            }}
            QPushButton#font_target_btn:checked {{
                background: {p['accent']};
                color: {p['toggled_text']};
                border-color: {p['accent']};
            }}
            /* font_preview_text styled inline via _update_preview_for */
            QPushButton#font_apply {{
                background: {p['accent']};
                color: {p['toggled_text']};
                border: none;
                border-radius: 6px;
            }}
            QPushButton#font_apply:hover {{
                background: {p['accent_light']};
            }}
            QLabel#font_status {{
                background: transparent;
            }}
            QSizeGrip#font_grip {{
                background: transparent;
                width: 16px;
                height: 16px;
            }}
        """
        self.setStyleSheet(qss)

    # ── Drag (header-only) ──

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            header_bottom = 10 + 36  # outer margin + header height
            if event.position().y() <= header_bottom:
                self._dragging = True
                self.old_pos = event.globalPosition().toPoint()
            else:
                self._dragging = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._dragging and event.buttons() == Qt.MouseButton.LeftButton:
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self._dragging = False
        super().mouseReleaseEvent(event)

    # ── Resize ──

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._grip:
            self._grip.move(
                self.width() - self._grip.width() - 2,
                self.height() - self._grip.height() - 2
            )
