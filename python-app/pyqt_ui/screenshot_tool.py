"""ScreenshotCropOverlay — fullscreen "snipping tool" used to capture an
avatar from the live game window for the NPC Manager.

Flow:
  1. Caller hides the NPC Manager + grabs full-screen pixmap
  2. Constructs ScreenshotCropOverlay(pixmap, character_name)
  3. Overlay shows fullscreen, displays the snapshot underneath a
     semi-transparent black mask
  4. User click-drags to define a crop rectangle. The mask is "punched
     out" inside that rectangle so the user can see clearly what they're
     cropping. A vivid cyan border + corner handles indicate selection.
  5. ENTER or double-click inside selection confirms → emits
     `crop_confirmed(QPixmap)` with the cropped region
  6. ESC or click outside any selection (after one exists) cancels → emits
     `crop_cancelled()`

The overlay is intentionally a single self-contained QWidget — no nested
windows, no painters on top of painters. Easier to reason about and less
prone to multi-window flicker.

Theme: the cyan accent (#00d4ff default) is overrideable via the constructor
so the overlay can match the user's current Theme Manager accent if desired.
The dark mask is fixed at black @ 60% alpha — anything lighter washes the
photo out, anything darker makes it hard to see the cropped area.
"""
from __future__ import annotations

import logging
from typing import Optional

from PyQt6.QtCore import (
    QPoint,
    QRect,
    QSize,
    Qt,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontMetrics,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
)

log = logging.getLogger("screenshot-tool")


# ────────────────────────────────────────────────────────────────────
# Style constants
# ────────────────────────────────────────────────────────────────────
MASK_COLOR = QColor(0, 0, 0, 153)       # 60% black overlay outside the crop
DEFAULT_ACCENT = "#00d4ff"               # vivid cyan — pops on every theme

BORDER_WIDTH = 2
HANDLE_SIZE = 10                         # corner + edge resize handles
HANDLE_FILL = QColor(0, 212, 255)
HANDLE_OUTLINE = QColor(255, 255, 255, 220)

INSTR_PADDING = 18
INSTR_BG = QColor(0, 0, 0, 200)
INSTR_FG = QColor(255, 255, 255)
INSTR_ACCENT = QColor(0, 212, 255)

MIN_CROP = 32                            # ignore tiny accidental drags

FONT_FAMILY = "Anuphan"


class ScreenshotCropOverlay(QWidget):
    """Frameless fullscreen crop overlay over a captured screen pixmap."""

    crop_confirmed = pyqtSignal(QPixmap)   # cropped region
    crop_cancelled = pyqtSignal()

    def __init__(
        self,
        background_pixmap: QPixmap,
        character_name: str,
        accent_hex: str = DEFAULT_ACCENT,
        parent: Optional[QWidget] = None,
        target_screen=None,
    ):
        """target_screen: QScreen the overlay should cover. Required for
        multi-monitor setups so the overlay appears on the same monitor as
        the captured background. Falls back to primary if None."""
        super().__init__(parent)
        self._background = background_pixmap
        self._character_name = (character_name or "?").strip() or "?"
        self._accent = QColor(accent_hex) if accent_hex else QColor(DEFAULT_ACCENT)

        # Selection state
        self._selecting = False              # mouse currently dragging fresh selection
        self._sel_start = QPoint()
        self._sel_rect = QRect()             # current crop rect (in widget coords)
        self._has_selection = False          # at least one valid selection exists

        # Window flags — frameless, fullscreen, always-on-top, no taskbar entry
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        # NOT WA_TranslucentBackground — we paint the captured pixmap as bg.
        # Translucent bg would let the live desktop bleed through.
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.CrossCursor)

        # Cover the target screen exactly (multi-monitor aware). Use full
        # geometry (not availableGeometry) so we cover the taskbar too —
        # otherwise users can't crop near screen edges.
        screen = target_screen or QApplication.primaryScreen()
        if screen is None:
            self.setGeometry(0, 0, 1920, 1080)
        else:
            self.setGeometry(screen.geometry())

        # Fonts
        self._font_instr = QFont(FONT_FAMILY, 14, QFont.Weight.Bold)
        self._font_instr.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
        self._font_sub = QFont(FONT_FAMILY, 10)
        self._font_sub.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)

    # ──────────────────────────────────────────────────────────────
    # Painting
    # ──────────────────────────────────────────────────────────────
    def paintEvent(self, event):  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        # 1. Draw captured screen as background
        if self._background and not self._background.isNull():
            p.drawPixmap(self.rect(), self._background)

        # 2. Dark mask everywhere — punched out inside selection rect
        if self._has_selection and not self._sel_rect.isEmpty():
            mask_path = QPainterPath()
            mask_path.addRect(self.rect().toRectF())
            inner_path = QPainterPath()
            inner_path.addRect(self._sel_rect.toRectF())
            mask_path = mask_path.subtracted(inner_path)
            p.fillPath(mask_path, MASK_COLOR)

            # Crop border (cyan, 2px)
            pen = QPen(self._accent, BORDER_WIDTH)
            pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            # adjust by half-pen so 2px line sits cleanly inside the rect
            p.drawRect(self._sel_rect.adjusted(0, 0, -1, -1))

            # Corner + edge handles for visual affordance
            self._draw_handles(p, self._sel_rect)
        else:
            # No selection yet → fully masked
            p.fillRect(self.rect(), MASK_COLOR)

        # 3. Top instruction pill
        self._draw_instruction(p)

        # 4. Bottom hint
        self._draw_bottom_hint(p)

        p.end()

    def _draw_handles(self, p: QPainter, rect: QRect):
        """Draw 8 small filled squares at corners + edge midpoints."""
        h = HANDLE_SIZE
        h2 = h // 2
        cx = rect.center().x()
        cy = rect.center().y()
        points = [
            (rect.left(), rect.top()),       # TL
            (cx, rect.top()),                # T
            (rect.right(), rect.top()),      # TR
            (rect.right(), cy),              # R
            (rect.right(), rect.bottom()),   # BR
            (cx, rect.bottom()),             # B
            (rect.left(), rect.bottom()),    # BL
            (rect.left(), cy),               # L
        ]
        p.setPen(QPen(HANDLE_OUTLINE, 1))
        p.setBrush(QBrush(HANDLE_FILL))
        for x, y in points:
            p.drawRect(QRect(int(x) - h2, int(y) - h2, h, h))

    def _draw_instruction(self, p: QPainter):
        """Top-center pill: '📷 เลือกหน้าตาตัวละคร: <Name>'"""
        text = f"เลือกหน้าตาตัวละคร:  {self._character_name}"
        fm = QFontMetrics(self._font_instr)
        text_w = fm.horizontalAdvance(text)
        text_h = fm.height()

        pad_x = 28
        pad_y = 12
        pill_w = text_w + pad_x * 2
        pill_h = text_h + pad_y * 2
        pill_x = (self.width() - pill_w) // 2
        pill_y = 60

        # Pill background — dark, rounded
        p.setPen(QPen(self._accent, 1))
        p.setBrush(QBrush(INSTR_BG))
        p.drawRoundedRect(QRect(pill_x, pill_y, pill_w, pill_h), 22, 22)

        # Camera icon (drawn glyph — keeps overlay self-contained)
        icon_x = pill_x + 14
        icon_y = pill_y + (pill_h - 18) // 2
        self._draw_camera_glyph(p, icon_x, icon_y, 18, INSTR_ACCENT)

        # Text — accent for label, white for character name
        p.setFont(self._font_instr)
        p.setPen(self._accent)
        text_x = pill_x + pad_x + 12  # +12 to leave room for icon
        text_y = pill_y + (pill_h + text_h) // 2 - fm.descent()
        # Split label vs name for two-tone color
        label_part = "เลือกหน้าตาตัวละคร: "
        label_w = fm.horizontalAdvance(label_part)
        p.drawText(text_x, text_y, label_part)
        p.setPen(INSTR_FG)
        p.drawText(text_x + label_w, text_y, self._character_name)

    def _draw_camera_glyph(self, p: QPainter, x: int, y: int, sz: int, color: QColor):
        """Tiny inline camera glyph so we don't need to ship/load an asset."""
        body = QRect(x, y + sz // 4, sz, int(sz * 0.7))
        p.setPen(QPen(color, 1.6))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(body, 2, 2)
        # bump on top
        bump = QRect(x + sz // 4, y, sz // 2, sz // 4)
        p.drawRoundedRect(bump, 1, 1)
        # lens
        cx = x + sz // 2
        cy = y + sz // 2 + 2
        p.drawEllipse(QPoint(cx, cy), sz // 4, sz // 4)

    def _draw_bottom_hint(self, p: QPainter):
        """Bottom-center hint about controls."""
        if self._has_selection:
            text = "ENTER / double-click ในกรอบ = ยืนยัน    ·    ESC = ยกเลิก"
        else:
            text = "คลิก-ลาก เพื่อเลือกพื้นที่หน้าตาตัวละคร    ·    ESC = ยกเลิก"
        fm = QFontMetrics(self._font_sub)
        text_w = fm.horizontalAdvance(text)
        text_h = fm.height()
        pad_x = 18
        pad_y = 8
        pill_w = text_w + pad_x * 2
        pill_h = text_h + pad_y * 2
        pill_x = (self.width() - pill_w) // 2
        pill_y = self.height() - pill_h - 56

        p.setPen(QPen(QColor(255, 255, 255, 60), 1))
        p.setBrush(QBrush(QColor(0, 0, 0, 180)))
        p.drawRoundedRect(QRect(pill_x, pill_y, pill_w, pill_h), 16, 16)

        p.setFont(self._font_sub)
        p.setPen(QColor(220, 220, 220))
        p.drawText(
            QRect(pill_x, pill_y, pill_w, pill_h),
            int(Qt.AlignmentFlag.AlignCenter),
            text,
        )

    # ──────────────────────────────────────────────────────────────
    # Mouse — click-drag to define selection
    # ──────────────────────────────────────────────────────────────
    def mousePressEvent(self, event):  # noqa: N802
        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event); return
        self._sel_start = event.position().toPoint()
        self._sel_rect = QRect(self._sel_start, QSize(0, 0))
        self._selecting = True
        # Don't toggle has_selection until release — avoids flicker on tiny drags
        self.update()
        event.accept()

    def mouseMoveEvent(self, event):  # noqa: N802
        if self._selecting:
            cur = event.position().toPoint()
            self._sel_rect = QRect(self._sel_start, cur).normalized()
            self._has_selection = True
            self.update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton and self._selecting:
            self._selecting = False
            # Reject too-small drags (likely accidental clicks)
            if self._sel_rect.width() < MIN_CROP or self._sel_rect.height() < MIN_CROP:
                self._has_selection = False
                self._sel_rect = QRect()
            self.update()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):  # noqa: N802
        # Double-click inside selection = confirm
        if (
            self._has_selection
            and self._sel_rect.contains(event.position().toPoint())
        ):
            self._confirm()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    # ──────────────────────────────────────────────────────────────
    # Keyboard
    # ──────────────────────────────────────────────────────────────
    def keyPressEvent(self, event):  # noqa: N802
        key = event.key()
        if key == Qt.Key.Key_Escape:
            self._cancel()
            event.accept()
            return
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if self._has_selection:
                self._confirm()
            event.accept()
            return
        super().keyPressEvent(event)

    # ──────────────────────────────────────────────────────────────
    # Confirm / cancel
    # ──────────────────────────────────────────────────────────────
    def _confirm(self):
        if not self._has_selection or self._sel_rect.isEmpty():
            return
        try:
            # Map widget rect → background pixmap rect (they should be 1:1
            # since we cover the screen, but handle DPR scaling defensively)
            cropped = self._extract_crop()
            self.crop_confirmed.emit(cropped)
        except Exception as e:
            log.warning(f"crop extraction failed: {e}")
        finally:
            self.close()

    def _cancel(self):
        self.crop_cancelled.emit()
        self.close()

    def _extract_crop(self) -> QPixmap:
        """Extract the selected rectangle from the captured background.

        Handles HiDPI scaling: QScreen.grabWindow returns a pixmap whose
        device-pixel-ratio matches the source, so widget-coord rects need
        to be scaled by that ratio when slicing.
        """
        bg = self._background
        if bg is None or bg.isNull():
            return QPixmap()
        dpr = bg.devicePixelRatio() or 1.0
        # Selection rect is in widget (logical) pixels; convert to device px
        rect_dp = QRect(
            int(self._sel_rect.x() * dpr),
            int(self._sel_rect.y() * dpr),
            int(self._sel_rect.width() * dpr),
            int(self._sel_rect.height() * dpr),
        )
        # Clamp to pixmap bounds (defensive — drag past edge could overshoot)
        rect_dp = rect_dp.intersected(QRect(0, 0, bg.width(), bg.height()))
        if rect_dp.isEmpty():
            return QPixmap()
        return bg.copy(rect_dp)
