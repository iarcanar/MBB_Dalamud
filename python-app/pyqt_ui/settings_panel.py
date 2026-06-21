"""
SettingsPanel (PyQt6) — Frameless settings window matching MBB main window style
Replaces the old Tkinter SettingsUI with consistent PyQt6 design.
"""
import time
import random
import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGraphicsDropShadowEffect, QCheckBox, QScrollArea, QFrame,
    QSizePolicy, QMenu,
)
from PyQt6.QtGui import QColor, QFont, QPainter, QBrush, QPen
from PyQt6.QtCore import (
    Qt, QPoint, QTimer, QPropertyAnimation, QEasingCurve,
    pyqtProperty, pyqtSignal, QRectF, QSize,
)

from pyqt_ui.styles import FONT_PRIMARY, FONT_MONO, derive_palette

log = logging.getLogger("mbb-qt")

WIDTH = 360    # bumped from 300 (+20%) for easier reading
HEIGHT = 676   # +52 over 624 for the taller two-row shortcut info card


# ────────────────────────────────────────────────────────────────────
# ToggleSwitch — Modern iOS-style switch with sliding knob + animation
# Replaces QCheckBox::indicator pill (which had no knob → unclear state).
# Drop-in compatible API: isChecked(), setChecked(bool), toggled signal.
# ────────────────────────────────────────────────────────────────────
class ToggleSwitch(QWidget):
    toggled = pyqtSignal(bool)
    # Compat: emit a state-change signal mimicking QCheckBox.stateChanged
    stateChanged = pyqtSignal(int)

    # Visual constants — bumped 20% from 44×22 for the larger Settings UI
    _W = 52
    _H = 26
    _KNOB_PAD = 4            # padding from track edge
    _KNOB_DIAMETER = _H - 2 * _KNOB_PAD  # 18 px

    def __init__(self, parent=None, palette=None):
        super().__init__(parent)
        self.setFixedSize(self._W, self._H)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)

        self._checked = False
        self._hover = False

        # Animated knob X position
        off_x = self._KNOB_PAD
        on_x = self._W - self._KNOB_PAD - self._KNOB_DIAMETER
        self._off_x = off_x
        self._on_x = on_x
        self._knob_x = off_x

        self._anim = QPropertyAnimation(self, b"knob_x", self)
        self._anim.setDuration(160)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Default palette (overridable via set_palette)
        self._color_track_off = QColor("#3a3a3a")
        self._color_track_off_border = QColor("#4a4a4a")
        self._color_track_on = QColor("#2bb5ff")
        self._color_knob = QColor("#f5f5f5")
        self._color_knob_shadow = QColor(0, 0, 0, 90)
        if palette:
            self.set_palette(palette)

    # ── Public API ──
    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, checked: bool):
        checked = bool(checked)
        if checked == self._checked:
            return
        self._checked = checked
        self._animate_to_target()
        self.toggled.emit(checked)
        self.stateChanged.emit(2 if checked else 0)
        self.update()

    def set_palette(self, palette: dict):
        """Apply theme colors. Expected keys: accent, bg_titlebar, border_subtle."""
        self._color_track_on = QColor(palette.get("accent", "#2bb5ff"))
        # Off = darker neutral so off-state is visually distinct from on-state
        self._color_track_off = QColor(palette.get("bg_titlebar", "#2a2a2a")).darker(110)
        self._color_track_off_border = QColor(palette.get("border_subtle", "#3a3a3a"))
        self.update()

    # ── Qt property for animation ──
    def _get_knob_x(self) -> int:
        return self._knob_x

    def _set_knob_x(self, x: int):
        self._knob_x = x
        self.update()

    knob_x = pyqtProperty(int, fget=_get_knob_x, fset=_set_knob_x)

    def _animate_to_target(self):
        target = self._on_x if self._checked else self._off_x
        self._anim.stop()
        self._anim.setStartValue(self._knob_x)
        self._anim.setEndValue(target)
        self._anim.start()

    # ── Events ──
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.setChecked(not self._checked)
            event.accept()
            return
        super().mousePressEvent(event)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.setChecked(not self._checked)
            event.accept()
            return
        super().keyPressEvent(event)

    def enterEvent(self, event):
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self.update()
        super().leaveEvent(event)

    # ── Painting ──
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Track
        track_rect = QRectF(0.5, 0.5, self._W - 1, self._H - 1)
        radius = self._H / 2

        if self._checked:
            track_color = QColor(self._color_track_on)
            border_color = QColor(self._color_track_on).darker(115)
        else:
            track_color = QColor(self._color_track_off)
            border_color = QColor(self._color_track_off_border)

        if self._hover:
            track_color = track_color.lighter(108)

        p.setBrush(QBrush(track_color))
        p.setPen(QPen(border_color, 1))
        p.drawRoundedRect(track_rect, radius, radius)

        # Knob shadow (subtle, below knob)
        shadow_rect = QRectF(
            self._knob_x, self._KNOB_PAD + 1,
            self._KNOB_DIAMETER, self._KNOB_DIAMETER
        )
        p.setBrush(QBrush(self._color_knob_shadow))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(shadow_rect)

        # Knob
        knob_rect = QRectF(
            self._knob_x, self._KNOB_PAD,
            self._KNOB_DIAMETER, self._KNOB_DIAMETER
        )
        p.setBrush(QBrush(self._color_knob))
        p.setPen(QPen(QColor(0, 0, 0, 40), 1))
        p.drawEllipse(knob_rect)

        p.end()


class SettingsPanel(QWidget):
    """Frameless settings panel — matches MBB main window design."""

    def __init__(self, settings, apply_settings_callback,
                 update_hotkeys_callback, appearance_manager,
                 main_app=None):
        super().__init__()
        self.settings = settings
        self.apply_settings_callback = apply_settings_callback
        self.update_hotkeys_callback = update_hotkeys_callback
        self.am = appearance_manager
        self.main_app = main_app
        self.old_pos = QPoint()

        # Sub-panel references
        self._hotkey_panel = None
        self._model_panel = None
        self._font_panel = None

        # Toggle state tracking
        self._toggles = {}       # key -> ToggleSwitch
        self._initial_values = {}
        self._has_changes = False

        # Widget refs
        self.bg = None
        self.shadow = None
        self._apply_btn = None
        self._status_label = None
        self._shortcut_toggle_lbl = None
        self._shortcut_start_lbl = None

        # Callbacks
        self.on_close_callback = None

        # Palette must exist before _build_ui (ToggleSwitch needs it)
        primary = self.am.get_accent_color()
        secondary = self.am.get_theme_color("secondary", "#888888")
        surface = self.am.get_theme_color("surface_override")
        text_override = self.am.get_theme_color("text_override")
        self.palette = derive_palette(primary, secondary, surface=surface, text_override=text_override)

        self._init_window()
        self._build_ui()
        self._apply_theme()

    # ── Window Setup ──

    def _init_window(self):
        self.setWindowTitle("Settings")
        self.setFixedSize(WIDTH, HEIGHT)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    # ── UI Construction ──

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)

        self.bg = QWidget()
        self.bg.setObjectName("settings_bg")
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
        header.setObjectName("settings_header")
        header.setFixedHeight(52)  # +20% from 44
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(14, 0, 6, 0)
        h_layout.setSpacing(4)

        title = QLabel("SETTINGS")
        title.setObjectName("settings_title")
        title.setFont(QFont(FONT_PRIMARY, 13, QFont.Weight.Bold))  # +20% from 11pt
        h_layout.addWidget(title)
        h_layout.addStretch()

        btn_close = QPushButton("\u2715")
        btn_close.setObjectName("settings_close")
        btn_close.setFixedSize(34, 34)  # +20% from 28
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.clicked.connect(self.close_settings)
        h_layout.addWidget(btn_close)

        main.addWidget(header)

        # ── Divider ──
        div = QFrame()
        div.setObjectName("settings_divider")
        div.setFixedHeight(1)
        main.addWidget(div)

        # ── Scrollable Content ──
        scroll = QScrollArea()
        scroll.setObjectName("settings_scroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        content.setObjectName("settings_content")
        c_layout = QVBoxLayout(content)
        c_layout.setContentsMargins(14, 10, 14, 14)
        c_layout.setSpacing(6)

        # Section: Feature Toggles  (header stays English; toggle labels in Thai
        # for clarity with our primarily-Thai userbase)
        self._add_section_label(c_layout, "Feature Toggles")
        self._add_toggle(c_layout, "enable_wasd_auto_hide",
                         "ซ่อน UI เมื่อวิ่ง (WASD)", False)
        # "Smart Performance" toggle removed 2026-04-25 (dead OCR-era CPU throttling)
        self._add_toggle(c_layout, "enable_tui_auto_show",
                         "โชว์ TUI อัตโนมัติเมื่อแปล", True)
        self._add_toggle(c_layout, "enable_battle_chat_mode",
                         "แสดงคำแปลซีนต่อสู้", True)
        self._add_toggle(c_layout, "enable_conversation_logging",
                         "บันทึกประวัติการแปล", False)
        self._add_log_path_info(c_layout)
        self._add_toggle(c_layout, "enable_starting_key_visual",
                         "เริ่มโปรแกรมด้วยภาพ artwork", True)

        c_layout.addSpacing(4)

        # Section: Advanced → "ตั้งค่าอื่นๆ"
        self._add_section_label(c_layout, "ตั้งค่าอื่นๆ")
        adv_row = QHBoxLayout()
        adv_row.setSpacing(6)

        btn_font = self._make_section_btn("FONT")
        btn_font.clicked.connect(self._toggle_font)
        adv_row.addWidget(btn_font)

        btn_model = self._make_section_btn("MODEL")
        btn_model.clicked.connect(self._toggle_model)
        adv_row.addWidget(btn_model)

        btn_hotkey = self._make_section_btn("HOTKEY")
        btn_hotkey.clicked.connect(self._toggle_hotkey)
        adv_row.addWidget(btn_hotkey)

        c_layout.addLayout(adv_row)
        c_layout.addSpacing(4)

        # Section: Test Hook → "ทดสอบการแปลรูปแบบต่างๆ"
        self._add_section_label(c_layout, "ทดสอบการแปลรูปแบบต่างๆ")
        test_row = QHBoxLayout()
        test_row.setSpacing(6)

        for label, subtitle, handler in [
            ("Dialog", "ChatType 61", self._inject_test_dialog),
            ("Battle", "ChatType 68", self._inject_test_battle),
            ("Cutscene", "ChatType 71", self._inject_test_cutscene),
            ("Choice", "pipe-separated", self._inject_test_choice),
        ]:
            test_row.addWidget(self._make_test_btn(label, subtitle, handler))

        c_layout.addLayout(test_row)
        c_layout.addSpacing(4)

        # Section: Shortcuts → "ปุ่มลัด" — READ-ONLY info display (not buttons).
        # Rendered as a distinct card with keycap-style values so it reads as a
        # reference table, visually separate from the clickable buttons above.
        # (Edit the keys via the HOTKEY button.)
        self._add_section_label(c_layout, "ปุ่มลัด")

        sc_card = QWidget()
        sc_card.setObjectName("settings_shortcut_card")
        sc_v = QVBoxLayout(sc_card)
        sc_v.setContentsMargins(12, 9, 12, 9)
        sc_v.setSpacing(7)

        # NOTE: F9 (start_stop_translate) is bound to toggle_translated_ui() —
        # it shows/hides the TUI window, so the label reflects that, not
        # "start/stop translation" (that lives on the control-panel button).
        row1, self._shortcut_toggle_lbl = self._make_shortcut_info_row(
            "เปิด / ปิด UI",
            self.settings.get_shortcut("toggle_ui", "alt+h").upper(),
        )
        sc_v.addLayout(row1)

        row2, self._shortcut_start_lbl = self._make_shortcut_info_row(
            "โชว์ / ซ่อน TUI",
            self.settings.get_shortcut("start_stop_translate", "f9").upper(),
        )
        sc_v.addLayout(row2)

        c_layout.addWidget(sc_card)

        # Version
        from version import __version__
        ver_label = QLabel(f"MagicBabel Dalamud v{__version__} by iarcanar")
        ver_label.setObjectName("settings_version")
        ver_label.setFont(QFont(FONT_PRIMARY, 10))  # +20% from 8pt
        ver_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        c_layout.addWidget(ver_label)

        c_layout.addStretch()

        scroll.setWidget(content)
        main.addWidget(scroll, stretch=1)

        # ── Status + Apply ──
        footer = QWidget()
        footer.setObjectName("settings_footer")
        f_layout = QVBoxLayout(footer)
        f_layout.setContentsMargins(14, 6, 14, 10)
        f_layout.setSpacing(4)

        self._status_label = QLabel("")
        self._status_label.setObjectName("settings_status")
        self._status_label.setFont(QFont(FONT_PRIMARY, 10))  # +20% from 8pt
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        f_layout.addWidget(self._status_label)

        self._apply_btn = QPushButton("APPLY")
        self._apply_btn.setObjectName("settings_apply")
        self._apply_btn.setFont(QFont(FONT_PRIMARY, 12, QFont.Weight.Bold))  # +20% from 10pt
        self._apply_btn.setFixedHeight(40)  # +20% from 34
        self._apply_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._apply_btn.setEnabled(False)
        self._apply_btn.setProperty("state", "inactive")
        self._apply_btn.clicked.connect(self._on_apply)

        # APPLY stays put; the ⋮ kebab to its right holds rarely-used,
        # destructive actions (Restart App) — tucked away to prevent misclicks.
        apply_row = QHBoxLayout()
        apply_row.setSpacing(6)
        apply_row.addWidget(self._apply_btn, stretch=1)

        self._more_btn = QPushButton("⋮")  # ⋮ vertical ellipsis
        self._more_btn.setObjectName("settings_more")
        self._more_btn.setFont(QFont(FONT_PRIMARY, 16, QFont.Weight.Bold))
        self._more_btn.setFixedSize(40, 40)
        self._more_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._more_btn.setToolTip("ตัวเลือกเพิ่มเติม")
        self._more_btn.clicked.connect(self._show_more_menu)
        apply_row.addWidget(self._more_btn)

        f_layout.addLayout(apply_row)

        main.addWidget(footer)

    # ── Widget Factories ──

    def _add_section_label(self, layout, text):
        lbl = QLabel(text)
        lbl.setObjectName("settings_section")
        lbl.setFont(QFont(FONT_PRIMARY, 11, QFont.Weight.Bold))  # +20% from 9pt — section labels
        layout.addWidget(lbl)

    def _add_toggle(self, layout, key, label, default):
        row = QHBoxLayout()
        row.setSpacing(8)

        lbl = QLabel(label)
        lbl.setObjectName("settings_toggle_label")
        lbl.setFont(QFont(FONT_PRIMARY, 11))  # +20% from 9pt — toggle label
        row.addWidget(lbl, stretch=1)

        # Modern iOS-style switch with sliding knob (replaces QCheckBox pill)
        cb = ToggleSwitch(palette=self.palette)
        cb.setChecked(self.settings.get(key, default))
        cb.toggled.connect(lambda checked, k=key: self._on_toggle_changed(k))
        row.addWidget(cb, alignment=Qt.AlignmentFlag.AlignVCenter)

        # Make label clickable to toggle the switch (better UX)
        lbl.setCursor(Qt.CursorShape.PointingHandCursor)
        def _label_click(event, switch=cb):
            if event.button() == Qt.MouseButton.LeftButton:
                switch.setChecked(not switch.isChecked())
        lbl.mousePressEvent = _label_click

        layout.addLayout(row)
        self._toggles[key] = cb

    def _add_log_path_info(self, layout):
        """Path display + open-folder button under the conversation_logging
        toggle, so users know where logs land and can jump straight to them.

        Width-safe: label uses a SHORT compact text with tooltip carrying the
        full path. minimum width 0 + Preferred size policy + minimum-size hint
        suppression prevents this row from forcing the scroll content wider
        than the panel (which would push all other rows off-screen)."""
        import os
        from resource_utils import get_app_dir

        # Must match conversation_logger.__init__ — logs land next to the app
        log_dir = os.path.join(get_app_dir(), "logs", "conversation_logs")

        row = QHBoxLayout()
        row.setContentsMargins(8, 0, 4, 4)
        row.setSpacing(6)

        # Compact path label — full path lives in the tooltip. Sized so it
        # never forces the panel wider than its parent scroll area.
        path_lbl = QLabel("\U0001F4C1 ...\\conversation_logs")
        path_lbl.setObjectName("settings_log_path")
        path_lbl.setFont(QFont(FONT_MONO, 8))
        path_lbl.setStyleSheet("color: rgba(255, 255, 255, 0.45);")
        path_lbl.setToolTip(f"บันทึกที่:\n{log_dir}")
        path_lbl.setMinimumWidth(0)
        path_lbl.setSizePolicy(QSizePolicy.Policy.Preferred,
                               QSizePolicy.Policy.Preferred)
        row.addWidget(path_lbl, stretch=1)

        # Open-folder button (compact, fixed width — doesn't grow)
        btn = QPushButton("เปิดโฟลเดอร์")
        btn.setObjectName("settings_log_open_btn")
        btn.setFont(QFont(FONT_PRIMARY, 9))
        btn.setFixedHeight(22)
        btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(
            "QPushButton#settings_log_open_btn {"
            f"  background: {self.palette['btn_bg']};"
            f"  color: {self.palette['text']};"
            f"  border: 1px solid {self.palette['border_subtle']};"
            "  border-radius: 4px; padding: 2px 8px;"
            "}"
            "QPushButton#settings_log_open_btn:hover {"
            f"  background: {self.palette['accent']};"
            f"  color: {self.palette['toggled_text']};"
            "}"
        )
        btn.clicked.connect(lambda: self._open_log_folder(log_dir))
        row.addWidget(btn)

        layout.addLayout(row)

    def _open_log_folder(self, path):
        """Open the conversation log dir in Windows Explorer. Creates the
        directory first if it doesn't exist yet (toggle never turned on)."""
        import os
        import subprocess
        try:
            os.makedirs(path, exist_ok=True)
            subprocess.Popen(['explorer', path])
        except Exception as e:
            log.error(f"Failed to open log folder '{path}': {e}")

    def _make_section_btn(self, text):
        btn = QPushButton(text)
        btn.setObjectName("settings_section_btn")
        btn.setFont(QFont(FONT_PRIMARY, 11, QFont.Weight.Bold))  # +20% from 9pt
        btn.setFixedHeight(36)  # +20% from 30
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        return btn

    def _make_test_btn(self, text, subtitle, handler):
        container = QWidget()
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(1)

        btn = QPushButton(text)
        btn.setObjectName("settings_test_btn")
        btn.setFont(QFont(FONT_PRIMARY, 11))  # +20% from 9pt
        btn.setFixedHeight(32)  # +20% from 26
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(handler)
        v.addWidget(btn)

        sub = QLabel(subtitle)
        sub.setObjectName("settings_test_subtitle")
        sub.setFont(QFont(FONT_MONO, 8))  # +20% from 7pt
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(sub)

        return container

    def _make_shortcut_info_row(self, label_text, value_text):
        """One read-only shortcut row: description on the left, keycap-style
        value on the right. Returns (row_layout, value_label) so the caller
        keeps a ref for live updates. Nothing here is clickable."""
        row = QHBoxLayout()
        row.setSpacing(8)

        key_lbl = QLabel(label_text)
        key_lbl.setObjectName("settings_shortcut_key")
        key_lbl.setFont(QFont(FONT_PRIMARY, 10))
        row.addWidget(key_lbl)
        row.addStretch()

        val_lbl = QLabel(value_text)
        val_lbl.setObjectName("settings_shortcut_val")
        val_lbl.setFont(QFont(FONT_MONO, 10, QFont.Weight.Bold))
        val_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        val_lbl.setMinimumWidth(64)
        row.addWidget(val_lbl)

        return row, val_lbl

    # ── Toggle Logic ──

    def _on_toggle_changed(self, key):
        self._check_for_changes()
        # Immediate save for toggles
        val = self._toggles[key].isChecked()
        self.settings.set(key, val, save_immediately=False)
        self.settings.set("dalamud_enabled", True, save_immediately=False)
        self.settings.save_settings()
        log.info(f"Toggle {key} = {val}")

        # Callback
        if self.apply_settings_callback:
            settings_dict = {k: cb.isChecked() for k, cb in self._toggles.items()}
            settings_dict["dalamud_enabled"] = True
            self.apply_settings_callback(settings_dict)

    def _check_for_changes(self):
        changed = False
        for key, cb in self._toggles.items():
            if cb.isChecked() != self._initial_values.get(key, False):
                changed = True
                break
        self._has_changes = changed
        self._update_apply_state()

    def _update_apply_state(self):
        if self._has_changes:
            self._apply_btn.setEnabled(True)
            self._apply_btn.setProperty("state", "active")
        else:
            self._apply_btn.setEnabled(False)
            self._apply_btn.setProperty("state", "inactive")
        self._apply_btn.style().unpolish(self._apply_btn)
        self._apply_btn.style().polish(self._apply_btn)

    def _on_apply(self):
        settings_dict = {}
        for key, cb in self._toggles.items():
            val = cb.isChecked()
            self.settings.set(key, val, save_immediately=False)
            settings_dict[key] = val
        self.settings.set("dalamud_enabled", True, save_immediately=False)
        self.settings.save_settings()

        if self.apply_settings_callback:
            settings_dict["dalamud_enabled"] = True
            self.apply_settings_callback(settings_dict)

        # Visual feedback
        self._apply_btn.setProperty("state", "applied")
        self._apply_btn.style().unpolish(self._apply_btn)
        self._apply_btn.style().polish(self._apply_btn)
        self._apply_btn.setText("\u2713 APPLIED")
        self._status_label.setStyleSheet("color: #4CAF50; background: transparent;")
        self._status_label.setText("Settings applied successfully!")

        self._snapshot_initial_values()
        self._has_changes = False

        QTimer.singleShot(2000, self._reset_apply_button)

    def _reset_apply_button(self):
        self._apply_btn.setText("APPLY")
        self._update_apply_state()
        self._status_label.setText("")

    # ── Overflow menu + Restart (tucked behind the ⋮ to avoid misclicks) ──

    def _show_more_menu(self):
        """Overflow menu off the ⋮ kebab — currently just Restart App."""
        p = self.palette
        menu = QMenu(self)
        menu.setObjectName("settings_more_menu")
        menu.setCursor(Qt.CursorShape.PointingHandCursor)
        menu.setStyleSheet(f"""
            QMenu#settings_more_menu {{
                background: {p['bg_titlebar']};
                border: 1px solid {p['border_active']};
                border-radius: 8px;
                padding: 6px;
            }}
            QMenu#settings_more_menu::item {{
                background: transparent;
                color: {p['text']};
                padding: 8px 18px;
                border-radius: 5px;
            }}
            QMenu#settings_more_menu::item:selected {{
                background: rgba(204, 68, 68, 0.18);
                color: #ff6b6b;
            }}
        """)
        act_restart = menu.addAction("\U0001F504  รีสตาร์ทโปรแกรม")
        act_restart.triggered.connect(self._on_restart_clicked)
        # Anchor the menu's bottom-right at the kebab's top-right so it opens
        # upward (the kebab sits at the panel's bottom edge).
        anchor = self._more_btn.mapToGlobal(QPoint(self._more_btn.width(), 0))
        hint = menu.sizeHint()
        menu.exec(QPoint(anchor.x() - hint.width(), anchor.y() - hint.height()))

    def _on_restart_clicked(self):
        self._more_btn.setEnabled(False)
        self._apply_btn.setEnabled(False)
        self._restart_countdown = 3
        self._status_label.setStyleSheet("color: #FF8C00; background: transparent;")
        self._status_label.setText(f"กำลังรีสตาร์ทใน {self._restart_countdown}...")
        self._restart_timer = QTimer()
        self._restart_timer.timeout.connect(self._restart_tick)
        self._restart_timer.start(1000)

    def _restart_tick(self):
        self._restart_countdown -= 1
        if self._restart_countdown > 0:
            self._status_label.setText(f"กำลังรีสตาร์ทใน {self._restart_countdown}...")
        else:
            self._restart_timer.stop()
            self._status_label.setText("กำลังรีสตาร์ท...")
            if self.main_app and hasattr(self.main_app, 'restart_app'):
                self.main_app.restart_app()

    def _snapshot_initial_values(self):
        self._initial_values = {k: cb.isChecked() for k, cb in self._toggles.items()}

    # ── Sub-Panel Openers ──

    def _toggle_font(self):
        if self._font_panel and self._font_panel.isVisible():
            self._font_panel.close()
        else:
            self._ensure_font_panel()
            self._position_subpanel(self._font_panel)
            self._font_panel.show()

    def _toggle_model(self):
        if self._model_panel and self._model_panel.isVisible():
            self._model_panel.close()
        else:
            self._ensure_model_panel()
            self._position_subpanel(self._model_panel)
            self._model_panel.show()

    def _toggle_hotkey(self):
        if self._hotkey_panel and self._hotkey_panel.isVisible():
            self._hotkey_panel.close()
        else:
            self._ensure_hotkey_panel()
            self._position_subpanel(self._hotkey_panel)
            self._hotkey_panel.show()

    def _ensure_font_panel(self):
        if not self._font_panel:
            from pyqt_ui.font_panel import FontPanel
            from pyqt_ui.qt_font_manager import QtFontManager
            qfm = QtFontManager()
            self._font_panel = FontPanel(
                self.settings, qfm, self.am, main_app=self.main_app
            )

    def _ensure_model_panel(self):
        if not self._model_panel:
            from pyqt_ui.model_panel import ModelPanel
            self._model_panel = ModelPanel(
                self.settings, self.am, main_app=self.main_app
            )

    def _ensure_hotkey_panel(self):
        if not self._hotkey_panel:
            from pyqt_ui.hotkey_panel import HotkeyPanel
            # Wrap the callback so saving a hotkey ALSO refreshes the read-only
            # 'ปุ่มลัด' card here — otherwise it shows stale keys until Settings
            # is reopened.
            def _on_hotkeys_saved():
                if self.update_hotkeys_callback:
                    self.update_hotkeys_callback()
                self._refresh_shortcut_display()
            self._hotkey_panel = HotkeyPanel(
                self.settings, _on_hotkeys_saved, self.am
            )

    def _position_subpanel(self, panel):
        """Position sub-panel to the right of this settings panel."""
        pos = self.pos()
        panel.move(pos.x() + self.width() + 8, pos.y())

    # ── Test Hook Injection ──

    def _inject_test_message(self, msg_type, speaker, message, chat_type):
        if not self.main_app or not hasattr(self.main_app, 'dalamud_handler'):
            log.warning("[TEST] Main app or dalamud_handler not available")
            return
        if not self.main_app.dalamud_handler:
            log.warning("[TEST] Dalamud handler not ready")
            return

        test_msg = {
            "Type": msg_type,
            "Speaker": speaker,
            "Message": message,
            "Timestamp": int(time.time() * 1000),
            "ChatType": chat_type,
        }
        self.main_app.dalamud_handler.process_message(test_msg)
        log.info(f"[TEST] Injected {msg_type} (ChatType {chat_type})")

    # ── Test Message Pools (6 per type) ──

    _TEST_DIALOG = [
        ("Y'shtola", "The aether here flows wrong. Whatever did this, it was no accident."),
        ("Wuk Lamat", "I want to be the kind of dawnservant who eats lunch with everyone, not just the nobles!"),
        ("Alisaie", "If you're done brooding, my brother, perhaps we could actually solve something today."),
        ("Alphinaud", "Strategy without compassion is just cruelty wearing a clever mask. Let us not forget that."),
        ("Thancred", "Trouble has a habit of finding me. Today it appears to have brought friends."),
        ("Tataru", "Don't you worry about a single gil! Tataru Taru has it ALL handled, as always!"),
        ("Urianger", "Forsooth, the threads of fate do tangle 'round thee once more. Mine heart misgiveth me, yet onward must we tread."),
        ("Krile", "You don't always have to carry it alone, you know. That's what friends are for."),
        ("G'raha Tia", "To stand beside you now, in this moment, as your equal... it is everything I hoped for and more."),
        ("Estinien", "Spare me the speeches. If there's a dragon to slay, point me at it."),
    ]

    _TEST_BATTLE = [
        ("Zenos", "Yes! YES! Show me more! Let me feel your hatred sing!"),
        ("Nidhogg", "Thy kind hath taken everything from me! Now I shall return the favor a thousandfold!"),
        ("Estinien", "Come then, wyrm! Let us see whose lance bites deeper today!"),
        ("Emet-Selch", "How utterly tiresome. Must I truly stoop to swatting you myself?"),
        ("Sephiroth", "You are nothing. A flicker of a flame about to be snuffed out."),
        ("???", "You should not have come here, hero. This is where your story ends."),
    ]

    _TEST_CUTSCENE = [
        # Narrative omniscient voice — no named speaker. ChatType 71 is for
        # scene descriptions, not character dialogue (characters speak via
        # ChatType 61 even during cutscenes). All speakers must stay "".
        ("", "And in the silence that followed, the realm itself seemed to hold its breath, waiting for a hero who might never come."),
        ("", "The crystal's light dimmed at last, and with it the final echo of an age the world would soon forget it had ever known."),
        ("", "Snow drifted across the battlefield, softening the shapes of the fallen until the cruelty of what had passed became almost gentle."),
        ("", "Through the rift between stars, a voice older than memory whispered a promise — and the wind carried it across every shore that ever was."),
    ]

    def _inject_test_dialog(self):
        speaker, message = random.choice(self._TEST_DIALOG)
        self._inject_test_message("dialogue", speaker, message, 61)

    def _inject_test_battle(self):
        speaker, message = random.choice(self._TEST_BATTLE)
        self._inject_test_message("battle", speaker, message, 68)

    def _inject_test_cutscene(self):
        speaker, message = random.choice(self._TEST_CUTSCENE)
        self._inject_test_message("cutscene", speaker, message, 71)

    # ── Choice test pool — English source, pipe-separated, as the C# bridge
    # sends them from the FFXIV SelectString addon (ChatType 70). The handler
    # routes Type="choice" through translate_choice() which preserves the
    # header + bullet format for the overlay. ──
    _TEST_CHOICE_2 = [
        # 2-choice flow — based on real game logs ("She is young..." case)
        "What will you say? | She is young, but has potential. | She is not ready to rule.",
        # Mirrors the Aranea/Hildibrand screenshot
        "What will you say? | I'm Aranea, Agent of Adventure. | I'm simply an ardent admirer of Inspector Hildibrand.",
        "What will you say? | I'm ready when you are. | Tell me more about the mission first.",
    ]
    _TEST_CHOICE_3 = [
        # 3-choice flow — moral/strategic options
        "What will you say? | The crystal must be returned to its rightful place. | These people deserve our help, no matter the cost. | This matter is beyond my concern.",
        "What will you say? | Aye, I'm ready. | Not yet — give me a moment. | What's the plan?",
        "What will you say? | I'll handle the negotiations. | Let Alphinaud speak first. | We should leave this to the locals.",
    ]

    def _inject_test_choice(self):
        # Alternate between 2-choice and 3-choice for varied testing
        pool = random.choice([self._TEST_CHOICE_2, self._TEST_CHOICE_3])
        message = random.choice(pool)
        # Real game sends:
        #   Type: "choice", ChatType: 70, Message: "Header | A | B [| C]"
        # The handler detects Type=="choice" → translate_choice() → emits
        # "Header\n• A\n• B [\n• C]" → reaches update_text with chat_type=70
        # → _is_choice_dialogue OR chat_type==70 check → routes to overlay.
        self._inject_test_message("choice", "", message, 70)

    # ── Open / Close ──

    def open_settings(self, x, y, parent_width):
        """Open settings at position relative to parent."""
        self._load_current_settings()
        self.move(x + parent_width + 10, y)
        self.show()
        self.raise_()

    def _load_current_settings(self):
        """Load current values into toggles."""
        for key, cb in self._toggles.items():
            default = True if key != "enable_wasd_auto_hide" else False
            cb.blockSignals(True)
            cb.setChecked(self.settings.get(key, default))
            cb.blockSignals(False)
        self._snapshot_initial_values()
        self._has_changes = False
        self._update_apply_state()

        # Update shortcut display
        self._refresh_shortcut_display()

    def _refresh_shortcut_display(self):
        """Update the read-only 'ปุ่มลัด' card to the current bindings — called
        on open AND right after the Hotkey panel saves, so the displayed keys
        never go stale."""
        if self._shortcut_toggle_lbl:
            self._shortcut_toggle_lbl.setText(
                self.settings.get_shortcut("toggle_ui", "alt+h").upper()
            )
        if self._shortcut_start_lbl:
            self._shortcut_start_lbl.setText(
                self.settings.get_shortcut("start_stop_translate", "f9").upper()
            )

    def close_settings(self):
        """Close settings and all sub-panels."""
        self.hide()
        if self._hotkey_panel:
            self._hotkey_panel.close()
        if self._model_panel:
            self._model_panel.close()
        if self._font_panel:
            self._font_panel.close()
        if self.on_close_callback:
            self.on_close_callback()

    @property
    def settings_visible(self):
        return self.isVisible()

    # ── Theming ──

    def _apply_theme(self):
        primary = self.am.get_accent_color()
        secondary = self.am.get_theme_color("secondary", "#888888")
        surface = self.am.get_theme_color("surface_override")
        text_override = self.am.get_theme_color("text_override")
        p = derive_palette(primary, secondary, surface=surface, text_override=text_override)
        self.palette = p

        # Accent-tinted hover backgrounds (rgba from the theme accent) so every
        # button's hover is clearly visible, not a faint ~5% lightness bump.
        _ac = QColor(p['accent'])
        accent_rgb = f"{_ac.red()}, {_ac.green()}, {_ac.blue()}"

        # Update toggle switch colors to match new theme (if rebuilt)
        for sw in self._toggles.values():
            if hasattr(sw, "set_palette"):
                sw.set_palette(p)

        qss = f"""
            QWidget#settings_bg {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {p['bg']}, stop:1 {p['bg_deeper']});
                border-radius: 10px;
                border: 1px solid {p['border_subtle']};
            }}
            QWidget#settings_header {{
                background: {p['bg_titlebar']};
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }}
            QLabel#settings_title {{
                color: {p['text']};
                background: transparent;
            }}
            QPushButton#settings_close {{
                background: transparent;
                border: none; border-radius: 4px;
                color: {p['text_dim']}; font-size: 13px; font-weight: bold;
            }}
            QPushButton#settings_close:hover {{
                background: #cc4444; color: #ffffff;
            }}
            QFrame#settings_divider {{
                background: {p['border_subtle']};
                border: none;
            }}
            QScrollArea#settings_scroll {{
                background: transparent;
                border: none;
            }}
            QWidget#settings_content {{
                background: transparent;
            }}
            QLabel#settings_section {{
                color: {p['text_dim']};
                background: transparent;
            }}
            QLabel#settings_toggle_label {{
                color: {p['text']};
                background: transparent;
            }}
            /* QCheckBox#settings_toggle styling removed — replaced by ToggleSwitch widget */
            QPushButton#settings_section_btn {{
                background: {p['btn_bg']};
                color: {p['text']};
                border: 1px solid {p['border_subtle']};
                border-radius: 4px;
                font-family: '{FONT_PRIMARY}';
            }}
            QPushButton#settings_section_btn:hover {{
                background: rgba({accent_rgb}, 0.16);
                border: 1px solid {p['accent']};
                color: {p['accent_light']};
            }}
            QPushButton#settings_section_btn:pressed {{
                background: rgba({accent_rgb}, 0.30);
            }}
            QPushButton#settings_test_btn {{
                background: {p['btn_bg']};
                color: {p['text']};
                border: 1px solid {p['border_subtle']};
                border-radius: 4px;
            }}
            QPushButton#settings_test_btn:hover {{
                background: rgba({accent_rgb}, 0.16);
                border: 1px solid {p['accent']};
                color: {p['accent_light']};
            }}
            QPushButton#settings_test_btn:pressed {{
                background: rgba({accent_rgb}, 0.30);
            }}
            QLabel#settings_test_subtitle {{
                color: {p['text_dim']};
                background: transparent;
            }}
            QWidget#settings_shortcut_card {{
                background: {p['bg_titlebar']};
                border: 1px solid {p['border_subtle']};
                border-radius: 8px;
            }}
            QLabel#settings_shortcut_key {{
                color: {p['text_dim']};
                background: transparent;
            }}
            QLabel#settings_shortcut_val {{
                color: {p['accent']};
                background: {p['bg_deeper']};
                border: 1px solid {p['border_active']};
                border-bottom: 2px solid {p['border_active']};
                border-radius: 5px;
                padding: 3px 10px;
            }}
            QLabel#settings_version {{
                color: {p['text_dim']};
                background: transparent;
            }}
            QWidget#settings_footer {{
                background: transparent;
            }}
            QLabel#settings_status {{
                background: transparent;
            }}
            QPushButton#settings_apply[state="inactive"] {{
                background: {p['bg_titlebar']};
                color: {p['text_dim']};
                border: none;
                border-radius: 6px;
            }}
            QPushButton#settings_apply[state="active"] {{
                background: {p['accent']};
                color: {p['toggled_text']};
                border: none;
                border-radius: 6px;
            }}
            QPushButton#settings_apply[state="active"]:hover {{
                background: {p['accent_light']};
            }}
            QPushButton#settings_apply[state="applied"] {{
                background: #4CAF50;
                color: #ffffff;
                border: none;
                border-radius: 6px;
            }}
            QPushButton#settings_more {{
                background: {p['bg_titlebar']};
                color: {p['text_dim']};
                border: none;
                border-radius: 6px;
            }}
            QPushButton#settings_more:hover {{
                background: {p['bg_medium']};
                color: {p['text']};
            }}
            QPushButton#settings_more:pressed {{
                background: rgba({accent_rgb}, 0.22);
            }}
            QPushButton#settings_more:disabled {{
                background: {p['bg_titlebar']};
                color: {p['text_dim']};
            }}
        """
        self.setStyleSheet(qss)

    def update_theme(self):
        """Re-apply theme to this panel and all open sub-panels."""
        self._apply_theme()
        if self._hotkey_panel:
            self._hotkey_panel._apply_theme()
        if self._model_panel:
            self._model_panel._apply_theme()
        if self._font_panel:
            self._font_panel._apply_theme()

    # ── Drag Support ──

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPosition().toPoint()
