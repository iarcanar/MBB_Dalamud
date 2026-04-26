"""
Translated Logs UI — PyQt6 rewrite (v1.7.9, 2026-04-26)

Chat-history overlay showing recent translations as LINE-style rounded bubbles.
Replaces the legacy Tkinter `translated_logs.py`.

Design:
- Frameless, always-on-top, rounded panel
- Bubble = single QFrame with one rounded background paint + wrapping QLabel
  inside → multi-line text never breaks the bubble shape
- Centered bubble alignment (no LINE-style tail; pure rounded card)
- Slide-up + fade-in animation for new bubbles (150ms ease-out)
- Auto-scroll to newest on every new message
- Reverse mode (newest-on-top) toggle
- Transparency slider (10-100) — replaces old A/B/C/D modes
- Lock mode is session-only (always starts unlocked on app launch)
- Smart Replacement DISABLED in this rewrite (kept as no-op flag)

Public API kept compatible with the old Tkinter version so MBB.py needs
minimal changes.
"""

from __future__ import annotations
import logging
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QFrame, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QScrollArea, QSlider, QGraphicsDropShadowEffect,
    QApplication, QSizePolicy,
)
from PyQt6.QtGui import (
    QColor, QFont, QIcon, QPainter, QPainterPath, QPen, QPixmap, QPolygon,
)
from PyQt6.QtCore import (
    Qt, QPoint, QSize, QRectF, QTimer, QPropertyAnimation, QEasingCurve,
    pyqtSignal,
)

import os

from pyqt_ui.styles import (
    FONT_PRIMARY, FONT_MONO, derive_palette, is_light_theme, invert_pixmap,
)
from resource_utils import resource_path

log = logging.getLogger("translated-logs")

# ────────────────────────────────────────────────────────────────────
# Constants
# ────────────────────────────────────────────────────────────────────
DEFAULT_W = 455   # tuned to fit 18pt Anuphan + speaker labels comfortably
DEFAULT_H = 935   # ~85% of a 1080p screen — leaves a strip of game visible
MIN_W = 240
MIN_H = 280
MAX_BUBBLES = 100        # destroy oldest beyond this
MAX_CACHE = 200          # message cache cap (LRU)
RIGHT_EDGE_PAD = 24      # px from screen right edge when smart-positioning
TOP_PAD = 100            # px from screen top
BUBBLE_RADIUS = 12       # rounded bubble corner radius
BUBBLE_PAD_H = 12
BUBBLE_PAD_V = 8
BUBBLE_GAP = 6           # vertical gap between bubbles
BUBBLE_SIDE_MARGIN = 14  # left+right margin inside the scroll viewport
ANIM_MS = 150            # bubble fade-in duration
SCROLL_ANIM_MS = 220     # auto-scroll to newest duration
DEFAULT_TRANSPARENCY = 95  # initial slider value (out of 100)

# Speaker color codes
COLOR_DIALOGUE = "#38bdf8"   # cyan — known characters
COLOR_UNKNOWN  = "#a855f7"   # purple — "???"
COLOR_CHOICE   = "#FFD700"   # gold — dialogue choice prompt
COLOR_LORE     = None        # narration — uses text_dim


# ────────────────────────────────────────────────────────────────────
# Theme cache — module-level so external code can invalidate
# ────────────────────────────────────────────────────────────────────
_THEME_CACHE: dict = {}


def _refresh_logs_theme():
    """Invalidate the cached palette. Called by MBB.py when theme changes."""
    _THEME_CACHE.clear()


def _palette() -> dict:
    """Return cached theme palette (rebuilt on first miss)."""
    if _THEME_CACHE:
        return _THEME_CACHE
    try:
        from appearance import appearance_manager as am
        primary = am.get_accent_color()
        secondary = am.get_theme_color("secondary", "#888888")
        surface = am.get_theme_color("surface_override")
        text_o = am.get_theme_color("text_override")
        p = derive_palette(primary, secondary, surface=surface, text_override=text_o)
    except Exception:
        p = derive_palette("#16181c", "#7c8aed")  # fallback to Graphite-ish
    _THEME_CACHE.update(p)
    return _THEME_CACHE


# ────────────────────────────────────────────────────────────────────
# Thai-aware soft-wrap — Qt's QLabel.wordWrap only breaks at spaces, but
# Thai has no inter-word spaces. We insert zero-width-spaces (U+200B) at
# syllable boundaries so wordWrap can break inside long Thai runs.
# Algorithm ported from translated_ui.py:_split_for_wrap (proven on TUI).
# ────────────────────────────────────────────────────────────────────
_ZWSP = "​"
_THAI_LEADING_VOWELS = set("เแโใไ")
_THAI_DEPENDENT = (
    set(chr(c) for c in range(0x0E31, 0x0E3B))
    | set(chr(c) for c in range(0x0E47, 0x0E4F))
)
_THAI_CONSONANTS = set(chr(c) for c in range(0x0E01, 0x0E2F))


def _insert_thai_breakpoints(text: str) -> str:
    """Inject ZWSP at Thai syllable boundaries so Qt can soft-wrap inside
    Thai runs. Returns the original string unchanged if no Thai is present."""
    if not text:
        return text
    if not any("ก" <= c <= "๛" for c in text):
        return text  # pure English/etc — Qt's space-based wrap handles it

    out = []
    space_parts = text.split(" ")
    for part_idx, part in enumerate(space_parts):
        if not part:
            if part_idx < len(space_parts) - 1:
                out.append(" ")
            continue

        part_has_thai = any("ก" <= c <= "๛" for c in part)
        # Short tokens or pure non-Thai — keep as-is
        if not part_has_thai or len(part) <= 6:
            out.append(part)
            if part_idx < len(space_parts) - 1:
                out.append(" ")
            continue

        run = ""
        for i, ch in enumerate(part):
            # Break BEFORE Thai leading vowels (start of a new syllable)
            if (
                i > 0
                and ch in _THAI_LEADING_VOWELS
                and run
                and part[i - 1] != " "
                and (
                    "ก" <= part[i - 1] <= "๛"
                    or part[i - 1] in _THAI_DEPENDENT
                )
            ):
                out.append(run)
                out.append(_ZWSP)
                run = ch
                continue

            run += ch

            # Force-break runs >14 Thai chars without a vowel breakpoint
            if (
                len(run) > 14
                and i + 1 < len(part)
                and part[i + 1] in _THAI_CONSONANTS
                and ch not in _THAI_DEPENDENT
                and part[i + 1] not in _THAI_LEADING_VOWELS
            ):
                out.append(run)
                out.append(_ZWSP)
                run = ""

        if run:
            out.append(run)
        if part_idx < len(space_parts) - 1:
            out.append(" ")

    return "".join(out)


def _hex_to_rgba(hex_color: str, alpha: int) -> str:
    """Convert '#RRGGBB' or '#RRGGBBAA' + alpha (0-255) to a CSS rgba() string.
    Used to make ONLY the background card alpha-controlled while keeping
    bubbles fully opaque."""
    h = hex_color.lstrip("#")
    if len(h) >= 6:
        r = int(h[0:2], 16)
        g = int(h[2:4], 16)
        b = int(h[4:6], 16)
    else:
        r = g = b = 0
    a = max(0, min(255, int(alpha)))
    return f"rgba({r}, {g}, {b}, {a})"


# ────────────────────────────────────────────────────────────────────
# ChatBubble — single rounded card. Multi-line wraps cleanly inside the
# bubble without breaking the shape.
# ────────────────────────────────────────────────────────────────────
class ChatBubble(QFrame):
    """A LINE-style rounded chat bubble.

    The frame paints ONE rounded rectangle background. Inside lives a
    speaker label (small, color-coded by type) and a wrapping message
    label (the full message body). Word wrap is handled by Qt natively
    so multi-line content never visually breaks the bubble shape.
    """

    def __init__(self, speaker: str, message: str, is_lore: bool = False,
                 font_family: str = "Anuphan", font_size: int = 18,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._speaker = speaker
        self._message = message
        self._is_lore = is_lore
        self._font_family = font_family
        self._font_size = font_size
        # NO graphics effect / fade animation — QGraphicsOpacityEffect on
        # a child of a frameless+translucent window leaves ghost paint trails
        # on drag (effect cache doesn't invalidate). Bubbles appear instantly.
        # Bubble fills horizontally up to the parent's allocated width and
        # uses heightForWidth() to compute its own height — that's how text
        # wraps cleanly inside without forcing the parent wider.
        sp = QSizePolicy(
            QSizePolicy.Policy.MinimumExpanding,
            QSizePolicy.Policy.Maximum,
        )
        sp.setHeightForWidth(True)
        self.setSizePolicy(sp)
        self._build()
        self._apply_palette()

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, w: int) -> int:
        """Compute total bubble height for a given width — used by Qt's
        layout system to size the bubble correctly when text wraps."""
        inner_w = max(1, w - 2 * BUBBLE_PAD_H)
        msg_h = self._msg_lbl.heightForWidth(inner_w) if self._msg_lbl else 0
        if msg_h <= 0 and self._msg_lbl is not None:
            msg_h = self._msg_lbl.sizeHint().height()
        speaker_h = (
            self._speaker_lbl.sizeHint().height()
            if self._speaker_lbl is not None else 0
        )
        spacing = 2 if speaker_h > 0 else 0
        return BUBBLE_PAD_V * 2 + speaker_h + spacing + msg_h

    def _build(self):
        v = QVBoxLayout(self)
        v.setContentsMargins(BUBBLE_PAD_H, BUBBLE_PAD_V, BUBBLE_PAD_H, BUBBLE_PAD_V)
        v.setSpacing(2)

        if self._speaker:
            self._speaker_lbl = QLabel(self._speaker)
            self._speaker_lbl.setObjectName("bubble_speaker")
            f = QFont(self._font_family, max(8, self._font_size - 4), QFont.Weight.Bold)
            self._speaker_lbl.setFont(f)
            v.addWidget(self._speaker_lbl)
        else:
            self._speaker_lbl = None

        # Insert ZWSPs at Thai syllable breaks BEFORE handing the text to
        # QLabel — Qt's wordWrap only breaks at whitespace, but Thai has
        # none, so without these Qt treats whole sentences as a single
        # unbreakable word and overflows the bubble.
        wrap_text = _insert_thai_breakpoints(self._message)
        self._msg_lbl = QLabel(wrap_text)
        self._msg_lbl.setObjectName("bubble_msg")
        self._msg_lbl.setFont(QFont(self._font_family, self._font_size))
        self._msg_lbl.setWordWrap(True)
        self._msg_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        # CRITICAL: QLabel.wordWrap by itself returns sizeHint = unwrapped
        # width (very wide). Layout will then grow the bubble + container to
        # match. To force the label to wrap at its allocated width, use
        # MinimumExpanding policy + setHeightForWidth so the layout asks
        # heightForWidth() instead of using sizeHint() naively.
        sp = QSizePolicy(
            QSizePolicy.Policy.MinimumExpanding,
            QSizePolicy.Policy.Preferred,
        )
        sp.setHeightForWidth(True)
        self._msg_lbl.setSizePolicy(sp)
        # Tiny minimum width keeps layout from getting stuck on huge sizeHint
        self._msg_lbl.setMinimumWidth(50)
        v.addWidget(self._msg_lbl)

    def _apply_palette(self):
        p = _palette()
        # Speaker color depends on identity / mode
        if self._is_lore:
            speaker_col = p["text_dim"]
            msg_col = p["text_dim"]
        elif self._speaker == "???":
            speaker_col = COLOR_UNKNOWN
            msg_col = p["text"]
        elif self._speaker == "คุณจะพูดว่าอย่างไร?":
            speaker_col = COLOR_CHOICE
            msg_col = p["text"]
        else:
            speaker_col = COLOR_DIALOGUE
            msg_col = p["text"]
        # CRITICAL: Qt's stylesheet system overrides setFont() on QLabels
        # inside styled widgets — so font-family + font-size MUST go in QSS,
        # not just setFont(). Otherwise font changes from FontPanel are
        # silently ignored (only size kicks in via setFont, but family stays
        # at the inherited default).
        if self._speaker_lbl is not None:
            sp_size = max(8, self._font_size - 4)
            self._speaker_lbl.setStyleSheet(
                f"color: {speaker_col}; background: transparent; "
                f"font-family: '{self._font_family}'; "
                f"font-size: {sp_size}pt; font-weight: bold;"
            )
        self._msg_lbl.setStyleSheet(
            f"color: {msg_col}; background: transparent; "
            f"font-family: '{self._font_family}'; "
            f"font-size: {self._font_size}pt;"
        )
        self.update()

    def paintEvent(self, event):
        """Paint a single rounded rect background — one shape only."""
        p = _palette()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        rect = QRectF(0.5, 0.5, self.width() - 1.0, self.height() - 1.0)
        path.addRoundedRect(rect, BUBBLE_RADIUS, BUBBLE_RADIUS)
        painter.fillPath(path, QColor(p["bg_titlebar"]))
        # Subtle border for definition
        painter.setPen(QPen(QColor(p["border_subtle"]), 1.0))
        painter.drawPath(path)
        painter.end()

    def update_font(self, family: str, size: int):
        """Hot-swap font without rebuilding the bubble. Apply via BOTH
        setFont (for fontMetrics-based heightForWidth) AND QSS (for the
        actual rendered font, since stylesheets override setFont in Qt)."""
        self._font_family = family
        self._font_size = size
        if self._speaker_lbl is not None:
            self._speaker_lbl.setFont(
                QFont(family, max(8, size - 4), QFont.Weight.Bold)
            )
        self._msg_lbl.setFont(QFont(family, size))
        # Re-apply QSS — this is what actually changes the rendered font
        # family. Without this, only setFont gets called and Qt's stylesheet
        # silently overrides it back to the inherited default.
        self._apply_palette()
        # Invalidate size cache so heightForWidth is recomputed
        if self._speaker_lbl is not None:
            self._speaker_lbl.updateGeometry()
        self._msg_lbl.updateGeometry()
        self.updateGeometry()
        self.adjustSize()

    def refresh_theme(self):
        """Call after theme change to repaint with new palette colors."""
        self._apply_palette()

    def fade_in(self):
        """No-op — animation removed. Kept for API compatibility."""
        pass


# ────────────────────────────────────────────────────────────────────
# Bottom-right resize grip — drag to resize the panel
# ────────────────────────────────────────────────────────────────────
class _ResizeGrip(QWidget):
    SIZE = 18

    def __init__(self, target_window: QWidget, parent: QWidget):
        super().__init__(parent)
        self.target = target_window
        self.setFixedSize(self.SIZE, self.SIZE)
        self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        self._dragging = False
        self._start_pos = QPoint()
        self._start_size = QSize()
        self._pixmap: Optional[QPixmap] = None
        self._load_icon(invert=False)

    def _load_icon(self, invert: bool = False):
        """Load assets/resize.png — auto-invert for light themes."""
        try:
            path = resource_path("assets/resize.png")
            if os.path.exists(path):
                pix = QPixmap(path).scaled(
                    self.SIZE, self.SIZE,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                if invert:
                    pix = invert_pixmap(pix)
                self._pixmap = pix
            else:
                self._pixmap = None
        except Exception:
            self._pixmap = None
        self.update()

    def set_invert(self, invert: bool):
        """Called by panel theme refresh — invert icon on light themes."""
        self._load_icon(invert=invert)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        if self._pixmap and not self._pixmap.isNull():
            p.drawPixmap(0, 0, self._pixmap)
        else:
            # Fallback — same triangle as before if icon failed to load
            s = self.SIZE
            m = 2
            tri = QPolygon([
                QPoint(s - m, m),
                QPoint(s - m, s - m),
                QPoint(m, s - m),
            ])
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(150, 150, 150, 200))
            p.drawPolygon(tri)
        p.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._start_pos = event.globalPosition().toPoint()
            self._start_size = self.target.size()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._dragging:
            delta = event.globalPosition().toPoint() - self._start_pos
            new_w = max(MIN_W, self._start_size.width() + delta.x())
            new_h = max(MIN_H, self._start_size.height() + delta.y())
            self.target.resize(new_w, new_h)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._dragging = False
        event.accept()


# ────────────────────────────────────────────────────────────────────
# Main panel
# ────────────────────────────────────────────────────────────────────
class TranslatedLogsPanel(QWidget):
    """Frameless overlay window showing translated dialogue history."""

    closed = pyqtSignal()  # emitted when user clicks the close button

    def __init__(self, settings, main_app=None, on_close_callback=None):
        super().__init__()
        self.settings = settings
        self.main_app = main_app
        self.on_close_callback = on_close_callback

        # ── State ──
        self.is_visible = False              # tracked manually for MBB.py compat
        self._bubbles: list[ChatBubble] = []
        self.message_cache: dict = {}        # kept empty but exposed for compat
        self._reverse_mode = bool(self.settings.get("logs_reverse_mode", False))
        self._is_locked = False              # session-only, always start False
        self._scroll_anim: Optional[QPropertyAnimation] = None
        self._dragging = False
        self._drag_pos = QPoint()
        self._first_show = True              # smart-position on first show

        # Font from settings (logs has its own font, separate from TUI)
        logs_settings = self._get_logs_settings()
        self._font_family = logs_settings.get("font_family", "Anuphan")
        self._font_size = int(logs_settings.get("font_size", 18))

        # Transparency value (10-100) — new key, fall back to old A/B/C/D map
        self._transparency = int(logs_settings.get(
            "transparency_value",
            self._migrate_old_transparency(logs_settings.get("transparency_mode")),
        ))
        self._transparency = max(10, min(100, self._transparency))

        self._build_window()
        self._build_ui()
        self._apply_theme()
        self._start_hover_polling()

        # Compatibility shim: old code uses `instance.root`
        self.root = self

    # ─── Compatibility shims for old Tkinter API ───
    def winfo_exists(self) -> bool:
        return True  # PyQt widget is alive once constructed; MBB.py uses this

    def state(self) -> str:
        return "withdrawn" if not self.isVisible() else "normal"

    def withdraw(self):
        self.hide_window()

    def deiconify(self):
        # Used in some legacy paths; no-op + visible
        self.show()
        self.is_visible = True

    def winfo_x(self) -> int:
        return self.x()

    def winfo_y(self) -> int:
        return self.y()

    def winfo_width(self) -> int:
        return self.width()

    def winfo_height(self) -> int:
        return self.height()

    @staticmethod
    def _migrate_old_transparency(mode: Optional[str]) -> int:
        """Convert legacy A/B/C/D → 10-100 slider value."""
        if not mode:
            return DEFAULT_TRANSPARENCY
        return {"A": 95, "B": 70, "C": 50, "D": 100}.get(mode, DEFAULT_TRANSPARENCY)

    def _get_logs_settings(self) -> dict:
        try:
            return self.settings.get_logs_settings() or {}
        except Exception:
            return {}

    # ─── Window setup ───
    def _build_window(self):
        self.setWindowTitle("Translation Logs")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool  # don't show in taskbar
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumSize(MIN_W, MIN_H)
        # Initial size from settings or defaults
        ls = self._get_logs_settings()
        w = int(ls.get("width", DEFAULT_W))
        h = int(ls.get("height", DEFAULT_H))
        self.resize(max(MIN_W, w), max(MIN_H, h))
        # Window stays at 100% opacity; only the card background fades via QSS
        # rgba (handled in _apply_theme using self._transparency).

    def _build_ui(self):
        # Outer margins for the drop shadow
        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(0)

        # Card frame (rounded background — paints itself via QSS)
        self.bg = QFrame()
        self.bg.setObjectName("logs_bg")
        outer.addWidget(self.bg)

        # Drop shadow on the card
        sh = QGraphicsDropShadowEffect(self)
        sh.setBlurRadius(24)
        sh.setColor(QColor(0, 0, 0, 160))
        sh.setOffset(0, 4)
        self.bg.setGraphicsEffect(sh)

        # Card contents
        v = QVBoxLayout(self.bg)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        v.addWidget(self._build_header())
        v.addWidget(self._build_scroll_area(), stretch=1)
        v.addWidget(self._build_bottom_bar())

        # Resize grip overlay (positioned in resizeEvent)
        self._grip = _ResizeGrip(self, self.bg)

    def _build_header(self) -> QWidget:
        wrap = QWidget()
        wrap.setObjectName("logs_header")
        wrap.setFixedHeight(40)
        h = QHBoxLayout(wrap)
        h.setContentsMargins(12, 0, 6, 0)
        h.setSpacing(6)

        self.title_lbl = QLabel("💬  บทสนทนา")
        self.title_lbl.setObjectName("logs_title")
        self.title_lbl.setFont(QFont(FONT_PRIMARY, 11, QFont.Weight.Bold))
        h.addWidget(self.title_lbl)
        h.addStretch(1)

        # Font size −/+ buttons
        self.btn_size_minus = self._mk_icon_btn("−", "ลดขนาดตัวอักษร")
        self.btn_size_minus.clicked.connect(self._on_size_decrease)
        h.addWidget(self.btn_size_minus)

        self.lbl_size = QLabel(str(self._font_size))
        self.lbl_size.setObjectName("logs_size_lbl")
        self.lbl_size.setFont(QFont(FONT_MONO, 9))
        self.lbl_size.setMinimumWidth(22)
        self.lbl_size.setAlignment(Qt.AlignmentFlag.AlignCenter)
        h.addWidget(self.lbl_size)

        self.btn_size_plus = self._mk_icon_btn("+", "เพิ่มขนาดตัวอักษร")
        self.btn_size_plus.clicked.connect(self._on_size_increase)
        h.addWidget(self.btn_size_plus)

        h.addSpacing(6)

        # Clear button — uses assets/clear.png (broom icon)
        self.btn_clear = self._mk_icon_btn("", "ล้างประวัติบทสนทนาทั้งหมด")
        self.btn_clear.setIconSize(QSize(16, 16))
        self.btn_clear.clicked.connect(self._on_clear_clicked)
        h.addWidget(self.btn_clear)
        self._update_clear_icon()

        # Close button (red hover)
        self.btn_close = self._mk_icon_btn("✕", "ปิดหน้าต่างบทสนทนา")
        self.btn_close.setObjectName("logs_close")
        self.btn_close.clicked.connect(self._on_close_clicked)
        h.addWidget(self.btn_close)

        return wrap

    def _mk_icon_btn(self, text: str, tip: str) -> QPushButton:
        b = QPushButton(text)
        b.setObjectName("logs_icon_btn")
        b.setFixedSize(26, 26)
        b.setFont(QFont(FONT_PRIMARY, 11, QFont.Weight.Bold))
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.setToolTip(tip)
        return b

    def _build_scroll_area(self) -> QScrollArea:
        self.scroll = QScrollArea()
        self.scroll.setObjectName("logs_scroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)

        # Inner container that holds the bubbles. Width tracks scroll viewport;
        # bubbles fill horizontally with side margins, stack tightly with
        # BUBBLE_GAP between them. Stretch at end pushes them to the top.
        self._bubbles_container = QWidget()
        self._bubbles_container.setObjectName("logs_bubbles")
        self._bubbles_layout = QVBoxLayout(self._bubbles_container)
        self._bubbles_layout.setContentsMargins(
            BUBBLE_SIDE_MARGIN, 8, BUBBLE_SIDE_MARGIN, 8
        )
        self._bubbles_layout.setSpacing(BUBBLE_GAP)
        # NOTE: Don't call setAlignment on the layout itself — that controls
        # the layout's position within its parent, NOT children inside it.
        # We pack bubbles tightly via insert + trailing stretch instead.
        self._bubbles_layout.addStretch(1)

        self.scroll.setWidget(self._bubbles_container)
        # Watch viewport resizes so we can constrain bubble widths to it —
        # QScrollArea.setWidgetResizable(True) lets the inner widget GROW
        # past the viewport when children's sizeHint demands it (which
        # QLabel.wordWrap=True does because its naive sizeHint is unwrapped).
        self.scroll.viewport().installEventFilter(self)
        return self.scroll

    def eventFilter(self, obj, event):
        from PyQt6.QtCore import QEvent
        et = event.type()
        # Drive hover bar visibility on ANY mouse motion — MouseMove fires
        # during drag (button down), HoverMove/HoverEnter fire on plain hover
        # (no button) when WA_Hover is set. We listen for all three so the
        # bar appears whether the user is dragging, hovering with no button,
        # or first entering the panel.
        if et in (
            QEvent.Type.MouseMove,
            QEvent.Type.HoverMove,
            QEvent.Type.HoverEnter,
            QEvent.Type.HoverLeave,
            QEvent.Type.Enter,
            QEvent.Type.Leave,
        ):
            self._update_hover_state()
        # Scroll viewport resize → constrain bubble widths
        elif obj is self.scroll.viewport() and et == QEvent.Type.Resize:
            self._constrain_bubble_widths()
        return super().eventFilter(obj, event)

    def _constrain_bubble_widths(self):
        """Cap each bubble's width AND its inner QLabel's width to the scroll
        viewport. Capping only the bubble isn't enough — QLabel.wordWrap uses
        the label's own width to decide wrap points, and if the label thinks
        it's wider than the bubble allows, text spills past the bubble paint."""
        if not hasattr(self, "scroll") or not hasattr(self, "_bubbles"):
            return
        vp_w = self.scroll.viewport().width()
        if vp_w <= 0:
            return
        # Reserve a small safety margin (scrollbar can claim ~12px when it
        # appears unexpectedly during font growth)
        safety = 4
        bubble_max_w = vp_w - 2 * BUBBLE_SIDE_MARGIN - safety
        if bubble_max_w <= 0:
            return
        label_max_w = bubble_max_w - 2 * BUBBLE_PAD_H
        for b in self._bubbles:
            b.setMaximumWidth(bubble_max_w)
            if getattr(b, "_msg_lbl", None) is not None:
                b._msg_lbl.setMaximumWidth(label_max_w)
                # Force re-layout so heightForWidth recomputes with new width
                b._msg_lbl.updateGeometry()
            b.updateGeometry()
        self._bubbles_container.setMaximumWidth(vp_w)

    def _build_bottom_bar(self) -> QWidget:
        """Hover-shown bottom bar with quick controls.

        Shown when mouse is over the panel; hidden otherwise.
        """
        wrap = QWidget()
        wrap.setObjectName("logs_bottom")
        wrap.setFixedHeight(34)
        h = QHBoxLayout(wrap)
        h.setContentsMargins(10, 4, 10, 4)
        h.setSpacing(8)

        # Lock toggle — uses assets/lock.png + assets/unlock.png
        self.btn_lock = QPushButton()
        self.btn_lock.setObjectName("logs_bottom_btn")
        self.btn_lock.setCheckable(True)
        self.btn_lock.setFixedSize(28, 26)
        self.btn_lock.setIconSize(QSize(16, 16))
        self.btn_lock.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_lock.setToolTip("ล็อกตำแหน่งและขนาด (เฉพาะเซสชันนี้)")
        self.btn_lock.clicked.connect(self._on_lock_toggled)
        h.addWidget(self.btn_lock)
        self._update_lock_icon()  # initial icon

        # Reverse toggle
        self.btn_reverse = QPushButton("↕")
        self.btn_reverse.setObjectName("logs_bottom_btn")
        self.btn_reverse.setCheckable(True)
        self.btn_reverse.setChecked(self._reverse_mode)
        self.btn_reverse.setFixedSize(26, 26)
        self.btn_reverse.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reverse.setToolTip("สลับลำดับข้อความ ใหม่ ↔ เก่า")
        self.btn_reverse.clicked.connect(self._on_reverse_toggled)
        h.addWidget(self.btn_reverse)

        h.addStretch(1)

        # Transparency slider (compact, 10-100)
        opacity_lbl = QLabel("○")
        opacity_lbl.setObjectName("logs_bottom_lbl")
        opacity_lbl.setFont(QFont(FONT_PRIMARY, 11))
        opacity_lbl.setToolTip("ปรับความโปร่งใส")
        h.addWidget(opacity_lbl)

        self.transparency_slider = QSlider(Qt.Orientation.Horizontal)
        self.transparency_slider.setObjectName("logs_slider")
        self.transparency_slider.setMinimum(10)
        self.transparency_slider.setMaximum(100)
        self.transparency_slider.setValue(self._transparency)
        self.transparency_slider.setFixedWidth(86)
        self.transparency_slider.setToolTip(f"ความโปร่งใส: {self._transparency}%")
        self.transparency_slider.valueChanged.connect(self._on_transparency_changed)
        h.addWidget(self.transparency_slider)

        h.addStretch(1)

        # Font picker button
        self.btn_font = QPushButton("Aa")
        self.btn_font.setObjectName("logs_bottom_btn")
        self.btn_font.setFixedSize(36, 26)
        self.btn_font.setFont(QFont(FONT_PRIMARY, 10, QFont.Weight.Bold))
        self.btn_font.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_font.setToolTip("ตั้งค่าฟอนต์ — บทสนทนา")
        self.btn_font.clicked.connect(self._on_font_clicked)
        h.addWidget(self.btn_font)
        # Spacer reserves room on the right for the resize grip overlay
        # (which sits in the bottom-right corner of bg). Without this, the
        # font button overlaps the grip and is hard to click.
        h.addSpacing(20)

        wrap.setVisible(False)  # hidden by default; hover shows
        self._bottom_bar = wrap
        return wrap

    # ─── Theme ───
    def _apply_theme(self):
        _refresh_logs_theme()  # invalidate cache so we get fresh palette
        p = _palette()
        light = is_light_theme(p["bg"])

        # Asset-based icons — auto-inverted for light themes
        if hasattr(self, "btn_lock"):
            self._update_lock_icon()
        if hasattr(self, "btn_clear"):
            self._update_clear_icon()

        # Background card uses an rgba colour driven by the transparency slider.
        # Bubbles paint themselves with solid colours in their own paintEvent,
        # so they remain fully opaque regardless of this alpha. This is the key
        # design decision: only the card behind the bubbles fades, not the text.
        bg_alpha = max(0, min(255, int(self._transparency * 255 / 100)))
        bg_rgba = _hex_to_rgba(p["bg"], bg_alpha)
        border_rgba = _hex_to_rgba(p["border_subtle"], bg_alpha)

        qss = f"""
            QFrame#logs_bg {{
                background: {bg_rgba};
                border: 1px solid {border_rgba};
                border-radius: 12px;
            }}
            QWidget#logs_header {{
                background: transparent;
            }}
            QWidget#logs_bottom {{
                background: {p['bg_titlebar']};
                border-top: 1px solid {p['border_subtle']};
                border-bottom-left-radius: 12px;
                border-bottom-right-radius: 12px;
            }}
            QLabel#logs_title {{
                color: {p['text']};
                background: transparent;
            }}
            QLabel#logs_size_lbl, QLabel#logs_bottom_lbl {{
                color: {p['text_dim']};
                background: transparent;
            }}
            QPushButton#logs_icon_btn, QPushButton#logs_bottom_btn {{
                background: transparent;
                color: {p['text_dim']};
                border: none;
                border-radius: 4px;
            }}
            QPushButton#logs_icon_btn:hover, QPushButton#logs_bottom_btn:hover {{
                background: {p['bg_medium']};
                color: {p['text']};
            }}
            QPushButton#logs_bottom_btn:checked {{
                background: {p['accent']};
                color: {p['toggled_text']};
            }}
            QPushButton#logs_close:hover {{
                background: #d23030;
                color: #ffffff;
            }}
            QScrollArea#logs_scroll {{
                background: transparent;
                border: none;
            }}
            QWidget#logs_bubbles {{
                background: transparent;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 8px;
                margin: 4px 2px 4px 0;
            }}
            QScrollBar::handle:vertical {{
                background: {p['border_active']};
                border-radius: 4px;
                min-height: 24px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {p['accent']};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
                background: transparent;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: transparent;
            }}
            QSlider#logs_slider::groove:horizontal {{
                background: {p['btn_bg']};
                height: 4px;
                border-radius: 2px;
            }}
            QSlider#logs_slider::handle:horizontal {{
                background: {p['accent']};
                width: 12px;
                height: 12px;
                margin: -4px 0;
                border-radius: 6px;
            }}
            QSlider#logs_slider::sub-page:horizontal {{
                background: {p['accent']};
                border-radius: 2px;
            }}
        """
        self.setStyleSheet(qss)
        # Refresh existing bubbles
        for b in self._bubbles:
            b.refresh_theme()
        # Resize grip icon: invert for light themes so the dark triangle
        # stays visible against the light background.
        if hasattr(self, "_grip"):
            self._grip.set_invert(light)

    # ─── Position grip + bottom bar on resize ───
    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Grip in bottom-right corner of bg
        margin = 4
        self._grip.move(
            self.bg.width() - self._grip.width() - margin,
            self.bg.height() - self._grip.height() - margin,
        )
        self._grip.raise_()
        # Persist size if locked
        if self._is_locked:
            self._save_geometry()

    # ─── Drag (header only) ───
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Only drag if click is within header area (top 40px)
            if event.position().y() <= 48:
                self._dragging = True
                self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._dragging and (event.buttons() & Qt.MouseButton.LeftButton):
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            # Force a repaint of the panel and all its descendants — without
            # this, frameless + WA_TranslucentBackground windows leave ghost
            # paint trails of child widgets (especially those with graphics
            # effects) at their old screen positions.
            self.update()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._dragging:
            self._dragging = False
            if self._is_locked:
                self._save_geometry()
        super().mouseReleaseEvent(event)

    # ─── Hover detection for bottom bar ───
    # `enterEvent` / `leaveEvent` only fire on the panel widget itself, NOT
    # on its children. Mouse moving onto a button inside the panel makes the
    # panel "leave" (hiding the bar) and then fail to re-enter when on the
    # button. We install an application-level eventFilter so we catch mouse
    # motion REGARDLESS of which child widget is under the cursor — pure
    # QTimer polling can stall when `_save_geometry`'s disk I/O blocks the
    # event loop, which is exactly what happened with the lock-mode setting
    # being persisted on every routine layout reflow.
    def _start_hover_polling(self):
        from PyQt6.QtGui import QCursor
        self._cursor_cls = QCursor
        # CRITICAL: Qt widgets do NOT emit mouseMoveEvent on plain hover by
        # default — only when a button is held down (drag). To get hover
        # events without a button press we must either enable mouseTracking
        # or use Qt's hover system (WA_Hover + HoverMove events). We do both
        # for maximum reliability.
        self._enable_mouse_tracking_recursive(self)
        # Application-level filter — catches MouseMove (during drag) AND
        # HoverMove (during plain hover) on any widget in the app
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)
        # Periodic safety net (cursor stops moving / window state changes)
        self._hover_timer = QTimer(self)
        self._hover_timer.setInterval(250)
        self._hover_timer.timeout.connect(self._check_hover)
        self._hover_timer.start()

    def _enable_mouse_tracking_recursive(self, w: QWidget):
        """Turn on mouseTracking + WA_Hover on the widget and every descendant
        so they emit HoverMove / mouseMoveEvent on plain hover (no button)."""
        try:
            w.setMouseTracking(True)
            w.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
            for child in w.findChildren(QWidget):
                child.setMouseTracking(True)
                child.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        except Exception as e:
            log.debug(f"enable_mouse_tracking failed: {e}")

    def _update_hover_state(self):
        """Single source of truth for bottom-bar visibility based on cursor."""
        if not self.isVisible():
            if self._bottom_bar.isVisible():
                self._bottom_bar.setVisible(False)
            return
        global_pos = self._cursor_cls.pos()
        local_pos = self.mapFromGlobal(global_pos)
        inside = self.rect().contains(local_pos)
        if inside != self._bottom_bar.isVisible():
            self._bottom_bar.setVisible(inside)

    def _check_hover(self):
        # Backup poll path — same logic as the eventFilter
        self._update_hover_state()

    # ─── Smart positioning ───
    def _smart_position(self, mbb_side: str = "left",
                        monitor_info: Optional[dict] = None):
        """Place the panel near the right edge (or left edge if MBB is on
        the right). Centered vertically. Never blocks gameplay area."""
        screen = QApplication.primaryScreen()
        if monitor_info:
            sw = int(monitor_info.get("width", screen.size().width()))
            sh = int(monitor_info.get("height", screen.size().height()))
            sx = int(monitor_info.get("left", 0))
            sy = int(monitor_info.get("top", 0))
        else:
            geo = screen.availableGeometry()
            sw, sh, sx, sy = geo.width(), geo.height(), geo.x(), geo.y()

        # Default to RIGHT edge; if MBB is on the right, mirror to LEFT
        w, h = self.width(), self.height()
        if mbb_side == "right":
            x = sx + RIGHT_EDGE_PAD
        else:
            x = sx + sw - w - RIGHT_EDGE_PAD
        y = sy + max(TOP_PAD, (sh - h) // 2)
        # Clamp to monitor
        x = max(sx, min(sx + sw - w, x))
        y = max(sy, min(sy + sh - h, y))
        self.move(x, y)

    # ─── Public API (compatible with old Tkinter version) ───
    def show_window(self, mbb_side: str = "left",
                    monitor_info: Optional[dict] = None):
        """Show the panel with smart positioning."""
        if self._first_show or not self._is_locked:
            self._smart_position(mbb_side, monitor_info)
        # Card alpha already encoded in QSS via _apply_theme — no setWindowOpacity
        self.show()
        self.raise_()
        self.activateWindow()
        self.is_visible = True
        self._first_show = False
        # Auto-scroll to latest after showing
        QTimer.singleShot(50, self._scroll_to_latest)

    def hide_window(self):
        self.hide()
        self.is_visible = False
        if self._is_locked:
            self._save_geometry()
        if callable(self.on_close_callback):
            try:
                self.on_close_callback()
            except Exception as e:
                log.error(f"on_close_callback error: {e}")

    def add_message(self, text: str, is_force_retranslation: bool = False,
                    is_lore_text: bool = False):
        """Add a new message bubble.

        Args:
            text: Message text. May be `"Speaker: dialogue"` or just dialogue.
            is_force_retranslation: Ignored in this rewrite (Smart Replacement
                is disabled). Kept for API compatibility.
            is_lore_text: If True, render as narration (dim color, no speaker).
        """
        if not text or not text.strip():
            return
        speaker, msg = self._parse_message(text, is_lore_text)
        bubble = ChatBubble(
            speaker=speaker,
            message=msg,
            is_lore=is_lore_text,
            font_family=self._font_family,
            font_size=self._font_size,
            parent=self._bubbles_container,
        )
        self._insert_bubble(bubble)
        self._enforce_bubble_cap()
        # No fade animation — bubble appears instantly (clean drag behavior)
        # Scroll to the newly inserted bubble after layout settles
        QTimer.singleShot(20, self._scroll_to_latest)

    def add_message_from_translation(self, text: str,
                                     is_force_retranslation: bool = False):
        """Alias used by some legacy call sites in MBB.py."""
        self.add_message(text, is_force_retranslation=is_force_retranslation)

    def update_font_settings(self, font_name: str, font_size: int):
        """Called by FontPanel when the user applies a font change with
        target='logs' or 'both'. Updates all live bubbles + persists."""
        if not font_name:
            font_name = self._font_family
        try:
            font_size = int(font_size)
        except (TypeError, ValueError):
            font_size = self._font_size
        font_size = max(8, min(36, font_size))
        self._font_family = font_name
        self._font_size = font_size
        self.lbl_size.setText(str(font_size))
        for b in self._bubbles:
            b.update_font(font_name, font_size)
        # Reapply width constraints AFTER font change — new font metrics
        # mean new wrap points; without this, large fonts overflow because
        # the cached layout still uses the old font's heightForWidth result.
        self._constrain_bubble_widths()
        # And once more after the layout has settled (next event loop tick)
        QTimer.singleShot(0, self._constrain_bubble_widths)
        # Persist
        try:
            self.settings.set_logs_settings(
                font_family=font_name, font_size=font_size,
            )
        except Exception as e:
            log.error(f"update_font_settings persist failed: {e}")

    def clear_logs(self):
        """Remove all bubbles and clear the cache."""
        for b in self._bubbles:
            b.setParent(None)
            b.deleteLater()
        self._bubbles.clear()
        self.message_cache.clear()

    def get_cache_stats(self) -> dict:
        return {
            "total_cached": len(self.message_cache),
            "total_bubbles": len(self._bubbles),
            "last_message": self._bubbles[-1]._message if self._bubbles else "",
            "smart_mode": False,  # disabled in this rewrite
        }

    def cleanup(self):
        """Called on app shutdown — persist + tear down."""
        try:
            self._save_geometry(force=True)
        except Exception:
            pass
        # Detach application-level eventFilter to avoid dangling references
        try:
            app = QApplication.instance()
            if app is not None:
                app.removeEventFilter(self)
        except Exception:
            pass
        self.clear_logs()

    # ─── Internals ───
    def _parse_message(self, text: str, is_lore: bool) -> tuple[str, str]:
        """Split a `Speaker: dialogue` string. Returns (speaker, body).
        Lore text never has a speaker."""
        text = text.strip()
        if is_lore:
            return ("", text)
        if ": " in text:
            head, tail = text.split(": ", 1)
            head = head.strip()
            # Speaker names are short — guard against false splits
            if head and len(head) <= 40 and "\n" not in head:
                return (head, tail.strip())
        return ("", text)

    def _insert_bubble(self, bubble: ChatBubble):
        """Add bubble at top (reverse mode) or bottom (normal mode).
        The layout has a stretch at the end — we insert before it (normal)
        or at index 0 (reverse)."""
        # Constrain BOTH bubble + inner label width BEFORE adding (avoids
        # the brief overflow flash on first paint when label sizeHint
        # would otherwise dictate a too-wide bubble).
        vp_w = self.scroll.viewport().width()
        if vp_w > 0:
            safety = 4
            bubble_max_w = vp_w - 2 * BUBBLE_SIDE_MARGIN - safety
            bubble.setMaximumWidth(bubble_max_w)
            if getattr(bubble, "_msg_lbl", None) is not None:
                bubble._msg_lbl.setMaximumWidth(bubble_max_w - 2 * BUBBLE_PAD_H)
        # Layout count: bubbles + 1 stretch
        if self._reverse_mode:
            self._bubbles_layout.insertWidget(0, bubble)
            self._bubbles.insert(0, bubble)
        else:
            # Insert before the trailing stretch
            insert_at = self._bubbles_layout.count() - 1
            self._bubbles_layout.insertWidget(insert_at, bubble)
            self._bubbles.append(bubble)

    def _enforce_bubble_cap(self):
        """Destroy oldest bubbles when over MAX_BUBBLES."""
        while len(self._bubbles) > MAX_BUBBLES:
            # Oldest = first in normal mode, last in reverse mode
            old = self._bubbles.pop(0 if not self._reverse_mode else -1)
            old.setParent(None)
            old.deleteLater()

    def _scroll_to_latest(self):
        """Smooth-scroll the QScrollArea to the newest bubble."""
        sb = self.scroll.verticalScrollBar()
        target = sb.minimum() if self._reverse_mode else sb.maximum()
        if sb.value() == target:
            return
        if self._scroll_anim and self._scroll_anim.state() == QPropertyAnimation.State.Running:
            self._scroll_anim.stop()
        anim = QPropertyAnimation(sb, b"value", self)
        anim.setDuration(SCROLL_ANIM_MS)
        anim.setStartValue(sb.value())
        anim.setEndValue(target)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start()
        self._scroll_anim = anim

    def _repack_bubbles(self):
        """Used by reverse-mode toggle — re-add all bubbles in the new order."""
        # Snapshot + remove
        snap = list(self._bubbles)
        for b in snap:
            self._bubbles_layout.removeWidget(b)
        self._bubbles.clear()
        # Re-insert in original chronological order; _insert_bubble handles
        # placement based on current _reverse_mode
        for b in snap:
            self._insert_bubble(b)
        QTimer.singleShot(20, self._scroll_to_latest)

    def _save_geometry(self, force: bool = False):
        """Persist current size (and position if locked) to settings.

        Throttled via a single-shot timer (500ms) so rapid resizeEvent fires
        from layout reflows (bottom-bar show/hide, drag, etc.) collapse into
        ONE disk write. Without this, every layout reflow caused a synchronous
        json save which blocked the event loop and starved the hover timer."""
        if force:
            self._do_save_geometry()
            return
        if not hasattr(self, "_save_throttle"):
            self._save_throttle = QTimer(self)
            self._save_throttle.setSingleShot(True)
            self._save_throttle.setInterval(500)
            self._save_throttle.timeout.connect(self._do_save_geometry)
        self._save_throttle.start()  # restarts countdown each call

    def _do_save_geometry(self):
        try:
            kwargs = {"width": self.width(), "height": self.height()}
            if self._is_locked:
                kwargs["x"] = self.x()
                kwargs["y"] = self.y()
            self.settings.set_logs_settings(**kwargs)
        except Exception as e:
            log.debug(f"save_geometry failed: {e}")

    # ─── Header button handlers ───
    def _on_size_decrease(self):
        if self._font_size > 8:
            self.update_font_settings(self._font_family, self._font_size - 1)

    def _on_size_increase(self):
        if self._font_size < 36:
            self.update_font_settings(self._font_family, self._font_size + 1)

    def _on_clear_clicked(self):
        if not self._bubbles:
            return
        # Reuse the NPC Manager's confirm_delete for visual consistency
        try:
            from pyqt_ui.npc_manager_panel import confirm_delete
            ok = confirm_delete(
                self, "ล้างประวัติ",
                f"ต้องการล้างข้อความทั้งหมด ({len(self._bubbles)} รายการ) ใช่หรือไม่?",
            )
        except Exception:
            ok = True  # fallback if helper unavailable
        if ok:
            self.clear_logs()

    def _on_close_clicked(self):
        self.hide_window()
        self.closed.emit()

    # ─── Bottom bar handlers ───
    def _on_lock_toggled(self):
        self._is_locked = self.btn_lock.isChecked()
        self._update_lock_icon()
        if self._is_locked:
            self._save_geometry()

    def _update_clear_icon(self):
        """Load assets/clear.png (broom). Auto-invert on light themes."""
        try:
            path = resource_path("assets/clear.png")
            if os.path.exists(path):
                pix = QPixmap(path).scaled(
                    16, 16,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                try:
                    p = _palette()
                    if is_light_theme(p["bg"]):
                        pix = invert_pixmap(pix)
                except Exception:
                    pass
                self.btn_clear.setIcon(QIcon(pix))
                self.btn_clear.setText("")
                return
        except Exception:
            pass
        self.btn_clear.setIcon(QIcon())
        self.btn_clear.setText("⌫")

    def _update_lock_icon(self):
        """Pick lock.png or unlock.png from assets, auto-invert on light themes."""
        try:
            asset = "lock.png" if self._is_locked else "unlock.png"
            path = resource_path(f"assets/{asset}")
            if os.path.exists(path):
                pix = QPixmap(path).scaled(
                    16, 16,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                # Light-theme inversion (assets are white-on-transparent)
                try:
                    p = _palette()
                    if is_light_theme(p["bg"]):
                        pix = invert_pixmap(pix)
                except Exception:
                    pass
                self.btn_lock.setIcon(QIcon(pix))
                self.btn_lock.setText("")
                return
        except Exception:
            pass
        # Fallback to emoji if asset missing
        self.btn_lock.setIcon(QIcon())
        self.btn_lock.setText("🔒" if self._is_locked else "🔓")

    def _on_reverse_toggled(self):
        self._reverse_mode = self.btn_reverse.isChecked()
        try:
            self.settings.set_logs_settings(logs_reverse_mode=self._reverse_mode)
        except Exception:
            pass
        self._repack_bubbles()

    def _on_transparency_changed(self, value: int):
        """Slider 10-100. Affects ONLY the background card alpha — bubbles
        and text remain fully opaque (their paintEvents use solid colours)."""
        self._transparency = max(10, min(100, value))
        self.transparency_slider.setToolTip(f"ความโปร่งใส: {self._transparency}%")
        self._apply_theme()  # rebuild QSS with new bg alpha
        # Persist (best-effort)
        try:
            self.settings.set_logs_settings(transparency_value=self._transparency)
        except TypeError:
            try:
                if "logs_ui" not in self.settings.settings:
                    self.settings.settings["logs_ui"] = {}
                self.settings.settings["logs_ui"]["transparency_value"] = self._transparency
                self.settings.save_settings()
            except Exception:
                pass
        except Exception:
            pass

    def _on_font_clicked(self):
        """Open FontPanel via main_app's settings_ui. Pre-select target='logs'
        so the panel reflects this UI's font (not TUI's)."""
        try:
            if not (self.main_app and hasattr(self.main_app, "settings_ui")):
                log.warning("Font button: main_app.settings_ui not available")
                return
            sp = self.main_app.settings_ui
            if not hasattr(sp, "_ensure_font_panel"):
                log.warning("Font button: settings_ui._ensure_font_panel missing")
                return
            sp._ensure_font_panel()
            # NB: attribute is `_font_panel` (private), NOT `font_panel`
            fp = getattr(sp, "_font_panel", None)
            if fp is None:
                log.warning("Font button: _font_panel still None after ensure")
                return
            # Pre-select logs target then reload so size/font display reflects ours
            if hasattr(fp, "_set_target"):
                try:
                    fp._set_target("logs")
                except Exception as e:
                    log.debug(f"_set_target('logs') skipped: {e}")
            self._position_font_panel_near_logs(fp)
            fp.show()
            fp.raise_()
            fp.activateWindow()
        except Exception as e:
            log.error(f"open font panel failed: {e}", exc_info=True)

    def _position_font_panel_near_logs(self, fp: QWidget):
        """Place FontPanel just to the left of the logs window, vertically aligned."""
        try:
            screen = QApplication.primaryScreen().availableGeometry()
            x = self.x() - fp.width() - 10
            if x < screen.x():
                x = self.x() + self.width() + 10  # fallback to right
            y = self.y()
            # Clamp
            x = max(screen.x(), min(screen.x() + screen.width() - fp.width(), x))
            y = max(screen.y(), min(screen.y() + screen.height() - fp.height(), y))
            fp.move(x, y)
        except Exception:
            pass


# ────────────────────────────────────────────────────────────────────
# Module-level alias for MBB.py compatibility
# ────────────────────────────────────────────────────────────────────
# Old code: `from translated_logs import Translated_Logs`
# We export the same name from this module so a redirected import works.
Translated_Logs = TranslatedLogsPanel
