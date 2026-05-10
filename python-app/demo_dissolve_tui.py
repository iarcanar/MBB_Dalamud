"""
demo_dissolve_tui.py — Standalone visual demo for a dissolve-edge battle TUI.

A frameless, always-on-top overlay window with:
  - Solid dark tinted background (~90% of width)
  - Smooth alpha-gradient dissolve on left edge (~5%) and right edge (~5%)
  - Centered Thai + English sample dialogue (text stays fully opaque)
  - Press ESC to close

Run:
    python demo_dissolve_tui.py

This is a standalone demo — it imports nothing from the MBB project.
PyQt6 is the only third-party dependency.
"""

from __future__ import annotations

import os
import sys

from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QFontMetrics,
    QLinearGradient,
    QPainter,
)
from PyQt6.QtWidgets import QApplication, QWidget


# ────────────────────────────────────────────────────────────────────
# Tunables — tweak these and re-run to evaluate different looks
# ────────────────────────────────────────────────────────────────────
WINDOW_W = 1000          # overall overlay width  (battle dialog feel = wide)
WINDOW_H = 140           # overall overlay height (short)
TOP_OFFSET = 80          # px from screen top — battle text usually appears high

FADE_PCT = 0.05          # dissolve zone width as fraction of window width
                         # 0.05 = 5% per side. Increase for softer fade.

# Background tint — Carbon-theme adjacent dark slate
BG_COLOR_RGBA = (20, 22, 28, 230)   # (r, g, b, a) — a=230 ≈ 90% opacity

# Sample dialogue (English line above Thai line)
LINE_EN = "Stand back! I'll handle this one."
LINE_TH = "ระวัง! ฉันจะจัดการเอง"

FONT_FAMILY_PREFERRED = "Anuphan"
FONT_SIZE_PT = 22
FONT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "fonts", "Anuphan.ttf")

# Hint label
HINT_TEXT = "Press ESC to close"
HINT_FONT_PT = 9
HINT_COLOR_RGBA = (180, 180, 180, 160)   # dim gray


# ────────────────────────────────────────────────────────────────────
# Demo widget
# ────────────────────────────────────────────────────────────────────
class DissolveDemo(QWidget):
    def __init__(self) -> None:
        super().__init__()

        # Frameless + always-on-top + tool window (no taskbar entry)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        # Translucent so our paintEvent is the ONLY thing drawn
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self.resize(WINDOW_W, WINDOW_H)
        self._center_top_on_screen()

        # Resolve font: try Anuphan, fall back to system default
        family = self._load_font_family()
        self._main_font = QFont(family, FONT_SIZE_PT)
        self._main_font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)

        self._hint_font = QFont(family, HINT_FONT_PT)
        self._hint_font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)

    # ────────────────────────────────────────────────────────
    # Setup helpers
    # ────────────────────────────────────────────────────────
    def _load_font_family(self) -> str:
        """Register Anuphan if available, else return a sensible system fallback."""
        if os.path.exists(FONT_PATH):
            font_id = QFontDatabase.addApplicationFont(FONT_PATH)
            if font_id != -1:
                families = QFontDatabase.applicationFontFamilies(font_id)
                if families:
                    return families[0]
        # Fallback chain — Qt will pick the first installed family
        for candidate in (FONT_FAMILY_PREFERRED, "Segoe UI", "Tahoma", "Arial"):
            return candidate
        return ""  # Qt default

    def _center_top_on_screen(self) -> None:
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        geo = screen.availableGeometry()
        x = geo.x() + (geo.width() - WINDOW_W) // 2
        y = geo.y() + TOP_OFFSET
        self.move(x, y)

    # ────────────────────────────────────────────────────────
    # Paint
    # ────────────────────────────────────────────────────────
    def paintEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        w = self.width()
        h = self.height()

        # ── 1. Background gradient (alpha fade on both edges) ──
        # Horizontal gradient stops:
        #   0.00 → fully transparent
        #   FADE → fully opaque tint   (left fade-in done)
        #   1-FADE → fully opaque tint (right fade-out start)
        #   1.00 → fully transparent
        base = QColor(*BG_COLOR_RGBA)
        clear = QColor(BG_COLOR_RGBA[0], BG_COLOR_RGBA[1], BG_COLOR_RGBA[2], 0)

        gradient = QLinearGradient(0.0, 0.0, float(w), 0.0)
        gradient.setColorAt(0.00, clear)
        gradient.setColorAt(FADE_PCT, base)
        gradient.setColorAt(1.0 - FADE_PCT, base)
        gradient.setColorAt(1.00, clear)

        p.fillRect(self.rect(), gradient)

        # ── 2. Main dialogue text (fully opaque, centered) ──
        p.setFont(self._main_font)
        fm = QFontMetrics(self._main_font)
        line_h = fm.height()
        gap = 6  # vertical spacing between EN and TH lines
        block_h = line_h * 2 + gap

        # Vertical block start so the two lines are centered together
        block_top = (h - block_h) // 2

        # English line
        p.setPen(QColor(255, 255, 255, 255))
        en_rect = QRect(0, block_top, w, line_h)
        p.drawText(en_rect, Qt.AlignmentFlag.AlignCenter, LINE_EN)

        # Thai line — slight warm tint to differentiate, still fully opaque
        p.setPen(QColor(255, 230, 200, 255))
        th_rect = QRect(0, block_top + line_h + gap, w, line_h)
        p.drawText(th_rect, Qt.AlignmentFlag.AlignCenter, LINE_TH)

        # ── 3. ESC hint (bottom-right, dim) ──
        p.setFont(self._hint_font)
        p.setPen(QColor(*HINT_COLOR_RGBA))
        hint_rect = QRect(0, h - 22, w - 14, 18)
        p.drawText(
            hint_rect,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            HINT_TEXT,
        )

        p.end()

    # ────────────────────────────────────────────────────────
    # Input
    # ────────────────────────────────────────────────────────
    def keyPressEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)


# ────────────────────────────────────────────────────────────────────
# Entry point
# ────────────────────────────────────────────────────────────────────
def main() -> int:
    app = QApplication(sys.argv)
    demo = DissolveDemo()
    demo.show()
    # Keyboard focus so ESC works without clicking first
    demo.activateWindow()
    demo.setFocus(Qt.FocusReason.OtherFocusReason)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
