"""
translated_ui_qt.py — PyQt6 dialogue TUI (ChatType 61). MAIN-WORK migration of
the Tkinter `Translated_UI` (translated_ui.py, ~8.3k lines).

STATUS: Phase 1 — window + diffuse paint + geometry + contract surface. Built on
the proven dissolve_overlay patterns (winId() HWND pre-create, _save_armed,
hover-poll grip, debounced geometry save) + the shared tk_compat shim. Standalone
runnable (`python pyqt_ui/translated_ui_qt.py`); NOT yet wired into MBB.py.

Later phases (see task list / project_tui_qt_migration memory):
  P2 text rendering (typewriter, *italic*/**highlight**, name colors, overflow)
  P3 chrome (rail buttons, color/alpha picker, click-name→NPC, lock, resize save)
  P4 dispatcher + mode-switch coordination (FLOWFIX_8 chain-memory)
  P5 integration behind a feature flag

WHY Qt: dialogue needs a feathered/diffuse background — Tk's `transparentcolor`
is a 1-bit colour key (no per-pixel alpha), so it can't feather. The diffuse
QRadialGradient below is the whole point of moving this mode to Qt.

CONTRACT: mirrors Translated_UI's constructor (14 args) + the methods/attrs
MBB.py touches. `.root` is a TkWindowShim so MBB's `self.translated_ui.root.*`
Tk calls keep working untouched. See project_tui_qt_migration memory.
"""

from __future__ import annotations

# Standalone-preview bootstrap: `python pyqt_ui/translated_ui_qt.py` puts pyqt_ui/
# on sys.path[0], so the app-root imports below (resource_utils, tui_rich_text)
# wouldn't resolve. Add python-app/ to the path when run as a script. No-op when
# imported as pyqt_ui.translated_ui_qt (the normal in-app path).
if __package__ in (None, ""):
    import os as _os
    import sys as _sys
    _sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))

import logging
from dataclasses import dataclass
from typing import Any, Callable, Optional

from PyQt6.QtCore import (
    QAbstractAnimation,
    QPoint,
    QPropertyAnimation,
    QRect,
    QRectF,
    QSize,
    Qt,
    QTimer,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QColor,
    QCursor,
    QFont,
    QFontDatabase,
    QFontMetrics,
    QIcon,
    QImage,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QPolygon,
    QTextDocument,
)
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from resource_utils import resource_path
from tui_rich_text import RichTextFormatter
from pyqt_ui.styles import invert_pixmap, is_light_theme
from pyqt_ui.tk_compat import TkWindowShim

log = logging.getLogger("translated-ui-qt")

# Font registration (Anuphan body + FC Minimal italic) — idempotent. PyQt6 needs
# addApplicationFont so the HTML font-family in _segments_to_html resolves.
_FONTS_READY = False
_ITALIC_FAMILY = "FC Minimal Medium"


def _ensure_fonts():
    global _FONTS_READY, _ITALIC_FAMILY
    if _FONTS_READY:
        return
    for rel in ("fonts/Anuphan.ttf", "fonts/FC Minimal.ttf"):
        try:
            fid = QFontDatabase.addApplicationFont(resource_path(rel))
            fams = QFontDatabase.applicationFontFamilies(fid) if fid != -1 else []
            if "Minimal" in rel and fams:
                _ITALIC_FAMILY = fams[0]
        except Exception:
            pass
    _FONTS_READY = True


def _rgba(hex_color: str, alpha: float) -> str:
    """'#rrggbb' → 'rgba(r,g,b,a)' for QSS accent hover tints."""
    h = (hex_color or "#000000").lstrip("#")
    if len(h) < 6:
        return f"rgba(0,0,0,{alpha})"
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"

# ── constants ──
MODE_KEY = "dialog"                      # settings sub-key (NOT "dialogue")
NAME_COLOR_KNOWN = "#38bdf8"             # cyan — speaker is a known character
NAME_COLOR_UNKNOWN = "#a855f7"           # purple — unknown / contains "?"
NAME_LINE_ALPHA = 130                    # white underline beneath the speaker name
NAME_LINE_EXTRA_CHARS = 4                # underline runs this many char-widths past
NAME_LINE_TAPER = 0.44                   # fade fraction per end (→0.5 = sharper taper)
DEFAULT_BG = "#0b0f14"
DEFAULT_BG_ALPHA = 0.97
DEFAULT_FONT = "Anuphan"
DEFAULT_FONT_SIZE = 24
DEFAULT_W = 600
DEFAULT_H = 150
MIN_W = 280
MIN_H = 90
GRIP_SIZE = 16
SAVE_DEBOUNCE_MS = 400
HOVER_POLL_MS = 140
TYPE_BASE_MS = 15                        # typewriter base delay (matches Tk type_writer_effect)
AUTO_HIDE_MS = 10000                     # fade out + hide after this idle time
FADE_OUT_MS = 500
# Diffuse radial-gradient shape (fraction of size). cy below centre so the halo
# sits a touch low, matching where dialogue text usually lands.
FEATHER_PX = 30                          # soft-edge band width (px) for diffuse bg
EDGE_FALLOFF = 1.8                        # >1 → outermost edge fades nearer to 0
BG_RADIUS = 16                           # rounded-corner radius
GRIP_MARGIN = FEATHER_PX - 6             # inset resize grip onto the SOLID bar,
                                         # clear of the transparent feathered halo
RAIL_BTN = 20                            # rail icon-button size
RAIL_GAP = 4                             # gap between rail buttons
PAD_L = 22                               # left text padding
PAD_R = 48                               # right padding (room for the rail)
PAD_Y = 16                               # top/bottom text padding


@dataclass
class _UIState:
    """The subset of the Tk UIState that MBB.py reads/writes + the fade system
    needs. Kept local so this module stays independent of the Tk translated_ui
    (parallel migration — D1)."""
    is_window_hidden: bool = False
    is_fading: bool = False
    just_faded_out: bool = False
    fade_timer_id: Optional[object] = None
    window_hide_timer_id: Optional[object] = None
    last_activity_time: float = 0.0
    fadeout_enabled: bool = True
    auto_hide_after_fade: bool = True


# ────────────────────────────────────────────────────────────────────
# Resize grip (bottom-right) — adapted from dissolve_overlay._ResizeGrip
# ────────────────────────────────────────────────────────────────────
class _ResizeGrip(QWidget):
    def __init__(self, target: "TranslatedUIQt"):
        super().__init__(target)
        self._target = target
        self.setFixedSize(GRIP_SIZE, GRIP_SIZE)
        self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        self._dragging = False
        self._start = QPoint()
        self._start_size = None
        self.setVisible(False)

    def paintEvent(self, event):  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        s = GRIP_SIZE
        m = 2
        tri = QPolygon([QPoint(s - m, m), QPoint(s - m, s - m), QPoint(m, s - m)])
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(200, 200, 200, 170))
        p.drawPolygon(tri)
        p.end()

    def mousePressEvent(self, event):  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._start = event.globalPosition().toPoint()
            self._start_size = self._target.size()
            event.accept()

    def mouseMoveEvent(self, event):  # noqa: N802
        if self._dragging:
            delta = event.globalPosition().toPoint() - self._start
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
# Colour + transparency popup (mirrors the Tk ImprovedColorAlphaPickerWindow:
# 6 step-locked transparency levels + a bg-colour pick, applied live)
# ────────────────────────────────────────────────────────────────────
class _ColorAlphaModal(QDialog):
    STEPS = (50, 80, 92, 100)

    def __init__(self, parent, cur_hex, cur_pct, apply_cb):
        super().__init__(parent)
        self._apply_cb = apply_cb
        self._hex = cur_hex if (isinstance(cur_hex, str) and cur_hex.startswith("#")) else DEFAULT_BG
        self._pct = min(self.STEPS, key=lambda s: abs(s - cur_pct))
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setStyleSheet(
            "QDialog{background:#1b1f27;border:1px solid #2a3340;border-radius:8px;}"
            "QLabel{color:#cfd8e3;font:600 10pt 'Segoe UI';}"
        )
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(8)
        lay.addWidget(QLabel("ความโปร่งใสพื้นหลัง"))
        row = QHBoxLayout()
        row.setSpacing(4)
        self._step_btns = {}
        for s in self.STEPS:
            b = QPushButton(f"{s}%")
            b.setFixedSize(46, 26)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _=False, v=s: self._set_pct(v))
            row.addWidget(b)
            self._step_btns[s] = b
        lay.addLayout(row)
        crow = QHBoxLayout()
        crow.setSpacing(8)
        crow.addWidget(QLabel("สีพื้นหลัง"))
        self._swatch = QLabel()
        self._swatch.setFixedSize(40, 22)
        crow.addWidget(self._swatch)
        cbtn = QPushButton("เลือกสี…")
        cbtn.setFixedHeight(26)
        cbtn.setCursor(Qt.CursorShape.PointingHandCursor)
        cbtn.setStyleSheet("QPushButton{background:#262c36;color:#cfd8e3;border:none;"
                           "border-radius:5px;padding:0 10px;font:600 9pt 'Segoe UI';}"
                           "QPushButton:hover{background:#374252;}")
        cbtn.clicked.connect(self._pick_color)
        crow.addWidget(cbtn)
        crow.addStretch(1)
        lay.addLayout(crow)
        self._refresh()

    def _refresh(self):
        for s, b in self._step_btns.items():
            on = (s == self._pct)
            b.setStyleSheet(
                f"QPushButton{{background:{'#2f6df0' if on else '#262c36'};"
                f"color:{'#ffffff' if on else '#cfd8e3'};border:none;border-radius:5px;"
                "font:600 9pt 'Segoe UI';}QPushButton:hover{background:#374252;}")
        self._swatch.setStyleSheet(
            f"background:{self._hex};border:1px solid #3a4150;border-radius:4px;")

    def _set_pct(self, v):
        self._pct = v
        self._refresh()
        self._apply_cb(self._hex, v)

    def _pick_color(self):
        from PyQt6.QtWidgets import QColorDialog
        c = QColorDialog.getColor(QColor(self._hex), self, "เลือกสีพื้นหลัง")
        if c.isValid():
            self._hex = c.name()
            self._refresh()
            self._apply_cb(self._hex, self._pct)


# ────────────────────────────────────────────────────────────────────
# Dialogue TUI
# ────────────────────────────────────────────────────────────────────
class TranslatedUIQt(QWidget):
    """PyQt6 dialogue TUI. Same constructor + public surface as Translated_UI."""

    # Thread-safe text update — translator pipeline runs off the UI thread.
    _text_update = pyqtSignal(str, bool, int)  # text, is_lore, chat_type

    def __init__(
        self,
        root=None,
        toggle_translation: Optional[Callable] = None,
        stop_translation: Optional[Callable] = None,
        previous_dialog_callback: Optional[Callable] = None,
        toggle_main_ui: Optional[Callable] = None,
        toggle_ui: Optional[Callable] = None,
        settings: Any = None,
        switch_area: Optional[Callable] = None,
        logging_manager: Any = None,
        character_names: Optional[set] = None,
        main_app=None,
        font_settings=None,
        toggle_npc_manager_callback: Optional[Callable] = None,
        on_close_callback: Optional[Callable] = None,
    ):
        super().__init__(parent=None)

        # ── store the same references the Tk version kept ──
        self.toggle_translation = toggle_translation
        self.stop_translation = stop_translation
        self.previous_dialog_callback = None  # Tk sets this to None too (line 214)
        self.toggle_main_ui = toggle_main_ui
        self.toggle_ui = toggle_ui
        self.settings = settings
        self.switch_area = switch_area
        self.logging_manager = logging_manager
        self.names = character_names or set()
        self.main_app = main_app
        self.font_settings = font_settings
        self.toggle_npc_manager_callback = toggle_npc_manager_callback
        self.on_close_callback = on_close_callback

        # ── contract attributes MBB.py touches directly ──
        self.lock_mode = 0
        self._closing_from_f9 = False
        self.state = _UIState()
        # overlays wired externally (unchanged); coordination flags for P4
        self.dissolve_overlay = None
        self.choice_overlay = None
        self._dissolve_active = False
        self._tk_was_visible_before_dissolve = False
        self._choice_overlay_active = False
        self._tk_was_visible_before_choice = False
        self.current_chat_type = 61

        # ── visual state ──
        _ensure_fonts()
        self._style = "diffuse"            # "diffuse" | "box"
        self._text = ""
        self._speaker = ""
        self._is_lore = False
        self._rich = RichTextFormatter()   # Tk-free segmenter, reused as-is
        self._segments = []                # parsed body segments
        self._type_text = ""               # joined body text for the typewriter
        self._doc = None                   # QTextDocument for the body
        self._typed_chars = 0              # typewriter reveal count
        self._total_chars = 0
        self._typing = False
        self._name_rect = QRect()          # speaker-name hit area (click → NPC mgr)
        self._font_family = self._setting("font", DEFAULT_FONT)
        self._font_size = int(self._setting("font_size", DEFAULT_FONT_SIZE))
        self._bg_rgb = self._load_bg_rgb()
        self._bg_alpha = self._load_bg_alpha()
        self._bg_pixmap = None             # cached feathered background

        # ── drag / save state ──
        self._dragging = False
        self._drag_offset = QPoint()
        self._cursor_inside = False
        self._save_armed = False

        self._init_window()

        self._grip = _ResizeGrip(self)

        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(SAVE_DEBOUNCE_MS)
        self._save_timer.timeout.connect(self._save_geometry_now)

        self._hover_timer = QTimer(self)
        self._hover_timer.setInterval(HOVER_POLL_MS)
        self._hover_timer.timeout.connect(self._poll_hover)

        self._type_timer = QTimer(self)
        self._type_timer.timeout.connect(self._typewriter_tick)

        # Fade-out + auto-hide (Tk fadeout principle): AUTO_HIDE_MS after the
        # last text, fade the window out then hide it. Toggled by the rail
        # fadeout button.
        self._fade_enabled = True
        self._autohide_timer = QTimer(self)
        self._autohide_timer.setSingleShot(True)
        self._autohide_timer.setInterval(AUTO_HIDE_MS)
        self._autohide_timer.timeout.connect(self._begin_fade)
        self._fade_anim = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade_anim.setDuration(FADE_OUT_MS)
        self._fade_anim.finished.connect(self._on_fade_finished)

        self._rail = {}
        self._build_rail()

        self._restore_geometry()
        self._reposition_chrome()

        self._text_update.connect(self._dispatch)

        # the shim MBB.py / overlays call Tk methods on
        self.root = TkWindowShim(self)

        # Force HWND now so the first show() applies the saved geometry instead
        # of flashing at OS-default (same race + fix as dissolve_overlay).
        self.winId()

    # ── settings helpers ────────────────────────────────────────────
    def _setting(self, key, default):
        try:
            return self.settings.get(key, default)
        except Exception:
            return default

    def _load_bg_rgb(self):
        hexv = self._setting("bg_color", None)
        if not (isinstance(hexv, str) and hexv.startswith("#") and len(hexv) == 7):
            try:
                from appearance import appearance_manager
                hexv = appearance_manager.bg_color
            except Exception:
                hexv = DEFAULT_BG
        try:
            return (int(hexv[1:3], 16), int(hexv[3:5], 16), int(hexv[5:7], 16))
        except Exception:
            h = DEFAULT_BG.lstrip("#")
            return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))

    def _load_bg_alpha(self):
        a = self._setting("bg_alpha", DEFAULT_BG_ALPHA)
        try:
            return int(max(0.0, min(1.0, float(a))) * 255)
        except Exception:
            return int(DEFAULT_BG_ALPHA * 255)

    # ── window / chrome ─────────────────────────────────────────────
    def _init_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMouseTracking(True)
        self.setMinimumSize(MIN_W, MIN_H)
        w = int(self._setting("width", DEFAULT_W) or DEFAULT_W)
        h = int(self._setting("height", DEFAULT_H) or DEFAULT_H)
        self.resize(max(MIN_W, w), max(MIN_H, h))

    # ── hover-revealed icon rail (close/lock/color/fadeout/log) ─────
    def _accent(self):
        try:
            from appearance import appearance_manager
            c = appearance_manager.get_accent_color()
            if isinstance(c, str) and c.startswith("#"):
                return c
        except Exception:
            pass
        return NAME_COLOR_KNOWN

    def _icon(self, filename, size=RAIL_BTN - 4):
        pm = QPixmap(resource_path(f"assets/{filename}"))
        if pm.isNull():
            return QIcon()
        pm = pm.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio,
                       Qt.TransformationMode.SmoothTransformation)
        # White-line icons → invert on a light dialogue background.
        if is_light_theme("#%02x%02x%02x" % self._bg_rgb):
            pm = invert_pixmap(pm)
        return QIcon(pm)

    def _build_rail(self):
        """Vertical icon rail mirroring the Tk dialogue control column."""
        accent = self._accent()
        icon_qss = (
            "QPushButton{background:transparent;border:none;border-radius:6px;}"
            f"QPushButton:hover{{background:{_rgba(accent, 0.30)};}}"
            f"QPushButton:pressed{{background:{_rgba(accent, 0.48)};}}"
        )
        close_qss = (
            "QPushButton{background:transparent;border:none;border-radius:6px;"
            "color:#e8eef5;font:600 12px 'Segoe UI';}"
            "QPushButton:hover{background:#d23030;color:#ffffff;}"
        )
        specs = [
            ("close", None, self.close_window, "ปิดหน้าต่าง"),
            ("lock", "normal.png", self._on_lock, "ล็อก/ปลดล็อกหน้าต่าง"),
            ("color", "TUI_BG.png", self._on_color, "สีพื้นหลัง / ความโปร่งใส"),
            ("fadeout", "fade.png", self._on_fadeout, "จางหาย (fade out)"),
            ("log", "chat.png", self._on_log, "เปิดบันทึกคำแปล (Logs)"),
        ]
        for key, icon_file, slot, tip in specs:
            btn = QPushButton(self)
            btn.setFixedSize(RAIL_BTN, RAIL_BTN)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(tip)
            btn.clicked.connect(lambda _=False, s=slot: s())
            btn.setVisible(False)
            if icon_file:
                btn.setIcon(self._icon(icon_file))
                btn.setIconSize(QSize(RAIL_BTN - 4, RAIL_BTN - 4))
                btn.setStyleSheet(icon_qss)
            else:
                btn.setText("✕")
                btn.setStyleSheet(close_qss)
            self._rail[key] = btn

    def _on_log(self):
        # Open the Translated Logs — NOT toggle_ui (that swaps Main/Mini UI).
        try:
            if self.main_app and hasattr(self.main_app, "toggle_translated_logs"):
                self.main_app.toggle_translated_logs()
            else:
                log.warning("[TUIQT log btn] main_app.toggle_translated_logs unavailable")
        except Exception as e:
            log.error(f"[TUIQT log btn] toggle failed: {e}")

    def _on_lock(self):
        # Cycle lock_mode 0→1→2→0 (circular):
        #   0 normal.png  — bg shown, UI draggable
        #   1 lock.png    — bg HIDDEN (text + outline only), UI locked
        #   2 BG_lock.png — bg shown, UI locked
        self.lock_mode = (self.lock_mode + 1) % 3
        btn = self._rail.get("lock")
        if btn:
            btn.setIcon(self._icon(
                {0: "normal.png", 1: "lock.png", 2: "BG_lock.png"}[self.lock_mode]))
        self.update()  # bg show/hide changed

    def _on_color(self):
        self._open_color_modal()

    def _on_fadeout(self):
        self._fade_enabled = not self._fade_enabled
        log.info(f"[TUIQT] fadeout toggled → enabled={self._fade_enabled} "
                 f"(visible={self.isVisible()})")
        if not self._fade_enabled:
            self._autohide_timer.stop()
            if self._fade_anim.state() == QAbstractAnimation.State.Running:
                self._fade_anim.stop()
            if self.windowOpacity() < 1.0:
                self.setWindowOpacity(1.0)
            self.show_feedback_message("ปิดซ่อนข้อความอัตโนมัติ",
                                       bg_color="#c62828", font_size=11, duration=1600)
        else:
            self._restart_autohide()
            self.show_feedback_message("เปิดซ่อนข้อความอัตโนมัติ (10 วิ)",
                                       bg_color="#2e7d32", font_size=11, duration=1600)
        btn = self._rail.get("fadeout")
        if btn:
            btn.setToolTip("ซ่อนข้อความอัตโนมัติ: เปิด" if self._fade_enabled
                           else "ซ่อนข้อความอัตโนมัติ: ปิด (ค้างไว้)")

    # ── fade-out + auto-hide (Tk fadeout principle) ─────────────────
    def _restart_autohide(self):
        if self._fade_anim.state() == QAbstractAnimation.State.Running:
            self._fade_anim.stop()
        if self.windowOpacity() < 1.0:
            self.setWindowOpacity(1.0)
        self._autohide_timer.stop()
        if self._fade_enabled:
            self._autohide_timer.start()

    def _begin_fade(self):
        if not self.isVisible() or not self._fade_enabled:
            log.info(f"[TUIQT] auto-hide tick skipped "
                     f"(visible={self.isVisible()} enabled={self._fade_enabled})")
            return
        if self._cursor_inside:            # don't fade under the user's cursor
            log.info("[TUIQT] auto-hide deferred (cursor inside) — retry in 10s")
            self._autohide_timer.start()
            return
        log.info("[TUIQT] auto-hide START fade-out")
        self._fade_anim.stop()
        self._fade_anim.setStartValue(self.windowOpacity())
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.start()

    def _on_fade_finished(self):
        if self.windowOpacity() <= 0.05 and self.isVisible():
            log.info("[TUIQT] auto-hide COMPLETE → hide()")
            self.hide()
            self.setWindowOpacity(1.0)
            self.state.is_window_hidden = True

    # ── colour / transparency modal ─────────────────────────────────
    def _open_color_modal(self):
        cur_hex = "#%02x%02x%02x" % self._bg_rgb
        cur_pct = round(self._bg_alpha / 255 * 100)
        m = _ColorAlphaModal(self, cur_hex, cur_pct, self._apply_bg_color_alpha)
        btn = self._rail.get("color")
        if btn:
            gp = btn.mapToGlobal(QPoint(0, 0))
            m.move(max(0, gp.x() - 230), gp.y())
        m.show()

    def _apply_bg_color_alpha(self, hex_color, alpha_pct):
        try:
            h = hex_color.lstrip("#")
            self._bg_rgb = (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
        except Exception:
            return
        self._bg_alpha = int(max(0, min(100, alpha_pct)) / 100.0 * 255)
        self._bg_pixmap = None              # force feathered-bg rebuild
        self.update()
        if self.settings is not None:
            try:
                self.settings.set("bg_color", hex_color, save_immediately=False)
                self.settings.set("bg_alpha", alpha_pct / 100.0, save_immediately=True)
            except Exception:
                pass

    def _reposition_chrome(self):
        # Rail: vertical column on the right, inset onto the solid bar, stacked
        # from the top. Grip: bottom-right corner, below the rail.
        rail_x = self.width() - RAIL_BTN - (GRIP_MARGIN - 2)
        y = PAD_Y - 4
        for key in ("close", "lock", "color", "fadeout", "log"):
            btn = self._rail.get(key)
            if btn:
                btn.move(rail_x, y)
                btn.raise_()
                y += RAIL_BTN + RAIL_GAP
        self._grip.move(self.width() - GRIP_SIZE - GRIP_MARGIN,
                        self.height() - GRIP_SIZE - GRIP_MARGIN)
        self._grip.raise_()

    # ── paint: diffuse background + text ────────────────────────────
    def paintEvent(self, event):  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        w, h = self.width(), self.height()

        # lock_mode 1 = "hide background": skip the bg entirely; the text is
        # drawn with a dark outline instead (readable over the game scene).
        hide_bg = (self.lock_mode == 1)
        if not hide_bg:
            if self._style == "box":
                r, g, b = self._bg_rgb
                path = QPainterPath()
                path.addRoundedRect(QRectF(0, 0, w, h), BG_RADIUS, BG_RADIUS)
                p.fillPath(path, QColor(r, g, b, self._bg_alpha))
            else:
                # DIFFUSE: a feathered rounded-rect — edges fade softly to
                # transparent on ALL sides (the "ฟุ้ง" look Tk's 1-bit colour-key
                # can't do). Cached pixmap, rebuilt only when the size changes.
                if (self._bg_pixmap is None
                        or self._bg_pixmap.width() != w
                        or self._bg_pixmap.height() != h):
                    self._rebuild_bg()
                if self._bg_pixmap is not None:
                    p.drawPixmap(0, 0, self._bg_pixmap)

        self._paint_text(p, w, h, shadow=hide_bg)
        p.end()

    def _rebuild_bg(self):
        """Build the cached feathered rounded-rect background. Stacked rounded
        rects (outer faint → inner opaque) make a soft edge band FEATHER_PX wide
        that fades to transparent on every side — the 'ฟุ้ง' glow Tk can't do.
        Per-layer alpha is chosen so the fully-covered centre reaches bg_alpha."""
        w, h = self.width(), self.height()
        if w < 2 or h < 2:
            return
        feather = max(1, min(FEATHER_PX, w // 2 - 1, h // 2 - 1))
        frac = self._bg_alpha / 255.0
        r, g, b = self._bg_rgb

        img = QImage(w, h, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(Qt.GlobalColor.transparent)
        qp = QPainter(img)
        qp.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        qp.setPen(Qt.PenStyle.NoPen)
        # Per-layer alpha chosen so the CUMULATIVE (source-over) alpha ramps
        # linearly from ~0 at the outer edge to bg_alpha at the core — a clean
        # fade-to-transparent feather, not a 1-step soft edge.
        prev_a = 0.0
        for i in range(feather):
            # ease-in (EDGE_FALLOFF > 1): outer rings stay near-transparent,
            # opacity builds toward the core — a softer outermost edge.
            target = frac * ((i + 1) / feather) ** EDGE_FALLOFF
            a_i = 1.0 - (1.0 - target) / max(1e-6, 1.0 - prev_a)
            prev_a = target
            qp.setBrush(QColor(r, g, b, max(0, min(255, int(round(a_i * 255))))))
            rad = max(2.0, BG_RADIUS - i)
            qp.drawRoundedRect(QRectF(i, i, w - 2 * i, h - 2 * i), rad, rad)
        qp.end()
        self._bg_pixmap = QPixmap.fromImage(img)

    def _paint_text(self, p: QPainter, w: int, h: int, shadow: bool = False):
        body_y = PAD_Y
        self._name_rect = QRect()
        # Speaker line — cyan (known) / purple (contains "?" → the ??? speaker).
        # Matches translated_ui._handle_normal_text_fast: colour keys on "?" only.
        if self._speaker:
            f_name = QFont(self._font_family, max(10, self._font_size - 6))
            fm = QFontMetrics(f_name)
            bw = fm.horizontalAdvance(self._speaker)
            cu = max(4, fm.averageCharWidth())
            content_l, content_r = PAD_L, self.width() - PAD_R
            line_w = min(bw + NAME_LINE_EXTRA_CHARS * cu,
                         max(10.0, content_r - content_l))
            line_x = content_l                       # underline anchored at left
            name_x = line_x + (line_w - bw) / 2.0    # name centred over the line
            line_y = PAD_Y + fm.ascent() + 12
            # Speaker name — cyan (known) / purple ("?" → ??? speaker), nudged
            # right so it sits centred over its underline.
            p.setFont(f_name)
            if shadow:                       # hide-bg lock mode → dark outline
                p.setPen(QColor(0, 0, 0, 235))
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1), (1, 2)):
                    p.drawText(int(name_x) + dx, PAD_Y + fm.ascent() + dy,
                               self._speaker)
            p.setPen(QColor(NAME_COLOR_UNKNOWN if "?" in self._speaker
                            else NAME_COLOR_KNOWN))
            p.drawText(int(name_x), PAD_Y + fm.ascent(), self._speaker)
            self._name_rect = QRect(int(name_x), PAD_Y, int(bw), fm.height())
            # Thin tapered underline (bright middle dissolving to nothing at both
            # ends) running +N char-widths beyond the name, anchored in-bounds.
            grad = QLinearGradient(float(line_x), 0.0, float(line_x + line_w), 0.0)
            grad.setColorAt(0.0, QColor(255, 255, 255, 0))
            grad.setColorAt(NAME_LINE_TAPER, QColor(255, 255, 255, NAME_LINE_ALPHA))
            grad.setColorAt(1.0 - NAME_LINE_TAPER, QColor(255, 255, 255, NAME_LINE_ALPHA))
            grad.setColorAt(1.0, QColor(255, 255, 255, 0))
            p.fillRect(QRectF(line_x, line_y, line_w, 1.6), grad)
            body_y = line_y + 8

        # Body — rich text laid out by QTextDocument (handles Thai wrap + the
        # per-segment styling). In hide-bg lock mode it gets a dark outline so
        # it stays readable over the game scene.
        if self._doc is not None:
            self._draw_doc_with_shadow(p, PAD_L, body_y, shadow)

    # ── rich-text document (body) ───────────────────────────────────
    def _rebuild_doc(self):
        limit = self._typed_chars if self._typing else None
        doc = QTextDocument()
        doc.setDefaultFont(QFont(self._font_family, self._font_size))
        doc.setTextWidth(max(40, self.width() - PAD_L - PAD_R))
        doc.setHtml(self._segments_to_html(self._segments, limit))
        self._doc = doc

    def _segments_to_html(self, segments, limit=None):
        import html as _html
        out = []
        count = 0
        for seg in segments:
            raw = seg.get("text", "")
            if limit is not None:                # typewriter: first N chars only
                room = limit - count
                if room <= 0:
                    break
                if len(raw) > room:
                    raw = raw[:room]
                count += len(raw)
            t = _html.escape(raw).replace("\n", "<br>")
            style = seg.get("font_style", "normal")
            if style == "italic":
                out.append(f'<span style="font-family:\'{_ITALIC_FAMILY}\';'
                           f'font-style:italic;color:#f2f6fb">{t}</span>')
            elif style == "bold":            # **highlight**
                out.append(f'<span style="color:#FFB366;font-weight:bold">{t}</span>')
            elif style == "name":            # character name detected in body
                c = NAME_COLOR_UNKNOWN if "?" in seg.get("text", "") else NAME_COLOR_KNOWN
                out.append(f'<span style="color:{c}">{t}</span>')
            else:                            # normal
                color = "#cccccc" if self._is_lore else "#f2f6fb"
                out.append(f'<span style="color:{color}">{t}</span>')
        return "".join(out)

    def _draw_doc_with_shadow(self, p, x, y, shadow):
        doc = self._doc
        if doc is None:
            return
        if not shadow:
            p.save()
            p.translate(x, y)
            doc.drawContents(p)
            p.restore()
            return
        # Hide-bg lock mode: render the doc, derive a black silhouette from its
        # alpha (SourceAtop), stamp it around the text (outline + drop shadow),
        # then draw the real text on top.
        sz = doc.size()
        iw = max(1, int(sz.width()) + 4)
        ih = max(1, int(sz.height()) + 4)
        img = QImage(iw, ih, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(Qt.GlobalColor.transparent)
        ip = QPainter(img)
        doc.drawContents(ip)
        ip.end()
        sil = QImage(img)
        sp = QPainter(sil)
        sp.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceAtop)
        sp.fillRect(sil.rect(), QColor(0, 0, 0, 240))
        sp.end()
        ix, iy = int(x), int(y)
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1),
                       (-1, -1), (1, -1), (-1, 1), (1, 1), (1, 2)):
            p.drawImage(ix + dx, iy + dy, sil)
        p.drawImage(ix, iy, img)

    # ── drag-to-move ────────────────────────────────────────────────
    def mousePressEvent(self, event):  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            local = event.position().toPoint()
            if self._grip.geometry().contains(local):
                return  # grip handles it
            # Click on the speaker name → open the NPC Manager for that character.
            if (self._speaker and self.toggle_npc_manager_callback
                    and self._name_rect.contains(local)):
                try:
                    self.toggle_npc_manager_callback(self._speaker)
                except Exception as e:
                    log.debug(f"npc-manager callback failed: {e}")
                return
            if self.lock_mode != 0:
                return  # locked (modes 1 & 2) — the UI can't be moved
            self._dragging = True
            self._drag_offset = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )
            event.accept()

    def mouseMoveEvent(self, event):  # noqa: N802
        if self._dragging and (event.buttons() & Qt.MouseButton.LeftButton):
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()

    def mouseReleaseEvent(self, event):  # noqa: N802
        if self._dragging:
            self._dragging = False
            self._schedule_save_geometry()
            event.accept()

    def resizeEvent(self, event):  # noqa: N802
        self._reposition_chrome()
        if self._segments:
            self._rebuild_doc()  # width changed → re-wrap the body
        self._schedule_save_geometry()
        super().resizeEvent(event)

    # ── hover poll (grip visibility) — Enter/Leave flicker on children ──
    def showEvent(self, event):  # noqa: N802
        self._hover_timer.start()
        super().showEvent(event)

    def hideEvent(self, event):  # noqa: N802
        self._hover_timer.stop()
        self._cursor_inside = False
        self._set_chrome_visible(False)
        super().hideEvent(event)

    def _poll_hover(self):
        if not self.isVisible():
            return
        local = self.mapFromGlobal(QCursor.pos())
        inside = self.rect().contains(local)
        if inside != self._cursor_inside:
            self._cursor_inside = inside
            self._set_chrome_visible(inside)
            if inside:
                self.reset_fade_timer_for_user_activity("hover")
        # Pointing-hand cursor over the clickable speaker name.
        if self._speaker and self.toggle_npc_manager_callback:
            want = (Qt.CursorShape.PointingHandCursor
                    if self._name_rect.contains(local)
                    else Qt.CursorShape.ArrowCursor)
            if self.cursor().shape() != want:
                self.setCursor(want)

    def _set_chrome_visible(self, vis):
        self._grip.setVisible(vis)
        for btn in self._rail.values():
            btn.setVisible(vis)

    # ── geometry persistence — SAME keys as dissolve_overlay ────────
    def _schedule_save_geometry(self):
        if not self._save_armed:
            return
        self._save_timer.start()

    def _save_geometry_now(self):
        if self.settings is None:
            return
        try:
            positions = self.settings.get("tui_positions", {}) or {}
            if not isinstance(positions, dict):
                positions = {}
            positions[MODE_KEY] = {"x": int(self.x()), "y": int(self.y())}
            self.settings.set("tui_positions", positions, save_immediately=False)

            geometries = self.settings.get("tui_geometries", {}) or {}
            if not isinstance(geometries, dict):
                geometries = {}
            geometries[MODE_KEY] = {"w": int(self.width()), "h": int(self.height())}
            self.settings.set("tui_geometries", geometries, save_immediately=True)
            log.info(f"[TUIQT] saved dialog pos=({self.x()},{self.y()}) "
                     f"size=({self.width()}x{self.height()})")
        except Exception as e:
            log.debug(f"save_geometry_now failed: {e}")

    def _restore_geometry(self):
        # size
        w, h = self.width(), self.height()
        try:
            geo = (self.settings.get("tui_geometries", {}) or {}).get(MODE_KEY) or {}
            if isinstance(geo.get("w"), int) and isinstance(geo.get("h"), int):
                w, h = max(MIN_W, geo["w"]), max(MIN_H, geo["h"])
                self.resize(w, h)
        except Exception:
            pass
        # position — saved, else default (centred, y = 70.7% of screen)
        x = y = None
        try:
            pos = (self.settings.get("tui_positions", {}) or {}).get(MODE_KEY) or {}
            if isinstance(pos.get("x"), int) and isinstance(pos.get("y"), int):
                x, y = pos["x"], pos["y"]
        except Exception:
            pass
        if x is None or y is None:
            screen = QApplication.primaryScreen()
            if screen is not None:
                g = screen.availableGeometry()
                x = g.x() + (g.width() - w) // 2
                y = g.y() + round(g.height() * 0.707)
            else:
                x, y = 200, 400
        self.move(int(x), int(y))

    # ════════════════════════════════════════════════════════════════
    # PUBLIC CONTRACT — signatures match Translated_UI
    # ════════════════════════════════════════════════════════════════
    def update_text(self, text, is_lore_text=False, force_choice_mode=False, chat_type=61):
        # Error blips are not displayed as dialogue (FLOWFIX_1 spirit).
        if text and "[Error:" in str(text):
            return
        # P4 will route 68/71/70 to the overlays here. P1 = dialogue only.
        self._text_update.emit(str(text or ""), bool(is_lore_text), int(chat_type))

    def _render_dialogue(self, text, is_lore, chat_type):
        self._is_lore = is_lore
        # Speaker is "Name: body" (Tk fast-path split on ": "). Strip rich-text
        # markers + zero-width chars from the name (matches translated_ui).
        speaker, body = "", text
        if ": " in text:
            head, _, tail = text.partition(": ")
            speaker = (head.replace("**", "").replace("*", "")
                       .replace("​", "").replace("‌", "").strip())
            body = tail.strip()
        self._speaker = speaker
        self._text = body
        # Reuse the Tk RichTextFormatter (Tk-free) so segmentation stays in
        # lockstep with the legacy renderer: *italic* / **highlight** / names.
        self._segments = self._rich.parse_rich_text_with_names(body, self.names)
        # Typewriter reveals the joined segment text (markers already stripped)
        # in batches — Thai streams faster — matching the Tk type_writer_effect.
        self._type_text = "".join(s.get("text", "") for s in self._segments)
        self._total_chars = len(self._type_text)
        self._typed_chars = 0
        self._typing = self._total_chars > 0
        self._rebuild_doc()
        if self._typing:
            self._type_timer.start(TYPE_BASE_MS)
        else:
            self._type_timer.stop()
        self.update()
        if not self.isVisible():
            self.show()
        if not self._save_armed:
            self._save_armed = True
        self._restart_autohide()

    def _typewriter_tick(self):
        text = self._type_text
        i = self._typed_chars
        if i >= len(text):
            self._typing = False
            self._type_timer.stop()
            return
        # Batch size — Thai streams in larger chunks (matches Tk
        # type_writer_effect: 5 Thai / 4 long / 3 default).
        window = text[i:i + 20]
        if any("฀" <= c <= "๿" for c in window):
            batch = 5
        elif len(text) > 100:
            batch = 4
        else:
            batch = 3
        self._typed_chars = min(i + batch, len(text))
        self._rebuild_doc()
        self.update()
        if self._typed_chars >= len(text):
            self._typing = False
            self._type_timer.stop()
            return
        # Longer pause after sentence/clause punctuation (Tk: .!? x3, ", " x2).
        last = text[self._typed_chars - 1]
        delay = TYPE_BASE_MS * (3 if last in ".!?" else 2 if last in ", " else 1)
        self._type_timer.start(delay)

    def update_font(self, font_name):
        self._font_family = font_name
        if self._segments:
            self._rebuild_doc()
        self.update()

    def adjust_font_size(self, size):
        try:
            self._font_size = int(size)
        except (TypeError, ValueError):
            return
        if self._segments:
            self._rebuild_doc()
        self.update()

    def update_character_names(self, new_names):
        self.names = set(new_names) if new_names else set()
        self.update()

    def force_show_tui(self):
        self.show()
        self.raise_()
        if not self._save_armed:
            self._save_armed = True

    def clear_displayed_text(self):
        self._text = ""
        self._speaker = ""
        self._segments = []
        self._doc = None
        self.update()

    def close_window(self):
        try:
            if callable(self.on_close_callback):
                self.on_close_callback()
        finally:
            self.hide()

    # ── stubs filled in later phases (callable now so integration is safe) ──
    def reset_fade_timer_for_user_activity(self, activity_name="user_activity"):
        if self._fade_anim.state() == QAbstractAnimation.State.Running:
            self._fade_anim.stop()
        if self.windowOpacity() < 1.0:
            self.setWindowOpacity(1.0)
        if self._fade_enabled and self.isVisible():
            self._autohide_timer.start()

    def show_feedback_message(self, message, bg_color="#C62828", x_offset=10,
                              y_offset=10, duration=800, font_size=10):
        try:
            if getattr(self, "_toast", None) is None:
                self._toast = QLabel(self)
                self._toast.setAttribute(
                    Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
                self._toast_timer = QTimer(self)
                self._toast_timer.setSingleShot(True)
                self._toast_timer.timeout.connect(
                    lambda: self._toast.setVisible(False))
            self._toast.setStyleSheet(
                f"background:{bg_color};color:#ffffff;border-radius:6px;"
                f"padding:5px 10px;font:600 {font_size}pt 'Segoe UI';")
            self._toast.setText(message)
            self._toast.adjustSize()
            tx = max(4, (self.width() - self._toast.width()) // 2)
            self._toast.move(tx, max(4, y_offset))
            self._toast.setVisible(True)
            self._toast.raise_()
            self._toast_timer.start(int(duration))
        except Exception as e:
            log.debug(f"toast failed: {e}")

    def force_check_overflow(self):
        pass  # P2: overflow arrow

    def update_translation_status(self, *args, **kwargs):
        pass

    def handle_translation_toggle(self, *args, **kwargs):
        if callable(self.toggle_translation):
            self.toggle_translation()

    # ════════════════════════════════════════════════════════════════
    # Dispatcher + mode-switch coordination — ports translated_ui's
    # update_text routing + FLOWFIX_8 chain-memory. self.hide()/show()
    # replace Tk root.withdraw()/deiconify(); the overlays are the SAME
    # PyQt6 widgets MBB wires into .dissolve_overlay / .choice_overlay.
    # ════════════════════════════════════════════════════════════════
    def _dispatch(self, text, is_lore, chat_type):
        self._current_chat_type = chat_type
        # Battle (68) / Cutscene (71) → dissolve overlay
        if self.dissolve_overlay is not None and chat_type in (68, 71):
            try:
                self._route_to_dissolve_overlay(text, chat_type, is_lore)
                return
            except Exception as e:
                log.error(f"dissolve dispatch failed → dialogue: {e}", exc_info=True)
        elif self._dissolve_active and chat_type not in (68, 71):
            try:
                self._exit_dissolve_overlay()
            except Exception as e:
                log.error(f"exit dissolve failed: {e}")
        # Choice (chat_type 70 or pipe-detected) → choice overlay
        is_choice = (chat_type == 70) or self._is_choice_dialogue(text)
        if self.choice_overlay is not None and is_choice:
            try:
                self._route_to_choice_overlay(text)
                return
            except Exception as e:
                log.error(f"choice dispatch failed → dialogue: {e}", exc_info=True)
        elif self._choice_overlay_active and not is_choice:
            try:
                self._exit_choice_overlay()
            except Exception as e:
                log.error(f"exit choice failed: {e}")
        # Dialogue (61 / fallback)
        self._render_dialogue(text, is_lore, chat_type)

    def _split_speaker_dialogue(self, text):
        """(speaker, dialogue) for the overlays — mirrors translated_ui."""
        if not text:
            return "", ""
        t = text.strip()
        if ":" in t:
            head, tail = t.split(":", 1)
            for junk in ("**", "*", "​", "‌", "‍", "﻿"):
                head = head.replace(junk, "")
            head = head.strip()
            if head and len(head) <= 40 and "\n" not in head:
                return head, tail.strip()
        return "", t

    def _is_choice_dialogue(self, text):
        if " | " in (text or ""):
            parts = text.split(" | ")
            if len(parts) >= 2:
                first = parts[0].strip().lower()
                if "what will you say" in first:
                    return True
                if "คุณจะพูดว่าอย่างไร" in first or "คุณจะพูด" in first:
                    return True
        return False

    def _stop_dialogue_timers(self):
        for t in (self._type_timer, self._autohide_timer, self._save_timer):
            try:
                if t.isActive():
                    t.stop()
            except Exception:
                pass
        try:
            if self._fade_anim.state() == QAbstractAnimation.State.Running:
                self._fade_anim.stop()
        except Exception:
            pass
        self._typing = False
        if self.windowOpacity() < 1.0:
            self.setWindowOpacity(1.0)

    def _route_to_dissolve_overlay(self, text, chat_type, is_lore=False):
        mode = "battle" if chat_type == 68 else "cutscene"
        chain_owned = self._dissolve_active or self._choice_overlay_active
        # choice → dissolve transition: hide choice + transfer was-visible memory
        if self._choice_overlay_active:
            try:
                if self.choice_overlay is not None:
                    self.choice_overlay.hide_overlay()
            except Exception:
                pass
            self._choice_overlay_active = False
            self._tk_was_visible_before_dissolve = (
                self._tk_was_visible_before_dissolve
                or self._tk_was_visible_before_choice)
            self._tk_was_visible_before_choice = False
        self._stop_dialogue_timers()
        # FLOWFIX_8b chain-memory: only write False when no chain owns the hide.
        if self.isVisible() and not self._dissolve_active:
            self._tk_was_visible_before_dissolve = True
            self.hide()
        elif not self._dissolve_active and not chain_owned:
            self._tk_was_visible_before_dissolve = False
        # else (dissolve_active OR chain-owned) → preserve the memory
        speaker, dialogue = self._split_speaker_dialogue(text)
        cur = getattr(self.dissolve_overlay, "_current_mode", None)
        if (not self.dissolve_overlay.isVisible()) or cur != mode:
            self.dissolve_overlay.show_for_mode(mode)
        self.dissolve_overlay.set_text(dialogue, speaker=speaker, is_lore=is_lore)
        self._dissolve_active = True

    def _exit_dissolve_overlay(self):
        try:
            if self.dissolve_overlay is not None:
                self.dissolve_overlay.hide_overlay()
        except Exception:
            pass
        if self._tk_was_visible_before_dissolve:
            self.show()
            self.raise_()
        self._dissolve_active = False
        self._tk_was_visible_before_dissolve = False

    def _route_to_choice_overlay(self, text):
        from pyqt_ui.choice_parser import parse_choice_text
        chain_owned = self._dissolve_active or self._choice_overlay_active
        header, choices = parse_choice_text(text)
        if not choices:
            raise RuntimeError("empty choices — caller falls back to dialogue")
        self._stop_dialogue_timers()
        # FLOWFIX_8c: withdraw whenever visible (even if pre-armed); only write
        # False when no chain owns the hide.
        if self.isVisible():
            self._tk_was_visible_before_choice = True
            self.hide()
        elif not self._choice_overlay_active and not chain_owned:
            self._tk_was_visible_before_choice = False
        # else preserve
        self.choice_overlay.show_choice(header, choices)
        self._choice_overlay_active = True

    def _exit_choice_overlay(self):
        try:
            if self.choice_overlay is not None:
                self.choice_overlay.hide_overlay()
        except Exception:
            pass
        if self._tk_was_visible_before_choice:
            self.show()
            self.raise_()
        self._choice_overlay_active = False
        self._tk_was_visible_before_choice = False

    # ── demo helpers ──
    def set_speaker(self, name):
        self._speaker = name
        self.update()

    def set_style(self, style):
        self._style = "box" if style == "box" else "diffuse"
        self.update()


# ────────────────────────────────────────────────────────────────────
# Standalone preview — `python pyqt_ui/translated_ui_qt.py`
# ────────────────────────────────────────────────────────────────────
def _demo():
    import sys

    app = QApplication(sys.argv)
    scr = app.primaryScreen().availableGeometry()

    backdrop = QWidget()
    backdrop.setStyleSheet("background:#1a2536;")
    backdrop.resize(1000, 560)
    backdrop.move(scr.x() + (scr.width() - 1000) // 2,
                  scr.y() + (scr.height() - 560) // 2)
    backdrop.show()

    tui = TranslatedUIQt(settings=None, character_names={"Y'shtola", "Alphinaud"})
    tui.update_text(
        "Y'shtola: ข้าเชื่อว่า *ความหวัง* ที่เรามีร่วมกัน คือสิ่ง **สำคัญที่สุด** "
        "และ Alphinaud ก็คงรู้สึกเช่นเดียวกัน"
    )
    tui.resize(640, 185)
    tui.show()
    # Sit in the middle of the dark backdrop so the feathered edges show against
    # dark rather than the desktop. Diffuse is the default style — no toggle.
    bg = backdrop.geometry()
    tui.move(bg.x() + (bg.width() - 640) // 2, bg.y() + (bg.height() - 185) // 2)
    tui.raise_()

    sys.exit(app.exec())


if __name__ == "__main__":
    _demo()
