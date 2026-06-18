"""
mini_ui_qt.py — PyQt6 replacement for the Tkinter Mini UI (mini_ui.py).

WHY (pilot for the dialogue-TUI migration)
-------------------------------------------
The Mini UI is a tiny always-on-top launcher bar (50×176, expand + play/pause +
status dot). It was the last *simple* Tkinter window in the app. Porting it to
PyQt6 first:
  1. proves the Qt patterns (frameless+translucent paint, theme/icon-invert,
     the Tk-method shim) on a small surface before the big dialogue TUI rewrite,
  2. removes one Tk consumer so the eventual `root.update()` poll removal is
     unblocked (only the transient splash stays Tk afterwards).

WHAT QT MAKES DISAPPEAR (vs. the Tk version)
--------------------------------------------
  - Win32 CreateRoundRectRgn + SetWindowRgn (right-only rounded corners) → a
    QPainterPath in paintEvent. No ctypes, no SetWindowRgn jank.
  - Win32 MonitorFromWindow (find the monitor's left edge) → QGuiApplication
    .screenAt(QPoint).geometry().left().
  - destroy + rebuild on theme change (Tk bakes colors at widget creation) →
    a live re-theme: invalidate the palette cache, re-load/re-invert icons,
    repaint. No window teardown, no position snapshot/restore needed.
  - PIL _invert_rgb_keep_alpha → pyqt_ui.styles.invert_pixmap.

CONTRACT (kept byte-compatible so MBB.py only changes its import line)
----------------------------------------------------------------------
  Wrapper `MiniUI(root, show_main_ui_callback)` exposes:
    set_toggle_translation_callback, create_mini_ui (= live re-theme),
    set_activity_state, update_translation_status, position_at_center_of_main,
    start_move_mini_ui / do_move_mini_ui (monkey-patch target — see below),
    .blink_interval, .is_translating, .mini_ui (Tk shim over the real window)
  MBB.py talks Tk to `self.mini_ui.mini_ui` (deiconify/withdraw/geometry/state/
  attributes/winfo_*/destroy) — those land on TkWindowShim (pyqt_ui/tk_compat.py).
"""

from __future__ import annotations

import logging
from types import SimpleNamespace

from PyQt6.QtCore import Qt, QTimer, QPoint, QRectF
from PyQt6.QtGui import (
    QColor,
    QGuiApplication,
    QIcon,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PyQt6.QtWidgets import (
    QGraphicsDropShadowEffect,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from appearance import appearance_manager
from resource_utils import resource_path
from pyqt_ui.styles import derive_palette, invert_pixmap, is_light_theme
from pyqt_ui.tk_compat import TkWindowShim

log = logging.getLogger("mini-ui-qt")

# ── Window geometry (matches the Tk original) ──
MINI_W = 50
MINI_H = 176
CORNER_R = 5  # px radius for the right-side corners (Tk used ellipse=10 ≈ 5px)

# Entrance-glow stroke layers (width_px, alpha 0-255), drawn in the theme ACCENT
# color: soft wide outer halo → bright narrow core. Widths are ~30% wider than
# the original 2px white border flash (user request 2026-06-18) — tune freely.
GLOW_LAYERS = ((11.0, 55), (6.5, 100), (3.5, 190))

# ── Status dot colors — SEMANTIC (not theme-derived), kept identical to the Tk
#    version + Main UI's [DALAMUD:*] signal so both views read the same. ──
_STATUS_IDLE = "#555555"         # gray  — translation OFF (Stop pressed)
_STATUS_ACTIVE = "#4CAF50"       # green — translation ON, awaiting next message
_STATUS_TRANSLATING = "#00FFFF"  # cyan  — message arriving / translation in flight


# ── Theme palette (mirrors mini_ui._themed — pure derive_palette, no Tkinter) ──
_THEME_CACHE: dict | None = None


def _themed(role: str) -> str:
    """Themed color by role, cached. Mirror of mini_ui._themed (same keys)."""
    global _THEME_CACHE
    if _THEME_CACHE is None:
        try:
            primary = appearance_manager.get_accent_color()
            secondary = appearance_manager.get_theme_color("secondary", "#888888")
            surface = appearance_manager.get_theme_color("surface_override")
            text_o = appearance_manager.get_theme_color("text_override")
            p = derive_palette(primary, secondary, surface=surface, text_override=text_o)
            _THEME_CACHE = {
                "bg": p["bg"],
                "border": p["border_subtle"],
                "text": p["text"],
                "medium": p["bg_medium"],
                "accent": p["accent"],
            }
        except Exception:
            _THEME_CACHE = {
                "bg": "#1a1a1a", "border": "#2a2a2a",
                "text": "#e0e0e0", "medium": "#2a2a2a", "accent": "#007AFF",
            }
    return _THEME_CACHE.get(role, "#888888")


def _refresh_mini_theme() -> None:
    """Invalidate the palette cache. MBB.py calls this on theme change before
    MiniUI.create_mini_ui() (kept import-compatible with the Tk module)."""
    global _THEME_CACHE
    _THEME_CACHE = None


def _rgba(hex_color: str, alpha: float) -> str:
    """'#rrggbb' → 'rgba(r,g,b,a)' for QSS hover/pressed accent tints. Low alpha
    keeps the (possibly inverted) icon readable over both light + dark bg."""
    h = (hex_color or "#000000").lstrip("#")
    if len(h) < 6:
        return f"rgba(0,0,0,{alpha})"
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


# ────────────────────────────────────────────────────────────────────
# The real window (paint + interaction)
# ────────────────────────────────────────────────────────────────────
class _QtMiniWindow(QWidget):
    """Frameless 50×176 launcher bar. Background + right-rounded corners painted
    in paintEvent; expand / play-pause buttons + status dot are child widgets."""

    def __init__(self, wrapper: "MiniUI"):
        super().__init__(parent=None)
        self._wrapper = wrapper

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(MINI_W, MINI_H)

        # Painted-surface state
        self._bg = _themed("bg")
        self._border_color = _themed("border")
        self._border_w = 1.0
        self._flashing = False  # True during the entrance accent-glow window

        # ── Children: expand button, play/pause button, status dot ──
        self._expand_btn = QPushButton(self)
        self._expand_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._expand_btn.clicked.connect(self._on_expand)

        self._play_btn = QPushButton(self)
        self._play_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._play_btn.clicked.connect(self._on_play_pause)

        self._dot = QLabel(self)
        self._dot.setFixedSize(10, 10)
        # Colored glow → adds "depth" to the status dot; color tracks the dot's
        # state color (set in set_dot). Single childless widget → no QTBUG-56081
        # drop-shadow ghosting.
        self._dot_glow = QGraphicsDropShadowEffect(self._dot)
        self._dot_glow.setBlurRadius(14)
        self._dot_glow.setOffset(0, 0)
        self._dot.setGraphicsEffect(self._dot_glow)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 16, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self._expand_btn, 0, Qt.AlignmentFlag.AlignHCenter)
        lay.addSpacing(10)
        lay.addWidget(self._play_btn, 0, Qt.AlignmentFlag.AlignHCenter)
        lay.addSpacing(12)
        lay.addWidget(self._dot, 0, Qt.AlignmentFlag.AlignHCenter)
        lay.addStretch(1)

        # ── Entrance accent-glow flash (1.2s on show) ──
        self._flash_timer = QTimer(self)
        self._flash_timer.setSingleShot(True)
        self._flash_timer.timeout.connect(self._end_flash)

        # ── Drag state lives in the wrapper (start_move/do_move) so MBB.py's
        #    monkey-patch of do_move_mini_ui keeps working. ──

        self.reload_theme()          # icons + button QSS + dot
        self.set_dot("idle")

        # Force native HWND creation now so the first move()/show() applies the
        # real position instead of flashing at the OS default (0,0). Same race
        # + fix as dissolve_overlay (see its __init__ winId() comment).
        self.winId()

    # ── theme / icons ──────────────────────────────────────────────
    def reload_theme(self) -> None:
        """Re-read palette, re-load (re-invert) icons, restyle buttons, repaint.
        This is the Qt 'live re-theme' that replaces the Tk destroy+rebuild."""
        self._bg = _themed("bg")
        self._border_color = _themed("border")
        invert = is_light_theme(self._bg)
        self._expand_btn.setIcon(self._icon("assets/expand.png", 32, invert))
        self._expand_btn.setIconSize(_qsize(32))
        self._play_btn.setIcon(
            self._icon("assets/pause.png" if self._wrapper.is_translating
                       else "assets/play.png", 22, invert))
        self._play_btn.setIconSize(_qsize(22))
        # Buttons stay transparent so the painted bg shows through; hover +
        # pressed tint with the THEME ACCENT (low alpha so the icon — possibly
        # inverted on light themes — stays readable). Tooltip is themed to match.
        accent = _themed("accent")
        btn_qss = (
            "QPushButton{background:transparent;border:none;border-radius:8px;}"
            f"QPushButton:hover{{background:{_rgba(accent, 0.30)};}}"
            f"QPushButton:pressed{{background:{_rgba(accent, 0.48)};}}"
            f"QToolTip{{background:{_themed('bg')};color:{_themed('text')};"
            f"border:1px solid {_themed('border')};border-radius:4px;"
            "padding:3px 6px;}"
        )
        self._expand_btn.setStyleSheet(btn_qss)
        self._play_btn.setStyleSheet(btn_qss)
        self._expand_btn.setFixedSize(40, 40)
        self._play_btn.setFixedSize(34, 34)
        self._expand_btn.setToolTip("ขยายเป็นหน้าต่างหลัก")
        self._play_btn.setToolTip(
            "หยุดการแปล" if self._wrapper.is_translating else "เริ่มการแปล")
        self.update()

    def _icon(self, path: str, size: int, invert: bool) -> QIcon:
        pm = QPixmap(resource_path(path))
        if not pm.isNull():
            pm = pm.scaled(
                size, size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            if invert:
                pm = invert_pixmap(pm)
        return QIcon(pm)

    def set_dot(self, state: str) -> None:
        color = {
            "idle": _STATUS_IDLE,
            "active": _STATUS_ACTIVE,
            "translating": _STATUS_TRANSLATING,
        }.get(state, _STATUS_IDLE)
        self._dot.setStyleSheet(f"background:{color};border-radius:5px;")
        self._dot_glow.setColor(QColor(color))

    def set_play_pause(self, is_translating: bool) -> None:
        invert = is_light_theme(self._bg)
        self._play_btn.setIcon(self._icon(
            "assets/pause.png" if is_translating else "assets/play.png", 22, invert))
        self._play_btn.setToolTip("หยุดการแปล" if is_translating else "เริ่มการแปล")

    # ── highlight flash ────────────────────────────────────────────
    def flash_highlight(self) -> None:
        """Accent-colored glow hugging the bar's edges for 1.2s — the 'I just
        appeared' cue (painted in paintEvent while _flashing is True)."""
        self._flashing = True
        self.update()
        self._flash_timer.start(1200)

    def _end_flash(self) -> None:
        self._flashing = False
        self.update()

    # ── paint: bg + right-rounded corners + border ─────────────────
    def paintEvent(self, event):  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        w, h = self.width(), self.height()
        inset = 0.5  # crisp 1px stroke
        rect = QRectF(inset, inset, w - 2 * inset, h - 2 * inset)
        r = float(CORNER_R)

        # Left edge square (touches screen edge), right edge rounded.
        path = QPainterPath()
        path.moveTo(rect.left(), rect.top())
        path.lineTo(rect.right() - r, rect.top())
        path.quadTo(rect.right(), rect.top(), rect.right(), rect.top() + r)
        path.lineTo(rect.right(), rect.bottom() - r)
        path.quadTo(rect.right(), rect.bottom(), rect.right() - r, rect.bottom())
        path.lineTo(rect.left(), rect.bottom())
        path.closeSubpath()

        # Subtle vertical gradient (top a touch lighter) → material "depth"
        # vs. a flat fill. Degrades to flat on light themes (can't go lighter
        # than near-white), which is fine.
        grad = QLinearGradient(0.0, 0.0, 0.0, float(h))
        grad.setColorAt(0.0, QColor(self._bg).lighter(112))
        grad.setColorAt(1.0, QColor(self._bg))
        p.fillPath(path, grad)

        # Entrance glow — accent-colored soft halo hugging the edges for 1.2s
        # after the bar appears (flash_highlight). Painted, not a graphics
        # effect, so it never rasterizes the child buttons/dot (QTBUG-56081).
        # The outward half of each wide stroke clips at the window edge —
        # harmless; what remains reads as an inner accent glow.
        if self._flashing:
            p.setBrush(Qt.BrushStyle.NoBrush)
            accent = QColor(_themed("accent"))
            for _gw, _ga in GLOW_LAYERS:
                c = QColor(accent)
                c.setAlpha(_ga)
                gpen = QPen(c)
                gpen.setWidthF(_gw)
                p.setPen(gpen)
                p.drawPath(path)

        pen = QPen(QColor(self._border_color))
        pen.setWidthF(self._border_w)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)
        p.end()

    # ── button slots ───────────────────────────────────────────────
    def _on_expand(self) -> None:
        cb = self._wrapper.show_main_ui_callback
        if callable(cb):
            cb()

    def _on_play_pause(self) -> None:
        self._wrapper._handle_toggle_translation()

    # ── drag (delegates to wrapper so MBB's monkey-patch is honored) ──
    # Pressing a child button consumes the event, so these only fire on the
    # window background — exactly the Tk behavior (drag on bg, click on buttons).
    def mousePressEvent(self, event):  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._wrapper.start_move_mini_ui(_tk_event(event))
            event.accept()

    def mouseMoveEvent(self, event):  # noqa: N802
        if event.buttons() & Qt.MouseButton.LeftButton:
            # Look up do_move_mini_ui on the wrapper at call time so MBB.py's
            # update_mini_ui_move() monkey-patch (wraps it to save positions) is
            # picked up.
            self._wrapper.do_move_mini_ui(_tk_event(event))
            event.accept()

    def mouseDoubleClickEvent(self, event):  # noqa: N802
        self._wrapper.show_main_ui_from_mini()
        event.accept()


def _qsize(n: int):
    from PyQt6.QtCore import QSize
    return QSize(n, n)


def _tk_event(qt_event):
    """Adapt a Qt mouse event into the (x_root, y_root) shape the Tk-era
    start_move_mini_ui / do_move_mini_ui handlers expect."""
    gp = qt_event.globalPosition().toPoint()
    return SimpleNamespace(x_root=int(gp.x()), y_root=int(gp.y()))


# ────────────────────────────────────────────────────────────────────
# Wrapper — same public surface as the Tk MiniUI
# ────────────────────────────────────────────────────────────────────
class MiniUI:
    def __init__(self, root, show_main_ui_callback):
        self.root = root  # kept for constructor parity; unused by the Qt path
        self.show_main_ui_callback = show_main_ui_callback
        self.blink_interval = 500
        self.is_translating = False
        self.toggle_translation_callback = None
        self._current_activity_state = "idle"

        # drag offset (set in start_move_mini_ui)
        self._drag_dx = 0
        self._drag_dy = 0

        self._window = _QtMiniWindow(self)
        # MBB.py reaches into `self.mini_ui.mini_ui` with Tk methods — that lands
        # on the shim, which forwards to the real window.
        self.mini_ui = TkWindowShim(self._window)
        self._window.hide()  # starts withdrawn, like the Tk original

    # ── callbacks ──────────────────────────────────────────────────
    def set_toggle_translation_callback(self, callback) -> None:
        self.toggle_translation_callback = callback

    def _handle_toggle_translation(self) -> None:
        if self.toggle_translation_callback:
            self.toggle_translation_callback()

    def show_main_ui_from_mini(self) -> None:
        self._window.hide()
        if callable(self.show_main_ui_callback):
            self.show_main_ui_callback()

    # ── theme (live re-theme; no destroy/rebuild) ──────────────────
    def create_mini_ui(self) -> None:
        """In the Tk version this destroyed + rebuilt the window. In Qt we just
        re-theme in place (the palette cache was already invalidated by MBB via
        _refresh_mini_theme). MBB's snapshot/restore around this call is a no-op
        here because the window is never torn down."""
        self._window.reload_theme()
        # Re-assert the dot for the current activity state (parity with the Tk
        # rebuild that re-applied the last-known dot).
        self._window.set_dot(self._current_activity_state)

    # ── status / activity dot ──────────────────────────────────────
    def set_activity_state(self, state: str) -> None:
        self._current_activity_state = state
        try:
            self._window.set_dot(state)
        except RuntimeError:
            pass

    def update_translation_status(self, is_translating: bool) -> None:
        """Switch play/pause icon + dot. Delegates the dot to set_activity_state
        so every caller shares one update path (no Start/Stop vs message skew)."""
        try:
            self.is_translating = is_translating
            self._window.set_play_pause(is_translating)
            self.set_activity_state("active" if is_translating else "idle")
        except RuntimeError:
            pass

    # ── positioning ────────────────────────────────────────────────
    def position_at_center_of_main(self, main_x, main_y, main_width, main_height) -> None:
        """Snap to the left edge of the monitor containing the main window, align
        Y with it, then flash the highlight border. (Qt screenAt replaces the
        Win32 MonitorFromWindow logic.)"""
        screen = (QGuiApplication.screenAt(QPoint(int(main_x), int(main_y)))
                  or QGuiApplication.primaryScreen())
        left = screen.geometry().left() if screen is not None else 0
        self._window.move(int(left), int(main_y))
        self._window.flash_highlight()

    # ── drag handlers (Tk-signature; mouse events feed these) ──────
    # MBB.update_mini_ui_move() monkey-patches do_move_mini_ui to append a
    # save_ui_positions() call — kept working by reading via the wrapper.
    def start_move_mini_ui(self, event) -> None:
        self._drag_dx = event.x_root - self.mini_ui.winfo_x()
        self._drag_dy = event.y_root - self.mini_ui.winfo_y()

    def do_move_mini_ui(self, event) -> None:
        x = event.x_root - self._drag_dx
        y = event.y_root - self._drag_dy
        self.mini_ui.geometry(f"+{x}+{y}")


# ────────────────────────────────────────────────────────────────────
# Standalone preview — `python mini_ui_qt.py`
# ────────────────────────────────────────────────────────────────────
def _demo():
    import sys
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    backdrop = QWidget()
    backdrop.setStyleSheet("background:#243044;")
    backdrop.resize(900, 500)
    backdrop.move(200, 200)
    backdrop.show()

    ui = MiniUI(root=None, show_main_ui_callback=lambda: print("expand clicked"))
    ui.set_toggle_translation_callback(
        lambda: ui.update_translation_status(not ui.is_translating))
    ui.mini_ui.deiconify()
    ui.position_at_center_of_main(250, 230, 300, 330)

    sys.exit(app.exec())


if __name__ == "__main__":
    _demo()
