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
    QSizePolicy,
)
from PyQt6.QtGui import QColor, QFont, QPainter, QBrush, QPen
from PyQt6.QtCore import (
    Qt, QPoint, QTimer, QPropertyAnimation, QEasingCurve,
    pyqtProperty, pyqtSignal, QRectF, QSize,
)

from pyqt_ui.styles import FONT_PRIMARY, FONT_MONO, derive_palette

log = logging.getLogger("mbb-qt")

WIDTH = 360    # bumped from 300 (+20%) for easier reading
HEIGHT = 624   # bumped from 520 (+20%) — proportional to width


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
        ]:
            test_row.addWidget(self._make_test_btn(label, subtitle, handler))

        c_layout.addLayout(test_row)
        c_layout.addSpacing(4)

        # Section: Shortcuts → "ปุ่มลัด"
        self._add_section_label(c_layout, "ปุ่มลัด")
        shortcuts_row = QHBoxLayout()
        shortcuts_row.setSpacing(8)

        shortcuts_row.addWidget(self._make_shortcut_label("เปิด/ปิด UI:"))
        self._shortcut_toggle_lbl = self._make_shortcut_value(
            self.settings.get_shortcut("toggle_ui", "alt+l").upper()
        )
        shortcuts_row.addWidget(self._shortcut_toggle_lbl)
        shortcuts_row.addSpacing(8)
        shortcuts_row.addWidget(self._make_shortcut_label("เริ่ม/หยุด:"))
        self._shortcut_start_lbl = self._make_shortcut_value(
            self.settings.get_shortcut("start_stop_translate", "f9").upper()
        )
        shortcuts_row.addWidget(self._shortcut_start_lbl)
        shortcuts_row.addStretch()

        c_layout.addLayout(shortcuts_row)

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
        f_layout.addWidget(self._apply_btn)

        self._restart_btn = QPushButton("RESTART APP")
        self._restart_btn.setObjectName("settings_restart")
        self._restart_btn.setFont(QFont(FONT_PRIMARY, 11, QFont.Weight.Bold))  # +20% from 9pt
        self._restart_btn.setFixedHeight(36)  # +20% from 30
        self._restart_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._restart_btn.clicked.connect(self._on_restart_clicked)
        f_layout.addWidget(self._restart_btn)

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

    def _make_shortcut_label(self, text):
        lbl = QLabel(text)
        lbl.setObjectName("settings_shortcut_key")
        lbl.setFont(QFont(FONT_PRIMARY, 10))  # +20% from 8pt
        return lbl

    def _make_shortcut_value(self, text):
        lbl = QLabel(text)
        lbl.setObjectName("settings_shortcut_val")
        lbl.setFont(QFont(FONT_MONO, 10, QFont.Weight.Bold))  # +20% from 8pt
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setMinimumWidth(60)  # +20% from 50
        return lbl

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

    # ── Restart ──

    def _on_restart_clicked(self):
        self._restart_btn.setEnabled(False)
        self._restart_countdown = 3
        self._restart_btn.setText(f"Restarting in {self._restart_countdown}...")
        self._status_label.setStyleSheet("color: #FF8C00; background: transparent;")
        self._status_label.setText("Application will restart shortly...")
        self._restart_timer = QTimer()
        self._restart_timer.timeout.connect(self._restart_tick)
        self._restart_timer.start(1000)

    def _restart_tick(self):
        self._restart_countdown -= 1
        if self._restart_countdown > 0:
            self._restart_btn.setText(f"Restarting in {self._restart_countdown}...")
        else:
            self._restart_timer.stop()
            self._restart_btn.setText("Restarting...")
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
            self._hotkey_panel = HotkeyPanel(
                self.settings, self.update_hotkeys_callback, self.am
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
        ("Tataru", "Oh, welcome back! I've been looking into some new business ventures while you were away. Don't worry, I'll handle all the paperwork!"),
        ("Alphinaud", "We cannot afford to act in haste. Let us gather what intelligence we can before committing to a course of action."),
        ("Alisaie", "Standing around deliberating won't save anyone. If you won't act, I will."),
        ("Thancred", "I make no claims to heroism. I simply528 go where I'm needed and do what must be done."),
        ("Y'shtola", "The aetherial currents here are... wrong. Something has disturbed the natural flow. We must tread carefully."),
        ("G'raha Tia", "To think I would one day stand beside the Warrior of Light, not as an observer, but as a comrade. It is more than I ever dared dream."),
        ("Estinien", "Save your sentiments for after the battle. The enemy will not wait for us to finish reminiscing."),
        ("Urianger", "The stars foretell a confluence of fates. What was sundered shall be made whole, yet the path remaineth shrouded."),
        ("Krile", "Grandfather always said that the truest measure of a person is not their strength, but their willingness to lend it to others."),
        ("Wuk Lamat", "Everyone deserves to live with a smile on their face. That's the kind of leader I want to be!"),
    ]

    _TEST_BATTLE = [
        ("Zenos", "Yes! More! Show me your fury!"),
        ("Nidhogg", "Thy sins shall be paid in blood!"),
        ("Emet-Selch", "Such a disappointment."),
        ("Sephirot", "Kneel before my might!"),
        ("Thordan VII", "By Halone's grace, I shall strike you down!"),
        ("???", "You cannot escape your fate, Warrior of Light."),
    ]

    _TEST_CUTSCENE = [
        ("", "Hear... Feel... Think... Crystal bearer, your journey has only just begun."),
        ("", "The night sky stretched endlessly above the Source, a thousand thousand stars bearing silent witness to the tale about to unfold."),
        ("", "And so it was that the Warrior of Light set forth once more, guided by hope and burdened by duty, into the unknown."),
        ("", "In that moment, the weight of every sacrifice, every loss, every hard-won victory pressed upon your heart like a prayer."),
        ("", "The crystal's light flickered, and with it, the last echo of a world that once was."),
        ("", "Remember us. Remember that we once lived."),
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
        if self._shortcut_toggle_lbl:
            self._shortcut_toggle_lbl.setText(
                self.settings.get_shortcut("toggle_ui", "alt+l").upper()
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
                background: {p['bg_medium']};
                border: 1px solid {p['border_active']};
            }}
            QPushButton#settings_test_btn {{
                background: {p['btn_bg']};
                color: {p['text']};
                border: 1px solid {p['border_subtle']};
                border-radius: 4px;
            }}
            QPushButton#settings_test_btn:hover {{
                background: {p['bg_medium']};
                border: 1px solid {p['border_active']};
            }}
            QLabel#settings_test_subtitle {{
                color: {p['text_dim']};
                background: transparent;
            }}
            QLabel#settings_shortcut_key {{
                color: {p['text_dim']};
                background: transparent;
            }}
            QLabel#settings_shortcut_val {{
                color: {p['text']};
                background: {p['bg_titlebar']};
                border: 1px solid {p['border_subtle']};
                border-radius: 3px;
                padding: 2px 6px;
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
            QPushButton#settings_restart {{
                background: transparent;
                color: {p['text_dim']};
                border: 1px solid {p['border_subtle']};
                border-radius: 6px;
            }}
            QPushButton#settings_restart:hover {{
                background: rgba(204, 68, 68, 0.15);
                color: #ff6b6b;
                border: 1px solid rgba(204, 68, 68, 0.5);
            }}
            QPushButton#settings_restart:disabled {{
                background: {p['bg_titlebar']};
                color: #FF8C00;
                border: 1px solid rgba(255, 140, 0, 0.4);
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
