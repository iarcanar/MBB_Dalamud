"""
ModelPanel (PyQt6) — Frameless AI model configuration matching MBB style.

Card-based layout: API Key · Model · Parameters · Trial Usage.
Trial lockdown (trial_config.TRIAL_PACK): when LOCK_MODEL / LOCK_PARAMETERS are set the
model dropdown becomes a read-only pill, the parameter sliders + RESET/APPLY are hidden,
so a trial user cannot accidentally degrade translation quality. The API-key card + usage
card are always shown.
"""
import logging
import webbrowser

from PyQt6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGraphicsDropShadowEffect, QComboBox, QSlider, QProgressBar, QLineEdit,
)
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtCore import Qt, QPoint, QTimer

from pyqt_ui.styles import FONT_PRIMARY, FONT_MONO, derive_palette
from api_key_manager import get_current_key, mask_key, validate_format, save_key

try:
    from trial_config import LOCK_MODEL, LOCK_PARAMETERS, FORCED_MODEL, FORCED_PARAMS
except Exception:
    LOCK_MODEL = False
    LOCK_PARAMETERS = False
    FORCED_MODEL = "gemini-3.1-flash-lite"
    FORCED_PARAMS = {"max_tokens": 500, "temperature": 0.8, "top_p": 0.9}

log = logging.getLogger("mbb-qt")

WIDTH = 420
HEIGHT = 620

AVAILABLE_MODELS = [
    "gemini-2.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-2.5-flash",
]

_MODEL_LABELS = {
    "gemini-2.5-flash-lite": "Gemini 2.5 Flash-Lite",
    "gemini-3.1-flash-lite": "Gemini 3.1 Flash-Lite",
    "gemini-2.5-flash": "Gemini 2.5 Flash",
}

PARAM_HINTS = {
    "max_tokens": "จำนวนคำตอบสูงสุด — ยิ่งมากยิ่งแปลได้ยาว  แนะนำ 500-1000",
    "temperature": "ความสร้างสรรค์ — ต่ำ=แปลตรง สูง=หลากหลาย  แนะนำ 0.70-0.80",
    "top_p": "ช่วงคำที่เลือกใช้ — ต่ำ=เฉพาะเจาะจง สูง=กว้าง  แนะนำ 0.90-0.95",
}


class ModelPanel(QWidget):
    """Frameless model settings panel — no PIN required."""

    def __init__(self, settings, appearance_manager, main_app=None):
        super().__init__()
        self.settings = settings
        self.am = appearance_manager
        self.main_app = main_app
        self.old_pos = QPoint()

        self.bg = None
        self.shadow = None
        self._model_combo = None
        self._sliders = {}       # key -> (QSlider, QLabel, display_scale)
        self._apply_btn = None
        self._status_label = None
        self._usage_label = None
        self._usage_bar = None
        self._usage_models_label = None

        # API key widgets
        self._key_field = None
        self._key_eye = None
        self._key_action = None
        self._key_status = None
        self._key_dot = None
        self._key_editing = False
        self._key_revealed = False

        self._usage_timer = QTimer(self)
        self._usage_timer.setInterval(5000)
        self._usage_timer.timeout.connect(self._refresh_usage)

        self._init_window()
        self._build_ui()
        self._apply_theme()
        self._load_current()

    def _init_window(self):
        self.setWindowTitle("AI Model Configuration")
        self.setFixedSize(WIDTH, HEIGHT)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    # ── Build ──

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)

        self.bg = QWidget()
        self.bg.setObjectName("model_bg")
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
        header.setObjectName("model_header")
        header.setFixedHeight(44)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(16, 0, 6, 0)

        title = QLabel("AI Model Configuration")
        title.setObjectName("model_title")
        title.setFont(QFont(FONT_PRIMARY, 11, QFont.Weight.Bold))
        h_layout.addWidget(title)
        h_layout.addStretch()

        btn_close = QPushButton("✕")
        btn_close.setObjectName("model_close")
        btn_close.setFixedSize(28, 28)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.clicked.connect(self.close)
        h_layout.addWidget(btn_close)

        main.addWidget(header)

        # Content
        content = QWidget()
        content.setObjectName("model_content")
        c = QVBoxLayout(content)
        c.setContentsMargins(16, 14, 16, 14)
        c.setSpacing(12)

        self._build_api_key_card(c)
        self._build_model_card(c)
        self._build_parameters_card(c)  # always shown; disabled (view-only) when locked
        self._build_usage_card(c)

        c.addStretch()
        main.addWidget(content, stretch=1)

        # Footer — only when something is editable (hidden in a fully-locked trial)
        if not (LOCK_MODEL and LOCK_PARAMETERS):
            main.addWidget(self._build_footer())

    def _card(self, parent_layout, title):
        """Create a titled card frame; return its inner vertical layout."""
        card = QFrame()
        card.setObjectName("model_card")
        v = QVBoxLayout(card)
        v.setContentsMargins(12, 10, 12, 12)
        v.setSpacing(7)
        lbl = QLabel(title)
        lbl.setObjectName("model_section")
        lbl.setFont(QFont(FONT_PRIMARY, 9, QFont.Weight.Bold))
        v.addWidget(lbl)
        parent_layout.addWidget(card)
        return v

    def _build_api_key_card(self, parent_layout):
        v = self._card(parent_layout, "API KEY")

        row = QHBoxLayout()
        row.setSpacing(4)

        self._key_field = QLineEdit()
        self._key_field.setObjectName("model_key_field")
        self._key_field.setReadOnly(True)
        self._key_field.setFont(QFont(FONT_MONO, 9))
        self._key_field.returnPressed.connect(self._save_key)
        row.addWidget(self._key_field, stretch=1)

        self._key_eye = QPushButton("👁")
        self._key_eye.setObjectName("model_icon_btn")
        self._key_eye.setFixedSize(30, 28)
        self._key_eye.setCursor(Qt.CursorShape.PointingHandCursor)
        self._key_eye.setToolTip("แสดง / ซ่อน API Key")
        self._key_eye.clicked.connect(self._toggle_key_reveal)
        row.addWidget(self._key_eye)

        self._key_action = QPushButton("✎")
        self._key_action.setObjectName("model_icon_btn")
        self._key_action.setFixedSize(30, 28)
        self._key_action.setCursor(Qt.CursorShape.PointingHandCursor)
        self._key_action.setToolTip("แก้ไข API Key")
        self._key_action.clicked.connect(self._on_key_action)
        row.addWidget(self._key_action)

        v.addLayout(row)

        bottom = QHBoxLayout()
        bottom.setSpacing(6)
        self._key_dot = QLabel("●")
        self._key_dot.setObjectName("model_key_dot")
        bottom.addWidget(self._key_dot)
        self._key_status = QLabel("")
        self._key_status.setObjectName("model_key_status")
        self._key_status.setFont(QFont(FONT_PRIMARY, 8))
        bottom.addWidget(self._key_status, stretch=1)

        link = QPushButton("เปิด Google AI Studio")
        link.setObjectName("model_link")
        link.setFont(QFont(FONT_PRIMARY, 8))
        link.setCursor(Qt.CursorShape.PointingHandCursor)
        link.clicked.connect(lambda: webbrowser.open("https://aistudio.google.com/app/apikey"))
        bottom.addWidget(link)

        v.addLayout(bottom)

    def _build_model_card(self, parent_layout):
        v = self._card(parent_layout, "MODEL")
        if LOCK_MODEL:
            pill = QLabel(f"{_MODEL_LABELS.get(FORCED_MODEL, FORCED_MODEL)}   ✓ แนะนำ")
            pill.setObjectName("model_pill")
            pill.setFont(QFont(FONT_PRIMARY, 10, QFont.Weight.Bold))
            v.addWidget(pill)
        else:
            self._model_combo = QComboBox()
            self._model_combo.setObjectName("model_combo")
            self._model_combo.setFont(QFont(FONT_PRIMARY, 10))
            self._model_combo.addItems(AVAILABLE_MODELS)
            self._model_combo.setFixedHeight(30)
            v.addWidget(self._model_combo)

    def _build_parameters_card(self, parent_layout):
        title = "PARAMETERS"
        if LOCK_PARAMETERS:
            title = "PARAMETERS   🔒 ล็อก (แสดงอย่างเดียว)"
        v = self._card(parent_layout, title)
        self._add_slider(v, "max_tokens", "Max Tokens", 100, 2000, 50, 500, fmt="{:.0f}")
        self._add_slider(v, "temperature", "Temperature", 0, 100, 5, 80,
                         display_scale=0.01, fmt="{:.2f}")
        self._add_slider(v, "top_p", "Top P", 0, 100, 5, 90,
                         display_scale=0.01, fmt="{:.2f}")
        if LOCK_PARAMETERS:
            # View-only: keep values visible but block dragging (dev/full build can edit).
            for slider, _, _ in self._sliders.values():
                slider.setEnabled(False)

    def _build_usage_card(self, parent_layout):
        v = self._card(parent_layout, "การใช้งาน Token (Trial Usage)")

        self._usage_label = QLabel("—")
        self._usage_label.setObjectName("model_usage_label")
        self._usage_label.setFont(QFont(FONT_MONO, 9))
        v.addWidget(self._usage_label)

        self._usage_bar = QProgressBar()
        self._usage_bar.setObjectName("model_usage_bar")
        self._usage_bar.setTextVisible(False)
        self._usage_bar.setFixedHeight(8)
        v.addWidget(self._usage_bar)

        self._usage_models_label = QLabel("")
        self._usage_models_label.setObjectName("model_usage_models")
        self._usage_models_label.setFont(QFont(FONT_PRIMARY, 8))
        self._usage_models_label.setWordWrap(True)
        v.addWidget(self._usage_models_label)

    def _build_footer(self):
        footer = QWidget()
        footer.setObjectName("model_footer")
        f = QHBoxLayout(footer)
        f.setContentsMargins(16, 6, 16, 12)
        f.setSpacing(8)

        btn_reset = QPushButton("RESET")
        btn_reset.setObjectName("model_btn")
        btn_reset.setFont(QFont(FONT_PRIMARY, 9, QFont.Weight.Bold))
        btn_reset.setFixedHeight(32)
        btn_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_reset.clicked.connect(self._reset_defaults)
        f.addWidget(btn_reset)

        self._status_label = QLabel("")
        self._status_label.setObjectName("model_status")
        self._status_label.setFont(QFont(FONT_PRIMARY, 8))
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        f.addWidget(self._status_label, stretch=1)

        self._apply_btn = QPushButton("APPLY")
        self._apply_btn.setObjectName("model_apply")
        self._apply_btn.setFont(QFont(FONT_PRIMARY, 9, QFont.Weight.Bold))
        self._apply_btn.setFixedHeight(32)
        self._apply_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._apply_btn.clicked.connect(self._on_apply)
        f.addWidget(self._apply_btn)

        return footer

    # ── Helpers ──

    def _add_slider(self, layout, key, label, min_v, max_v, step, default,
                    display_scale=1.0, fmt="{}"):
        row = QHBoxLayout()
        row.setSpacing(6)

        lbl = QLabel(label)
        lbl.setObjectName("model_param_label")
        lbl.setFont(QFont(FONT_PRIMARY, 9))
        lbl.setMinimumWidth(80)
        row.addWidget(lbl)

        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setObjectName("model_slider")
        slider.setMinimum(min_v)
        slider.setMaximum(max_v)
        slider.setSingleStep(step)
        slider.setValue(default)
        row.addWidget(slider, stretch=1)

        val_lbl = QLabel(fmt.format(default * display_scale))
        val_lbl.setObjectName("model_param_value")
        val_lbl.setFont(QFont(FONT_MONO, 9, QFont.Weight.Bold))
        val_lbl.setMinimumWidth(44)
        val_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(val_lbl)

        slider.valueChanged.connect(
            lambda v: val_lbl.setText(fmt.format(v * display_scale))
        )

        layout.addLayout(row)

        hint = PARAM_HINTS.get(key, "")
        if hint:
            hint_lbl = QLabel(hint)
            hint_lbl.setObjectName("model_hint")
            hint_lbl.setFont(QFont(FONT_PRIMARY, 8))
            hint_lbl.setWordWrap(True)
            layout.addWidget(hint_lbl)

        self._sliders[key] = (slider, val_lbl, display_scale)

    # ── API key ──

    def _refresh_key_display(self):
        self._key_editing = False
        self._key_revealed = False
        key = get_current_key()
        self._key_field.setReadOnly(True)
        self._key_field.setEchoMode(QLineEdit.EchoMode.Normal)
        self._key_field.setPlaceholderText("")
        self._key_field.setText(mask_key(key) if key else "(ยังไม่ได้ตั้งค่า)")
        self._key_action.setText("✎")
        self._key_action.setToolTip("แก้ไข API Key")
        self._key_eye.setEnabled(bool(key))

        ok = bool(key) and validate_format(key)[0]
        self._key_dot.setStyleSheet(
            f"color: {'#3fa15a' if ok else '#cc4444'}; background: transparent;"
        )
        self._set_key_status("เชื่อมต่อแล้ว" if ok else "ยังไม่มี API Key", ok=ok)

    def _toggle_key_reveal(self):
        if self._key_editing:
            self._key_revealed = not self._key_revealed
            self._key_field.setEchoMode(
                QLineEdit.EchoMode.Normal if self._key_revealed else QLineEdit.EchoMode.Password
            )
        else:
            self._key_revealed = not self._key_revealed
            key = get_current_key()
            if key:
                self._key_field.setText(key if self._key_revealed else mask_key(key))

    def _on_key_action(self):
        if not self._key_editing:
            # enter edit mode
            self._key_editing = True
            self._key_revealed = False
            self._key_field.setReadOnly(False)
            self._key_field.setEchoMode(QLineEdit.EchoMode.Password)
            self._key_field.clear()
            self._key_field.setPlaceholderText("วาง API Key ใหม่ที่นี่")
            self._key_field.setFocus()
            self._key_eye.setEnabled(True)
            self._key_action.setText("💾")
            self._key_action.setToolTip("บันทึก API Key")
            self._set_key_status("วาง key แล้วกด 💾 หรือ Enter", ok=True)
        else:
            self._save_key()

    def _save_key(self):
        if not self._key_editing:
            return
        key = self._key_field.text().strip()
        ok, msg = validate_format(key)
        if not ok:
            self._set_key_status(msg, ok=False)
            self._key_field.setFocus()
            return
        saved, err = save_key(key)
        if not saved:
            self._set_key_status(f"บันทึกไม่ได้: {err}", ok=False)
            return
        # apply to live translator without restart
        if self.main_app and hasattr(self.main_app, "reload_api_key"):
            self.main_app.reload_api_key()
        self._refresh_key_display()
        self._set_key_status("✓ บันทึกและใช้งานทันที", ok=True)

    def _set_key_status(self, msg, ok=True):
        if self._key_status:
            self._key_status.setStyleSheet(
                f"color: {'#3fa15a' if ok else '#cc4444'}; background: transparent;"
            )
            self._key_status.setText(msg)

    # ── Data ──

    def _load_current(self):
        params = self.settings.get_api_parameters()

        if self._model_combo is not None:
            model = params.get("model", FORCED_MODEL)
            idx = self._model_combo.findText(model)
            if idx >= 0:
                self._model_combo.setCurrentIndex(idx)

        if self._sliders:
            src = FORCED_PARAMS if LOCK_PARAMETERS else params
            self._set_slider("max_tokens", src.get("max_tokens", 500))
            self._set_slider("temperature", src.get("temperature", 0.8), scale=100)
            self._set_slider("top_p", src.get("top_p", 0.9), scale=100)

        self._refresh_key_display()

    def _set_slider(self, key, value, scale=1):
        if key in self._sliders:
            slider, _, _ = self._sliders[key]
            slider.setValue(int(value * scale))

    # ── Usage ──

    def _get_tracker(self):
        if self.main_app and getattr(self.main_app, "translator", None) is not None:
            return getattr(self.main_app.translator, "usage_tracker", None)
        return None

    @staticmethod
    def _fmt_tokens(n):
        """ย่อจำนวน token ด้วย k เพื่อไม่ให้รก: 768 / 1.5k / 12.3k / 100k"""
        n = int(n or 0)
        if n < 1000:
            return str(n)
        if n < 100000:
            s = f"{n / 1000.0:.1f}".rstrip("0").rstrip(".")
            return f"{s}k"
        return f"{round(n / 1000)}k"

    def _refresh_usage(self):
        if self._usage_label is None:
            return
        tracker = self._get_tracker()
        if tracker is None:
            self._usage_label.setText("ยังไม่เริ่มการแปล")
            self._usage_bar.setRange(0, 1)
            self._usage_bar.setValue(0)
            self._usage_models_label.setText("")
            return

        snap = tracker.snapshot()
        used = snap.get("total_tokens", 0)
        limit = snap.get("trial_limit", 0)
        reqs = snap.get("total_requests", 0)

        if snap.get("tampered"):
            self._usage_label.setText("⚠️ พบการแก้ไขข้อมูล — ระบบถูกล็อก")
            self._usage_label.setStyleSheet("color: #cc4444;")
            self._usage_bar.setRange(0, 1)
            self._usage_bar.setValue(1)
            self._usage_bar.setStyleSheet(
                "QProgressBar#model_usage_bar::chunk { background: #cc4444; "
                "border-radius: 4px; }"
            )
            self._usage_models_label.setText("ติดต่อผู้พัฒนา หรือติดตั้งใหม่")
            return

        self._usage_label.setStyleSheet("")  # clear any prior tamper-red
        if limit and limit > 0:
            pct = min(100, int(used * 100 / limit)) if limit else 0
            self._usage_label.setText(
                f"ใช้ไป {self._fmt_tokens(used)} / {self._fmt_tokens(limit)} tokens  ({pct}%)"
            )
            self._usage_bar.setRange(0, limit)
            self._usage_bar.setValue(min(used, limit))
            if pct >= 100:
                chunk = "#cc4444"
            elif pct >= 80:
                chunk = "#e0a030"
            else:
                chunk = "#3fa15a"
            self._usage_bar.setStyleSheet(
                f"QProgressBar#model_usage_bar::chunk {{ background: {chunk}; "
                f"border-radius: 4px; }}"
            )
        else:
            self._usage_label.setText(
                f"ใช้ไป {self._fmt_tokens(used)} tokens  ·  {reqs:,} ครั้ง  (ไม่จำกัด)"
            )
            self._usage_bar.setRange(0, 1)
            self._usage_bar.setValue(0)

        parts = []
        for m, d in (snap.get("per_model") or {}).items():
            short = m.replace("gemini-", "")
            parts.append(f"{short}: {self._fmt_tokens(d.get('tokens', 0))}")
        self._usage_models_label.setText("  ·  ".join(parts))

    def showEvent(self, event):
        super().showEvent(event)
        self._refresh_key_display()
        self._refresh_usage()
        self._usage_timer.start()

    def hideEvent(self, event):
        self._usage_timer.stop()
        super().hideEvent(event)

    # ── Apply / Reset (full mode only) ──

    def _on_apply(self):
        try:
            model = self._model_combo.currentText() if self._model_combo else FORCED_MODEL

            if self._sliders:
                max_tokens = self._sliders["max_tokens"][0].value()
                temperature = self._sliders["temperature"][0].value() * self._sliders["temperature"][2]
                top_p = self._sliders["top_p"][0].value() * self._sliders["top_p"][2]
            else:
                max_tokens = FORCED_PARAMS["max_tokens"]
                temperature = FORCED_PARAMS["temperature"]
                top_p = FORCED_PARAMS["top_p"]

            api_params = {
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "top_p": top_p,
                "role_mode": "rpg_general",
            }

            self.settings.validate_model_parameters(api_params)

            success, error = self.settings.set_api_parameters(**api_params)
            if not success:
                raise ValueError(error)

            self.settings.save_settings()

            if self.main_app and hasattr(self.main_app, "update_api_settings"):
                self.main_app.update_api_settings()

            if self.main_app and hasattr(self.main_app, "translator"):
                if self.main_app.translator and hasattr(self.main_app.translator, "set_role_mode"):
                    self.main_app.translator.set_role_mode("rpg_general")

            self._show_status("Applied!")
            self._apply_btn.setText("✓ Applied")
            QTimer.singleShot(2000, lambda: self._apply_btn.setText("APPLY"))

        except Exception as e:
            log.error(f"Model apply failed: {e}")
            self._show_status(str(e), error=True)

    def _reset_defaults(self):
        if self._model_combo is not None:
            idx = self._model_combo.findText(FORCED_MODEL)
            if idx >= 0:
                self._model_combo.setCurrentIndex(idx)
        self._set_slider("max_tokens", FORCED_PARAMS["max_tokens"])
        self._set_slider("temperature", FORCED_PARAMS["temperature"], scale=100)
        self._set_slider("top_p", FORCED_PARAMS["top_p"], scale=100)
        self._show_status("Reset to defaults")

    def _show_status(self, text, error=False):
        if self._status_label:
            color = "#cc4444" if error else "#4CAF50"
            self._status_label.setStyleSheet(f"color: {color}; background: transparent;")
            self._status_label.setText(text)
            QTimer.singleShot(3000, lambda: self._status_label.setText(""))

    # ── Theming ──

    def _apply_theme(self):
        primary = self.am.get_accent_color()
        secondary = self.am.get_theme_color("secondary", "#888888")
        p = derive_palette(primary, secondary)

        qss = f"""
            QWidget#model_bg {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {p['bg']}, stop:1 {p['bg_deeper']});
                border-radius: 10px;
                border: 1px solid {p['border_subtle']};
            }}
            QWidget#model_header {{
                background: {p['bg_titlebar']};
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }}
            QLabel#model_title {{
                color: {p['text']};
                background: transparent;
            }}
            QPushButton#model_close {{
                background: transparent;
                border: none; border-radius: 4px;
                color: {p['text_dim']}; font-size: 13px; font-weight: bold;
            }}
            QPushButton#model_close:hover {{
                background: #cc4444; color: #ffffff;
            }}
            QWidget#model_content {{
                background: transparent;
            }}
            QFrame#model_card {{
                background: {p['bg_titlebar']};
                border: 1px solid {p['border_subtle']};
                border-radius: 8px;
            }}
            QLabel#model_section {{
                color: {p['text_dim']};
                background: transparent;
            }}
            QLabel#model_pill {{
                color: {p['accent']};
                background: {p['bg_medium']};
                border: 1px solid {p['border_active']};
                border-radius: 6px;
                padding: 7px 12px;
            }}
            QLineEdit#model_key_field {{
                background: {p['bg']};
                color: {p['text']};
                border: 1px solid {p['border_subtle']};
                border-radius: 5px;
                padding: 6px 9px;
                selection-background-color: {p['accent']};
            }}
            QLineEdit#model_key_field:focus {{
                border: 1px solid {p['accent']};
            }}
            QPushButton#model_icon_btn {{
                background: {p['btn_bg']};
                color: {p['text']};
                border: 1px solid {p['border_subtle']};
                border-radius: 5px;
                font-size: 13px;
            }}
            QPushButton#model_icon_btn:hover {{
                background: {p['bg_medium']};
                border: 1px solid {p['border_active']};
            }}
            QLabel#model_key_dot {{
                background: transparent;
                font-size: 10px;
            }}
            QLabel#model_key_status {{
                background: transparent;
            }}
            QPushButton#model_link {{
                background: transparent;
                color: {p['accent']};
                border: none;
                text-align: right;
            }}
            QPushButton#model_link:hover {{
                color: {p['accent_light']};
                text-decoration: underline;
            }}
            QComboBox#model_combo {{
                background: {p['bg']};
                color: {p['text']};
                border: 1px solid {p['border_subtle']};
                border-radius: 4px;
                padding: 4px 8px;
            }}
            QComboBox#model_combo::drop-down {{
                border: none;
                width: 24px;
            }}
            QComboBox#model_combo::down-arrow {{
                width: 0px; height: 0px;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid {p['text']};
            }}
            QComboBox#model_combo QAbstractItemView {{
                background: {p['bg_titlebar']};
                color: {p['text']};
                selection-background-color: {p['bg_medium']};
                border: 1px solid {p['border_subtle']};
            }}
            QLabel#model_param_label {{
                color: {p['text']};
                background: transparent;
            }}
            QLabel#model_param_value {{
                color: {p['accent']};
                background: transparent;
            }}
            QLabel#model_hint {{
                color: {p['text_dim']};
                background: transparent;
                padding-left: 4px;
            }}
            QLabel#model_usage_label {{
                color: {p['text']};
                background: transparent;
            }}
            QLabel#model_usage_models {{
                color: {p['text_dim']};
                background: transparent;
                padding-left: 2px;
            }}
            QProgressBar#model_usage_bar {{
                background: {p['bg']};
                border: none;
                border-radius: 4px;
            }}
            QProgressBar#model_usage_bar::chunk {{
                background: {p['accent']};
                border-radius: 4px;
            }}
            QSlider#model_slider::groove:horizontal {{
                border: none;
                height: 4px;
                background: {p['bg']};
                border-radius: 2px;
            }}
            QSlider#model_slider::handle:horizontal {{
                background: {p['accent']};
                border: none;
                width: 14px; height: 14px;
                margin: -5px 0;
                border-radius: 7px;
            }}
            QSlider#model_slider::sub-page:horizontal {{
                background: {p['accent']};
                border-radius: 2px;
            }}
            QSlider#model_slider:disabled::handle:horizontal {{
                background: {p['text_dim']};
            }}
            QSlider#model_slider:disabled::sub-page:horizontal {{
                background: {p['border_active']};
            }}
            QWidget#model_footer {{
                background: transparent;
            }}
            QPushButton#model_btn {{
                background: {p['btn_bg']};
                color: {p['text']};
                border: 1px solid {p['border_subtle']};
                border-radius: 4px;
            }}
            QPushButton#model_btn:hover {{
                background: {p['bg_medium']};
                border: 1px solid {p['border_active']};
            }}
            QPushButton#model_apply {{
                background: {p['accent']};
                color: {p['toggled_text']};
                border: none;
                border-radius: 4px;
            }}
            QPushButton#model_apply:hover {{
                background: {p['accent_light']};
            }}
            QLabel#model_status {{
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
