"""
Dissolve Overlay — PyQt6 frameless TUI used for battle (ChatType 68) and
cutscene (ChatType 71) translation display.

Replaces the Tkinter `translated_ui` window for those two modes only.
Dialogue mode (ChatType 61) keeps using the legacy Tkinter UI.

Visual design (proven in demo_dissolve_tui.py):
  - Frameless, always-on-top, translucent
  - Horizontal alpha-gradient background:
        0%   → fully transparent
        5%   → fully opaque dark tint  (FADE_PCT)
        95%  → fully opaque dark tint
        100% → fully transparent
    → soft "dissolve" feel into the game scene at the left + right edges
  - Text drawn fully opaque on top of the gradient
  - Per-mode font color (v1.8.8 — cutscene switched gold → turquoise):
        battle   → #FF6B00 (orange) — vivid alert/combat
        cutscene → #40E0D0 (turquoise) — cool, magical, cinematic
        Speaker color: battle uses WHITE for contrast; cutscene matches body.
  - Speaker name (smaller, same color, bold) above the dialogue line

Production additions over the demo:
  - set_text(text, speaker) — live updates from the translator pipeline
  - set_mode(mode)          — switches text color (battle vs cutscene)
  - show_for_mode(mode)     — loads per-mode size/pos from settings
  - Drag-to-move + bottom-right resize grip
  - Hover-revealed close (X) button in top-right
  - Position + size persisted to the SAME settings keys translated_ui uses
    ("tui_positions" / "tui_geometries") so user preferences stay in sync
  - Debounced disk writes (avoid thrash on every move/resize pixel)

Hover detection uses timer-based cursor polling (Enter/Leave on overlapping
sibling widgets flickers — see project_pyqt6_gotchas.md).
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
    QSize,
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
    QPolygon,
)
from PyQt6.QtWidgets import (
    QApplication,
    QPushButton,
    QWidget,
)

from resource_utils import resource_path

log = logging.getLogger("dissolve-overlay")


# ────────────────────────────────────────────────────────────────────
# Constants
# ────────────────────────────────────────────────────────────────────
DEFAULT_W_BATTLE = 1000
DEFAULT_H_BATTLE = 140
DEFAULT_W_CUTSCENE = 1400
DEFAULT_H_CUTSCENE = 160

MIN_W = 360
MIN_H = 90

FADE_PCT = 0.05                  # gradient fade zone (5% per side)
BG_COLOR_RGB = (20, 22, 28)      # Carbon-adjacent dark slate
BG_ALPHA = 252                   # 252/255 ≈ 99% opaque (v1.8.10 — was 230 ≈ 90%,
                                 # original game text was bleeding through during
                                 # FFXIV cutscenes / battle banners)

# Cutscene width is computed dynamically at show time as a fraction of the
# primary screen width (per user request: cutscene text should span most of
# the screen to handle long cinematic prose). Overrides any saved width
# (`tui_geometries["cutscene"]["w"]`) and re-centers position x.
CUTSCENE_WIDTH_FRACTION = 0.90

COLOR_BATTLE = "#FF6B00"         # vibrant orange — matches TUI v4
COLOR_CUTSCENE = "#40E0D0"       # turquoise — v1.8.8 (was gold #FFD700)
COLOR_SPEAKER_FALLBACK = "#FFE6C8"

CLOSE_BTN_SIZE = 22
GRIP_SIZE = 16

SAVE_DEBOUNCE_MS = 400           # debounce disk writes during drag/resize
HOVER_POLL_MS = 140              # cursor poll interval

# Auto-hide — battle/cutscene have NO "stay forever" option (per user
# requirement). After AUTO_HIDE_MS of no new text, fade out + hide.
# 10s matches the Tk TUI fade-timer default (translated_ui.start_fade_timer).
AUTO_HIDE_MS = 10000
FADE_OUT_MS = 500

FONT_FAMILY_PREFERRED = "Anuphan"
FONT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "fonts", "Anuphan.ttf",
)

DEFAULT_FONT_PT = 22             # body / dialogue font
SPEAKER_FONT_PT = 14             # smaller, above body


# ────────────────────────────────────────────────────────────────────
# Resize grip (small triangle in bottom-right)
# ────────────────────────────────────────────────────────────────────
class _ResizeGrip(QWidget):
    def __init__(self, target: "DissolveOverlay"):
        super().__init__(target)
        self._target = target
        self.setFixedSize(GRIP_SIZE, GRIP_SIZE)
        self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        self._dragging = False
        self._start_pos = QPoint()
        self._start_size = QSize()
        # Visible on hover only (managed by overlay's hover-state machine)
        self.setVisible(False)

    def paintEvent(self, event):  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        s = GRIP_SIZE
        m = 2
        tri = QPolygon([
            QPoint(s - m, m),
            QPoint(s - m, s - m),
            QPoint(m, s - m),
        ])
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(200, 200, 200, 170))
        p.drawPolygon(tri)
        p.end()

    def mousePressEvent(self, event):  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._start_pos = event.globalPosition().toPoint()
            self._start_size = self._target.size()
            event.accept()

    def mouseMoveEvent(self, event):  # noqa: N802
        if self._dragging:
            delta = event.globalPosition().toPoint() - self._start_pos
            new_w = max(MIN_W, self._start_size.width() + delta.x())
            new_h = max(MIN_H, self._start_size.height() + delta.y())
            self._target.resize(new_w, new_h)
            event.accept()

    def mouseReleaseEvent(self, event):  # noqa: N802
        if self._dragging:
            self._dragging = False
            self._target._schedule_save_geometry()
            event.accept()


# ────────────────────────────────────────────────────────────────────
# Main overlay
# ────────────────────────────────────────────────────────────────────
class DissolveOverlay(QWidget):
    """Frameless gradient overlay used for battle + cutscene translations.

    Public API (called from translated_ui.update_text dispatcher):
        set_mode(mode)              — "battle" | "cutscene"
        set_text(text, speaker="")  — update displayed dialogue
        show_for_mode(mode)         — load per-mode geometry, then show
        hide_overlay()              — hide and persist if needed
        cleanup()                   — flush settings, drop event filters
    """

    VALID_MODES = ("battle", "cutscene")

    def __init__(self, settings, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._settings = settings
        self._current_mode: str = "battle"
        self._text: str = ""
        self._speaker: str = ""
        self._is_lore: bool = False

        # Drag state
        self._dragging = False
        self._drag_offset = QPoint()
        # Hover state (controls grip + close button visibility)
        self._cursor_inside = False
        # Save-arming flag — saves are SUPPRESSED until the first show_for_mode
        # call. Without this, Qt's HWND creation (forced via winId() at the end
        # of __init__) fires a spurious moveEvent at the OS-default position
        # which would queue a save and overwrite the user's saved position.
        self._save_armed = False

        # Window flags — frameless, always-on-top, no taskbar entry
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMouseTracking(True)
        self.setMinimumSize(MIN_W, MIN_H)

        # Set up font (prefer Anuphan, register if needed)
        self._font_family = self._load_font_family()
        # Body font size tracks the TUI dialog's font (settings["font_size"]) so
        # battle/cutscene text matches the dialog mode that user just tuned.
        # Speaker label stays smaller, scaled relative to body.
        self._apply_user_font_size()

        # Initial color (battle by default — set_mode will pick the right one)
        self._text_color = QColor(COLOR_BATTLE)

        # Initial size (battle default — overridden by show_for_mode)
        self.resize(DEFAULT_W_BATTLE, DEFAULT_H_BATTLE)

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

        # ── Resize grip ──
        self._grip = _ResizeGrip(self)
        self._reposition_chrome()

        # ── Debounced settings save ──
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(SAVE_DEBOUNCE_MS)
        self._save_timer.timeout.connect(self._save_geometry_now)

        # ── Hover polling (Enter/Leave events flicker on overlapping siblings,
        #    so we poll cursor pos every HOVER_POLL_MS instead). ──
        self._hover_timer = QTimer(self)
        self._hover_timer.setInterval(HOVER_POLL_MS)
        self._hover_timer.timeout.connect(self._poll_hover)
        # Started in showEvent / stopped in hideEvent

        # ── Auto-hide — battle/cutscene MUST disappear after timeout. ──
        # User explicit requirement: no "stay forever" mode like dialogue,
        # because there's no UX for it (battle/cutscene text is event-driven).
        self._auto_hide_timer = QTimer(self)
        self._auto_hide_timer.setSingleShot(True)
        self._auto_hide_timer.setInterval(AUTO_HIDE_MS)
        self._auto_hide_timer.timeout.connect(self._begin_auto_hide)

        # Fade animation — soft visual cue before the overlay disappears.
        self._fade_anim = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade_anim.setDuration(FADE_OUT_MS)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade_anim.finished.connect(self._on_fade_finished)

        # Force native window handle creation NOW (at end of __init__ so all
        # timers/handlers exist before Qt fires the move/resize events that
        # follow HWND creation). Without this, the very first show_for_mode
        # races against HWND creation — setGeometry queues, show() creates
        # HWND at default (0,0), and the user sees the overlay flash at
        # top-left before the queued geometry catches up one frame later.
        # winId() forces HWND creation without showing, so the first real
        # show() applies setGeometry cleanly.
        self.winId()

    # ──────────────────────────────────────────────────────────────
    # Font loading
    # ──────────────────────────────────────────────────────────────
    def _apply_user_font_size(self) -> None:
        """Read settings['font_size'] (set by TUI dialog FontPanel) and rebuild
        the body + speaker QFont objects to match. Called from __init__ and
        from show_for_mode so font changes pick up on next mode show.

        Body size = user's TUI font size.
        Speaker size = body - 8 (keeps the visual hierarchy from the demo).
        """
        try:
            raw = self._settings.get("font_size", DEFAULT_FONT_PT)
            body_pt = max(10, int(raw))
        except Exception:
            body_pt = DEFAULT_FONT_PT
        speaker_pt = max(8, body_pt - 8)
        self._font_body = QFont(self._font_family, body_pt)
        self._font_body.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
        self._font_speaker = QFont(self._font_family, speaker_pt, QFont.Weight.Bold)
        self._font_speaker.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)

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
        # Fallback chain — Qt picks the first installed family
        for candidate in (FONT_FAMILY_PREFERRED, "Segoe UI", "Tahoma", "Arial"):
            return candidate
        return ""

    # ──────────────────────────────────────────────────────────────
    # Public API — called from the translator pipeline / dispatcher
    # ──────────────────────────────────────────────────────────────
    def set_mode(self, mode: str) -> None:
        """Switch text color based on chat type."""
        if mode not in self.VALID_MODES:
            log.warning(f"set_mode unknown mode: {mode!r}")
            return
        self._current_mode = mode
        if mode == "battle":
            self._text_color = QColor(COLOR_BATTLE)
        else:  # cutscene
            self._text_color = QColor(COLOR_CUTSCENE)
        self.update()

    def set_text(self, text: str, speaker: str = "", is_lore: bool = False) -> None:
        """Update the displayed text. Speaker is optional (empty string for
        cutscene narration). Triggers a single repaint.

        Restarts the auto-hide timer so the overlay disappears AUTO_HIDE_MS
        after the most recent text. Also cancels any in-progress fade so a
        late-arriving translation isn't masked behind a half-faded overlay.
        """
        self._text = (text or "").strip()
        self._speaker = (speaker or "").strip()
        self._is_lore = bool(is_lore)

        # Cancel a fade-out in progress (translation arrived while we were
        # disappearing) and snap opacity back to 100%.
        if self._fade_anim.state() == QAbstractAnimation.State.Running:
            self._fade_anim.stop()
        if self.windowOpacity() < 1.0:
            self.setWindowOpacity(1.0)

        # (Re)start auto-hide countdown — every new text resets the clock.
        self._auto_hide_timer.start()
        log.info(
            f"[DISSOLVE-DBG] set_text({self._current_mode}): "
            f"speaker={speaker!r} len={len(self._text)} "
            f"current_geom=({self.x()},{self.y()},{self.width()}x{self.height()}) "
            f"opacity={self.windowOpacity():.2f}"
        )
        self.update()

    def show_for_mode(self, mode: str) -> None:
        """Apply per-mode geometry from settings, set color, then show.

        Reads from the SAME settings keys translated_ui uses:
            settings["tui_geometries"][mode]  → {"w": int, "h": int}
            settings["tui_positions"][mode]   → {"x": int, "y": int}
        so user preferences saved in either UI carry over.
        """
        if mode not in self.VALID_MODES:
            log.warning(f"show_for_mode unknown mode: {mode!r}")
            return
        self.set_mode(mode)
        # Re-read TUI dialog font size — picks up FontPanel changes since last show
        self._apply_user_font_size()

        # Load size
        try:
            geometries = self._settings.get("tui_geometries", {}) or {}
        except Exception:
            geometries = {}
        if mode == "battle":
            default_w, default_h = DEFAULT_W_BATTLE, DEFAULT_H_BATTLE
        else:
            default_w, default_h = DEFAULT_W_CUTSCENE, DEFAULT_H_CUTSCENE
        size_dict = geometries.get(mode) or {}
        w = int(size_dict.get("w") or default_w)
        h = int(size_dict.get("h") or default_h)
        w = max(MIN_W, w)
        h = max(MIN_H, h)

        # Load position (default: centered horizontally, near top)
        try:
            positions = self._settings.get("tui_positions", {}) or {}
        except Exception:
            positions = {}
        pos_dict = positions.get(mode) or {}
        x = pos_dict.get("x")
        y = pos_dict.get("y")
        if not isinstance(x, int) or not isinstance(y, int):
            screen = QApplication.primaryScreen()
            if screen is not None:
                geo = screen.availableGeometry()
                x = geo.x() + (geo.width() - w) // 2
                # battle near top, cutscene near bottom
                if mode == "battle":
                    y = geo.y() + 80
                else:
                    y = geo.y() + geo.height() - h - max(80, geo.height() // 20)
            else:
                x, y = 100, 80

        # ── Cutscene: FORCE width = 90% of primary screen + recenter x ──
        # Overrides both saved geometry and DEFAULT_W_CUTSCENE. Saved height
        # is preserved (user-tunable), but width must hit 90% so long
        # cinematic prose isn't truncated. Position x is recomputed to keep
        # the overlay centered with the new (wider) width.
        if mode == "cutscene":
            try:
                _screen = QApplication.primaryScreen()
                if _screen is not None:
                    _geo = _screen.availableGeometry()
                    w = int(_geo.width() * CUTSCENE_WIDTH_FRACTION)
                    x = _geo.x() + (_geo.width() - w) // 2
            except Exception as e:
                log.debug(f"cutscene 90%-width recalc failed: {e}")

        # Clamp to primary screen so a stale saved position can't push the
        # window off-screen (e.g. user unplugged a monitor)
        x_clamped, y_clamped, w_clamped, h_clamped = self._clamp_to_screen(x, y, w, h)

        log.info(
            f"[DISSOLVE-DBG] show_for_mode({mode}): "
            f"loaded pos=({pos_dict.get('x')}, {pos_dict.get('y')}) "
            f"size=({size_dict.get('w')}, {size_dict.get('h')}) "
            f"→ clamped=({x_clamped},{y_clamped},{w_clamped}x{h_clamped})"
        )

        self.setGeometry(x_clamped, y_clamped, w_clamped, h_clamped)
        self._reposition_chrome()
        self.show()
        # Defensive: re-apply position AFTER show() in case Qt deferred the
        # pre-show setGeometry until the platform window existed. Without this,
        # the first show in a session can land at (0,0) even though winId() in
        # __init__ pre-creates the HWND. Cheap on subsequent shows (no-op move).
        if (self.x(), self.y()) != (x_clamped, y_clamped):
            self.move(x_clamped, y_clamped)
        self.raise_()
        # Arm save NOW — from this point real user move/resize events should
        # persist to settings. Cancel any pending save that may have been
        # queued by Qt internals during show() (defensive — _save_armed should
        # have been False the whole time, but no harm flushing).
        self._save_armed = True
        if self._save_timer.isActive():
            self._save_timer.stop()
        # We deliberately don't activateWindow() — game window must keep focus
        log.info(
            f"[DISSOLVE-DBG] show_for_mode({mode}) AFTER show: "
            f"actual_pos=({self.x()},{self.y()}) "
            f"expected=({x_clamped},{y_clamped}) "
            f"save_armed=True"
        )

    def hide_overlay(self) -> None:
        """Hide the overlay and flush any pending geometry save."""
        if self._save_timer.isActive():
            self._save_timer.stop()
            self._save_geometry_now()
        # Stop fade + auto-hide timers — caller wants instant hide
        if self._auto_hide_timer.isActive():
            self._auto_hide_timer.stop()
        if self._fade_anim.state() == QAbstractAnimation.State.Running:
            self._fade_anim.stop()
        self.setWindowOpacity(1.0)  # reset for next show
        self.hide()

    def cleanup(self) -> None:
        """Called on app shutdown — flush settings, stop timers."""
        try:
            if self._save_timer.isActive():
                self._save_timer.stop()
            self._save_geometry_now()
        except Exception:
            pass
        try:
            if self._hover_timer.isActive():
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

    # ──────────────────────────────────────────────────────────────
    # Auto-hide (timeout-driven, no opt-out)
    # ──────────────────────────────────────────────────────────────
    def _begin_auto_hide(self) -> None:
        """Start the fade-out animation. On finish → hide overlay.

        Called by self._auto_hide_timer after AUTO_HIDE_MS of inactivity.
        New `set_text` calls cancel this and snap opacity back to 100%.

        Concession: if cursor is currently inside the overlay, the user is
        likely dragging / resizing / about to close — restart the timer
        instead of hiding under their hand. Once they move away, auto-hide
        proceeds normally on the next tick.
        """
        if not self.isVisible():
            return
        if self._cursor_inside:
            # User is interacting — defer hide until they move away
            log.info(f"[DISSOLVE-DBG] auto_hide deferred: cursor inside overlay")
            self._auto_hide_timer.start()
            return
        # Already fading? Let it finish.
        if self._fade_anim.state() == QAbstractAnimation.State.Running:
            return
        log.info(f"[DISSOLVE-DBG] auto_hide START fade-out (mode={self._current_mode})")
        self._fade_anim.stop()
        self._fade_anim.setStartValue(self.windowOpacity())
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.start()

    def _on_fade_finished(self) -> None:
        """When the fade-out completes (opacity ≈ 0), actually hide the
        window. Reset opacity to 1.0 so the next show isn't invisible."""
        if self.windowOpacity() <= 0.05 and self.isVisible():
            log.info(f"[DISSOLVE-DBG] auto_hide COMPLETE → hide() (mode={self._current_mode})")
            self.hide()
            self.setWindowOpacity(1.0)

    # ──────────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────────
    def _clamp_to_screen(self, x: int, y: int, w: int, h: int):
        """Keep the window on the primary screen even if saved position is
        for a monitor that no longer exists."""
        screen = QApplication.primaryScreen()
        if screen is None:
            return x, y, w, h
        geo = screen.availableGeometry()
        # If the saved size is wider than the screen, shrink it
        w = min(w, geo.width())
        h = min(h, geo.height())
        # Clamp position
        x = max(geo.x(), min(geo.x() + geo.width() - w, x))
        y = max(geo.y(), min(geo.y() + geo.height() - h, y))
        return x, y, w, h

    def _reposition_chrome(self) -> None:
        """Place close button (top-right) and resize grip (bottom-right)."""
        margin = 4
        # Close button — top-right
        self._close_btn.move(
            self.width() - CLOSE_BTN_SIZE - margin,
            margin,
        )
        # Resize grip — bottom-right
        self._grip.move(
            self.width() - GRIP_SIZE - margin,
            self.height() - GRIP_SIZE - margin,
        )
        self._close_btn.raise_()
        self._grip.raise_()

    def _schedule_save_geometry(self) -> None:
        """Restart debounce timer — disk save fires after the user stops
        moving/resizing for SAVE_DEBOUNCE_MS.

        Suppressed when `_save_armed = False` — that's the case during
        __init__ (so winId()'s spurious move events don't overwrite the
        user's saved position) and after `cleanup()`.
        """
        if not self._save_armed:
            return
        self._save_timer.start()

    def _save_geometry_now(self) -> None:
        """Persist current pos+size into the same settings keys that
        translated_ui uses, so they stay in sync between UIs."""
        try:
            mode = self._current_mode
            # Position
            try:
                positions = self._settings.get("tui_positions", {}) or {}
            except Exception:
                positions = {}
            if not isinstance(positions, dict):
                positions = {}
            positions[mode] = {"x": int(self.x()), "y": int(self.y())}
            self._settings.set("tui_positions", positions, save_immediately=False)

            # Size
            try:
                geometries = self._settings.get("tui_geometries", {}) or {}
            except Exception:
                geometries = {}
            if not isinstance(geometries, dict):
                geometries = {}
            geometries[mode] = {"w": int(self.width()), "h": int(self.height())}
            self._settings.set("tui_geometries", geometries, save_immediately=True)
            log.info(
                f"[DISSOLVE-DBG] OVERLAY saved {mode}: "
                f"pos=({int(self.x())},{int(self.y())}) "
                f"size=({int(self.width())}x{int(self.height())})"
            )
        except Exception as e:
            log.debug(f"save_geometry_now failed: {e}")

    # ──────────────────────────────────────────────────────────────
    # Hover polling
    # ──────────────────────────────────────────────────────────────
    def _poll_hover(self) -> None:
        """Show/hide chrome (close + grip) based on cursor position.

        Why poll instead of using enterEvent/leaveEvent: when the close button
        and grip are children of the overlay, moving the cursor onto them
        causes the overlay's leaveEvent to fire (since the cursor is now on a
        child). This makes Enter/Leave-driven visibility flicker (per
        project_pyqt6_gotchas.md). A QTimer poll on global cursor pos sidesteps
        the entire issue.
        """
        try:
            if not self.isVisible():
                return
            global_pos = QCursor.pos()
            local_pos = self.mapFromGlobal(global_pos)
            inside = self.rect().contains(local_pos)
            if inside != self._cursor_inside:
                self._cursor_inside = inside
                self._close_btn.setVisible(inside)
                self._grip.setVisible(inside)
        except Exception as e:
            log.debug(f"_poll_hover failed: {e}")

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
        # Stop auto-hide + fade so a hidden window doesn't keep firing
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
        # Reset hover state + opacity so next show starts clean
        self._cursor_inside = False
        self._close_btn.setVisible(False)
        self._grip.setVisible(False)
        if self.windowOpacity() < 1.0:
            self.setWindowOpacity(1.0)
        super().hideEvent(event)

    def resizeEvent(self, event):  # noqa: N802
        super().resizeEvent(event)
        self._reposition_chrome()
        self._schedule_save_geometry()

    def moveEvent(self, event):  # noqa: N802
        super().moveEvent(event)
        # Only debounce-save when actually moved (not on initial layout from
        # show_for_mode — but it's harmless either way; debounce collapses).
        self._schedule_save_geometry()

    # ─── Drag-to-move (anywhere on the body, but not on chrome) ───
    def mousePressEvent(self, event):  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            # Don't start drag if click landed on close button or grip
            local = event.position().toPoint()
            if self._close_btn.geometry().contains(local):
                return  # button handles it
            if self._grip.geometry().contains(local):
                return  # grip handles it
            self._dragging = True
            self._drag_offset = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )
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
            self._schedule_save_geometry()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    # ──────────────────────────────────────────────────────────────
    # Paint — gradient bg + speaker label + dialogue
    # ──────────────────────────────────────────────────────────────
    def paintEvent(self, event):  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        w = self.width()
        h = self.height()

        # ── 1. Background gradient (alpha fade on both edges) ──
        base = QColor(BG_COLOR_RGB[0], BG_COLOR_RGB[1], BG_COLOR_RGB[2], BG_ALPHA)
        clear = QColor(BG_COLOR_RGB[0], BG_COLOR_RGB[1], BG_COLOR_RGB[2], 0)

        gradient = QLinearGradient(0.0, 0.0, float(w), 0.0)
        gradient.setColorAt(0.00, clear)
        gradient.setColorAt(FADE_PCT, base)
        gradient.setColorAt(1.0 - FADE_PCT, base)
        gradient.setColorAt(1.00, clear)
        p.fillRect(self.rect(), gradient)

        # ── 2. Text content ──
        if not self._text and not self._speaker:
            p.end()
            return

        # Inner padding — matches the gradient plateau (5% on each side) so
        # text never spills onto the dissolved edges
        pad_x = max(int(w * FADE_PCT) + 12, 24)
        pad_y = 12
        inner_w = max(50, w - 2 * pad_x)

        # Body color = mode color (orange for battle, turquoise for cutscene)
        body_color = QColor(self._text_color)

        # Speaker color rule (v1.8.8 visual update):
        #   - battle  → WHITE (#FFFFFF) — high contrast vs the orange body text,
        #               makes the speaker name pop out as a "label" against the
        #               translation it owns
        #   - cutscene → mode color (turquoise) — keeps the cinematic single-tone
        #                feel; cutscene speakers are often empty (narration) anyway
        # The lore override below wins over both — never break that.
        if self._current_mode == "battle":
            speaker_color = QColor("#FFFFFF")
        else:  # cutscene (or any future mode that's not battle)
            speaker_color = QColor(self._text_color)

        speaker = self._speaker
        # Lore items get a dim grey speaker+body regardless of mode color
        if self._is_lore:
            speaker = ""
            body_color = QColor("#cccccc")
            speaker_color = QColor("#cccccc")

        # Layout: speaker line on top, dialogue below.
        # If no speaker → dialogue centered vertically across the full inner area.
        speaker_line_h = 0
        speaker_metrics = QFontMetrics(self._font_speaker)
        body_metrics = QFontMetrics(self._font_body)

        if speaker:
            speaker_line_h = speaker_metrics.height()

        spacing = 2 if speaker else 0
        # Use boundingRect with TextWordWrap to know how many lines we need
        body_rect_full = QRect(0, 0, inner_w, max(1, h - 2 * pad_y - speaker_line_h - spacing))
        body_bounding = body_metrics.boundingRect(
            body_rect_full,
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop
            | Qt.TextFlag.TextWordWrap,
            self._text,
        )
        body_h = body_bounding.height()
        # Cap to available height — elide if necessary
        max_body_h = h - 2 * pad_y - speaker_line_h - spacing
        if body_h > max_body_h and max_body_h > 0:
            body_h = max_body_h

        block_h = speaker_line_h + spacing + body_h
        # Center the speaker+body block vertically in the overlay so the text
        # sits in the middle of the dissolve gradient. pad_y is the floor —
        # if the block is taller than (h - 2*pad_y), it pins to the top edge.
        block_top = max(pad_y, (h - block_h) // 2)

        # ── 2a. Speaker (centered, smaller, bold, mode color) ──
        if speaker:
            p.setFont(self._font_speaker)
            p.setPen(speaker_color)
            sp_rect = QRect(pad_x, block_top, inner_w, speaker_line_h)
            # Long speaker names — elide rather than wrap (it's chrome)
            elided_speaker = speaker_metrics.elidedText(
                speaker, Qt.TextElideMode.ElideRight, inner_w,
            )
            p.drawText(
                sp_rect,
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
                elided_speaker,
            )

        # ── 2b. Dialogue (centered, body font, mode color) ──
        p.setFont(self._font_body)
        p.setPen(body_color)
        body_rect = QRect(
            pad_x,
            block_top + speaker_line_h + spacing,
            inner_w,
            body_h,
        )
        p.drawText(
            body_rect,
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop
            | Qt.TextFlag.TextWordWrap,
            self._text,
        )

        p.end()

    # ──────────────────────────────────────────────────────────────
    # Keyboard — ESC to hide
    # ──────────────────────────────────────────────────────────────
    def keyPressEvent(self, event):  # noqa: N802
        if event.key() == Qt.Key.Key_Escape:
            self.hide_overlay()
            return
        super().keyPressEvent(event)
