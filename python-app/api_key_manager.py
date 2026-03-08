"""
API Key Manager for MBB Dalamud — PyQt6 frameless panel
"""

import os
import sys
import webbrowser
import logging
from dotenv import load_dotenv
from resource_utils import get_app_dir

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QWidget, QGraphicsDropShadowEffect, QApplication,
)
from PyQt6.QtCore import Qt, QPoint, QTimer
from PyQt6.QtGui import QColor, QFont, QCursor

log = logging.getLogger("mbb-qt")

# ── Color constants (match MBB dark theme) ───────────────────────────────────
_BG          = "#141414"
_BG_HEADER   = "#0e0e0e"
_BG_INPUT    = "#1c1c1c"
_BG_CARD     = "#1a1a1a"
_BORDER_RED  = "#ef4444"          # bright red — signals required action
_BORDER_NORM = "#2a2a2a"
_TEXT        = "#e0e0e0"
_TEXT_DIM    = "#888888"
_ACCENT      = "#6366f1"          # indigo button
_ACCENT_H    = "#818cf8"
_GREEN       = "#22c55e"
_RED         = "#ef4444"
_YELLOW      = "#eab308"
_FONT        = "Segoe UI"
_FONT_MONO   = "Consolas"

_QSS = f"""
    QWidget#api_bg {{
        background: {_BG};
        border-radius: 10px;
        border: 2px solid {_BORDER_RED};
    }}
    QWidget#api_header {{
        background: {_BG_HEADER};
        border-top-left-radius: 8px;
        border-top-right-radius: 8px;
        border-bottom: 1px solid #1f1f1f;
        margin: 0px;
    }}
    QLabel#api_title {{
        color: {_TEXT};
        background: transparent;
        font-family: '{_FONT}';
        font-size: 11pt;
        font-weight: bold;
    }}
    QPushButton#api_close {{
        background: transparent;
        border: none;
        color: {_TEXT_DIM};
        font-size: 13px;
        font-weight: bold;
        border-radius: 4px;
    }}
    QPushButton#api_close:hover {{
        background: #cc3333;
        color: white;
    }}
    QWidget#api_content {{
        background: transparent;
    }}
    QLabel#api_sub {{
        color: {_TEXT_DIM};
        background: transparent;
        font-family: '{_FONT}';
        font-size: 9pt;
    }}
    QLabel#api_card {{
        color: {_TEXT_DIM};
        background: {_BG_CARD};
        border-left: 3px solid {_ACCENT};
        border-radius: 4px;
        padding: 8px 10px;
        font-family: '{_FONT}';
        font-size: 9pt;
    }}
    QLabel#step_num {{
        color: white;
        background: {_ACCENT};
        border-radius: 3px;
        font-family: '{_FONT}';
        font-size: 8pt;
        font-weight: bold;
    }}
    QLabel#step_text {{
        color: {_TEXT};
        background: transparent;
        font-family: '{_FONT}';
        font-size: 10pt;
    }}
    QPushButton#api_open {{
        background: {_ACCENT};
        color: white;
        border: none;
        border-radius: 6px;
        font-family: '{_FONT}';
        font-size: 10pt;
        font-weight: bold;
        padding: 9px 16px;
        text-align: left;
    }}
    QPushButton#api_open:hover {{
        background: {_ACCENT_H};
    }}
    QLineEdit#api_entry {{
        background: {_BG_INPUT};
        color: {_TEXT};
        border: 1px solid #2a2a2a;
        border-radius: 5px;
        padding: 7px 10px;
        font-family: '{_FONT_MONO}';
        font-size: 10pt;
        selection-background-color: {_ACCENT};
    }}
    QLineEdit#api_entry:focus {{
        border: 1px solid {_ACCENT};
    }}
    QPushButton#api_eye {{
        background: transparent;
        border: none;
        color: {_TEXT_DIM};
        font-size: 12px;
        padding: 0px 6px;
    }}
    QPushButton#api_eye:hover {{
        color: {_TEXT};
    }}
    QPushButton#api_save {{
        background: #14532d;
        color: white;
        border: none;
        border-radius: 6px;
        font-family: '{_FONT}';
        font-size: 10pt;
        font-weight: bold;
        padding: 9px 16px;
    }}
    QPushButton#api_save:hover {{
        background: {_GREEN};
    }}
    QLabel#api_status {{
        background: transparent;
        font-family: '{_FONT}';
        font-size: 9pt;
    }}
    QLabel#api_footer {{
        color: {_TEXT_DIM};
        background: transparent;
        font-family: '{_FONT}';
        font-size: 8pt;
    }}
"""


# ─────────────────────────────────────────────────────────────────────────────

def check_and_setup() -> bool:
    """
    ตรวจสอบ API key — ถ้าไม่มี แสดง PyQt6 setup dialog
    Returns True ถ้ามี key พร้อมใช้งาน, False ถ้า user ยกเลิก
    """
    search_paths = [
        os.path.join(get_app_dir(), ".env"),
        os.path.join(os.getcwd(), ".env"),
    ]
    for env_path in search_paths:
        if os.path.exists(env_path):
            load_dotenv(env_path)
            key = os.getenv("GEMINI_API_KEY")
            if key and key != "your_api_key_here" and len(key) > 10:
                log.info(f"API key loaded from: {env_path}")
                return True

    log.warning("No valid API key — showing setup dialog")
    dlg = APIKeyDialog(is_invalid=False)
    dlg.exec()
    return dlg.success


def show_invalid_key_ui() -> bool:
    """
    แสดง dialog เมื่อ key มีปัญหาขณะ runtime
    Returns True ถ้าผู้ใช้ใส่ key ใหม่สำเร็จ
    """
    dlg = APIKeyDialog(is_invalid=True)
    dlg.exec()
    return dlg.success


# ─────────────────────────────────────────────────────────────────────────────

class APIKeyDialog(QDialog):
    """Frameless PyQt6 dialog — API key first-run / invalid key"""

    def __init__(self, is_invalid: bool = False, parent=None):
        super().__init__(parent)
        self.is_invalid = is_invalid
        self.success = False
        self._dragging = False
        self._drag_pos = QPoint()
        self._showing_key = False

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Dialog
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(500)

        self._build()
        self.setStyleSheet(_QSS)
        self.adjustSize()
        self._center()

    # ── Layout ──────────────────────────────────────────────────────────────

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(0)

        self.bg = QWidget()
        self.bg.setObjectName("api_bg")
        outer.addWidget(self.bg)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(0, 0, 0, 160))
        shadow.setOffset(0, 4)
        self.bg.setGraphicsEffect(shadow)

        root = QVBoxLayout(self.bg)
        root.setContentsMargins(2, 2, 2, 2)
        root.setSpacing(0)

        root.addWidget(self._make_header())
        root.addWidget(self._make_content())

    def _make_header(self) -> QWidget:
        hdr = QWidget()
        hdr.setObjectName("api_header")
        hdr.setFixedHeight(40)
        lay = QHBoxLayout(hdr)
        lay.setContentsMargins(14, 0, 8, 0)

        # Red dot icon (visually marks required)
        dot = QLabel("●")
        dot.setStyleSheet(f"color: {_BORDER_RED}; background: transparent; font-size: 10px;")
        lay.addWidget(dot)
        lay.addSpacing(6)

        title = QLabel("MBB Dalamud — ตั้งค่า Gemini API Key")
        title.setObjectName("api_title")
        lay.addWidget(title, stretch=1)

        btn_x = QPushButton("✕")
        btn_x.setObjectName("api_close")
        btn_x.setFixedSize(28, 28)
        btn_x.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_x.clicked.connect(self.reject)
        lay.addWidget(btn_x)

        return hdr

    def _make_content(self) -> QWidget:
        cw = QWidget()
        cw.setObjectName("api_content")
        lay = QVBoxLayout(cw)
        lay.setContentsMargins(20, 16, 20, 20)
        lay.setSpacing(12)

        # ── Sub-title / state ────────────────────────────────────────────
        if self.is_invalid:
            sub_txt   = "⚠  API Key ที่มีอยู่ไม่ถูกต้องหรือหมดอายุ — กรุณาอัปเดต"
            sub_color = _YELLOW
        else:
            sub_txt   = "โปรแกรมต้องการ Gemini API Key เพื่อแปลข้อความ"
            sub_color = _TEXT_DIM

        sub = QLabel(sub_txt)
        sub.setObjectName("api_sub")
        sub.setStyleSheet(f"color: {sub_color}; background: transparent; font-family: '{_FONT}'; font-size: 9pt;")
        lay.addWidget(sub)

        # ── Info card ────────────────────────────────────────────────────
        card = QLabel(
            "Gemini API Key ใช้งานฟรี · 1,500 ครั้ง/วัน · ไม่ต้องใส่บัตรเครดิต\n"
            "เพียงพอสำหรับการเล่นเกม FFXIV ทั้งวัน"
        )
        card.setObjectName("api_card")
        card.setWordWrap(True)
        lay.addWidget(card)

        lay.addSpacing(4)

        # ── Step 1 ────────────────────────────────────────────────────────
        lay.addWidget(self._step_row("1", "รับ API Key จาก Google AI Studio"))
        self._btn_open = QPushButton("  🌐  เปิด Google AI Studio ในเบราว์เซอร์")
        self._btn_open.setObjectName("api_open")
        self._btn_open.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._btn_open.clicked.connect(self._open_browser)
        lay.addWidget(self._btn_open)

        lay.addSpacing(4)

        # ── Step 2 ────────────────────────────────────────────────────────
        lay.addWidget(self._step_row("2", "วาง API Key ในช่องด้านล่าง"))

        entry_row = QHBoxLayout()
        entry_row.setSpacing(4)

        self._entry = QLineEdit()
        self._entry.setObjectName("api_entry")
        self._entry.setEchoMode(QLineEdit.EchoMode.Password)
        self._entry.setPlaceholderText("AIzaSy...")
        self._entry.textChanged.connect(self._on_key_changed)
        self._entry.returnPressed.connect(self._save)
        entry_row.addWidget(self._entry, stretch=1)

        self._btn_eye = QPushButton("👁")
        self._btn_eye.setObjectName("api_eye")
        self._btn_eye.setFixedWidth(34)
        self._btn_eye.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._btn_eye.setToolTip("แสดง / ซ่อน API Key")
        self._btn_eye.clicked.connect(self._toggle_show)
        entry_row.addWidget(self._btn_eye)

        lay.addLayout(entry_row)

        # Validation status
        self._lbl_status = QLabel("")
        self._lbl_status.setObjectName("api_status")
        self._lbl_status.setStyleSheet(f"color: {_TEXT_DIM}; background: transparent; font-family: '{_FONT}'; font-size: 9pt;")
        lay.addWidget(self._lbl_status)

        # ── Step 3 ────────────────────────────────────────────────────────
        lay.addWidget(self._step_row("3", "บันทึก และเริ่มโปรแกรม"))

        self._btn_save = QPushButton("  💾  บันทึก และเริ่มโปรแกรม")
        self._btn_save.setObjectName("api_save")
        self._btn_save.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._btn_save.clicked.connect(self._save)
        lay.addWidget(self._btn_save)

        lay.addSpacing(8)

        # Footer
        footer = QLabel("API Key บันทึกในไฟล์ .env  ·  ครั้งต่อไปจะไม่แสดงหน้านี้อีก")
        footer.setObjectName("api_footer")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(footer)

        return cw

    def _step_row(self, num: str, text: str) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        row = QHBoxLayout(w)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        badge = QLabel(num)
        badge.setObjectName("step_num")
        badge.setFixedSize(20, 20)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row.addWidget(badge)

        lbl = QLabel(text)
        lbl.setObjectName("step_text")
        row.addWidget(lbl, stretch=1)

        return w

    # ── Callbacks ────────────────────────────────────────────────────────────

    def _open_browser(self):
        url = "https://aistudio.google.com/app/apikey"
        try:
            webbrowser.open(url)
            # Brief pulse
            self._btn_open.setStyleSheet(f"QPushButton#api_open {{ background: {_ACCENT_H}; color: white; border: none; border-radius: 6px; font-family: '{_FONT}'; font-size: 10pt; font-weight: bold; padding: 9px 16px; }}")
            QTimer.singleShot(600, lambda: self._btn_open.setStyleSheet(""))
        except Exception as e:
            self._set_status(f"ไม่สามารถเปิดเบราว์เซอร์อัตโนมัติ: {e}", ok=False)

    def _toggle_show(self):
        self._showing_key = not self._showing_key
        mode = QLineEdit.EchoMode.Normal if self._showing_key else QLineEdit.EchoMode.Password
        self._entry.setEchoMode(mode)
        self._btn_eye.setStyleSheet(
            f"QPushButton#api_eye {{ color: {_TEXT if self._showing_key else _TEXT_DIM}; background: transparent; border: none; font-size: 12px; padding: 0px 6px; }}"
        )

    def _on_key_changed(self, text: str):
        key = text.strip()
        if not key:
            self._lbl_status.setText("")
            self._entry.setStyleSheet("")
            return
        ok, msg = self._validate_format(key)
        self._set_status(msg, ok=ok)
        border = _GREEN if ok else _RED
        self._entry.setStyleSheet(
            f"QLineEdit#api_entry {{ background: {_BG_INPUT}; color: {_TEXT}; border: 1px solid {border}; border-radius: 5px; padding: 7px 10px; font-family: '{_FONT_MONO}'; font-size: 10pt; }}"
        )

    def _validate_format(self, key: str):
        if not key.startswith("AIza"):
            return False, "✗  ต้องเริ่มด้วย 'AIza'"
        if len(key) < 30:
            return False, f"✗  สั้นเกินไป ({len(key)} ตัวอักษร — ควรมีประมาณ 39)"
        return True, f"✓  รูปแบบถูกต้อง ({len(key)} ตัวอักษร)"

    def _set_status(self, msg: str, ok: bool = True):
        color = _GREEN if ok else _RED
        self._lbl_status.setStyleSheet(
            f"color: {color}; background: transparent; font-family: '{_FONT}'; font-size: 9pt;"
        )
        self._lbl_status.setText(msg)

    def _save(self):
        key = self._entry.text().strip()
        ok, msg = self._validate_format(key)
        if not ok:
            self._set_status(msg, ok=False)
            self._entry.setFocus()
            return

        app_dir = get_app_dir()
        env_path = os.path.join(app_dir, ".env")

        try:
            with open(env_path, "w", encoding="utf-8") as f:
                f.write("# Google Gemini API Key\n")
                f.write(f"GEMINI_API_KEY={key}\n")
                f.write("\n# Application Settings\n")
                f.write("MBB_DEBUG=false\n")
                f.write("MBB_LOG_LEVEL=info\n")

            os.environ["GEMINI_API_KEY"] = key
            load_dotenv(env_path)
            self.success = True

            # Success flash
            self._btn_save.setText("  ✓  บันทึกแล้ว — กำลังเริ่มโปรแกรม...")
            self._btn_save.setStyleSheet(
                f"QPushButton#api_save {{ background: {_GREEN}; color: white; border: none; border-radius: 6px; font-family: '{_FONT}'; font-size: 10pt; font-weight: bold; padding: 9px 16px; }}"
            )
            QTimer.singleShot(900, self.accept)

        except Exception as e:
            self._set_status(f"✗  บันทึกไฟล์ไม่ได้: {e}", ok=False)

    # ── Drag (header-only) ────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Only drag from header zone (top 40px of bg)
            bg_pos = self.bg.mapFromGlobal(event.globalPosition().toPoint())
            if bg_pos.y() <= 40:
                self._dragging = True
                self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._dragging and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._dragging = False
        super().mouseReleaseEvent(event)

    def _center(self):
        screen = QApplication.primaryScreen()
        if screen:
            sg = screen.availableGeometry()
            self.move(
                sg.left() + (sg.width()  - self.width())  // 2,
                sg.top()  + (sg.height() - self.height()) // 2,
            )


# For standalone testing
if __name__ == "__main__":
    app = QApplication(sys.argv)
    result = check_and_setup()
    print(f"Setup result: {'Success' if result else 'Cancelled'}")
