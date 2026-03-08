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
)
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtCore import Qt, QPoint, QTimer

from pyqt_ui.styles import FONT_PRIMARY, FONT_MONO, derive_palette

log = logging.getLogger("mbb-qt")

WIDTH = 300
HEIGHT = 520


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
        self._toggles = {}       # key -> QCheckBox
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
        header.setFixedHeight(44)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(14, 0, 6, 0)
        h_layout.setSpacing(4)

        title = QLabel("SETTINGS")
        title.setObjectName("settings_title")
        title.setFont(QFont(FONT_PRIMARY, 11, QFont.Weight.Bold))
        h_layout.addWidget(title)
        h_layout.addStretch()

        btn_close = QPushButton("\u2715")
        btn_close.setObjectName("settings_close")
        btn_close.setFixedSize(28, 28)
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

        # Section: Feature Toggles
        self._add_section_label(c_layout, "Feature Toggles")
        self._add_toggle(c_layout, "enable_wasd_auto_hide",
                         "Auto-hide UI (WASD)", False)
        self._add_toggle(c_layout, "enable_cpu_monitoring",
                         "Smart Performance", True)
        self._add_toggle(c_layout, "enable_tui_auto_show",
                         "Auto Show TUI", True)
        self._add_toggle(c_layout, "enable_battle_chat_mode",
                         "Battle Chat Mode", True)
        self._add_toggle(c_layout, "enable_conversation_logging",
                         "Conversation Log", False)

        c_layout.addSpacing(4)

        # Section: Advanced
        self._add_section_label(c_layout, "Advanced")
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

        # Section: Test Hook
        self._add_section_label(c_layout, "Test Hook")
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

        # Section: Shortcuts
        self._add_section_label(c_layout, "Shortcuts")
        shortcuts_row = QHBoxLayout()
        shortcuts_row.setSpacing(8)

        shortcuts_row.addWidget(self._make_shortcut_label("Toggle UI:"))
        self._shortcut_toggle_lbl = self._make_shortcut_value(
            self.settings.get_shortcut("toggle_ui", "alt+l").upper()
        )
        shortcuts_row.addWidget(self._shortcut_toggle_lbl)
        shortcuts_row.addSpacing(8)
        shortcuts_row.addWidget(self._make_shortcut_label("Start/Stop:"))
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
        ver_label.setFont(QFont(FONT_PRIMARY, 8))
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
        self._status_label.setFont(QFont(FONT_PRIMARY, 8))
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        f_layout.addWidget(self._status_label)

        self._apply_btn = QPushButton("APPLY")
        self._apply_btn.setObjectName("settings_apply")
        self._apply_btn.setFont(QFont(FONT_PRIMARY, 10, QFont.Weight.Bold))
        self._apply_btn.setFixedHeight(34)
        self._apply_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._apply_btn.setEnabled(False)
        self._apply_btn.setProperty("state", "inactive")
        self._apply_btn.clicked.connect(self._on_apply)
        f_layout.addWidget(self._apply_btn)

        main.addWidget(footer)

    # ── Widget Factories ──

    def _add_section_label(self, layout, text):
        lbl = QLabel(text)
        lbl.setObjectName("settings_section")
        lbl.setFont(QFont(FONT_PRIMARY, 9, QFont.Weight.Bold))
        layout.addWidget(lbl)

    def _add_toggle(self, layout, key, label, default):
        row = QHBoxLayout()
        row.setSpacing(8)

        lbl = QLabel(label)
        lbl.setObjectName("settings_toggle_label")
        lbl.setFont(QFont(FONT_PRIMARY, 9))
        row.addWidget(lbl, stretch=1)

        cb = QCheckBox()
        cb.setObjectName("settings_toggle")
        cb.setChecked(self.settings.get(key, default))
        cb.stateChanged.connect(lambda state, k=key: self._on_toggle_changed(k))
        row.addWidget(cb)

        layout.addLayout(row)
        self._toggles[key] = cb

    def _make_section_btn(self, text):
        btn = QPushButton(text)
        btn.setObjectName("settings_section_btn")
        btn.setFont(QFont(FONT_PRIMARY, 9, QFont.Weight.Bold))
        btn.setFixedHeight(30)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        return btn

    def _make_test_btn(self, text, subtitle, handler):
        container = QWidget()
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(1)

        btn = QPushButton(text)
        btn.setObjectName("settings_test_btn")
        btn.setFont(QFont(FONT_PRIMARY, 9))
        btn.setFixedHeight(26)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(handler)
        v.addWidget(btn)

        sub = QLabel(subtitle)
        sub.setObjectName("settings_test_subtitle")
        sub.setFont(QFont(FONT_MONO, 7))
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(sub)

        return container

    def _make_shortcut_label(self, text):
        lbl = QLabel(text)
        lbl.setObjectName("settings_shortcut_key")
        lbl.setFont(QFont(FONT_PRIMARY, 8))
        return lbl

    def _make_shortcut_value(self, text):
        lbl = QLabel(text)
        lbl.setObjectName("settings_shortcut_val")
        lbl.setFont(QFont(FONT_MONO, 8, QFont.Weight.Bold))
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setMinimumWidth(50)
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
        ("Tataru", "Welcome back, adventurer! How may I assist you today?"),
        ("Alphinaud", "We must528 consider our next course of action carefully."),
        ("Alisaie", "Enough talk. Let's get moving before they notice us."),
        ("Thancred", "I've scouted ahead. The path through Garlemald is clear."),
        ("Y'shtola", "The aether here is unusually dense. Pray, be on your guard."),
        ("G'raha Tia", "This reminds me of a tale from the Crystal Tower archives."),
    ]

    _TEST_BATTLE = [
        ("Gaius", "The weak shall be consumed by the strong!"),
        ("Zenos", "Yes! Finally, a foe worthy of my blade!"),
        ("Nidhogg", "Thou shalt pay for the sins of Ishgard, mortal!"),
        ("Emet-Selch", "Such devastation... this was not my intention."),
        ("Sephirot", "I shall crush you beneath the weight of my power!"),
        ("???", "You cannot escape your fate, Warrior of Light."),
    ]

    _TEST_CUTSCENE = [
        ("Hydaelyn", "Hear... Feel... Think... Your journey has only just begun."),
        ("Venat", "The future is not yet written. Walk ever forward, my friend."),
        ("Meteion", "Why do people continue to live, knowing they will one day die?"),
        ("Emet-Selch", "Remember us. Remember that we once lived."),
        ("Hythlodaeus", "You remind me of someone I once knew. How very curious."),
        ("Wuk Lamat", "I want to build a world where everyone can smile together!"),
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
        p = derive_palette(primary, secondary)

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
            QCheckBox#settings_toggle {{
                background: transparent;
                spacing: 0px;
            }}
            QCheckBox#settings_toggle::indicator {{
                width: 36px;
                height: 18px;
                border-radius: 9px;
                border: 1px solid {p['border_subtle']};
                background: {p['bg_titlebar']};
            }}
            QCheckBox#settings_toggle::indicator:checked {{
                background: {p['accent']};
                border: 1px solid {p['accent']};
            }}
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
