"""
Choice Overlay — PyQt6 frameless TUI used for choice dialogues
(ChatType 0x0045 / 0x0046, content-detected by `_is_choice_dialogue`).

Replaces the Tk Canvas choice rendering in translated_ui._handle_choice_text.

Visual design — distinct from battle/cutscene (DissolveOverlay):
  - VERTICAL alpha-gradient background (top + bottom fade) — battle/cutscene
    fades left + right, this one fades top + bottom. Same dark base color.
  - Header line in gold (#FFD700) above the choices.
  - Each choice rendered as a "pill" — rounded rect with slightly brighter
    background than the container — for visual hierarchy.
  - Transient geometry (no save/restore). Position recomputed every show:
        x = center horizontally on primary screen
        y = 60.1% of screen height (preserves current Tk UX)
  - No drag, no resize, no UI buttons. Auto-hide after 10s (or ESC).
  - Hover prevention: if cursor inside overlay, auto-hide timer restarts.

Dispatcher rules (mirror DissolveOverlay):
  1. `_route_to_choice_overlay` MUST NOT touch translated_ui's mode flags.
  2. Mode change choice → other must call `hide_overlay()` and reset
     `_choice_overlay_active = False` before re-deiconifying Tk root.
  3. `MBB._do_tui_auto_show` MUST early-return when `_choice_overlay_active`.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from PyQt6.QtCore import (
    QAbstractAnimation,
    QEasingCurve,
    QPoint,
    QPropertyAnimation,
    QRect,
    QRectF,
    Qt,
    QTimer,
)
from PyQt6.QtGui import (
    QColor,
    QCursor,
    QFont,
    QFontDatabase,
    QFontMetrics,
    QLinearGradient,
    QPainter,
)
from PyQt6.QtWidgets import (
    QApplication,
    QPushButton,
    QWidget,
)

log = logging.getLogger("choice-overlay")


# ────────────────────────────────────────────────────────────────────
# Constants
# ────────────────────────────────────────────────────────────────────
VFADE_PCT = 0.10                  # 10% top, 10% bottom (5% too thin vertically)

BG_COLOR_RGB = (20, 22, 28)       # #14161c — same dark base as DissolveOverlay
BG_ALPHA = 242                    # ≈95% opaque — slight see-through to game scene

PILL_COLOR_RGB = (31, 36, 45)     # #1f242d — brighter than container ~5 lightness
PILL_ALPHA = 255                  # fully opaque — pills must stand out against
                                  # the semi-transparent BG so choices stay readable
PILL_RADIUS = 8
PILL_PADDING_X = 18
PILL_PADDING_Y = 12
PILL_GAP = 8

PADDING_X = 24
HEADER_MARGIN_BOTTOM = 14

HEADER_COLOR = "#FFD700"          # gold — preserved from current Tk renderer
HEADER_FONT_PT_OFFSET = 4         # body_pt + N for header
CHOICE_COLOR = "#FFFFFF"

AUTO_HIDE_MS = 10000
FADE_OUT_MS = 500
HOVER_POLL_MS = 140

DEFAULT_Y_FRACTION = 0.601        # 60.1% — matches current Tk choice default
MIN_W = 600
MAX_W_FRACTION = 0.70
WIDTH_BUFFER_PX = 60              # extra width over measured text

DEFAULT_BODY_PT = 22

CLOSE_BTN_SIZE = 22
CLOSE_BTN_MARGIN = 6

FONT_FAMILY_PREFERRED = "Anuphan"
FONT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "fonts", "Anuphan.ttf",
)


# ────────────────────────────────────────────────────────────────────
# Main overlay
# ────────────────────────────────────────────────────────────────────
class ChoiceOverlay(QWidget):
    """Frameless gradient overlay used for choice dialogues.

    Public API (called from translated_ui._route_to_choice_overlay):
        show_choice(header, choices)  — set content + show + restart auto-hide
        hide_overlay()                — instant hide (stops timers/anim)
        cleanup()                     — on app shutdown
    """

    def __init__(self, settings, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._settings = settings
        self._header: str = ""
        self._choices: list[str] = []
        self._cursor_inside = False
        # Drag-to-move state. Position is cached IN-MEMORY for the lifetime
        # of the app process (not persisted to settings.json) — once the user
        # drags the overlay to a comfortable spot, every subsequent choice in
        # the same session shows there. Reset on app restart.
        self._dragging = False
        self._drag_offset = QPoint()
        self._cached_pos: Optional[tuple[int, int]] = None

        # Window flags — frameless, always-on-top, no taskbar entry
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # Font registration + initial sizes
        self._font_family = self._load_font_family()
        self._apply_user_font_size()

        # ── Close button (hover-revealed, top-right) ──
        self._close_btn = QPushButton("✕", self)
        self._close_btn.setFixedSize(CLOSE_BTN_SIZE, CLOSE_BTN_SIZE)
        self._close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._close_btn.setToolTip("ปิดหน้าต่างนี้")
        self._close_btn.setStyleSheet(
            """
            QPushButton {
                background: rgba(0, 0, 0, 120);
                color: rgba(255, 255, 255, 200);
                border: none;
                border-radius: 4px;
                font-weight: bold;
                font-size: 11pt;
            }
            QPushButton:hover {
                background: #d23030;
                color: #ffffff;
            }
            """
        )
        self._close_btn.clicked.connect(self.hide_overlay)
        self._close_btn.setVisible(False)

        # Hover poll (Enter/Leave events flicker — see project_pyqt6_gotchas.md)
        self._hover_timer = QTimer(self)
        self._hover_timer.setInterval(HOVER_POLL_MS)
        self._hover_timer.timeout.connect(self._poll_hover)

        # Auto-hide timer
        self._auto_hide_timer = QTimer(self)
        self._auto_hide_timer.setSingleShot(True)
        self._auto_hide_timer.setInterval(AUTO_HIDE_MS)
        self._auto_hide_timer.timeout.connect(self._begin_auto_hide)

        # Fade-out animation
        self._fade_anim = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade_anim.setDuration(FADE_OUT_MS)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade_anim.finished.connect(self._on_fade_finished)

        # Force native HWND creation NOW — without this, first show races
        # against HWND creation and the overlay flashes at OS-default (0,0)
        # before queued setGeometry applies. Same fix as DissolveOverlay.
        self.winId()

    # ──────────────────────────────────────────────────────────────
    # Font loading
    # ──────────────────────────────────────────────────────────────
    def _apply_user_font_size(self) -> None:
        """Read settings['font_size'] (set by TUI FontPanel) and rebuild
        QFont objects. Called from __init__ and from show_choice so font
        changes pick up on next show."""
        try:
            raw = self._settings.get("font_size", DEFAULT_BODY_PT)
            body_pt = max(10, int(raw))
        except Exception:
            body_pt = DEFAULT_BODY_PT
        header_pt = body_pt + HEADER_FONT_PT_OFFSET
        self._font_body = QFont(self._font_family, body_pt)
        self._font_body.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
        self._font_header = QFont(self._font_family, header_pt, QFont.Weight.Bold)
        self._font_header.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)

    def _load_font_family(self) -> str:
        """Register Anuphan if not already loaded; fall back to system default."""
        try:
            if os.path.exists(FONT_PATH):
                font_id = QFontDatabase.addApplicationFont(FONT_PATH)
                if font_id != -1:
                    families = QFontDatabase.applicationFontFamilies(font_id)
                    if families:
                        return families[0]
        except Exception as e:
            log.debug(f"Anuphan registration skipped: {e}")
        return FONT_FAMILY_PREFERRED

    # ──────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────
    def show_choice(self, header: str, choices: list[str]) -> None:
        """Display a choice dialogue. Computes geometry from content,
        positions on screen, shows, restarts auto-hide timer."""
        self._header = (header or "").strip()
        self._choices = [c.strip() for c in (choices or []) if c.strip()]
        self._apply_user_font_size()

        if not self._choices:
            log.info("[CHOICE-DBG] show_choice: no choices to render → skip")
            return

        # ── Measure → compute width ──
        screen = QApplication.primaryScreen()
        if screen is None:
            log.warning("[CHOICE-DBG] no primary screen")
            return
        sg = screen.availableGeometry()
        max_w = int(sg.width() * MAX_W_FRACTION)

        body_metrics = QFontMetrics(self._font_body)
        header_metrics = QFontMetrics(self._font_header)
        longest_choice = max(
            (body_metrics.horizontalAdvance(c) for c in self._choices),
            default=0,
        )
        longest = max(
            header_metrics.horizontalAdvance(self._header),
            longest_choice + 2 * PILL_PADDING_X,
        )
        w = max(MIN_W, min(longest + 2 * PADDING_X + WIDTH_BUFFER_PX, max_w))

        # ── Measure → compute height ──
        # Each pill is single-line — height is constant regardless of choice text.
        # Pills shrink-to-fit the text horizontally (computed in paintEvent).
        single_line_h = body_metrics.height()
        pill_h = single_line_h + 2 * PILL_PADDING_Y
        total_pill_h = len(self._choices) * pill_h
        gap_h = (len(self._choices) - 1) * PILL_GAP if len(self._choices) > 1 else 0
        content_h = header_metrics.height() + HEADER_MARGIN_BOTTOM + total_pill_h + gap_h

        # Fade zones are a % of total height — solve iteratively:
        #   h = 2 * fade_zone(h) + content_h + 16  where fade_zone = h * VFADE_PCT + 8
        # Closed form: h * (1 - 2*VFADE_PCT) = content_h + 16 + 16
        h = int((content_h + 32) / (1.0 - 2.0 * VFADE_PCT))

        # ── Position: cached in-memory position OR center x + 60.1% screen y ──
        # Cache survives auto-hide/re-show within the same app session so the
        # user only needs to drag once per session. Reset on app restart.
        if self._cached_pos is not None:
            x, y = self._cached_pos
        else:
            x = sg.x() + (sg.width() - w) // 2
            y = sg.y() + int(sg.height() * DEFAULT_Y_FRACTION)
        # Clamp to screen so the cached position can't push window off-screen
        # (e.g. user changed display resolution between shows).
        max_x = sg.x() + sg.width() - w - 8
        max_y = sg.y() + sg.height() - h - 8
        x = max(sg.x() + 8, min(x, max_x))
        y = max(sg.y() + 8, min(y, max_y))

        log.info(
            f"[CHOICE-DBG] show_choice: header={self._header!r} "
            f"choices={len(self._choices)} geom=({x},{y},{w}x{h})"
        )

        # Cancel in-flight fade + restore opacity
        if self._fade_anim.state() == QAbstractAnimation.State.Running:
            self._fade_anim.stop()
        if self.windowOpacity() < 1.0:
            self.setWindowOpacity(1.0)

        self.setGeometry(x, y, w, h)
        self._reposition_close_btn()
        self.show()
        # Defensive: re-apply position AFTER show() in case Qt deferred the
        # pre-show setGeometry until the platform window existed. Same HWND
        # race fix as DissolveOverlay.show_for_mode.
        if (self.x(), self.y()) != (x, y):
            self.move(x, y)
        self.raise_()

        self._auto_hide_timer.start()
        self.update()

    def hide_overlay(self) -> None:
        """Instant hide — stops timers and fade animation."""
        if self._auto_hide_timer.isActive():
            self._auto_hide_timer.stop()
        if self._fade_anim.state() == QAbstractAnimation.State.Running:
            self._fade_anim.stop()
        self.setWindowOpacity(1.0)
        self.hide()
        log.info("[CHOICE-DBG] hide_overlay (manual)")

    def cleanup(self) -> None:
        """Called on app shutdown — stop all timers + animations."""
        for attr in ("_hover_timer", "_auto_hide_timer"):
            try:
                t = getattr(self, attr, None)
                if t is not None and t.isActive():
                    t.stop()
            except Exception:
                pass
        try:
            if self._fade_anim.state() == QAbstractAnimation.State.Running:
                self._fade_anim.stop()
        except Exception:
            pass

    # ──────────────────────────────────────────────────────────────
    # Auto-hide
    # ──────────────────────────────────────────────────────────────
    def _begin_auto_hide(self) -> None:
        """Start fade-out animation. On finish → hide.

        Hover prevention: if cursor inside, defer (restart timer)."""
        if not self.isVisible():
            return
        if self._cursor_inside:
            log.info("[CHOICE-DBG] auto_hide deferred: cursor inside overlay")
            self._auto_hide_timer.start()
            return
        if self._fade_anim.state() == QAbstractAnimation.State.Running:
            return
        log.info("[CHOICE-DBG] auto_hide START fade-out")
        self._fade_anim.stop()
        self._fade_anim.setStartValue(self.windowOpacity())
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.start()

    def _on_fade_finished(self) -> None:
        if self.windowOpacity() <= 0.05 and self.isVisible():
            log.info("[CHOICE-DBG] auto_hide COMPLETE → hide()")
            self.hide()
            self.setWindowOpacity(1.0)

    # ──────────────────────────────────────────────────────────────
    # Hover polling
    # ──────────────────────────────────────────────────────────────
    def _poll_hover(self) -> None:
        try:
            if not self.isVisible():
                return
            global_pos = QCursor.pos()
            local_pos = self.mapFromGlobal(global_pos)
            inside = self.rect().contains(local_pos)
            if inside != self._cursor_inside:
                self._cursor_inside = inside
                self._close_btn.setVisible(inside)
        except Exception as e:
            log.debug(f"_poll_hover failed: {e}")

    def _reposition_close_btn(self) -> None:
        """Place close button at top-right corner of the overlay."""
        try:
            self._close_btn.move(
                self.width() - CLOSE_BTN_SIZE - CLOSE_BTN_MARGIN,
                CLOSE_BTN_MARGIN,
            )
            self._close_btn.raise_()
        except Exception:
            pass

    def resizeEvent(self, event):  # noqa: N802
        # Keep close button glued to top-right when window size changes
        # (currently size is recomputed per show, but defensive for future).
        self._reposition_close_btn()
        super().resizeEvent(event)

    # ──────────────────────────────────────────────────────────────
    # Qt event handlers
    # ──────────────────────────────────────────────────────────────
    def showEvent(self, event):  # noqa: N802
        try:
            self._hover_timer.start()
        except Exception:
            pass
        super().showEvent(event)

    def hideEvent(self, event):  # noqa: N802
        try:
            self._hover_timer.stop()
        except Exception:
            pass
        try:
            if self._auto_hide_timer.isActive():
                self._auto_hide_timer.stop()
        except Exception:
            pass
        try:
            if self._fade_anim.state() == QAbstractAnimation.State.Running:
                self._fade_anim.stop()
        except Exception:
            pass
        super().hideEvent(event)

    def keyPressEvent(self, event):  # noqa: N802
        # ESC → instant hide
        if event.key() == Qt.Key.Key_Escape:
            self.hide_overlay()
            event.accept()
            return
        super().keyPressEvent(event)

    # ──────────────────────────────────────────────────────────────
    # Drag-to-move — overlay may cover the actual in-game choice UI,
    # so user must be able to drag it out of the way. Position is
    # transient (resets to default on next show — matches user's earlier
    # "no save" decision for choice mode).
    # ──────────────────────────────────────────────────────────────
    def mousePressEvent(self, event):  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            # Don't start drag if click landed on close button (let it handle)
            local = event.position().toPoint()
            if self._close_btn.geometry().contains(local):
                return
            self._dragging = True
            self._drag_offset = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            # Cancel pending auto-hide while user is interacting
            if self._auto_hide_timer.isActive():
                self._auto_hide_timer.stop()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):  # noqa: N802
        if self._dragging and (event.buttons() & Qt.MouseButton.LeftButton):
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):  # noqa: N802
        if self._dragging:
            self._dragging = False
            self.unsetCursor()
            # Cache drop position in memory for next show (this session only)
            self._cached_pos = (self.x(), self.y())
            log.info(f"[CHOICE-DBG] cached drop position: {self._cached_pos}")
            # Restart auto-hide countdown from drop point
            self._auto_hide_timer.start()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    # ──────────────────────────────────────────────────────────────
    # Painting
    # ──────────────────────────────────────────────────────────────
    def paintEvent(self, event):  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        w = self.width()
        h = self.height()

        # ── 1. Vertical gradient background ──
        base = QColor(BG_COLOR_RGB[0], BG_COLOR_RGB[1], BG_COLOR_RGB[2], BG_ALPHA)
        clear = QColor(BG_COLOR_RGB[0], BG_COLOR_RGB[1], BG_COLOR_RGB[2], 0)
        gradient = QLinearGradient(0.0, 0.0, 0.0, float(h))  # vertical
        gradient.setColorAt(0.00, clear)
        gradient.setColorAt(VFADE_PCT, base)
        gradient.setColorAt(1.0 - VFADE_PCT, base)
        gradient.setColorAt(1.00, clear)
        p.fillRect(self.rect(), gradient)

        if not self._header and not self._choices:
            p.end()
            return

        fade_zone = int(h * VFADE_PCT) + 8
        inner_w = max(50, w - 2 * PADDING_X)
        y = fade_zone

        # ── 2. Header (gold, left-aligned — matches original Tk anchor="nw") ──
        if self._header:
            p.setFont(self._font_header)
            p.setPen(QColor(HEADER_COLOR))
            h_metrics = QFontMetrics(self._font_header)
            header_rect = QRect(PADDING_X, y, inner_w, h_metrics.height())
            p.drawText(
                header_rect,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                self._header,
            )
            y += h_metrics.height() + HEADER_MARGIN_BOTTOM

        # ── 3. Pills — one per choice, shrink-to-fit horizontally ──
        # Each pill is exactly 1 line tall (no wrap). Pill width = text width
        # + paddings; pill is left-aligned within the container. If a choice
        # is longer than the available inner width, elide with "...".
        p.setFont(self._font_body)
        body_metrics = QFontMetrics(self._font_body)
        max_pill_text_w = max(20, inner_w - 2 * PILL_PADDING_X)
        single_line_h = body_metrics.height()
        pill_h = single_line_h + 2 * PILL_PADDING_Y
        pill_brush = QColor(
            PILL_COLOR_RGB[0], PILL_COLOR_RGB[1], PILL_COLOR_RGB[2], PILL_ALPHA,
        )
        text_color = QColor(CHOICE_COLOR)

        for choice in self._choices:
            # Snug-fit width: actual text advance, clamped to inner area.
            measured = body_metrics.horizontalAdvance(choice)
            pill_text_w = min(measured, max_pill_text_w)
            pill_w = pill_text_w + 2 * PILL_PADDING_X

            # Elide if the choice is too long to fit in one line
            display_text = (
                choice if measured <= max_pill_text_w
                else body_metrics.elidedText(
                    choice, Qt.TextElideMode.ElideRight, pill_text_w,
                )
            )

            # Pill background (left-aligned, shrink-wraps the text)
            p.setBrush(pill_brush)
            p.setPen(Qt.PenStyle.NoPen)
            pill_rect = QRectF(float(PADDING_X), float(y), float(pill_w), float(pill_h))
            p.drawRoundedRect(pill_rect, float(PILL_RADIUS), float(PILL_RADIUS))

            # Choice text inside pill — single line, vertical-centered
            p.setPen(text_color)
            text_rect = QRect(
                PADDING_X + PILL_PADDING_X,
                y + PILL_PADDING_Y,
                pill_text_w,
                single_line_h,
            )
            p.drawText(
                text_rect,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                display_text,
            )

            y += pill_h + PILL_GAP

        p.end()
