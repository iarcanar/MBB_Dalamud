"""
ThemePanel (PyQt6) — Frameless theme manager matching MBB main window style
"""
import os
import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QGraphicsDropShadowEffect, QColorDialog, QGridLayout,
    QSizePolicy,
)
from PyQt6.QtGui import QColor, QFont, QIcon, QPainter, QBrush, QPen
from PyQt6.QtCore import Qt, QPoint, QTimer, QRectF, pyqtSignal

from pyqt_ui.styles import (
    FONT_PRIMARY, FONT_MONO, derive_palette, _luminance,
)

log = logging.getLogger("mbb-qt")

WIDTH = 400
HEIGHT = 520


# ────────────────────────────────────────────────────────────────────
# ThemeSwatch — Visual preset card showing the FULL palette as dots
# (replaces the old 2-color gradient button which was misleading)
# ────────────────────────────────────────────────────────────────────
class ThemeSwatch(QWidget):
    clicked = pyqtSignal(str)  # emits theme_id

    _W = 84
    _H = 56

    def __init__(self, theme_id: str, theme_data: dict, parent=None):
        super().__init__(parent)
        self.theme_id = theme_id
        self.theme_data = theme_data
        self.setFixedSize(self._W, self._H)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._hover = False
        self._selected = False
        self.setToolTip(theme_data.get("name", theme_id))

    def set_selected(self, selected: bool):
        if self._selected != selected:
            self._selected = selected
            self.update()

    def update_data(self, theme_data: dict):
        self.theme_data = theme_data
        self.setToolTip(theme_data.get("name", self.theme_id))
        self.update()

    def enterEvent(self, event):
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.theme_id)
            event.accept()
            return
        super().mousePressEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        primary = self.theme_data.get("accent", "#1a1a1a")
        secondary = self.theme_data.get("secondary", "#888888")
        # Build the full derived palette so the dots reflect what user actually sees
        palette = derive_palette(primary, secondary)

        # Background = theme bg
        bg = QColor(palette["bg"])
        bg_deeper = QColor(palette["bg_deeper"])
        rect = QRectF(0.5, 0.5, self._W - 1, self._H - 1)
        radius = 6.0

        # Border color depends on state
        if self._selected:
            border_color = QColor(palette["accent"])
            border_width = 2
        elif self._hover:
            border_color = QColor("#ffffff")
            border_color.setAlpha(180)
            border_width = 2
        else:
            border_color = QColor(palette["border_subtle"])
            border_width = 1

        # Draw bg with subtle gradient (top → bottom slightly darker, mimics real UI)
        from PyQt6.QtGui import QLinearGradient
        grad = QLinearGradient(0, 0, 0, self._H)
        grad.setColorAt(0, bg)
        grad.setColorAt(1, bg_deeper)
        p.setBrush(QBrush(grad))
        p.setPen(QPen(border_color, border_width))
        p.drawRoundedRect(rect, radius, radius)

        # Draw 5 color dots showing the palette
        # Selection: bg_titlebar, surface, border, accent, text
        dot_colors = [
            palette["bg_titlebar"],
            palette["btn_bg"],
            palette["border_active"],
            palette["accent"],
            palette["text"],
        ]
        dot_diameter = 10
        gap = 4
        total_w = len(dot_colors) * dot_diameter + (len(dot_colors) - 1) * gap
        x_start = (self._W - total_w) / 2
        y_start = (self._H - dot_diameter) / 2 - 6

        for i, c in enumerate(dot_colors):
            cx = x_start + i * (dot_diameter + gap)
            dot_rect = QRectF(cx, y_start, dot_diameter, dot_diameter)
            # Subtle dark outline so light dots stay visible on light bg
            p.setBrush(QBrush(QColor(c)))
            outline = QColor(0, 0, 0, 80) if _luminance(c) > 0.5 else QColor(255, 255, 255, 40)
            p.setPen(QPen(outline, 0.5))
            p.drawEllipse(dot_rect)

        # Theme name text below the dots
        name = self.theme_data.get("name", self.theme_id)
        text_color = QColor(palette["text"])
        text_color.setAlpha(220 if (self._selected or self._hover) else 160)
        p.setPen(QPen(text_color))
        font = QFont(FONT_PRIMARY, 7, QFont.Weight.DemiBold)
        p.setFont(font)
        text_rect = QRectF(2, self._H - 16, self._W - 4, 14)
        p.drawText(text_rect, int(Qt.AlignmentFlag.AlignCenter), name)

        p.end()


class ThemePanel(QWidget):
    """Frameless theme manager window — matches MBB main window design."""

    def __init__(self, appearance_manager, settings, on_theme_applied=None):
        super().__init__()
        self.am = appearance_manager
        self.settings = settings
        self._on_theme_applied = on_theme_applied
        self.old_pos = QPoint()

        # Current editing state — 4 customizable colors
        self._selected_theme_id = None
        self._primary_color = "#1a1a1a"        # Background
        self._secondary_color = "#888888"      # Accent / Highlight
        self._surface_color = None             # Surface (None = auto-derive)
        self._text_color = None                # Text (None = auto-derive)
        self._dragging = False                 # Header-only drag flag

        # Widget refs
        self.bg = None
        self.shadow = None
        self._preset_buttons = {}
        self._primary_swatch = None
        self._secondary_swatch = None
        self._surface_swatch = None
        self._text_swatch = None
        self._name_input = None

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

        # Section: Preset themes (instant-apply on click)
        sec_preset = QLabel("เลือกธีม  ·  คลิกเพื่อใช้ทันที")
        sec_preset.setObjectName("theme_section")
        sec_preset.setFont(QFont(FONT_PRIMARY, 9, QFont.Weight.Bold))
        c_layout.addWidget(sec_preset)

        grid = QGridLayout()
        grid.setSpacing(8)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)
        self._build_presets(grid)
        c_layout.addLayout(grid)

        c_layout.addSpacing(8)

        # Section: Customize — instant apply on every color change
        sec_custom = QLabel("ปรับแต่งละเอียด  ·  เปลี่ยนทันทีที่เลือกสี")
        sec_custom.setObjectName("theme_section")
        sec_custom.setFont(QFont(FONT_PRIMARY, 9, QFont.Weight.Bold))
        c_layout.addWidget(sec_custom)

        # Two-column layout: 4 color swatches arranged 2x2
        custom_grid = QGridLayout()
        custom_grid.setHorizontalSpacing(14)
        custom_grid.setVerticalSpacing(8)

        # (label, attr_name, tooltip, callback)
        rows = [
            ("พื้นหลัง", "_primary_swatch",   "สีพื้นหลังหลักของหน้าต่าง",      self._pick_primary),
            ("ไฮไลท์",  "_secondary_swatch", "สีไฮไลท์ ปุ่มกด สถานะ active",   self._pick_secondary),
            ("พื้นปุ่ม", "_surface_swatch",   "สีพื้นปุ่มและการ์ด (auto ถ้าไม่ตั้ง)", self._pick_surface),
            ("ข้อความ", "_text_swatch",      "สีตัวอักษรหลัก (auto ถ้าไม่ตั้ง)",   self._pick_text),
        ]
        for i, (label_text, attr_name, tip, cb) in enumerate(rows):
            row_layout = QHBoxLayout()
            row_layout.setSpacing(8)
            lbl = QLabel(label_text)
            lbl.setObjectName("theme_label")
            lbl.setFont(QFont(FONT_PRIMARY, 9))
            row_layout.addWidget(lbl)
            row_layout.addStretch()
            swatch = QPushButton()
            swatch.setObjectName("color_swatch")
            swatch.setFixedSize(46, 22)
            swatch.setCursor(Qt.CursorShape.PointingHandCursor)
            swatch.setToolTip(tip)
            swatch.clicked.connect(cb)
            row_layout.addWidget(swatch)
            setattr(self, attr_name, swatch)
            custom_grid.addLayout(row_layout, i // 2, i % 2)
        c_layout.addLayout(custom_grid)

        # Theme name input
        c_layout.addSpacing(4)
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
        # Instant apply when user finishes typing (Enter or focus loss)
        self._name_input.returnPressed.connect(self._apply_instant)
        self._name_input.editingFinished.connect(self._apply_instant)
        row_n.addWidget(self._name_input)
        c_layout.addLayout(row_n)

        # No APPLY button — every change applies instantly.
        # No status label — instant apply makes status messages obsolete.

        c_layout.addStretch()
        main.addWidget(content, stretch=1)

        self._apply_panel_theme()

    def _build_presets(self, grid: QGridLayout):
        """Build preset theme swatches (ThemeSwatch widgets)."""
        themes = self.am.themes
        col = 0
        row = 0
        # Sort by Theme number (Theme1, Theme2, ...) so order is consistent
        def _sort_key(tid):
            if tid.startswith("Theme") and tid[5:].isdigit():
                return (0, int(tid[5:]))
            return (1, tid)
        for theme_id in sorted(themes.keys(), key=_sort_key):
            data = themes[theme_id]
            swatch = ThemeSwatch(theme_id, data)
            swatch.clicked.connect(self._on_swatch_clicked)
            grid.addWidget(swatch, row, col)
            self._preset_buttons[theme_id] = swatch
            col += 1
            if col >= 3:
                col = 0
                row += 1

    def _on_swatch_clicked(self, theme_id: str):
        """Theme swatch clicked → INSTANT apply (no need to press APPLY)."""
        self._select_preset(theme_id)
        self._apply_instant()

    def _select_preset(self, theme_id: str):
        """Select a preset theme and populate editors (no apply yet)."""
        data = self.am.themes.get(theme_id)
        if not data:
            return
        self._selected_theme_id = theme_id
        self._primary_color = data.get("accent", "#1a1a1a")
        self._secondary_color = data.get("secondary", "#888888")
        # Optional surface/text overrides — None means auto-derive
        self._surface_color = data.get("surface_override")
        self._text_color = data.get("text_override")
        if self._name_input:
            # Block signal to avoid triggering editingFinished during programmatic update
            self._name_input.blockSignals(True)
            self._name_input.setText(data.get("name", ""))
            self._name_input.blockSignals(False)
        self._update_swatches()
        self._highlight_selected()

    def _apply_instant(self):
        """Persist current edits to the selected theme + refresh UI everywhere."""
        tid = self._selected_theme_id
        if not tid:
            return
        # Theme name from input field, fallback to existing
        name = self._name_input.text().strip() if self._name_input else ""
        if not name:
            name = self.am.themes.get(tid, {}).get("name", "Theme")
        # Update via appearance_manager (handles save + callback to MBB main UI)
        success = self.am._update_theme(
            tid, name, self._primary_color, self._secondary_color
        )
        # Persist surface/text overrides into theme dict (not handled by _update_theme)
        if success and tid in self.am.themes:
            theme_data = self.am.themes[tid]
            if self._surface_color:
                theme_data["surface_override"] = self._surface_color
            else:
                theme_data.pop("surface_override", None)
            if self._text_color:
                theme_data["text_override"] = self._text_color
            else:
                theme_data.pop("text_override", None)
            # Persist to settings
            if self.settings:
                custom = self.settings.get("custom_themes", {}) or {}
                custom[tid] = theme_data
                self.settings.set("custom_themes", custom)
                self.settings.save_settings()
        if success:
            self._apply_panel_theme()
            self._refresh_swatches()

    def _load_current(self):
        """Load current theme into editors."""
        tid = self.am.current_theme
        if tid and tid in self.am.themes:
            self._select_preset(tid)

    def _highlight_selected(self):
        """Update swatch selection state."""
        for tid, swatch in self._preset_buttons.items():
            if hasattr(swatch, "set_selected"):
                swatch.set_selected(tid == self._selected_theme_id)

    def _refresh_swatches(self):
        """Refresh swatch palette colors after theme data update."""
        for tid, swatch in self._preset_buttons.items():
            data = self.am.themes.get(tid, {})
            if hasattr(swatch, "update_data"):
                swatch.update_data(data)

    def _update_swatches(self):
        """Update all 4 color swatch button backgrounds."""
        def _style(color, is_auto=False):
            if is_auto:
                # Show diagonal stripes for "auto" (no override) state
                return (
                    "QPushButton#color_swatch {"
                    "  background: qlineargradient(x1:0,y1:0,x2:1,y2:1,"
                    "    stop:0 #2a2a2a, stop:0.5 #3a3a3a, stop:1 #2a2a2a);"
                    "  border: 1px dashed #555555; border-radius: 4px;"
                    "}"
                    "QPushButton#color_swatch:hover { border: 1px dashed #ffffff; }"
                )
            return (
                f"QPushButton#color_swatch {{"
                f"  background: {color};"
                f"  border: 1px solid #555555; border-radius: 4px;"
                f"}}"
                f"QPushButton#color_swatch:hover {{ border: 1px solid #ffffff; }}"
            )

        if self._primary_swatch:
            self._primary_swatch.setStyleSheet(_style(self._primary_color))
        if self._secondary_swatch:
            self._secondary_swatch.setStyleSheet(_style(self._secondary_color))
        if self._surface_swatch:
            self._surface_swatch.setStyleSheet(_style(self._surface_color, is_auto=(self._surface_color is None)))
            self._surface_swatch.setToolTip(
                "พื้นปุ่ม: " + (self._surface_color if self._surface_color else "อัตโนมัติ (คำนวณจากพื้นหลัง)")
            )
        if self._text_swatch:
            self._text_swatch.setStyleSheet(_style(self._text_color, is_auto=(self._text_color is None)))
            self._text_swatch.setToolTip(
                "ข้อความ: " + (self._text_color if self._text_color else "อัตโนมัติ (ตามความสว่างพื้นหลัง)")
            )
    def _pick_primary(self):
        color = QColorDialog.getColor(
            QColor(self._primary_color), self, "เลือกสีพื้นหลัง"
        )
        if color.isValid():
            self._primary_color = color.name()
            self._update_swatches()
            self._apply_instant()  # instant apply

    def _pick_secondary(self):
        color = QColorDialog.getColor(
            QColor(self._secondary_color), self, "เลือกสีไฮไลท์"
        )
        if color.isValid():
            self._secondary_color = color.name()
            self._update_swatches()
            self._apply_instant()

    def _pick_surface(self):
        """Pick surface color override. Right-click resets to auto."""
        initial = QColor(self._surface_color) if self._surface_color else QColor("#222222")
        color = QColorDialog.getColor(initial, self, "เลือกสีพื้นปุ่ม (Cancel = อัตโนมัติ)")
        if color.isValid():
            self._surface_color = color.name()
        else:
            # User cancelled — reset to auto-derive
            self._surface_color = None
        self._update_swatches()
        self._apply_instant()

    def _pick_text(self):
        """Pick text color override. Right-click / cancel resets to auto."""
        initial = QColor(self._text_color) if self._text_color else QColor("#e6edf3")
        color = QColorDialog.getColor(initial, self, "เลือกสีข้อความ (Cancel = อัตโนมัติ)")
        if color.isValid():
            self._text_color = color.name()
        else:
            self._text_color = None
        self._update_swatches()
        self._apply_instant()

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

    # _show_status removed — instant apply replaces status messages.

    # ── Theming ──

    def _apply_panel_theme(self):
        """Apply current theme colors to this panel."""
        primary = self.am.get_accent_color()
        secondary = self.am.get_theme_color("secondary", "#888888")
        surface = self.am.get_theme_color("surface_override")
        text_override = self.am.get_theme_color("text_override")
        p = derive_palette(primary, secondary, surface=surface, text_override=text_override)

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
            /* theme_apply + theme_status QSS removed (instant-apply UX) */
        """
        self.setStyleSheet(qss)
        self._update_swatches()

    # ── Drag Support — header only ──
    # Outer margin (10) + header height (36) = 46. Clicks below this don't drag.
    # This prevents the panel from "bouncing" when the user clicks on a swatch /
    # color picker / empty content area and the mouse drifts a few pixels —
    # previously any LMB+move anywhere on the panel moved the window.
    _DRAG_HEADER_BOTTOM = 46

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if event.position().y() <= self._DRAG_HEADER_BOTTOM:
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
