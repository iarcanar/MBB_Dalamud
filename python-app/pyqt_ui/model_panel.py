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
    QStyle, QStyleOptionSlider,
)
from PyQt6.QtGui import QColor, QFont, QPainter, QIcon
from PyQt6.QtCore import Qt, QEvent, QPoint, QPointF, QRectF, QSize, QTimer

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
HEIGHT = 772   # settings-panel scale (bigger text + slider pip markers + hints)

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

# ── Parameter specs (REAL units) — UI range is intentionally NARROWER than the
# backend validators (settings.set_api_parameters: max_tokens 100-2000, temp/
# top_p 0.0-1.0). The slider only exposes the band that keeps translation
# quality good, so a user can't drag into a degrading value. `rec` = the
# recommended value (matches FORCED_PARAMS) the marker + RESET point to. Each
# slider runs in STEP-INDEX units (0..n) so every integer position is a snap
# stop → inherent "magnet" feel. ──
PARAM_SPECS = {
    "max_tokens":  {"lo": 400,  "hi": 1200, "step": 100,  "rec": 500,  "fmt": "{:.0f}", "label": "Max Tokens"},
    "temperature": {"lo": 0.50, "hi": 1.00, "step": 0.05, "rec": 0.80, "fmt": "{:.2f}", "label": "Temperature"},
    "top_p":       {"lo": 0.80, "hi": 1.00, "step": 0.05, "rec": 0.90, "fmt": "{:.2f}", "label": "Top P"},
}

PARAM_HINTS = {
    "max_tokens": "ความยาวคำแปลสูงสุด — สั้นไปจะตัดประโยคยาว  ·  แนะนำ 500",
    "temperature": "ความสร้างสรรค์ของคำแปล — ต่ำ=ตรงตัว สูง=หลากหลาย  ·  แนะนำ 0.80",
    "top_p": "ความหลากหลายของคำที่เลือกใช้  ·  แนะนำ 0.90",
}


def _spec_n(spec):
    """Number of snap steps (slider runs 0..n)."""
    return round((spec["hi"] - spec["lo"]) / spec["step"])


def _idx_to_real(spec, idx):
    """Step-index → real parameter value."""
    return spec["lo"] + idx * spec["step"]


def _real_to_idx(spec, real):
    """Real value → nearest in-range step-index (clamps out-of-band saved values)."""
    return max(0, min(_spec_n(spec), round((real - spec["lo"]) / spec["step"])))


class _MagnetSlider(QSlider):
    """Horizontal slider that runs in step-index units (each integer = one snap
    stop). FULLY self-painted — we deliberately do NOT call super().paintEvent
    so Qt never draws its default groove/sub-page/add-page subcontrols (those
    render as a tall grey block, and a QSS `background: transparent` won't
    suppress them). We draw a thin track + snap pips + an accent handle, with
    the recommended stop highlighted. Pairs with PARAM_SPECS."""

    def __init__(self, parent=None):
        super().__init__(Qt.Orientation.Horizontal, parent)
        self._rec_index = None
        self._pip_color = QColor("#555555")
        self._rec_color = QColor("#58a6ff")
        self._track_color = QColor("#222222")
        self._handle_color = QColor("#58a6ff")
        self.setMinimumHeight(30)

    def set_recommended(self, index):
        self._rec_index = index
        self.update()

    def set_marker_colors(self, accent_hex, pip_hex, track_hex):
        self._rec_color = QColor(accent_hex)
        self._handle_color = QColor(accent_hex)
        self._pip_color = QColor(pip_hex)
        self._track_color = QColor(track_hex)
        self.update()

    def paintEvent(self, event):
        opt = QStyleOptionSlider()
        self.initStyleOption(opt)
        groove = self.style().subControlRect(
            QStyle.ComplexControl.CC_Slider, opt,
            QStyle.SubControl.SC_SliderGroove, self)
        handle = self.style().subControlRect(
            QStyle.ComplexControl.CC_Slider, opt,
            QStyle.SubControl.SC_SliderHandle, self)
        span = groove.width() - handle.width()
        if span <= 0:
            return
        x0 = groove.x() + handle.width() // 2
        cy = float(groove.center().y())
        lo, hi = self.minimum(), self.maximum()

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)

        # Thin track (blends with the theme — no grey block)
        p.setBrush(self._track_color)
        p.drawRoundedRect(QRectF(x0, cy - 2, span, 4), 2, 2)

        # Snap pips below the track — ALL the same small size; the recommended
        # stop is distinguished by colour (accent) only, not size.
        pip_y = cy + 10
        pip_r = 1.6
        for idx in range(lo, hi + 1):
            x = x0 + QStyle.sliderPositionFromValue(lo, hi, idx, span)
            p.setBrush(self._rec_color if idx == self._rec_index else self._pip_color)
            p.drawEllipse(QPointF(float(x), float(pip_y)), pip_r, pip_r)

        # Handle
        hx = x0 + QStyle.sliderPositionFromValue(lo, hi, self.value(), span)
        p.setBrush(self._handle_color if self.isEnabled() else self._pip_color)
        p.drawEllipse(QPointF(float(hx), cy), 7.0, 7.0)
        p.end()


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
        self._sliders = {}       # key -> (_MagnetSlider, QLabel value, PARAM_SPECS spec)
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
        header.setFixedHeight(52)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(16, 0, 6, 0)

        title = QLabel("AI Model Configuration")
        title.setObjectName("model_title")
        title.setFont(QFont(FONT_PRIMARY, 13, QFont.Weight.Bold))
        h_layout.addWidget(title)
        h_layout.addStretch()

        btn_close = QPushButton("✕")
        btn_close.setObjectName("model_close")
        btn_close.setFixedSize(34, 34)
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
        lbl.setFont(QFont(FONT_PRIMARY, 11, QFont.Weight.Bold))
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
        self._key_field.setFont(QFont(FONT_MONO, 10))
        self._key_field.returnPressed.connect(self._save_key)
        row.addWidget(self._key_field, stretch=1)

        self._key_eye = QPushButton("👁")
        self._key_eye.setObjectName("model_icon_btn")
        self._key_eye.setFixedSize(34, 30)
        self._key_eye.setCursor(Qt.CursorShape.PointingHandCursor)
        self._key_eye.setToolTip("แสดง / ซ่อน API Key")
        self._key_eye.clicked.connect(self._toggle_key_reveal)
        row.addWidget(self._key_eye)

        self._key_action = QPushButton("✎")
        self._key_action.setObjectName("model_icon_btn")
        self._key_action.setFixedSize(34, 30)
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
        self._key_status.setFont(QFont(FONT_PRIMARY, 9))
        bottom.addWidget(self._key_status, stretch=1)

        link = QPushButton("เปิด Google AI Studio")
        link.setObjectName("model_link")
        link.setFont(QFont(FONT_PRIMARY, 9))
        link.setCursor(Qt.CursorShape.PointingHandCursor)
        link.clicked.connect(lambda: webbrowser.open("https://aistudio.google.com/app/apikey"))
        bottom.addWidget(link)

        v.addLayout(bottom)

    def _build_model_card(self, parent_layout):
        v = self._card(parent_layout, "MODEL")
        if LOCK_MODEL:
            pill = QLabel(f"{_MODEL_LABELS.get(FORCED_MODEL, FORCED_MODEL)}   ✓ แนะนำ")
            pill.setObjectName("model_pill")
            pill.setFont(QFont(FONT_PRIMARY, 11, QFont.Weight.Bold))
            v.addWidget(pill)
        else:
            self._model_combo = QComboBox()
            self._model_combo.setObjectName("model_combo")
            self._model_combo.setFont(QFont(FONT_PRIMARY, 12, QFont.Weight.Bold))
            self._model_combo.addItems(AVAILABLE_MODELS)
            self._model_combo.setFixedHeight(36)
            # Editable + read-only line edit → lets us centre the selected model
            # name prominently (a plain QComboBox can't centre its display text).
            self._model_combo.setEditable(True)
            le = self._model_combo.lineEdit()
            le.setReadOnly(True)
            le.setAlignment(Qt.AlignmentFlag.AlignCenter)
            le.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            le.setCursor(Qt.CursorShape.PointingHandCursor)
            le.installEventFilter(self)  # click the text (not just arrow) → open popup
            v.addWidget(self._model_combo)

    def _build_parameters_card(self, parent_layout):
        title = "PARAMETERS"
        if LOCK_PARAMETERS:
            title = "PARAMETERS   🔒 ล็อก (แสดงอย่างเดียว)"
        v = self._card(parent_layout, title)
        self._add_slider(v, "max_tokens")
        self._add_slider(v, "temperature")
        self._add_slider(v, "top_p")
        if LOCK_PARAMETERS:
            # View-only: keep values visible but block dragging (dev/full build can edit).
            for slider, _, _ in self._sliders.values():
                slider.setEnabled(False)

    def _build_usage_card(self, parent_layout):
        v = self._card(parent_layout, "การใช้งาน Token (Trial Usage)")

        self._usage_label = QLabel("—")
        self._usage_label.setObjectName("model_usage_label")
        self._usage_label.setFont(QFont(FONT_MONO, 10))
        v.addWidget(self._usage_label)

        self._usage_bar = QProgressBar()
        self._usage_bar.setObjectName("model_usage_bar")
        self._usage_bar.setTextVisible(False)
        self._usage_bar.setFixedHeight(10)
        v.addWidget(self._usage_bar)

        self._usage_models_label = QLabel("")
        self._usage_models_label.setObjectName("model_usage_models")
        self._usage_models_label.setFont(QFont(FONT_PRIMARY, 9))
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
        btn_reset.setFont(QFont(FONT_PRIMARY, 10, QFont.Weight.Bold))
        btn_reset.setFixedHeight(36)
        btn_reset.setMinimumWidth(96)
        btn_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_reset.setToolTip("คืนค่าแนะนำ (500 · 0.80 · 0.90)")
        btn_reset.clicked.connect(self._reset_defaults)
        f.addWidget(btn_reset)

        self._status_label = QLabel("")
        self._status_label.setObjectName("model_status")
        self._status_label.setFont(QFont(FONT_PRIMARY, 9))
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        f.addWidget(self._status_label, stretch=1)

        self._apply_btn = QPushButton("APPLY")
        self._apply_btn.setObjectName("model_apply")
        self._apply_btn.setFont(QFont(FONT_PRIMARY, 10, QFont.Weight.Bold))
        self._apply_btn.setFixedHeight(36)
        self._apply_btn.setMinimumWidth(96)
        self._apply_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._apply_btn.clicked.connect(self._on_apply)
        f.addWidget(self._apply_btn)

        return footer

    # ── Helpers ──

    def _add_slider(self, layout, key):
        """Magnet slider for one PARAM_SPECS entry. Runs in step-index units so
        every position snaps; paints snap pips + a recommended marker."""
        spec = PARAM_SPECS[key]
        fmt = spec["fmt"]

        row = QHBoxLayout()
        row.setSpacing(6)

        lbl = QLabel(spec["label"])
        lbl.setObjectName("model_param_label")
        lbl.setFont(QFont(FONT_PRIMARY, 10))
        lbl.setMinimumWidth(84)
        row.addWidget(lbl)

        slider = _MagnetSlider()
        slider.setObjectName("model_slider")
        slider.setMinimum(0)
        slider.setMaximum(_spec_n(spec))
        slider.setSingleStep(1)
        slider.setPageStep(1)
        slider.set_recommended(_real_to_idx(spec, spec["rec"]))
        slider.setValue(_real_to_idx(spec, spec["rec"]))
        row.addWidget(slider, stretch=1)

        val_lbl = QLabel(fmt.format(spec["rec"]))
        val_lbl.setObjectName("model_param_value")
        val_lbl.setFont(QFont(FONT_MONO, 10, QFont.Weight.Bold))
        val_lbl.setMinimumWidth(46)
        val_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(val_lbl)

        slider.valueChanged.connect(
            lambda idx, s=spec, vl=val_lbl: vl.setText(s["fmt"].format(_idx_to_real(s, idx)))
        )

        layout.addLayout(row)

        hint = PARAM_HINTS.get(key, "")
        if hint:
            hint_lbl = QLabel(hint)
            hint_lbl.setObjectName("model_hint")
            hint_lbl.setFont(QFont(FONT_PRIMARY, 9))
            hint_lbl.setWordWrap(True)
            layout.addWidget(hint_lbl)

        self._sliders[key] = (slider, val_lbl, spec)

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
        self._update_key_icons()

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
        self._update_key_icons()

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
            self._key_action.setToolTip("บันทึก API Key")
            self._update_key_icons()
            self._set_key_status("วาง key แล้วกดบันทึก หรือ Enter", ok=True)
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

    def _update_key_icons(self):
        """Apply SVG icons (tinted to the theme text colour) to the API-key
        eye + action buttons. Eye = open when masked (tap to reveal) / slashed
        when revealed (tap to hide); action = save while editing, else edit
        (pencil). Each falls back to its emoji glyph if the SVG is missing."""
        from pyqt_ui.qt_icons import load_icon
        color = getattr(self, "_icon_color", "#e6edf3")

        eye = load_icon("eye_close" if self._key_revealed else "eye_open", color)
        if eye is not None:
            self._key_eye.setIcon(eye)
            self._key_eye.setIconSize(QSize(18, 18))
            self._key_eye.setText("")

        if self._key_editing:
            save = load_icon("save", color)
            if save is not None:
                self._key_action.setIcon(save)
                self._key_action.setIconSize(QSize(18, 18))
                self._key_action.setText("")
            else:
                self._key_action.setIcon(QIcon())
                self._key_action.setText("💾")
        else:
            edit = load_icon("edit", color)
            if edit is not None:
                self._key_action.setIcon(edit)
                self._key_action.setIconSize(QSize(18, 18))
                self._key_action.setText("")
            else:
                self._key_action.setIcon(QIcon())
                self._key_action.setText("✎")

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
            for key, spec in PARAM_SPECS.items():
                self._set_slider(key, src.get(key, spec["rec"]))

        self._refresh_key_display()

    def _set_slider(self, key, real_value):
        """Snap a real parameter value onto the slider (clamps out-of-band)."""
        if key in self._sliders:
            slider, _, spec = self._sliders[key]
            slider.setValue(_real_to_idx(spec, real_value))

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
                s_mt, _, sp_mt = self._sliders["max_tokens"]
                s_t, _, sp_t = self._sliders["temperature"]
                s_p, _, sp_p = self._sliders["top_p"]
                max_tokens = int(round(_idx_to_real(sp_mt, s_mt.value())))
                temperature = round(_idx_to_real(sp_t, s_t.value()), 2)
                top_p = round(_idx_to_real(sp_p, s_p.value()), 2)
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
        for key, spec in PARAM_SPECS.items():
            self._set_slider(key, spec["rec"])
        self._show_status("คืนค่าแนะนำแล้ว")

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

        # Accent-tinted hover (rgba from theme accent) — matches the settings
        # panel so every button has a clearly-visible hover, not a faint bump.
        _ac = QColor(p['accent'])
        accent_rgb = f"{_ac.red()}, {_ac.green()}, {_ac.blue()}"

        # Bake a theme-tinted chevron PNG for the combo down-arrow (QSS
        # image:url can't tint a raw asset). Fall back to a CSS triangle.
        import os, tempfile
        from pyqt_ui.qt_icons import save_tinted_png
        _chevron = os.path.join(tempfile.gettempdir(), "mbb_chevron_down.png")
        if save_tinted_png("chevron", p['text'], _chevron, px=28):
            arrow_rule = (f"image: url({_chevron.replace(os.sep, '/')});"
                          f" width: 13px; height: 13px;")
        else:
            arrow_rule = (f"width: 0px; height: 0px;"
                          f" border-left: 5px solid transparent;"
                          f" border-right: 5px solid transparent;"
                          f" border-top: 5px solid {p['text']};")

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
                background: rgba({accent_rgb}, 0.16);
                border: 1px solid {p['accent']};
                color: {p['accent_light']};
            }}
            QPushButton#model_icon_btn:pressed {{
                background: rgba({accent_rgb}, 0.30);
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
                border-radius: 6px;
                padding: 4px 8px;
            }}
            QComboBox#model_combo:hover {{
                border: 1px solid {p['border_active']};
            }}
            QComboBox#model_combo QLineEdit {{
                background: transparent;
                border: none;
                color: {p['text']};
                selection-background-color: transparent;
                selection-color: {p['text']};
            }}
            QComboBox#model_combo::drop-down {{
                border: none;
                width: 30px;
            }}
            QComboBox#model_combo::down-arrow {{
                {arrow_rule}
            }}
            QComboBox#model_combo QAbstractItemView {{
                background: {p['bg_titlebar']};
                color: {p['text']};
                selection-background-color: {p['bg_medium']};
                border: 1px solid {p['border_subtle']};
                outline: none;
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
            QSlider#model_slider {{
                background: transparent;
                border: none;
            }}
            QWidget#model_footer {{
                background: transparent;
            }}
            QPushButton#model_btn {{
                background: {p['btn_bg']};
                color: {p['text']};
                border: 1px solid {p['border_subtle']};
                border-radius: 6px;
                padding: 0px 22px;
            }}
            QPushButton#model_btn:hover {{
                background: rgba({accent_rgb}, 0.16);
                border: 1px solid {p['accent']};
                color: {p['accent_light']};
            }}
            QPushButton#model_btn:pressed {{
                background: rgba({accent_rgb}, 0.30);
            }}
            QPushButton#model_apply {{
                background: {p['accent']};
                color: {p['toggled_text']};
                border: none;
                border-radius: 6px;
                padding: 0px 22px;
            }}
            QPushButton#model_apply:hover {{
                background: {p['accent_light']};
            }}
            QLabel#model_status {{
                background: transparent;
            }}
        """
        self.setStyleSheet(qss)

        # Recolor magnet-slider markers to match the theme (accent recommended
        # pip, dim for the other snap stops).
        for slider, _, _ in self._sliders.values():
            if hasattr(slider, "set_marker_colors"):
                slider.set_marker_colors(p['accent'], p['text_dim'], p['bg_deeper'])

        # Re-tint the API-key SVG icons to the new theme text colour.
        self._icon_color = p['text']
        self._update_key_icons()

    def eventFilter(self, obj, event):
        # Read-only model combo: clicking the centred text (not just the arrow)
        # opens the dropdown.
        if (self._model_combo is not None
                and obj is self._model_combo.lineEdit()
                and event.type() == QEvent.Type.MouseButtonPress):
            self._model_combo.showPopup()
            return True
        return super().eventFilter(obj, event)

    # ── Drag ──

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPosition().toPoint()
