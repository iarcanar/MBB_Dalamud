"""
ModelPanel (PyQt6) — Frameless AI model configuration matching MBB style
No PIN verification. No adult mode.
"""
import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGraphicsDropShadowEffect, QComboBox, QSlider,
)
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtCore import Qt, QPoint, QTimer

from pyqt_ui.styles import FONT_PRIMARY, FONT_MONO, derive_palette

log = logging.getLogger("mbb-qt")

WIDTH = 360
HEIGHT = 440

AVAILABLE_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.5-pro",
    "gemini-2.0-flash",
]

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
        h_layout.setContentsMargins(14, 0, 6, 0)

        title = QLabel("AI Model Configuration")
        title.setObjectName("model_title")
        title.setFont(QFont(FONT_PRIMARY, 10, QFont.Weight.Bold))
        h_layout.addWidget(title)
        h_layout.addStretch()

        btn_close = QPushButton("\u2715")
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
        c.setContentsMargins(14, 12, 14, 14)
        c.setSpacing(8)

        # ── AI Model ──
        self._add_section(c, "AI Model")
        self._model_combo = QComboBox()
        self._model_combo.setObjectName("model_combo")
        self._model_combo.setFont(QFont(FONT_PRIMARY, 10))
        self._model_combo.addItems(AVAILABLE_MODELS)
        self._model_combo.setFixedHeight(30)
        c.addWidget(self._model_combo)

        c.addSpacing(4)

        # ── Parameters ──
        self._add_section(c, "Parameters")
        self._add_slider(c, "max_tokens", "Max Tokens", 100, 2000, 50, 500)
        self._add_slider(c, "temperature", "Temperature", 0, 100, 5, 80,
                         display_scale=0.01, fmt="{:.2f}")
        self._add_slider(c, "top_p", "Top P", 0, 100, 5, 90,
                         display_scale=0.01, fmt="{:.2f}")

        c.addStretch()

        main.addWidget(content, stretch=1)

        # Footer
        footer = QWidget()
        footer.setObjectName("model_footer")
        f = QHBoxLayout(footer)
        f.setContentsMargins(14, 6, 14, 10)
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

        main.addWidget(footer)

    # ── Helpers ──

    def _add_section(self, layout, text):
        lbl = QLabel(text)
        lbl.setObjectName("model_section")
        lbl.setFont(QFont(FONT_PRIMARY, 9, QFont.Weight.Bold))
        layout.addWidget(lbl)

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

        # Thai hint below slider
        hint = PARAM_HINTS.get(key, "")
        if hint:
            hint_lbl = QLabel(hint)
            hint_lbl.setObjectName("model_hint")
            hint_lbl.setFont(QFont(FONT_PRIMARY, 8))
            hint_lbl.setWordWrap(True)
            layout.addWidget(hint_lbl)

        self._sliders[key] = (slider, val_lbl, display_scale)

    # ── Data ──

    def _load_current(self):
        params = self.settings.get_api_parameters()

        # Model
        model = params.get("model", "gemini-2.5-flash")
        idx = self._model_combo.findText(model)
        if idx >= 0:
            self._model_combo.setCurrentIndex(idx)

        # Parameters
        self._set_slider("max_tokens", params.get("max_tokens", 500))
        self._set_slider("temperature", params.get("temperature", 0.8), scale=100)
        self._set_slider("top_p", params.get("top_p", 0.9), scale=100)

    def _set_slider(self, key, value, scale=1):
        if key in self._sliders:
            slider, _, _ = self._sliders[key]
            slider.setValue(int(value * scale))

    def _on_apply(self):
        try:
            model = self._model_combo.currentText()

            max_tokens_slider, _, _ = self._sliders["max_tokens"]
            temp_slider, _, temp_scale = self._sliders["temperature"]
            top_p_slider, _, top_p_scale = self._sliders["top_p"]

            api_params = {
                "model": model,
                "max_tokens": max_tokens_slider.value(),
                "temperature": temp_slider.value() * temp_scale,
                "top_p": top_p_slider.value() * top_p_scale,
                "role_mode": "rpg_general",
            }

            self.settings.validate_model_parameters(api_params)

            success, error = self.settings.set_api_parameters(**api_params)
            if not success:
                raise ValueError(error)

            self.settings.save_settings()

            # Update main app
            if self.main_app and hasattr(self.main_app, "update_api_settings"):
                self.main_app.update_api_settings()

            # Update translator prompt
            if self.main_app and hasattr(self.main_app, "translator"):
                if self.main_app.translator and hasattr(self.main_app.translator, "set_role_mode"):
                    self.main_app.translator.set_role_mode("rpg_general")

            self._show_status("Applied!")
            self._apply_btn.setText("\u2713 Applied")
            QTimer.singleShot(2000, lambda: self._apply_btn.setText("APPLY"))

        except Exception as e:
            log.error(f"Model apply failed: {e}")
            self._show_status(str(e), error=True)

    def _reset_defaults(self):
        idx = self._model_combo.findText("gemini-2.5-flash")
        if idx >= 0:
            self._model_combo.setCurrentIndex(idx)
        self._set_slider("max_tokens", 500)
        self._set_slider("temperature", 0.7, scale=100)
        self._set_slider("top_p", 0.9, scale=100)
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
            QLabel#model_section {{
                color: {p['text_dim']};
                background: transparent;
            }}
            QComboBox#model_combo {{
                background: {p['bg_titlebar']};
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
            QSlider#model_slider::groove:horizontal {{
                border: none;
                height: 4px;
                background: {p['bg_titlebar']};
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
