"""
translated_ui_qt.py — PyQt6 rewrite of the Dialogue (ChatType 61) TUI.

STATUS: Skeleton / starting point for the migration. NOT yet wired into MBB.py.
        Runs standalone: `python translated_ui_qt.py` to preview the diffuse
        background + drag + resize + vertical rail.

DESIGN GOALS (see migration_plan.md):
  - Per-pixel translucent window (WA_TranslucentBackground) → real feathered edges
  - QRadialGradient background = "diffuse" look (toggleable vs legacy "box")
  - Same public method/attribute contract as the Tkinter Translated_UI so it can
    become a drop-in replacement with a thin RootShim.
  - Geometry persisted to the SAME settings keys the dissolve_overlay uses
    (tui_positions["dialog"], tui_geometries["dialog"]) so both UIs stay in sync.

This file deliberately keeps logic minimal and stubs out the heavy integration
points (rich text, NPC manager, fade machinery) with clear TODO markers so the
work can continue in VS Code.
"""

from __future__ import annotations

import sys
from typing import Any, Callable, Optional

from PyQt6.QtCore import Qt, QTimer, QRectF, QPoint, pyqtSignal
from PyQt6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QPainter,
    QPainterPath,
    QRadialGradient,
)
from PyQt6.QtWidgets import (
    QApplication,
    QPushButton,
    QWidget,
)


# ────────────────────────────────────────────────────────────────────────────
# Visual constants (mirror the values dialogue uses today; tune freely)
# ────────────────────────────────────────────────────────────────────────────
NAME_COLOR_KNOWN = "#38bdf8"     # blue — name is in the known-characters set
NAME_COLOR_UNKNOWN = "#a855f7"   # purple — name contains "?" / unknown
DEFAULT_BG_RGB = (11, 15, 20)    # #0b0f14
DEFAULT_BG_ALPHA = 247           # 247/255 ≈ 0.97
DEFAULT_FONT = "Anuphan"
DEFAULT_FONT_SIZE = 24
MODE_KEY = "dialog"              # settings sub-key for dialogue mode

# Diffuse feather amount in px (the radius of the soft halo beyond content box)
DEFAULT_FEATHER = 46
# Corner radius for the legacy "box" style
BOX_RADIUS = 14


# ────────────────────────────────────────────────────────────────────────────
# RootShim — lets MBB.py / dissolve_overlay keep calling Tkinter-style methods
# on `.root` without modification. Map only what is actually called (from grep).
# ────────────────────────────────────────────────────────────────────────────
class RootShim:
    """Translate the Tk root API surface that MBB.py + overlay rely on into Qt."""

    def __init__(self, widget: QWidget):
        self._w = widget

    # show / hide
    def deiconify(self):
        self._w.show()

    def withdraw(self):
        self._w.hide()

    def update_idletasks(self):
        QApplication.processEvents()

    def update(self):
        QApplication.processEvents()

    # geometry queries
    def winfo_x(self) -> int:
        return self._w.x()

    def winfo_y(self) -> int:
        return self._w.y()

    def winfo_width(self) -> int:
        return self._w.width()

    def winfo_height(self) -> int:
        return self._w.height()

    def winfo_exists(self) -> int:
        return 1 if self._w is not None else 0

    def winfo_ismapped(self) -> int:
        return 1 if self._w.isVisible() else 0

    def winfo_containing(self, x: int, y: int):
        # Best-effort: Qt equivalent is QApplication.widgetAt
        return QApplication.widgetAt(QPoint(x, y))

    # geometry setter — supports both query and "WxH+X+Y" form
    def geometry(self, spec: Optional[str] = None):
        if spec is None:
            return (
                f"{self._w.width()}x{self._w.height()}"
                f"+{self._w.x()}+{self._w.y()}"
            )
        try:
            size_part, _, pos_part = spec.partition("+")
            w_str, _, h_str = size_part.partition("x")
            x_str, _, y_str = pos_part.partition("+")
            if w_str and h_str:
                self._w.resize(int(w_str), int(h_str))
            if x_str and y_str:
                self._w.move(int(x_str), int(y_str))
        except Exception:
            pass

    # attributes("-alpha", v) / ("-topmost", v) — no-op or windowOpacity
    def attributes(self, name: str, *args):
        if name == "-alpha" and args:
            self._w.setWindowOpacity(float(args[0]))
        # -topmost handled by window flags at construction; ignore here

    def overrideredirect(self, _flag):  # frameless handled by flags
        pass

    def resizable(self, *_):
        pass

    def state(self, *_):
        return "normal"

    # after / after_cancel → QTimer
    def after(self, ms: int, callback=None):
        if callback is None:
            return None
        timer = QTimer(self._w)
        timer.setSingleShot(True)
        timer.timeout.connect(callback)
        timer.start(int(ms))
        return timer  # caller can keep this as the "id"

    def after_cancel(self, timer):
        try:
            if timer is not None:
                timer.stop()
        except Exception:
            pass


# ────────────────────────────────────────────────────────────────────────────
# Resize grip (bottom-right) — adapted from dissolve_overlay._ResizeGrip
# ────────────────────────────────────────────────────────────────────────────
class _ResizeGrip(QWidget):
    SIZE = 16

    def __init__(self, target: "TranslatedUIQt"):
        super().__init__(target)
        self._target = target
        self.setFixedSize(self.SIZE, self.SIZE)
        self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        self._dragging = False
        self._start = QPoint()
        self._start_size = None

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        col = QColor(255, 255, 255, 120)
        p.setPen(col)
        # three short diagonal ticks
        for off in (3, 7, 11):
            p.drawLine(self.SIZE - off, self.SIZE - 2,
                       self.SIZE - 2, self.SIZE - off)
        p.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._start = event.globalPosition().toPoint()
            self._start_size = self._target.size()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._dragging:
            delta = event.globalPosition().toPoint() - self._start
            new_w = max(220, self._start_size.width() + delta.x())
            new_h = max(90, self._start_size.height() + delta.y())
            self._target.resize(new_w, new_h)
            event.accept()

    def mouseReleaseEvent(self, event):
        if self._dragging:
            self._dragging = False
            self._target._schedule_save_geometry()
            event.accept()


# ────────────────────────────────────────────────────────────────────────────
# Main TUI widget
# ────────────────────────────────────────────────────────────────────────────
class TranslatedUIQt(QWidget):
    """PyQt6 dialogue TUI. Same constructor signature as the Tkinter version."""

    # Signal so background threads can request a text update safely.
    text_update_requested = pyqtSignal(str, bool, int)  # text, is_lore, chat_type

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

        # ── keep the exact same references the Tkinter version stored ──
        self.toggle_translation = toggle_translation
        self.stop_translation = stop_translation
        self.previous_dialog_callback = previous_dialog_callback
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

        # contract attributes MBB.py touches directly
        self.lock_mode = 0
        self._closing_from_f9 = False
        self.dissolve_overlay = None     # wired externally, unchanged
        self.choice_overlay = None       # wired externally, unchanged

        # ── visual state ──
        self._style = "diffuse"          # "diffuse" | "box"
        self._feather = DEFAULT_FEATHER
        self._bg_rgb = self._load_bg_rgb()
        self._bg_alpha = self._load_bg_alpha()
        self._speaker = "Ardbert"
        self._text = ""
        self._font_family = self._setting("font", DEFAULT_FONT)
        self._font_size = int(self._setting("font_size", DEFAULT_FONT_SIZE))

        # geometry persistence debounce
        self._save_timer: Optional[QTimer] = None

        # drag state
        self._dragging = False
        self._drag_offset = QPoint()

        self._init_window()
        self._build_rail()
        self._grip = _ResizeGrip(self)
        self._restore_geometry()
        self._reposition_chrome()

        # thread-safe text update bridge
        self.text_update_requested.connect(self._apply_text)

        # the shim MBB.py / overlay will call Tk methods on
        self.root = RootShim(self)

    # ────────────────────────────────────────────────────────────────────
    # settings helpers
    # ────────────────────────────────────────────────────────────────────
    def _setting(self, key, default):
        try:
            return self.settings.get(key, default)
        except Exception:
            return default

    def _load_bg_rgb(self):
        hexv = self._setting("bg_color", None)
        if isinstance(hexv, str) and hexv.startswith("#") and len(hexv) == 7:
            return (int(hexv[1:3], 16), int(hexv[3:5], 16), int(hexv[5:7], 16))
        return DEFAULT_BG_RGB

    def _load_bg_alpha(self):
        a = self._setting("bg_alpha", None)
        if isinstance(a, (int, float)):
            return int(max(0.0, min(1.0, float(a))) * 255)
        return DEFAULT_BG_ALPHA

    # ────────────────────────────────────────────────────────────────────
    # window / chrome
    # ────────────────────────────────────────────────────────────────────
    def _init_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMinimumSize(220, 90)
        self.resize(640, 150)

    def _build_rail(self):
        """Vertical button rail on the right (matches the real layout)."""
        self._rail_buttons = {}
        specs = [
            ("close", "×", self._on_close),
            ("lock", "L", self._on_lock),
            ("color", "C", self._on_color),
            ("font", "F", self._on_font),
            ("log", "≡", self._on_log),
        ]
        # TODO: replace single-char labels with the real PNG icons
        #       (assets/lock.png, TUI_BG.png, setting.png, chat.png).
        for i, (key, label, slot) in enumerate(specs):
            btn = QPushButton(label, self)
            btn.setFixedSize(26, 26)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(slot)
            btn.setStyleSheet(
                "QPushButton{background:transparent;color:#e8eef5;border:0;"
                "border-radius:7px;font:600 14px 'Segoe UI';}"
                "QPushButton:hover{background:rgba(255,255,255,0.12);}"
            )
            self._rail_buttons[key] = btn

    def _reposition_chrome(self):
        w, h = self.width(), self.height()
        # rail anchored top-right, stacked
        x = w - 34
        y = 14
        for key in ("close", "lock", "color", "font", "log"):
            btn = self._rail_buttons.get(key)
            if btn:
                btn.move(x, y)
                y += 32
        # grip bottom-right
        self._grip.move(w - _ResizeGrip.SIZE - 4, h - _ResizeGrip.SIZE - 4)

    # ────────────────────────────────────────────────────────────────────
    # paint — the heart of the diffuse look
    # ────────────────────────────────────────────────────────────────────
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        w, h = self.width(), self.height()
        r, g, b = self._bg_rgb
        base = QColor(r, g, b, self._bg_alpha)
        clear = QColor(r, g, b, 0)

        if self._style == "box":
            # legacy sharp rounded rectangle
            path = QPainterPath()
            path.addRoundedRect(QRectF(0, 0, w, h), BOX_RADIUS, BOX_RADIUS)
            p.fillPath(path, base)
        else:
            # DIFFUSE: radial gradient that fades to fully transparent at edges
            # → no hard border, feathered halo. This is what Tkinter can't do.
            cx, cy = w / 2.0, h * 0.55
            radius = max(w, h) * 0.72
            grad = QRadialGradient(cx, cy, radius)
            grad.setColorAt(0.00, base)
            grad.setColorAt(0.45, base)
            grad.setColorAt(0.72, QColor(r, g, b, int(self._bg_alpha * 0.5)))
            grad.setColorAt(1.00, clear)
            p.fillRect(self.rect(), grad)

        # ── text ──
        self._paint_text(p, w, h)
        p.end()

    def _paint_text(self, p: QPainter, w: int, h: int):
        pad_l = 24
        pad_r = 44          # leave room for the rail
        pad_y = 18
        inner_w = max(40, w - pad_l - pad_r)

        # speaker name (blue if known, purple if unknown / contains "?")
        name = self._speaker or ""
        is_unknown = "?" in name or (name and name not in self.names)
        name_color = QColor(NAME_COLOR_UNKNOWN if is_unknown else NAME_COLOR_KNOWN)

        f_name = QFont(self._font_family, 13, QFont.Weight.Bold)
        f_body = QFont(self._font_family, self._font_size)

        y = pad_y + QFontMetrics(f_name).ascent()
        if name:
            p.setFont(f_name)
            p.setPen(name_color)
            p.drawText(pad_l, y, name)
            y += 8

        # body
        p.setFont(f_body)
        p.setPen(QColor(242, 246, 251))
        body_rect = QRectF(pad_l, y, inner_w, h - y - pad_y)
        flags = int(Qt.TextFlag.TextWordWrap) | int(Qt.AlignmentFlag.AlignLeft)
        p.drawText(body_rect, flags, self._text)

    # ────────────────────────────────────────────────────────────────────
    # drag to move (adapted from dissolve_overlay)
    # ────────────────────────────────────────────────────────────────────
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            local = event.position().toPoint()
            # ignore clicks that belong to rail buttons / grip
            for btn in self._rail_buttons.values():
                if btn.geometry().contains(local):
                    return
            if self._grip.geometry().contains(local):
                return
            self._dragging = True
            self._drag_offset = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )
            event.accept()

    def mouseMoveEvent(self, event):
        if self._dragging and (event.buttons() & Qt.MouseButton.LeftButton):
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()

    def mouseReleaseEvent(self, event):
        if self._dragging:
            self._dragging = False
            self._schedule_save_geometry()
            event.accept()

    def resizeEvent(self, event):
        self._reposition_chrome()
        super().resizeEvent(event)

    # ────────────────────────────────────────────────────────────────────
    # geometry persistence — SAME keys as dissolve_overlay (stay in sync)
    # ────────────────────────────────────────────────────────────────────
    def _schedule_save_geometry(self):
        if self._save_timer is None:
            self._save_timer = QTimer(self)
            self._save_timer.setSingleShot(True)
            self._save_timer.timeout.connect(self._save_geometry_now)
        self._save_timer.start(400)

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
        except Exception:
            pass

    def _restore_geometry(self):
        if self.settings is None:
            return
        try:
            pos = (self.settings.get("tui_positions", {}) or {}).get(MODE_KEY)
            geo = (self.settings.get("tui_geometries", {}) or {}).get(MODE_KEY)
            if isinstance(geo, dict) and geo.get("w") and geo.get("h"):
                self.resize(int(geo["w"]), int(geo["h"]))
            if isinstance(pos, dict) and pos.get("x") is not None:
                self.move(int(pos["x"]), int(pos["y"]))
        except Exception:
            pass

    # ────────────────────────────────────────────────────────────────────
    # rail button slots (wire to the callbacks the constructor received)
    # ────────────────────────────────────────────────────────────────────
    def _on_close(self):
        self.close_window()

    def _on_lock(self):
        # TODO: cycle lock_mode 0→1→2 and apply transparentcolor equivalent
        self.lock_mode = (self.lock_mode + 1) % 3

    def _on_color(self):
        # TODO: open color/alpha picker (replaces TUI_BG.png button)
        pass

    def _on_font(self):
        # TODO: open font panel; for now just bump size as a smoke test
        self.adjust_font_size(self._font_size)

    def _on_log(self):
        if callable(self.toggle_ui):
            try:
                self.toggle_ui()
            except Exception:
                pass

    # ════════════════════════════════════════════════════════════════════
    # PUBLIC CONTRACT — signatures match the Tkinter Translated_UI
    # ════════════════════════════════════════════════════════════════════
    def update_text(self, text: str, is_lore_text: bool = False,
                    force_choice_mode: bool = False, chat_type: int = 61) -> None:
        """Dialogue path only. Battle(68)/Cutscene(71) are dispatched to the
        dissolve_overlay BEFORE reaching here (that routing logic lives in the
        caller and is unchanged). Emitting the signal keeps this thread-safe."""
        if text and "[Error:" in text:
            return
        self.text_update_requested.emit(text or "", bool(is_lore_text), int(chat_type))

    def _apply_text(self, text: str, is_lore: bool, chat_type: int):
        # TODO: rich-text (*italic*) formatting + typing animation + overflow arrow
        self._text = text
        self.update()  # trigger repaint
        if not self.isVisible():
            self.show()

    def update_font(self, font_name: str) -> None:
        self._font_family = font_name
        self.update()

    def adjust_font_size(self, size: int) -> None:
        self._font_size = int(size)
        self.update()

    def update_character_names(self, new_names) -> None:
        self.names = set(new_names) if new_names else set()
        self.update()

    def update_translation_status(self, *args, **kwargs) -> None:
        # TODO: port status indicator if needed
        pass

    def show_feedback_message(self, message: str, bg_color: str = "#C62828",
                              x_offset: int = 10, y_offset: int = 10,
                              duration: int = 800, font_size: int = 10) -> None:
        # TODO: small toast widget. Stub keeps the contract callable.
        pass

    def reset_fade_timer_for_user_activity(self,
                                           activity_name: str = "user_activity") -> None:
        # TODO: port fade timer machinery
        pass

    def handle_translation_toggle(self, *args, **kwargs) -> None:
        if callable(self.toggle_translation):
            self.toggle_translation()

    def force_show_tui(self) -> None:
        self.show()
        self.raise_()

    def force_check_overflow(self) -> None:
        # TODO: detect text overflow → show overflow arrow
        pass

    def close_window(self) -> None:
        try:
            if callable(self.on_close_callback):
                self.on_close_callback()
        finally:
            self.hide()

    def clear_displayed_text(self) -> None:
        self._text = ""
        self.update()

    # convenience for the standalone demo
    def set_speaker(self, name: str):
        self._speaker = name
        self.update()

    def set_style(self, style: str):
        self._style = "box" if style == "box" else "diffuse"
        self.update()


# ────────────────────────────────────────────────────────────────────────────
# Standalone preview — run this file directly to see the diffuse TUI
# ────────────────────────────────────────────────────────────────────────────
def _demo():
    app = QApplication(sys.argv)

    # a dark backdrop so the translucent/diffuse edges are visible
    backdrop = QWidget()
    backdrop.setStyleSheet("background:#1a2536;")
    backdrop.setWindowTitle("backdrop (move the TUI around on top of me)")
    backdrop.resize(1100, 600)
    backdrop.show()

    tui = TranslatedUIQt(settings=None, character_names={"Ardbert"})
    tui.set_speaker("Ardbert")
    tui.update_text(
        "Right. If I had to choose between saving one life or a hundred lives, "
        "I wouldn't choose one and abandon the other. They are both just as "
        "important—that's what I believe."
    )
    tui.move(240, 360)
    tui.show()

    # toggle box <-> diffuse every 2.5s so you can compare the edges
    state = {"box": False}

    def toggle():
        state["box"] = not state["box"]
        tui.set_style("box" if state["box"] else "diffuse")

    t = QTimer()
    t.timeout.connect(toggle)
    t.start(2500)

    sys.exit(app.exec())


if __name__ == "__main__":
    _demo()
