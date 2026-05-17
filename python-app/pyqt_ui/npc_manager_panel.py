"""
NPCManagerPanel (PyQt6) — Modern themed replacement for the legacy Tkinter
NPCManagerCard. Built 2026-04-25.

Phase 1: Shell + Main Characters tab (CRUD).
Other tabs (NPCs / Lore / Roles / Word Fixes) come in Phase 2-4.

Architecture:
- Frameless window (matches Settings/Theme/Font panels)
- Header with title + pin + close
- QTabBar-style tab buttons
- Per-tab: search bar + list (left) + details panel (right) + footer
- Theme via derive_palette() + QSS — same pattern as other PyQt6 panels
- Data layer in npc_data_manager.NPCDataManager (testable, UI-independent)
"""
import json
import os
import logging
import time
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QGraphicsDropShadowEffect, QFrame, QTreeWidget, QTreeWidgetItem,
    QStackedWidget, QComboBox, QButtonGroup, QMessageBox, QSizePolicy,
    QTextEdit, QHeaderView, QAbstractItemView,
    QDialog, QCheckBox, QScrollArea, QFileDialog, QApplication,
)
from PyQt6.QtGui import QColor, QFont, QIcon, QPixmap, QCursor
from PyQt6.QtCore import Qt, QPoint, QSize, QTimer, pyqtSignal

from pyqt_ui.styles import (
    FONT_PRIMARY, FONT_MONO, derive_palette, is_light_theme,
    invert_pixmap, tint_pixmap,
)
from resource_utils import resource_path
from npc_data_manager import NPCDataManager

log = logging.getLogger("npc-panel")

WIDTH = 940
HEIGHT = 920   # bumped from 840 to fit avatar (80px) + existing 14 items in details


# ────────────────────────────────────────────────────────────────────
# Helpers for the per-tab list widgets — QTreeWidget gives us proper
# column alignment (col 0 right, col 1 left) which QListWidget can't.
# ────────────────────────────────────────────────────────────────────
def _make_tree(columns: list) -> QTreeWidget:
    """Build a multi-column tree widget styled to look like a list.
    Column 0 is right-aligned, column 1+ is left-aligned (per user request)."""
    tree = QTreeWidget()
    tree.setObjectName("npc_list")
    tree.setColumnCount(len(columns))
    tree.setHeaderHidden(True)
    tree.setRootIsDecorated(False)        # no expand arrows (it's a flat list)
    tree.setAlternatingRowColors(False)
    tree.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    tree.setUniformRowHeights(True)
    tree.setIndentation(0)
    # Force icon cell size — without this Qt picks default ~16px and may
    # downscale our 22px badge, losing the photo-glyph detail.
    tree.setIconSize(QSize(22, 22))
    # Column sizing: first col gets ~40% of width, last col stretches
    header = tree.header()
    header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
    for i in range(1, len(columns)):
        header.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
    return tree


def _make_avatar_badge_icon(accent_hex: str, size: int = 22) -> QIcon:
    """Build a small flat-design 'has avatar' badge — themed rounded square bg
    with a white photo glyph (frame + mountain peak + sun) drawn on top.
    Used to mark MAIN-tab list rows that have an avatar set.

    Bg color falls back to dark slate (#2a2a2a) when the accent is too light
    (luminance > 0.6) — otherwise the white glyph would disappear into a
    near-white background. The glyph stays white either way (good contrast on
    both saturated accents and the dark fallback)."""
    from PyQt6.QtCore import QRectF, QPointF
    from PyQt6.QtGui import QPainter, QPen, QColor as _QC
    from pyqt_ui.styles import _luminance
    try:
        bg_color = _QC(accent_hex) if _luminance(accent_hex) <= 0.6 else _QC("#2a2a2a")
    except Exception:
        bg_color = _QC(accent_hex)
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    # Themed (or dark-fallback) background — rounded square
    p.setBrush(bg_color)
    p.setPen(Qt.PenStyle.NoPen)
    radius = max(3.0, size / 5.0)
    p.drawRoundedRect(QRectF(0, 0, size, size), radius, radius)
    # White photo glyph: thin frame + mountain peak + sun
    pen = QPen(_QC(255, 255, 255))
    pen.setWidthF(1.4)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    inset = size * 0.22
    frame = QRectF(inset, inset, size - 2 * inset, size - 2 * inset)
    p.drawRoundedRect(frame, 1.5, 1.5)
    # Mountain peak (V) inside frame
    cx, _cy = size / 2.0, size / 2.0
    base_y = size - inset - 1.0
    peak_y = size * 0.55
    p.drawLine(QPointF(inset + 1.0, base_y),
               QPointF(cx, peak_y))
    p.drawLine(QPointF(cx, peak_y),
               QPointF(size - inset - 1.0, base_y))
    # Sun dot
    p.setBrush(_QC(255, 255, 255))
    p.setPen(Qt.PenStyle.NoPen)
    sun_r = max(1.2, size * 0.075)
    p.drawEllipse(QPointF(size * 0.66, size * 0.38), sun_r, sun_r)
    p.end()
    return QIcon(pm)


def _make_empty_badge_icon(size: int = 22) -> QIcon:
    """Transparent placeholder same size as the avatar badge — keeps every row
    horizontally aligned even when no badge is shown."""
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    return QIcon(pm)


def _format_relative_time(ts: float) -> str:
    """Unix timestamp → 'X นาทีที่แล้ว' / 'X ชม.ที่แล้ว' / 'YYYY-MM-DD' for old.
    Used by the header status strip so the user can see at a glance how fresh
    the on-disk npc.json is."""
    import time
    if not ts or ts <= 0:
        return "—"
    delta = time.time() - ts
    if delta < 60:
        return "เมื่อสักครู่"
    if delta < 3600:
        return f"{int(delta / 60)} นาทีที่แล้ว"
    if delta < 86400:
        return f"{int(delta / 3600)} ชม.ที่แล้ว"
    if delta < 86400 * 7:
        return f"{int(delta / 86400)} วันที่แล้ว"
    from datetime import datetime
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d")


def _new_row(values: list, *, payload=None) -> QTreeWidgetItem:
    """Create a tree item with right-aligned col 0, left-aligned col 1+,
    and optional UserRole payload (e.g. data index or key)."""
    item = QTreeWidgetItem(values)
    # Col 0 right-align (with vertical center)
    item.setTextAlignment(0, int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter))
    for c in range(1, len(values)):
        item.setTextAlignment(c, int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter))
    if payload is not None:
        item.setData(0, Qt.ItemDataRole.UserRole, payload)
    return item


def _build_list_header(*labels) -> QHBoxLayout:
    """Build the visible NAME/TYPE header row above the tree.
    First label right-aligned, others left-aligned (mirrors row alignment)."""
    head = QHBoxLayout()
    head.setContentsMargins(8, 0, 8, 0)
    for i, txt in enumerate(labels):
        lbl = QLabel(txt)
        if i == 0:
            lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        else:
            lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        lbl.setObjectName("npc_list_header")  # theme-styled via panel QSS
        lbl.setFont(QFont(FONT_PRIMARY, 11, QFont.Weight.Bold))
        head.addWidget(lbl, stretch=1)
    return head


def confirm_delete(parent, title: str, message: str) -> bool:
    """Custom delete-confirm dialog — bigger text than the OS default
    QMessageBox, frameless to match the panel aesthetic, and a RED Yes
    button so the destructive action is visually obvious.
    Returns True if the user clicked 'ใช่ ลบ', False otherwise."""
    from PyQt6.QtWidgets import QDialog
    dlg = QDialog(parent)
    dlg.setWindowFlags(
        Qt.WindowType.Dialog
        | Qt.WindowType.FramelessWindowHint
        | Qt.WindowType.WindowStaysOnTopHint
    )
    dlg.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    dlg.setModal(True)

    # Background card
    bg = QFrame(dlg)
    bg.setObjectName("confirm_bg")
    shadow = QGraphicsDropShadowEffect(dlg)
    shadow.setBlurRadius(28)
    shadow.setOffset(0, 6)
    shadow.setColor(QColor(0, 0, 0, 200))
    bg.setGraphicsEffect(shadow)

    outer = QVBoxLayout(dlg)
    outer.setContentsMargins(18, 18, 18, 18)
    outer.addWidget(bg)

    inner = QVBoxLayout(bg)
    inner.setContentsMargins(28, 22, 28, 20)
    inner.setSpacing(18)

    # Title
    t = QLabel(title)
    t.setObjectName("confirm_title")
    t.setFont(QFont(FONT_PRIMARY, 14, QFont.Weight.Bold))
    inner.addWidget(t)

    # Message — large + readable
    m = QLabel(message)
    m.setObjectName("confirm_msg")
    m.setWordWrap(True)
    m.setFont(QFont(FONT_PRIMARY, 12))
    m.setMinimumWidth(360)
    inner.addWidget(m)

    # Buttons
    btn_row = QHBoxLayout()
    btn_row.setSpacing(10)
    btn_row.addStretch(1)
    btn_no = QPushButton("ยกเลิก")
    btn_no.setObjectName("confirm_no")
    btn_no.setFont(QFont(FONT_PRIMARY, 11))
    btn_no.setMinimumSize(110, 38)
    btn_no.setCursor(Qt.CursorShape.PointingHandCursor)
    btn_no.clicked.connect(dlg.reject)
    btn_row.addWidget(btn_no)

    btn_yes = QPushButton("ใช่ ลบ")
    btn_yes.setObjectName("confirm_yes")
    btn_yes.setFont(QFont(FONT_PRIMARY, 11, QFont.Weight.Bold))
    btn_yes.setMinimumSize(110, 38)
    btn_yes.setCursor(Qt.CursorShape.PointingHandCursor)
    btn_yes.clicked.connect(dlg.accept)
    btn_row.addWidget(btn_yes)
    inner.addLayout(btn_row)

    # Pull theme palette from parent panel if possible
    am = None
    p = parent
    while p is not None:
        if hasattr(p, "am"):
            am = p.am
            break
        p = p.parent() if hasattr(p, "parent") else None
    if am is not None:
        try:
            primary = am.get_accent_color()
            secondary = am.get_theme_color("secondary", "#888888")
            surface = am.get_theme_color("surface_override")
            text_override = am.get_theme_color("text_override")
            pal = derive_palette(primary, secondary, surface, text_override)
        except Exception:
            pal = derive_palette("#58a6ff", "#888888")
    else:
        pal = derive_palette("#58a6ff", "#888888")

    qss = f"""
        QFrame#confirm_bg {{
            background: {pal['bg_titlebar']};
            border: 1px solid {pal['border_subtle']};
            border-radius: 10px;
        }}
        QLabel#confirm_title {{
            color: {pal['text']};
            background: transparent;
        }}
        QLabel#confirm_msg {{
            color: {pal['text']};
            background: transparent;
            padding: 4px 0px;
        }}
        QPushButton#confirm_no {{
            background: {pal['btn_bg']};
            color: {pal['text']};
            border: 1px solid {pal['border_active']};
            border-radius: 6px;
            padding: 8px 18px;
        }}
        QPushButton#confirm_no:hover {{
            background: {pal['bg_medium']};
            border: 1px solid {pal['accent']};
        }}
        QPushButton#confirm_yes {{
            background: #d23030;
            color: #ffffff;
            border: 1px solid #d23030;
            border-radius: 6px;
            padding: 8px 18px;
        }}
        QPushButton#confirm_yes:hover {{
            background: #e85a5a;
            border: 1px solid #e85a5a;
        }}
    """
    dlg.setStyleSheet(qss)
    dlg.adjustSize()
    # Center over parent
    if parent is not None and hasattr(parent, "geometry"):
        pg = parent.geometry()
        dlg.move(pg.x() + (pg.width() - dlg.width()) // 2,
                 pg.y() + (pg.height() - dlg.height()) // 2)

    return dlg.exec() == QDialog.DialogCode.Accepted


# ────────────────────────────────────────────────────────────────────
# CycleFilterButton — click cycles through states; emits valueChanged
# Each state = (label, value, qss_state). value=None means "no filter".
# Visual styling driven by `filter_state` QSS attribute on the button.
# ────────────────────────────────────────────────────────────────────
class CycleFilterButton(QPushButton):
    valueChanged = pyqtSignal(object)  # emits new value (None | str)

    def __init__(self, states: list, parent=None):
        """states: list of (label, value, qss_state_name) tuples.
        First item should be the 'off' state (value=None)."""
        super().__init__(parent)
        self._states = states
        self._idx = 0
        self.setObjectName("npc_filter_btn")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(34)
        self.setFont(QFont(FONT_PRIMARY, 9, QFont.Weight.Bold))
        self.clicked.connect(self._cycle)
        self._refresh()

    def value(self):
        return self._states[self._idx][1]

    def _cycle(self):
        self._idx = (self._idx + 1) % len(self._states)
        self._refresh()
        self.valueChanged.emit(self.value())

    def _refresh(self):
        label, _value, qss_state = self._states[self._idx]
        self.setText(label)
        self.setProperty("filter_state", qss_state)
        # Re-evaluate QSS to apply the new filter_state styling
        self.style().unpolish(self)
        self.style().polish(self)


# ────────────────────────────────────────────────────────────────────
# CharacterAvatar — clickable rounded avatar widget
# Click opens the Polaroid view (which carries change/delete actions).
# ────────────────────────────────────────────────────────────────────
class CharacterAvatar(QWidget):
    avatar_clicked = pyqtSignal()         # emitted on left-click (open Polaroid)
    # NOTE: no hover_menu signals — using timer-based polling in the parent
    # tab instead. Popup-window menus steal mouse focus on show, which makes
    # avatar's enter/leave fire in a tight loop (the classic flicker pattern
    # documented in project_pyqt6_gotchas.md). Polling avoids it entirely.

    SIZE = 120

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(self.SIZE, self.SIZE)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._pixmap = None
        self._placeholder_text = "?"
        self._accent_color = "#58a6ff"
        self._bg_color = "#161b22"
        self._text_color = "#e6edf3"
        self._hover = False                 # cursor literally over the widget
        self._force_hover = False           # parent's hover-poll says "menu open"
        self._has_image = False
        self.setToolTip("hover: เลือกภาพ / Screenshot · คลิก: ดู Polaroid")

    def set_force_hover(self, on: bool):
        """Driven by the parent tab's hover-poll. While the popup menu is up,
        Qt fires a fake leaveEvent on us (popup steals mouse focus), which
        flickers the accent border off. The poll keeps `force_hover` True for
        as long as the cursor is on us OR on the menu, so the border stays
        steady the whole time the menu is interactable."""
        if self._force_hover != on:
            self._force_hover = on
            self.update()

    def set_image(self, image_path: Optional[str]):
        """Load image from disk; pass None / empty to show placeholder."""
        if image_path and os.path.exists(image_path):
            self._pixmap = QPixmap(image_path)
            self._has_image = True
        else:
            self._pixmap = None
            self._has_image = False
        self.update()

    def get_pixmap(self) -> Optional[QPixmap]:
        """Return current pixmap (used by Polaroid to render the enlarged view)."""
        return self._pixmap if (self._pixmap and not self._pixmap.isNull()) else None

    def has_image(self) -> bool:
        return self._has_image

    def set_placeholder(self, name: str):
        """Set placeholder text — typically first letter of character name."""
        self._placeholder_text = (name.strip()[:1] or "?").upper()
        self.update()

    def set_palette(self, palette: dict):
        """Apply theme colors."""
        self._accent_color = palette.get("accent", "#58a6ff")
        self._bg_color = palette.get("btn_bg", "#161b22")
        self._text_color = palette.get("text_dim", "#7d8590")
        self.update()

    def enterEvent(self, event):
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.avatar_clicked.emit()
            event.accept(); return
        super().mousePressEvent(event)

    def paintEvent(self, event):
        from PyQt6.QtGui import QPainter, QPainterPath, QPen
        from PyQt6.QtCore import QRectF
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        rect = QRectF(1, 1, self.SIZE - 2, self.SIZE - 2)

        # Circular clip
        path = QPainterPath()
        path.addEllipse(rect)
        p.setClipPath(path)

        if self._pixmap and not self._pixmap.isNull():
            scaled = self._pixmap.scaled(
                self.SIZE, self.SIZE,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            # Crop from TOP (so portrait photos keep the head/face visible),
            # center horizontally for landscape images.
            x = (self.SIZE - scaled.width()) // 2
            y = 0
            p.drawPixmap(x, y, scaled)
        else:
            # Placeholder: bg + initial letter (font scales with avatar size)
            p.fillPath(path, QColor(self._bg_color))
            p.setPen(QPen(QColor(self._text_color)))
            font = QFont(FONT_PRIMARY, max(20, int(self.SIZE * 0.35)), QFont.Weight.Bold)
            p.setFont(font)
            p.drawText(rect, int(Qt.AlignmentFlag.AlignCenter), self._placeholder_text)

        # Border — theme-aware. Treat "force_hover" (set by parent's poll
        # while the popup menu is open) the same as a real hover, so the
        # accent border doesn't strobe off when the popup grabs mouse focus.
        p.setClipping(False)
        if self._hover or self._force_hover:
            border_color = QColor(self._accent_color)
            border_width = 2.5
        else:
            from pyqt_ui.styles import _luminance
            bg_q = QColor(self._bg_color)
            try:
                if _luminance(self._bg_color) > 0.5:
                    border_color = bg_q.darker(125)
                else:
                    border_color = bg_q.lighter(160)
            except Exception:
                border_color = bg_q.lighter(140)
            border_width = 2
        p.setPen(QPen(border_color, border_width))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(rect)

        # Hover overlay — subtle accent tint (also applied while menu is up)
        if self._hover or self._force_hover:
            accent = QColor(self._accent_color)
            accent.setAlpha(45)
            p.setClipPath(path)
            p.fillRect(self.rect(), accent)
            p.setClipping(False)

        p.end()


# ────────────────────────────────────────────────────────────────────
# _AvatarHoverMenu — floating chip beside the avatar
# Shows on hover, offers 2 actions: choose-from-file / take-screenshot
# Theme-aware (accent border + bg_surface fill + text colors).
# Auto-hides via a grace timer when cursor leaves both menu AND avatar.
# ────────────────────────────────────────────────────────────────────
class _AvatarHoverMenu(QFrame):
    pick_image_requested = pyqtSignal()
    screenshot_requested = pyqtSignal()

    GRACE_MS = 220   # cursor-leave grace period before close (legacy — see _MainTab poll)
    BTN_W = 230      # widened so "ถ่ายภาพจอ (Screenshot)" fits without ellipsis
    BTN_H = 40

    def __init__(self, parent=None):
        # Popup window so it floats over everything but doesn't steal focus
        # from the underlying panel; hides on click-outside automatically.
        super().__init__(
            parent,
            Qt.WindowType.Popup
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.NoDropShadowWindowHint,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setObjectName("avatar_hover_menu")

        # Theme defaults — overridden by set_palette()
        self._accent = "#58a6ff"
        self._bg = "#161b22"
        self._bg2 = "#1c2128"
        self._text = "#e6edf3"
        self._text_dim = "#7d8590"

        # Auto-close grace timer (started on cursor leave)
        self._close_timer = QTimer(self)
        self._close_timer.setSingleShot(True)
        self._close_timer.setInterval(self.GRACE_MS)
        self._close_timer.timeout.connect(self._maybe_close)

        # Layout: vertical stack of 2 buttons w/ icons
        from PyQt6.QtWidgets import QVBoxLayout
        wrap = QVBoxLayout(self)
        wrap.setContentsMargins(8, 8, 8, 8)
        wrap.setSpacing(4)

        self.btn_pick = QPushButton("เลือกภาพจากไฟล์")
        self.btn_shot = QPushButton("ถ่ายภาพจอ (Screenshot)")
        for b in (self.btn_pick, self.btn_shot):
            b.setObjectName("avatar_menu_btn")
            b.setFixedSize(self.BTN_W, self.BTN_H)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setIconSize(QSize(18, 18))
            wrap.addWidget(b)

        # Icons (themed via load helpers if present)
        try:
            ico_pick = QIcon(resource_path("assets/images.png"))
            ico_shot = QIcon(resource_path("assets/camera.png"))
            self.btn_pick.setIcon(ico_pick)
            self.btn_shot.setIcon(ico_shot)
        except Exception as e:
            log.debug(f"[hover-menu] icon load skipped: {e}")

        # Wire button clicks → signals + close menu
        self.btn_pick.clicked.connect(self._on_pick)
        self.btn_shot.clicked.connect(self._on_shot)

        self._apply_qss()

    def set_palette(self, accent: str, bg: str, bg2: str, text: str, text_dim: str):
        self._accent = accent
        self._bg = bg
        self._bg2 = bg2
        self._text = text
        self._text_dim = text_dim
        self._apply_qss()

    def _apply_qss(self):
        # Outer frame — bright accent border (matches the avatar hover ring)
        # so the menu feels visually tethered to the avatar instead of floating
        # in space. 2px is thick enough to read on dark themes; on light
        # themes the accent itself provides the contrast.
        self.setStyleSheet(f"""
            QFrame#avatar_hover_menu {{
                background: {self._bg2};
                border: 2px solid {self._accent};
                border-radius: 12px;
            }}
            QPushButton#avatar_menu_btn {{
                background: {self._bg};
                color: {self._text};
                border: 1px solid transparent;
                border-radius: 7px;
                padding-left: 14px;
                text-align: left;
                font-family: "{FONT_PRIMARY}";
                font-size: 11pt;
            }}
            QPushButton#avatar_menu_btn:hover {{
                background: {self._accent};
                color: #ffffff;
                border-color: {self._accent};
            }}
            QPushButton#avatar_menu_btn:pressed {{
                background: {self._accent};
                color: #ffffff;
            }}
        """)

    def show_beside(self, anchor_widget: QWidget):
        """Position to the RIGHT of anchor_widget (or LEFT if no room)."""
        if anchor_widget is None:
            return
        try:
            anchor_global = anchor_widget.mapToGlobal(QPoint(0, 0))
            ax = anchor_global.x()
            ay = anchor_global.y()
            aw = anchor_widget.width()
            ah = anchor_widget.height()
            self.adjustSize()
            mw = self.width()
            mh = self.height()

            # Prefer right side; fall back to left if it would clip the screen
            screen = QApplication.primaryScreen()
            screen_geo = screen.availableGeometry() if screen else None
            x_right = ax + aw + 12
            x_left = ax - mw - 12
            if screen_geo and (x_right + mw > screen_geo.right()):
                x = max(screen_geo.left(), x_left)
            else:
                x = x_right
            # Vertically center on the avatar
            y = ay + (ah - mh) // 2
            if screen_geo:
                y = max(screen_geo.top(), min(y, screen_geo.bottom() - mh))
            self.move(x, y)
            self.show()
            self.raise_()
        except Exception as e:
            log.warning(f"[hover-menu] show_beside failed: {e}")

    def restart_close_timer(self):
        """Start (or restart) the grace timer — call this when cursor leaves
        the avatar OR the menu. If cursor enters the OTHER one within GRACE_MS,
        cancel via cancel_close_timer()."""
        self._close_timer.start()

    def cancel_close_timer(self):
        """Cancel a pending close — call when cursor enters menu or avatar."""
        if self._close_timer.isActive():
            self._close_timer.stop()

    def _maybe_close(self):
        """Close only if cursor is OUTSIDE both this menu and (we hope) the
        anchor avatar. The owner avatar reset-checks itself via leaveEvent."""
        try:
            cursor = QCursor.pos()
            local = self.mapFromGlobal(cursor)
            if not self.rect().contains(local):
                self.close()
        except Exception:
            self.close()

    # NOTE: enterEvent/leaveEvent removed. Visibility is owned by the parent
    # tab's QTimer-based hover poll (see _MainTab._poll_avatar_hover). Letting
    # the menu also start its own grace timer would race against the poll
    # — close timer fires while poll still says cursor-in-menu → menu vanishes
    # under the cursor mid-interaction.

    def _on_pick(self):
        self.close()
        self.pick_image_requested.emit()

    def _on_shot(self):
        self.close()
        self.screenshot_requested.emit()


# ────────────────────────────────────────────────────────────────────
# PolaroidOverlay — enlarged photo view triggered by avatar click.
# White card, image area + handwritten name strip below, drop shadow.
# Hover reveals: 📷 change-image (top-right), 🗑 delete (bottom-right, subtle).
# Dismissed by clicking the dimmed backdrop, pressing ESC, or clicking the
# polaroid card itself (when the cursor is not on a button).
# ────────────────────────────────────────────────────────────────────
class _PolaroidCard(QFrame):
    """The polaroid paper itself — paints the white card body + cropped image.
    Lives as the (only) shadow-effected widget; buttons are SIBLINGS of this so
    they don't get rasterized by the parent's shadow pass (which would leak a
    square ghost outline behind their rounded corners — QTBUG-56081)."""

    IMAGE_AREA = 360  # square image region inside the card

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self._pixmap: Optional[QPixmap] = None

    def set_pixmap(self, pixmap: Optional[QPixmap]):
        self._pixmap = pixmap
        self.update()

    def paintEvent(self, event):
        from PyQt6.QtGui import QPainter, QPen
        from PyQt6.QtCore import QRectF
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        w, h = self.width(), self.height()

        # Polaroid paper (off-white, slight rounding)
        p.setBrush(QColor("#fafaf6"))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(0, 0, w, h), 4, 4)

        # Image region — uniform margin all around (top + sides equal)
        margin = (w - self.IMAGE_AREA) // 2
        img_rect = QRectF(margin, margin, self.IMAGE_AREA, self.IMAGE_AREA)
        p.setBrush(QColor("#e8e8e2"))  # placeholder bg
        p.drawRect(img_rect)

        if self._pixmap and not self._pixmap.isNull():
            # DPR-aware rendering — scale at physical pixels, set DPR after, then
            # draw at logical size. Critical: NEVER upscale beyond source — if the
            # saved image is e.g. 128×128 (legacy default), upscaling to 360 logical
            # px just produces blurry pixels. Cap target_px at min(IMAGE_AREA*dpr,
            # source_dim) so small sources display at their native resolution
            # centered with letterbox.
            dpr = self.devicePixelRatioF() or 1.0
            src_w, src_h = self._pixmap.width(), self._pixmap.height()
            src_min = min(src_w, src_h)
            target_logical = min(self.IMAGE_AREA, src_min)  # don't upscale
            target_px = int(target_logical * dpr)
            scaled = self._pixmap.scaled(
                target_px, target_px,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            sx = max(0, (scaled.width() - target_px) // 2)
            sy = 0  # top-crop (portrait → keep face/head)
            cropped = scaled.copy(sx, sy, target_px, target_px)
            cropped.setDevicePixelRatio(dpr)
            # Center the (possibly-letterboxed) image inside img_rect
            offset = (self.IMAGE_AREA - target_logical) // 2
            p.drawPixmap(int(img_rect.x() + offset),
                         int(img_rect.y() + offset),
                         cropped)
        else:
            p.setPen(QPen(QColor("#9c9c93")))
            p.setFont(QFont(FONT_PRIMARY, 11))
            p.drawText(img_rect, int(Qt.AlignmentFlag.AlignCenter), "(ไม่มีภาพ)")

        p.end()


class PolaroidOverlay(QWidget):
    change_requested = pyqtSignal()
    delete_requested = pyqtSignal()

    CARD_W = 400
    CARD_H = 510
    IMAGE_AREA = 360  # square image region inside the card — bumped for detail
    STRIP_H = 110     # bottom white strip with handwritten name (taller to fit Caveat 38pt)

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setObjectName("polaroid_overlay")
        self._pixmap: Optional[QPixmap] = None
        self._name = ""
        self._accent_color = "#58a6ff"
        self._has_image = False
        self.hide()

        # ── Widget tree (proven pattern from BoxShadow-in-PyQt-PySide repo + QTBUG-56081) ──
        # The shadow effect rasterizes its widget AND ALL descendants together, so any
        # button that's a child of the shadowed widget gets its full bounding rect baked
        # into the shadow pass — which leaks a square ghost outline behind the rounded
        # button corners. Fix: shadow ONLY on `card`. Buttons are siblings of `card`
        # (children of overlay), positioned over the card with move() in resizeEvent.
        #
        #   PolaroidOverlay  ─ no shadow
        #     ├── card (QFrame, has shadow + paints white paper + image area)
        #     │     └── name_label (Caveat handwriting)
        #     ├── btn_change   ─── siblings of card, positioned to overlap visually
        #     └── btn_delete   ───
        self.card = _PolaroidCard(self)
        self.card.setObjectName("polaroid_card")
        self.card.setFixedSize(self.CARD_W, self.CARD_H)
        # Hover detection uses a polling timer (started in show_for) instead of
        # Enter/Leave events. Reason: buttons are siblings of the card painted
        # ON TOP, so cursor passing onto a button generates Card-Leave which
        # would hide the button → cursor falls back onto card → Card-Enter →
        # show button → loop = flicker. Geometry-based polling avoids that
        # entirely (we just check whether the cursor is inside card OR button
        # rects each tick).

        shadow = QGraphicsDropShadowEffect(self.card)
        shadow.setBlurRadius(48)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 8)
        self.card.setGraphicsEffect(shadow)

        # Handwritten name label — INSIDE the card so it's clipped to the card's surface.
        # We pre-render the name as a QPixmap via QPainter (in update_name()) and use
        # setPixmap on the QLabel — this BYPASSES the panel's QSS cascade entirely
        # (QSS only affects font of QLabel.setText, not pixmap content). The font
        # is resolved by QPainter directly via QFontDatabase, which is reliable.
        # Diagnostic: if QPainter rendering of Pacifico/Caveat is also wrong, the
        # issue is at QFontDatabase / addApplicationFont level.
        self.name_label = QLabel("", self.card)
        self.name_label.setObjectName("polaroid_name")
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label.setStyleSheet("background: transparent;")
        # Ensure handwriting fonts are registered in Qt's QFontDatabase.
        # Important: QtFontManager (which would do this at app init) is only
        # instantiated lazily when the Font Settings panel opens — so without
        # this explicit registration, QFont("Pacifico") silently falls back to
        # Segoe UI. Registration is idempotent — calling addApplicationFont on
        # the same file twice is harmless.
        from PyQt6.QtGui import QFontDatabase as _QFDB
        _existing = set(_QFDB.families())
        _fonts_dir = resource_path("fonts")
        for _fname in ("Pacifico.ttf", "Caveat.ttf"):
            _fpath = os.path.join(_fonts_dir, _fname)
            if os.path.exists(_fpath):
                _fid = _QFDB.addApplicationFont(_fpath)
                if _fid >= 0:
                    _fams = _QFDB.applicationFontFamilies(_fid)
                    log.info(f"[Polaroid] addApplicationFont {_fname} -> {_fams}")
        # Pick first available script-style font
        _all_fams = _QFDB.families()
        self._script_family = next(
            (f for f in _all_fams if f.lower().startswith(("pacifico", "caveat", "dancing", "sacramento"))),
            FONT_PRIMARY,
        )
        log.info(f"[Polaroid] script font resolved to: {self._script_family!r}")

        # ── Buttons: children of OVERLAY, not card. No shadow effect on them. ──
        self.btn_change = QPushButton("เปลี่ยนภาพ", self)
        self.btn_change.setObjectName("polaroid_change")
        self.btn_change.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_change.setFont(QFont(FONT_PRIMARY, 9, QFont.Weight.Bold))
        self.btn_change.setFixedHeight(32)
        # Use the same procedural avatar-badge icon as the MAIN list rows
        # (themed accent bg + white photo glyph) — picks up theme + scales cleanly.
        try:
            parent_tab = parent
            accent = parent_tab.panel.am.get_accent_color()
        except Exception:
            accent = "#58a6ff"
        self.btn_change.setIcon(_make_avatar_badge_icon(accent, size=20))
        self.btn_change.setIconSize(QSize(20, 20))
        self.btn_change.setStyleSheet(
            "QPushButton#polaroid_change {"
            "  background-color: rgba(20,20,20,225); color: #ffffff;"
            "  border: 0; border-radius: 16px;"
            "  padding: 6px 14px 6px 12px; outline: none;"
            "}"
            "QPushButton#polaroid_change:hover { background-color: rgba(45,45,45,240); }"
        )
        self.btn_change.adjustSize()
        self.btn_change.clicked.connect(self.change_requested.emit)
        self.btn_change.hide()

        self.btn_delete = QPushButton("✕", self)
        self.btn_delete.setObjectName("polaroid_delete")
        self.btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_delete.setFixedSize(30, 30)
        self.btn_delete.setToolTip("ลบรูปภาพ")
        self.btn_delete.setStyleSheet(
            "QPushButton#polaroid_delete {"
            "  background-color: rgba(40,40,40,110); color: rgba(255,255,255,160);"
            "  border: 0; border-radius: 15px;"
            "  font-size: 13pt; font-weight: bold; outline: none;"
            "}"
            "QPushButton#polaroid_delete:hover {"
            "  background-color: rgba(220,55,55,235); color: #ffffff;"
            "}"
        )
        self.btn_delete.clicked.connect(self.delete_requested.emit)
        self.btn_delete.hide()

        # ESC key handling
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # Hover-detection timer (runs only while the overlay is visible)
        self._hover_timer = QTimer(self)
        self._hover_timer.setInterval(60)  # 60ms — smooth, low CPU
        self._hover_timer.timeout.connect(self._update_hover_state)

    def show_for(self, image_path: Optional[str], name: str, has_image: bool):
        """Show the overlay. ``image_path`` is loaded fresh from disk (full
        resolution source — no caching from the small avatar widget)."""
        # Load full-resolution pixmap directly from disk
        if image_path and os.path.exists(image_path):
            self._pixmap = QPixmap(image_path)
        else:
            self._pixmap = None
        self._name = name or ""
        self._has_image = has_image
        # Match parent size first
        if self.parent():
            self.setGeometry(0, 0, self.parent().width(), self.parent().height())
        # Position the card (centered)
        cx = (self.width() - self.CARD_W) // 2
        cy = (self.height() - self.CARD_H) // 2
        self.card.move(cx, cy)
        self.card.set_pixmap(self._pixmap)
        # Name label inside the card's bottom strip (relative to card, not overlay)
        img_margin = (self.CARD_W - self.IMAGE_AREA) // 2
        strip_y = img_margin + self.IMAGE_AREA + 4
        self.name_label.setGeometry(0, strip_y, self.CARD_W, self.STRIP_H - 4)
        self._render_name_pixmap(self._name)
        # Position action buttons (children of self → overlay coords)
        self._reposition_card_buttons()
        # Buttons hidden initially — shown when cursor enters the card
        self.btn_change.hide()
        self.btn_delete.hide()
        self.show()
        self.raise_()
        self.setFocus()
        self.update()
        self._hover_timer.start()

    def _render_name_pixmap(self, name: str):
        """Pre-render the name label as a QPixmap via QPainter — bypasses the
        panel's QSS cascade which silently overrides setFont() for QLabel.
        This is the bulletproof font-rendering pattern (QPainter uses QFont
        directly, not Qt's stylesheet font resolution).

        Auto-shrinks the font from MAX_PT down to MIN_PT until the rendered
        text fits within the strip width (long names like 'Vow of Resolve
        Gulool Ja Ja' would otherwise overflow the polaroid card)."""
        from PyQt6.QtGui import QPainter, QFontMetrics
        from PyQt6.QtCore import QRect
        if not name:
            self.name_label.clear()
            return
        w = self.CARD_W
        h = self.STRIP_H - 4
        dpr = self.devicePixelRatioF() or 1.0
        pm = QPixmap(int(w * dpr), int(h * dpr))
        pm.setDevicePixelRatio(dpr)
        pm.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pm)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        # Shrink-to-fit: try sizes from 38 → 16, pick the largest that fits
        # within w - 24px (12px horizontal padding on each side)
        font = QFont()
        font.setFamilies([self._script_family])
        font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
        max_w = w - 24
        chosen_pt = 16
        for pt in (38, 34, 30, 26, 22, 18, 16):
            font.setPointSize(pt)
            if QFontMetrics(font).horizontalAdvance(name) <= max_w:
                chosen_pt = pt
                break
        font.setPointSize(chosen_pt)
        painter.setFont(font)
        painter.setPen(QColor("#1f1f1f"))
        painter.drawText(QRect(0, 0, w, h),
                         int(Qt.AlignmentFlag.AlignCenter), name)
        painter.end()
        self.name_label.setPixmap(pm)

    def _reposition_card_buttons(self):
        """Buttons are children of the overlay, so positions are in overlay coords.
        We anchor them relative to the card's current top-left corner."""
        cx = self.card.x()
        cy = self.card.y()
        cb = self.btn_change
        cb.move(cx + self.CARD_W - cb.width() - 10, cy + 10)
        db = self.btn_delete
        db.move(cx + self.CARD_W - db.width() - 10,
                cy + self.CARD_H - db.height() - 10)

    def set_palette(self, palette: dict):
        self._accent_color = palette.get("accent", "#58a6ff")
        self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Keep card + buttons positioned correctly when parent resizes
        if self.card:
            cx = (self.width() - self.CARD_W) // 2
            cy = (self.height() - self.CARD_H) // 2
            self.card.move(cx, cy)
            self._reposition_card_buttons()

    def _update_hover_state(self):
        """Poll cursor position vs. card / button rects (in overlay coords).
        Show action buttons when cursor is anywhere inside the card OR an
        already-visible button — that prevents the flicker that Enter/Leave
        gives us when the cursor crosses between card surface and overlaid
        buttons (which are siblings of the card, not children).

        Wrapped in try/except: this runs every 60ms and a single uncaught
        exception (e.g. mid-destroy widget access) could silently kill the
        QTimer or, worse, propagate up Qt's C++ stack and crash the app."""
        try:
            from PyQt6.QtGui import QCursor
            if not self.isVisible():
                self._hover_timer.stop()
                return
            cur = self.mapFromGlobal(QCursor.pos())
            in_card = self.card.geometry().contains(cur)
            in_btn_change = (self.btn_change.isVisible()
                             and self.btn_change.geometry().contains(cur))
            in_btn_delete = (self.btn_delete.isVisible()
                             and self.btn_delete.geometry().contains(cur))
            should_show = in_card or in_btn_change or in_btn_delete
            if should_show and not self.btn_change.isVisible():
                self.btn_change.show()
                self.btn_change.raise_()
                if self._has_image:
                    self.btn_delete.show()
                    self.btn_delete.raise_()
            elif not should_show and self.btn_change.isVisible():
                self.btn_change.hide()
                self.btn_delete.hide()
        except Exception as e:
            log.warning(f"[Polaroid] hover poll error (non-fatal): {e}")

    def showEvent(self, event):
        """Install app-level event filter to dismiss polaroid on:
        (a) any window resize — backdrop wouldn't follow cleanly otherwise, and
        (b) any mouse press outside the overlay's screen rect — covers clicks
        on the NPC Manager title bar / resize grip / outside-window areas."""
        super().showEvent(event)
        try:
            from PyQt6.QtWidgets import QApplication
            QApplication.instance().installEventFilter(self)
        except Exception as e:
            log.warning(f"[Polaroid] failed to install event filter: {e}")

    def hideEvent(self, event):
        """Stop the hover timer + remove the global event filter when hidden."""
        try:
            self._hover_timer.stop()
        except Exception:
            pass
        try:
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance()
            if app is not None:
                app.removeEventFilter(self)
        except Exception as e:
            log.warning(f"[Polaroid] failed to remove event filter: {e}")
        super().hideEvent(event)

    def eventFilter(self, obj, event):
        """Global filter (active only while overlay is visible). Closes polaroid
        on any Resize on the top-level window, OR any MouseButtonPress whose
        global position falls outside the overlay's on-screen rect.

        IMPORTANT: this filter receives EVERY event in the application while
        installed (mouse, key, paint, focus, custom posted events from other
        threads e.g. the global keyboard hook). Any uncaught exception inside
        eventFilter propagates back to Qt's C++ event dispatcher, which can
        terminate the app silently. We wrap the whole body and ALWAYS return a
        bool so Qt's contract is honored even on error.
        """
        try:
            from PyQt6.QtCore import QEvent, QRect, QPoint
            if not self.isVisible():
                return super().eventFilter(obj, event)
            et = event.type()
            if et == QEvent.Type.Resize:
                # Top-level window resized → backdrop wouldn't reflow → dismiss
                if obj is self.window():
                    self.hide()
                    return False
            elif et == QEvent.Type.MouseButtonPress:
                # Click outside the overlay's screen rect → dismiss
                try:
                    gp = event.globalPosition().toPoint()
                except AttributeError:
                    gp = event.globalPos()
                overlay_topleft = self.mapToGlobal(QPoint(0, 0))
                overlay_rect = QRect(overlay_topleft, self.size())
                if not overlay_rect.contains(gp):
                    self.hide()
                    # Don't consume — let the click reach its target
                    return False
            return super().eventFilter(obj, event)
        except Exception as e:
            # Never propagate — Qt's C++ side cannot handle Python exceptions
            # from eventFilter and may abort the process. Log and swallow.
            try:
                log.warning(f"[Polaroid] eventFilter error (non-fatal): {e}")
            except Exception:
                pass
            return False

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
            event.accept()
            return
        super().keyPressEvent(event)

    def mousePressEvent(self, event):
        # Click anywhere in the overlay (backdrop or card body — but not on buttons)
        # dismisses it. Buttons consume their own clicks first.
        if event.button() == Qt.MouseButton.LeftButton:
            self.hide()
            event.accept()
            return
        super().mousePressEvent(event)

    def paintEvent(self, event):
        from PyQt6.QtGui import QPainter
        p = QPainter(self)
        # Backdrop only — the card paints itself (its own widget paintEvent)
        # and the name renders via QLabel child of the card.
        p.fillRect(self.rect(), QColor(0, 0, 0, 150))
        p.end()


# ────────────────────────────────────────────────────────────────────
# ResizeGrip — corner widget that resizes parent on drag (uses resize.png)
# ────────────────────────────────────────────────────────────────────
class ResizeGrip(QWidget):
    """Custom bottom-right resize grip styled with assets/resize.png.
    Drag to resize the top-level window. Respects window's minimum size."""
    SIZE = 18

    def __init__(self, target_window: QWidget, parent=None):
        super().__init__(parent)
        self.target = target_window
        self.setFixedSize(self.SIZE, self.SIZE)
        self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        self._dragging = False
        self._start_pos = QPoint()
        self._start_size = QSize()
        self._pixmap = None
        # Load resize icon (auto-invert on light theme handled by parent panel)
        try:
            icon_path = resource_path("assets/resize.png")
            if os.path.exists(icon_path):
                self._pixmap = QPixmap(icon_path).scaled(
                    self.SIZE, self.SIZE,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
        except Exception:
            self._pixmap = None

    def set_invert(self, invert: bool):
        """Invert the icon for light themes (white→dark)."""
        try:
            icon_path = resource_path("assets/resize.png")
            if not os.path.exists(icon_path):
                return
            pix = QPixmap(icon_path).scaled(
                self.SIZE, self.SIZE,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            if invert:
                pix = invert_pixmap(pix)
            self._pixmap = pix
            self.update()
        except Exception:
            pass

    def paintEvent(self, event):
        from PyQt6.QtGui import QPainter
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        if self._pixmap and not self._pixmap.isNull():
            p.drawPixmap(0, 0, self._pixmap)
        else:
            # Fallback: draw 3 diagonal lines
            from PyQt6.QtGui import QPen
            p.setPen(QPen(QColor(180, 180, 180, 160), 1.4))
            for i in range(3):
                off = 4 + i * 4
                p.drawLine(self.SIZE - off, self.SIZE - 2,
                           self.SIZE - 2, self.SIZE - off)
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
            new_w = max(self.target.minimumWidth(), self._start_size.width() + delta.x())
            new_h = max(self.target.minimumHeight(), self._start_size.height() + delta.y())
            self.target.resize(new_w, new_h)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._dragging = False
        event.accept()


# ────────────────────────────────────────────────────────────────────
# Vertical resize grip for QTextEdit — small handle parented to a
# QTextEdit, drag downward to expand the textarea height. Repositions
# itself whenever the textarea resizes.
# ────────────────────────────────────────────────────────────────────
class _TextEditResizeGrip(QWidget):
    SIZE = 14

    def __init__(self, target_textedit: QWidget, min_height: int, max_height: int):
        super().__init__(target_textedit)
        self.target = target_textedit
        self.min_h = min_height
        self.max_h = max_height
        self._dragging = False
        self._start_y = 0
        self._start_h = 0
        self.setFixedSize(self.SIZE, self.SIZE)
        self.setCursor(Qt.CursorShape.SizeVerCursor)
        self.setToolTip("ลากเพื่อขยายช่องบุคลิก")
        # Hook target's resize so we follow its bottom-right corner
        orig_resize = target_textedit.resizeEvent
        grip = self
        def _patched(ev):
            orig_resize(ev)
            grip._reposition()
        target_textedit.resizeEvent = _patched
        QTimer.singleShot(0, self._reposition)
        self.show()
        self.raise_()

    def _reposition(self):
        te = self.target
        margin = 3
        self.move(te.width() - self.width() - margin,
                  te.height() - self.height() - margin)
        self.raise_()

    def paintEvent(self, event):
        from PyQt6.QtGui import QPainter, QPolygon
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Filled triangle hugging the bottom-right corner — the universal
        # "drag to resize" affordance.
        s = self.SIZE
        margin = 2
        tri = QPolygon([
            QPoint(s - margin, margin),       # top-right
            QPoint(s - margin, s - margin),   # bottom-right
            QPoint(margin, s - margin),       # bottom-left
        ])
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(160, 160, 160, 210))
        p.drawPolygon(tri)
        p.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._start_y = event.globalPosition().toPoint().y()
            self._start_h = self.target.height()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._dragging:
            delta = event.globalPosition().toPoint().y() - self._start_y
            new_h = max(self.min_h, min(self.max_h, self._start_h + delta))
            old_h = self.target.height()
            h_change = new_h - old_h
            if h_change == 0:
                event.accept()
                return
            # Grow/shrink the top-level window by the same delta so the layout
            # has room for the new textarea size — without this, setFixedHeight
            # makes the textarea overflow its layout slot and visually cover
            # the widgets below.
            window = self.target.window()
            if window is not None:
                cur_w = window.width()
                cur_h = window.height()
                min_h = window.minimumHeight() or 0
                max_h = window.maximumHeight() or 16777215
                new_win_h = max(min_h, min(max_h, cur_h + h_change))
                window.resize(cur_w, new_win_h)
            self.target.setFixedHeight(new_h)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._dragging = False
        event.accept()


# ────────────────────────────────────────────────────────────────────
# Tab descriptors — registry of all tabs (Phase 1 only enables Main)
# ────────────────────────────────────────────────────────────────────
TABS = [
    # (id, button_label, section_title, body_description)
    ("main",  "MAIN",     "ตัวละครหลัก",   "เพศ • น้ำเสียง • ความสัมพันธ์"),
    ("npcs",  "NPCS",     "NPC รอง",       "ชื่อ • บทบาท • คำอธิบาย"),
    ("lore",  "LORE",     "คำศัพท์ในโลก",  "ชื่อเฉพาะ • องค์กร • สถานที่"),
    ("fixes", "WORD FIX", "ปิดใช้งานแล้ว", ""),
]


# ────────────────────────────────────────────────────────────────────
# Main panel
# ────────────────────────────────────────────────────────────────────
class NPCManagerPanel(QWidget):
    """Modern PyQt6 NPC Manager — replaces legacy Tkinter NPCManagerCard."""

    on_data_saved = pyqtSignal()  # Fires after successful save (so MBB can reload translator)

    def __init__(self, appearance_manager, on_close_callback=None,
                 on_save_callback=None):
        super().__init__()
        self.am = appearance_manager
        self.on_close_callback = on_close_callback
        self.on_save_callback = on_save_callback
        self.old_pos = QPoint()

        # Data layer
        self.dm = NPCDataManager()

        # State
        self._current_tab = "main"
        self._selected_index = -1   # -1 = no selection (add mode)
        # Default = pinned (window flags in _init_window also set WindowStaysOnTopHint).
        # Both must agree at startup, otherwise the user has to click the pin twice
        # before the toggle visibly works.
        self._is_pinned = True
        self._has_backed_up = False  # backup once per session (avoids backup spam)

        # Widget refs
        self.bg = None
        self.shadow = None
        self._tab_buttons = {}
        self._tab_pages = {}
        self._stack = None
        self._search_input = None
        self._footer_label = None
        self._tab_description_label = None

        self._init_window()
        self._build_ui()
        self._apply_theme()
        # Default: show Main tab
        self._switch_tab("main")
        # Initial status strip + 60s auto-refresh so 'X นาทีที่แล้ว' stays current
        # while the panel sits open (cheap — one os.stat + 3 len() calls).
        self._update_db_status()
        self._db_refresh_timer = QTimer(self)
        self._db_refresh_timer.setInterval(60_000)
        self._db_refresh_timer.timeout.connect(self._update_db_status)
        self._db_refresh_timer.start()

    # ─── Window Setup ───
    def _init_window(self):
        self.setWindowTitle("NPC Manager")
        # ── Safety minimum size — enforced by ResizeGrip + Qt's resize machinery ──
        # Min calculated from content:
        #   width:  list_min(380) + spacing(14) + details_min(380) + outer(46) ≈ 820
        #   height: non-body(260) + details_min_with_avatar(630) + tab_margins(14) ≈ 904
        # Keep slightly above absolute min so resize doesn't pixel-clip text.
        self.setMinimumSize(820, 880)
        self.resize(WIDTH, HEIGHT)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    # ─── UI Build ───
    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)

        self.bg = QWidget()
        self.bg.setObjectName("npc_bg")
        outer.addWidget(self.bg)

        self.shadow = QGraphicsDropShadowEffect()
        self.shadow.setBlurRadius(28)
        self.shadow.setColor(QColor(0, 0, 0, 160))
        self.shadow.setOffset(0, 4)
        self.bg.setGraphicsEffect(self.shadow)

        main = QVBoxLayout(self.bg)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        # Header
        main.addWidget(self._build_header())
        main.addWidget(self._make_divider())
        # Tab bar
        main.addWidget(self._build_tab_bar())
        main.addWidget(self._make_divider())
        # Search bar
        main.addWidget(self._build_search_bar())
        # Body (stack of tab pages) — all 5 tabs implemented
        self._stack = QStackedWidget()
        self._stack.setObjectName("npc_stack")
        for tab_id, _, _, _ in TABS:
            if tab_id == "main":
                page = MainCharactersTab(self)
            elif tab_id == "npcs":
                page = NPCsTab(self)
            elif tab_id == "lore":
                page = LoreTab(self)
            elif tab_id == "fixes":
                page = WordFixesTab(self)
            else:
                page = _PlaceholderTab(tab_id)
            self._tab_pages[tab_id] = page
            self._stack.addWidget(page)
        main.addWidget(self._stack, stretch=1)
        # Footer
        main.addWidget(self._make_divider())
        main.addWidget(self._build_footer())

        # Resize grip — bottom-right corner overlay (positioned in resizeEvent)
        self._resize_grip = ResizeGrip(self, parent=self.bg)
        self._resize_grip.raise_()

    def _build_header(self) -> QWidget:
        header = QWidget()
        header.setObjectName("npc_header")
        header.setFixedHeight(54)
        h = QHBoxLayout(header)
        h.setContentsMargins(20, 10, 14, 10)
        h.setSpacing(12)

        title = QLabel("NPC Manager")
        title.setObjectName("npc_title")
        title.setFont(QFont(FONT_PRIMARY, 14, QFont.Weight.Bold))
        h.addWidget(title)
        # Dynamic database status — counts per section + file mtime.
        # Refreshed on init, autosave, manual reload, and every 60s
        # (so 'X นาทีที่แล้ว' stays accurate while panel is open).
        self._db_status_label = QLabel("")
        self._db_status_label.setObjectName("npc_subtitle")
        self._db_status_label.setFont(QFont(FONT_PRIMARY, 10))
        h.addWidget(self._db_status_label)
        h.addStretch()

        # Merge button — pull entries from another npc.json (a friend's file,
        # an older backup, etc.) into the current database. Opens a diff
        # modal so the user picks exactly which rows to import.
        self._btn_merge = QPushButton("Merge")
        self._btn_merge.setObjectName("npc_merge_btn")
        self._btn_merge.setFixedSize(64, 28)
        self._btn_merge.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_merge.setToolTip(
            "Merge ข้อมูลจากไฟล์ npc.json อื่น\n"
            "(เปรียบเทียบ + เลือกข้อมูลที่จะรวมเข้าฐานปัจจุบัน)"
        )
        self._btn_merge.setFont(QFont(FONT_PRIMARY, 9, QFont.Weight.Bold))
        self._btn_merge.clicked.connect(self._on_merge_request)
        h.addWidget(self._btn_merge)

        # Manual reload button — re-reads npc.json from disk for the
        # cases the auto-save pipeline can't cover: external edits,
        # merging another player's file, dev-mode tweaks.
        # Icon comes from assets/swap.png (auto-tinted dark on light themes
        # via _update_reload_icon — same pattern as the pin button).
        self._btn_reload = QPushButton()
        self._btn_reload.setObjectName("npc_header_btn")
        self._btn_reload.setFixedSize(28, 28)
        self._btn_reload.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_reload.setToolTip(
            "โหลด npc.json ใหม่จากดิสก์\n"
            "(ใช้กรณีแก้ไฟล์จากภายนอก หรือ merge ข้อมูลจากแหล่งอื่น)"
        )
        self._btn_reload.clicked.connect(self._on_reload)
        self._update_reload_icon()
        h.addWidget(self._btn_reload)

        self._btn_pin = QPushButton()
        self._btn_pin.setObjectName("npc_header_btn")
        self._btn_pin.setFixedSize(28, 28)
        self._btn_pin.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_pin.setToolTip("Always on top")
        self._btn_pin.clicked.connect(self._on_pin_click)
        self._update_pin_icon()  # uses same pin.png/unpin.png as MBB main window
        h.addWidget(self._btn_pin)

        btn_close = QPushButton("✕")
        btn_close.setObjectName("npc_close")
        btn_close.setFixedSize(28, 28)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.clicked.connect(self.close)
        h.addWidget(btn_close)
        return header

    def _build_tab_bar(self) -> QWidget:
        wrap = QWidget()
        wrap.setObjectName("npc_tabbar")
        wrap.setFixedHeight(58)
        h = QHBoxLayout(wrap)
        h.setContentsMargins(20, 10, 20, 10)
        h.setSpacing(8)

        for tab_id, label, _, _ in TABS:
            btn = QPushButton(label)
            btn.setObjectName("npc_tab_btn")
            btn.setProperty("active", "false")
            btn.setFont(QFont(FONT_PRIMARY, 11, QFont.Weight.Bold))
            btn.setMinimumHeight(36)
            # WORD FIX hidden — text hook input doesn't have OCR character
            # errors that word_fixes was built to correct. Button created but
            # NOT added to layout, so the WordFixesTab page (and class) stays
            # intact for backwards-compat / future re-enable.
            if tab_id == "fixes":
                btn.setVisible(False)
                self._tab_buttons[tab_id] = btn
                continue
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _checked, tid=tab_id: self._switch_tab(tid))
            self._tab_buttons[tab_id] = btn
            h.addWidget(btn)
        # Two-tone tab description, CENTERED in the remaining space:
        #   stretch | [TITLE bold large]  ·  [body thin smaller] | stretch
        h.addStretch(1)
        self._tab_title_label = QLabel("")
        self._tab_title_label.setObjectName("npc_tab_title")
        self._tab_title_label.setFont(QFont(FONT_PRIMARY, 13, QFont.Weight.Bold))
        self._tab_title_label.setAlignment(
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
        )
        h.addWidget(self._tab_title_label)
        h.addSpacing(4)
        self._tab_description_label = QLabel("")
        self._tab_description_label.setObjectName("npc_tab_desc")
        self._tab_description_label.setFont(QFont(FONT_PRIMARY, 11, QFont.Weight.Light))
        self._tab_description_label.setAlignment(
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
        )
        h.addWidget(self._tab_description_label)
        h.addStretch(1)
        return wrap

    def _build_search_bar(self) -> QWidget:
        # SAVE button removed 2026-04-25: panel uses auto-save now (every CRUD action persists).
        wrap = QWidget()
        wrap.setObjectName("npc_searchbar")
        wrap.setFixedHeight(52)
        h = QHBoxLayout(wrap)
        h.setContentsMargins(20, 10, 20, 6)
        h.setSpacing(10)

        icon = QLabel("🔍")
        icon.setStyleSheet("background: transparent; font-size: 14pt;")
        h.addWidget(icon)

        self._search_input = QLineEdit()
        self._search_input.setObjectName("npc_search")
        self._search_input.setPlaceholderText("ค้นหา (ชื่อ / role / description)...")
        self._search_input.setFont(QFont(FONT_PRIMARY, 11))
        self._search_input.setMinimumHeight(34)
        self._search_input.setMaximumWidth(460)  # 20% wider than previous 380
        self._search_input.textChanged.connect(self._on_search_changed)
        h.addWidget(self._search_input)

        # Custom clear button — child of the QLineEdit, positioned on the inside
        # right edge. Bigger + easier to click than Qt's built-in clear button.
        # Hover turns red. Only visible when search has text.
        self._search_clear_btn = QPushButton("✕", self._search_input)
        self._search_clear_btn.setObjectName("npc_search_clear")
        self._search_clear_btn.setFixedSize(26, 26)
        self._search_clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._search_clear_btn.setToolTip("ล้างคำค้น")
        self._search_clear_btn.setVisible(False)
        self._search_clear_btn.setFont(QFont(FONT_PRIMARY, 11, QFont.Weight.Bold))
        self._search_clear_btn.clicked.connect(self._search_input.clear)
        self._search_input.textChanged.connect(
            lambda txt: self._search_clear_btn.setVisible(bool(txt))
        )
        # Reserve right-side space inside the line edit so text never collides
        # with the X button. setTextMargins(left, top, right, bottom)
        self._search_input.setTextMargins(0, 0, 32, 0)
        # Reposition the X on every resize of the line edit
        def _position_clear_btn():
            le = self._search_input
            btn = self._search_clear_btn
            margin = 4
            btn.move(le.width() - btn.width() - margin,
                     (le.height() - btn.height()) // 2)
        _orig_resize = self._search_input.resizeEvent
        def _patched_resize(ev):
            _orig_resize(ev)
            _position_clear_btn()
        self._search_input.resizeEvent = _patched_resize
        # Initial placement (resize event won't fire until shown)
        QTimer.singleShot(0, _position_clear_btn)

        h.addSpacing(8)

        # ── Filter buttons (only shown on Main tab — toggled in _switch_tab) ──
        # Gender cycle: All → Male → Female → Neutral → All
        self._gender_filter = CycleFilterButton([
            ("เพศ", None, "off"),
            ("ชาย", "Male", "male"),
            ("หญิง", "Female", "female"),
            ("ไม่ระบุ", "Neutral", "neutral"),
        ])
        self._gender_filter.setMinimumWidth(64)
        self._gender_filter.setToolTip("กรองตามเพศ — คลิกเพื่อสลับ")
        self._gender_filter.valueChanged.connect(self._on_filter_changed)
        h.addWidget(self._gender_filter)

        # Completeness cycle: All → Complete (main+roles) → Incomplete (main only)
        self._completeness_filter = CycleFilterButton([
            ("ข้อมูล", None, "off"),
            ("ครบ", "complete", "complete"),
            ("ไม่ครบ", "incomplete", "incomplete"),
        ])
        self._completeness_filter.setMinimumWidth(72)
        self._completeness_filter.setToolTip(
            "กรองความสมบูรณ์ — ครบ: มีทั้ง main + role  /  ไม่ครบ: ขาด role"
        )
        self._completeness_filter.valueChanged.connect(self._on_filter_changed)
        h.addWidget(self._completeness_filter)

        # Recent-added cycle: off → recently added (sorted by _added_at desc)
        # Only matches entries that have the _added_at metadata field
        # (legacy entries without it won't appear — by design).
        self._recent_filter = CycleFilterButton([
            ("ใหม่", None, "off"),
            ("ล่าสุด", "recent", "recent"),
        ])
        self._recent_filter.setMinimumWidth(72)
        self._recent_filter.setToolTip(
            "แสดงเฉพาะตัวละครที่เพิ่งเพิ่มเข้ามาล่าสุด (เรียงจากใหม่สุด)"
        )
        self._recent_filter.valueChanged.connect(self._on_filter_changed)
        h.addWidget(self._recent_filter)

        h.addStretch(1)  # push toast slot to the right

        # Toast slot — shows "✓ บันทึกแล้ว" briefly after a save
        self._toast_label = QLabel("")
        self._toast_label.setObjectName("npc_toast")
        self._toast_label.setFont(QFont(FONT_PRIMARY, 10))
        self._toast_label.setMinimumWidth(140)
        self._toast_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        h.addWidget(self._toast_label)

        # ── Data-font scaler (visible only on DictTabBase tabs — currently LORE only) ──
        # Adjusts both left-side list rows and right-side details simultaneously.
        self._font_dec_btn = QPushButton("−")
        self._font_dec_btn.setObjectName("npc_font_btn")
        self._font_dec_btn.setFixedSize(32, 28)
        self._font_dec_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._font_dec_btn.setToolTip("ลดขนาดฟอนต์ข้อมูล")
        self._font_dec_btn.setFont(QFont(FONT_PRIMARY, 14, QFont.Weight.Bold))
        self._font_dec_btn.clicked.connect(self._on_font_dec)
        h.addWidget(self._font_dec_btn)

        self._font_inc_btn = QPushButton("+")
        self._font_inc_btn.setObjectName("npc_font_btn")
        self._font_inc_btn.setFixedSize(32, 28)
        self._font_inc_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._font_inc_btn.setToolTip("เพิ่มขนาดฟอนต์ข้อมูล")
        self._font_inc_btn.setFont(QFont(FONT_PRIMARY, 14, QFont.Weight.Bold))
        self._font_inc_btn.clicked.connect(self._on_font_inc)
        h.addWidget(self._font_inc_btn)
        return wrap

    def _current_dict_tab(self):
        """Return the current tab page if it's a DictTabBase subclass, else None."""
        tab = self._tab_pages.get(self._current_tab)
        if tab and isinstance(tab, DictTabBase):
            return tab
        return None

    def _on_font_inc(self):
        tab = self._current_dict_tab()
        if tab:
            tab.inc_data_font_size()

    def _on_font_dec(self):
        tab = self._current_dict_tab()
        if tab:
            tab.dec_data_font_size()

    def _build_footer(self) -> QWidget:
        wrap = QWidget()
        wrap.setObjectName("npc_footer")
        wrap.setFixedHeight(40)
        h = QHBoxLayout(wrap)
        h.setContentsMargins(20, 8, 20, 8)
        self._footer_label = QLabel("")
        self._footer_label.setObjectName("npc_footer_lbl")
        self._footer_label.setFont(QFont(FONT_PRIMARY, 10))
        h.addWidget(self._footer_label)
        h.addStretch()
        return wrap

    def _make_divider(self) -> QFrame:
        d = QFrame()
        d.setObjectName("npc_divider")
        d.setFixedHeight(1)
        return d

    # ─── Behavior ───
    def _switch_tab(self, tab_id: str):
        self._current_tab = tab_id
        # Update tab button visuals
        for tid, btn in self._tab_buttons.items():
            btn.setProperty("active", "true" if tid == tab_id else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        # Switch stack page
        idx = [t[0] for t in TABS].index(tab_id)
        self._stack.setCurrentIndex(idx)
        # Update tab title + body description (two-tone)
        title, body = next((t, b) for tid, _, t, b in TABS if tid == tab_id)
        self._tab_title_label.setText(title)
        # Use a middot bullet only when there's a body to introduce
        self._tab_description_label.setText(f"·  {body}" if body else "")
        # Show filter buttons only on Main tab (other tabs don't have these concepts)
        is_main = (tab_id == "main")
        if hasattr(self, "_gender_filter"):
            self._gender_filter.setVisible(is_main)
        if hasattr(self, "_completeness_filter"):
            self._completeness_filter.setVisible(is_main)
        if hasattr(self, "_recent_filter"):
            self._recent_filter.setVisible(is_main)
        # Font scaler buttons — only on dict-style tabs (lore/roles/fixes)
        # Currently only LORE is visible; roles+fixes share DictTabBase but are hidden.
        page = self._tab_pages.get(tab_id)
        is_dict_tab = isinstance(page, DictTabBase)
        if hasattr(self, "_font_dec_btn"):
            self._font_dec_btn.setVisible(is_dict_tab)
        if hasattr(self, "_font_inc_btn"):
            self._font_inc_btn.setVisible(is_dict_tab)
        # Refresh page
        page = self._tab_pages.get(tab_id)
        if hasattr(page, "refresh"):
            page.refresh(self._search_input.text() if self._search_input else "")
        # Update footer count
        self._update_footer()

    def _update_footer(self):
        # Auto-save model: never shows "unsaved" — always persists immediately.
        page = self._tab_pages.get(self._current_tab)
        if hasattr(page, "row_count"):
            count = page.row_count()
            section_name = next(t[1] for t in TABS if t[0] == self._current_tab)
            self._footer_label.setText(f"กำลังดู {section_name}    {count} รายการ")

    def _update_db_status(self):
        """Refresh the header status strip — section counts + file mtime.
        Cheap (one os.stat call + len() x3); safe to call frequently."""
        if not hasattr(self, "_db_status_label") or not self._db_status_label:
            return
        try:
            main_n = len(self.dm.data.get("main_characters", []))
            npcs_n = len(self.dm.data.get("npcs", []))
            lore_n = len(self.dm.data.get("lore", {}))
            mtime_str = "—"
            try:
                if self.dm.file_path and os.path.exists(self.dm.file_path):
                    mtime_str = _format_relative_time(os.path.getmtime(self.dm.file_path))
            except Exception:
                pass
            self._db_status_label.setText(
                f"main {main_n} · npcs {npcs_n} · lore {lore_n}   ·   อัปเดต {mtime_str}"
            )
        except Exception as e:
            log.warning(f"_update_db_status failed: {e}")

    def _on_reload(self):
        """Manual disk-reload — covers external edits / file merges that the
        auto-save signal pipeline can't see. Resets the per-session backup flag
        so the next save (after edits) starts a fresh backup."""
        try:
            self.dm.load()
        except Exception as e:
            log.error(f"Manual reload failed: {e}")
            self._show_toast("⚠ โหลดล้มเหลว", error=True)
            return
        # Fresh load ⇒ next save deserves a fresh backup
        self._has_backed_up = False
        # Refresh the visible tab + counts
        page = self._tab_pages.get(self._current_tab)
        if hasattr(page, "refresh"):
            try:
                search_text = self._search_input.text() if self._search_input else ""
                page.refresh(search_text)
            except Exception as e:
                log.warning(f"refresh after reload failed: {e}")
        self._update_footer()
        self._update_db_status()
        # Propagate to MBB so translator/text_corrector/caches pick up the new data
        if self.on_save_callback:
            try:
                self.on_save_callback()
            except Exception as e:
                log.warning(f"on_save_callback after reload failed: {e}")
        self._show_toast(
            "✓ โหลดใหม่ · ใช้ในการแปลทันที"
            if self.on_save_callback else "✓ โหลดใหม่จากดิสก์"
        )

    def _on_merge_request(self):
        """Open file picker → load target → show diff modal → on accept,
        write merged data + autosave (which fires reload pipeline)."""
        start_dir = ""
        if self.dm.file_path:
            start_dir = os.path.dirname(self.dm.file_path)
        src, _ = QFileDialog.getOpenFileName(
            self, "เลือกไฟล์ npc.json ที่จะ merge", start_dir,
            "NPC Files (NPC.json npc.json *.json)"
        )
        if not src:
            return
        # Don't let user pick the very file we're merging INTO
        if self.dm.file_path and os.path.abspath(src) == os.path.abspath(self.dm.file_path):
            QMessageBox.information(
                self, "ไฟล์เดียวกัน",
                "นั่นคือไฟล์ปัจจุบันอยู่แล้ว — ไม่มีอะไรให้ merge")
            return
        # Sanity cap on file size — real npc.json is well under 5MB. A multi-GB
        # JSON would freeze the UI thread (json.load is blocking) or OOM.
        try:
            sz = os.path.getsize(src)
        except Exception:
            sz = 0
        MAX_NPC_BYTES = 50 * 1024 * 1024  # 50 MB
        if sz > MAX_NPC_BYTES:
            QMessageBox.warning(
                self, "ไฟล์ใหญ่เกินไป",
                f"ไฟล์มีขนาด {sz // (1024*1024)} MB — ไฟล์ npc.json ปกติไม่เกิน 5 MB\n"
                f"ตรวจสอบว่าเป็นไฟล์ที่ถูกต้องหรือไม่")
            return
        try:
            with open(src, "r", encoding="utf-8") as f:
                target_data = json.load(f)
        except Exception as e:
            QMessageBox.warning(self, "อ่านไฟล์ไม่ได้",
                                f"ไม่สามารถอ่านไฟล์ JSON:\n{e}")
            return
        # Sanity check — must look like an npc.json structure
        looks_like_npc = (
            isinstance(target_data, dict)
            and any(k in target_data for k in
                    ("main_characters", "npcs", "lore", "character_roles"))
        )
        if not looks_like_npc:
            QMessageBox.warning(
                self, "ไม่ใช่ไฟล์ NPC",
                "ไฟล์ที่เลือกไม่มี main_characters / npcs / lore / character_roles\n"
                "— แน่ใจว่าเป็น npc.json?")
            return
        # Normalize so all expected keys exist
        for k in ("main_characters", "npcs"):
            target_data.setdefault(k, [])
        for k in ("lore", "character_roles", "word_fixes", "_game_info"):
            target_data.setdefault(k, {})
        # Show diff dialog. Read applied_count BEFORE deleteLater so we don't
        # touch a dangling reference. deleteLater is essential — without it,
        # repeated merge sessions accumulate dialog widgets owned by self.panel.
        dlg = _MergeDialog(self, src, target_data)
        result = dlg.exec()
        n_applied = dlg.applied_count if result == QDialog.DialogCode.Accepted else 0
        dlg.deleteLater()
        if n_applied > 0:
            # Refresh visible tab + propagate via autosave (fires
            # reload_npc_data → translator + text_corrector + caches).
            page = self._tab_pages.get(self._current_tab)
            if hasattr(page, "refresh"):
                try:
                    search_text = self._search_input.text() if self._search_input else ""
                    page.refresh(search_text)
                except Exception as e:
                    log.warning(f"refresh after merge failed: {e}")
            msg = (f"✓ Merge {n_applied} รายการ · ใช้ในการแปลทันที"
                   if self.on_save_callback
                   else f"✓ Merge {n_applied} รายการ")
            self.autosave(msg)

    def _on_search_changed(self, text: str):
        page = self._tab_pages.get(self._current_tab)
        if hasattr(page, "refresh"):
            page.refresh(text)
        self._update_footer()

    def _on_filter_changed(self, _value):
        """Filter buttons changed — refresh current tab to apply filters."""
        page = self._tab_pages.get(self._current_tab)
        if hasattr(page, "refresh"):
            page.refresh(self._search_input.text() if self._search_input else "")
        self._update_footer()

    def autosave(self, message: Optional[str] = None) -> bool:
        """Persist current data to npc.json. Backup created only on first save
        of this session (avoids backup spam on rapid edits). Shows toast on success.

        Args:
            message: Custom toast text (e.g. "✓ เพิ่ม 'X' แล้ว" for fresh-add flow).
                Pass None to use the default — varies by attachment state:
                with on_save_callback (live MBB) → "บันทึก · ใช้ในการแปลทันที",
                without (standalone/dev) → "บันทึกแล้ว".
        """
        if message is None:
            message = ("✓ บันทึก · ใช้ในการแปลทันที"
                       if self.on_save_callback else "✓ บันทึกแล้ว")
        backup = not self._has_backed_up
        ok = self.dm.save(backup=backup)
        if ok:
            self._has_backed_up = True
            self._show_toast(message)
            self.on_data_saved.emit()
            if self.on_save_callback:
                try:
                    self.on_save_callback()
                except Exception as e:
                    log.error(f"on_save_callback error: {e}")
        else:
            self._show_toast("⚠ บันทึกล้มเหลว", error=True)
        self._update_footer()
        self._update_db_status()  # mtime + counts changed
        return ok

    def _show_toast(self, text: str, error: bool = False):
        """Briefly show a toast message in the search bar slot."""
        if not self._toast_label:
            return
        color = "#e85a5a" if error else self.palette.get("accent", "#3fb950") if hasattr(self, "palette") else "#3fb950"
        self._toast_label.setStyleSheet(
            f"color: {color}; background: transparent; padding-right: 4px;"
        )
        self._toast_label.setText(text)
        # Fade after 2.2s
        QTimer.singleShot(2200, lambda: (
            self._toast_label.setText("") if self._toast_label else None
        ))

    def _on_pin_click(self):
        self._is_pinned = not self._is_pinned
        self._apply_topmost(self._is_pinned)
        self._update_pin_icon()

    def _apply_topmost(self, on: bool):
        """Toggle always-on-top.

        Win32-only SetWindowPos isn't enough on its own — Qt's internal window
        model still tracks WindowStaysOnTopHint and may re-apply it on next
        activate/raise. So we update BOTH: Qt's flag (so its internal state is
        correct + survives re-show) plus a Win32 SetWindowPos to enforce the
        actual z-order without the flicker that show() alone would cause.

        The order matters: setWindowFlag unmaps → show() remaps → THEN Win32
        SetWindowPos with NOACTIVATE+SHOWWINDOW puts the window at the right
        z-order without re-stealing focus. The brief unmap is unavoidable for
        flag changes, but is fast enough to not be visually jarring.
        """
        # 1) Qt-level: keep internal flag in sync (otherwise Qt re-applies topmost)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, on)
        self.show()
        # 2) Win32: enforce the actual z-order immediately
        try:
            import sys
            if sys.platform == "win32":
                import ctypes
                HWND_TOPMOST = -1
                HWND_NOTOPMOST = -2
                SWP_NOMOVE = 0x0002
                SWP_NOSIZE = 0x0001
                SWP_NOACTIVATE = 0x0010
                hwnd = int(self.winId())
                pos_flag = HWND_TOPMOST if on else HWND_NOTOPMOST
                ok = ctypes.windll.user32.SetWindowPos(
                    hwnd, pos_flag, 0, 0, 0, 0,
                    SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE
                )
                if not ok:
                    err = ctypes.get_last_error()
                    log.warning(f"SetWindowPos returned 0 (GetLastError={err})")
        except Exception as e:
            log.debug(f"Win32 SetWindowPos failed: {e}")

    def _update_reload_icon(self):
        """Load assets/swap.png for the manual-reload button. On light themes,
        tint to dark for guaranteed contrast (same pattern as the pin button)."""
        if not hasattr(self, "_btn_reload") or not self._btn_reload:
            return
        icon_path = resource_path("assets/swap.png")
        if not os.path.exists(icon_path):
            # Fallback to text glyph if asset is missing
            self._btn_reload.setText("↻")
            self._btn_reload.setFont(QFont(FONT_PRIMARY, 14, QFont.Weight.Bold))
            return
        pix = QPixmap(icon_path)
        try:
            bg = self.am.get_accent_color()
            if is_light_theme(bg):
                text_color = getattr(self, "palette", {}).get("text", "#1f2328")
                pix = tint_pixmap(pix, text_color)
        except Exception:
            pass
        self._btn_reload.setIcon(QIcon(pix))
        self._btn_reload.setIconSize(QSize(16, 16))
        self._btn_reload.setText("")

    def _update_pin_icon(self):
        """Use the same pin.png/unpin.png as MBB header_bar.
        On light themes, TINT the icon dark (stronger than invert for low-contrast pixels)."""
        if not self._btn_pin:
            return
        icon_name = "assets/pin.png" if self._is_pinned else "assets/unpin.png"
        icon_path = resource_path(icon_name)
        if os.path.exists(icon_path):
            pix = QPixmap(icon_path)
            try:
                bg = self.am.get_accent_color()
                if is_light_theme(bg):
                    # Tint to dark theme text color for guaranteed contrast
                    text_color = getattr(self, "palette", {}).get("text", "#1f2328")
                    pix = tint_pixmap(pix, text_color)
            except Exception:
                pass
            self._btn_pin.setIcon(QIcon(pix))
            self._btn_pin.setIconSize(QSize(16, 16))
            self._btn_pin.setText("")
        else:
            self._btn_pin.setText("📌" if self._is_pinned else "📍")

    def closeEvent(self, event):
        # Auto-save model: every CRUD persists immediately, so closing is safe.
        # Catch-all: if anything is still dirty, save quietly.
        if self.dm.is_dirty:
            try:
                self.dm.save(backup=not self._has_backed_up)
            except Exception as e:
                log.warning(f"Final auto-save on close failed: {e}")
        if self.on_close_callback:
            try:
                self.on_close_callback()
            except Exception as e:
                log.debug(f"on_close_callback error: {e}")
        super().closeEvent(event)

    # ─── Public API for external entry points ───
    def open_with_character(self, character_name: str):
        """Called when user clicks a character name on the TUI.
        Pipeline:
          A. Character exists → switch to MAIN tab, fill search box, auto-select row.
          B. Character missing → add new entry (firstName only) → autosave with
             custom toast → fall through to pipeline A with the just-added name.
        """
        name = (character_name or "").strip()
        if not name:
            return
        self._switch_tab("main")
        page = self._tab_pages.get("main")
        if not isinstance(page, MainCharactersTab):
            return

        def _find_index(chars):
            target = name.lower()
            for i, c in enumerate(chars):
                first = c.get("firstName", "").strip().lower()
                full = (c.get("firstName", "") + " " + c.get("lastName", "")).strip().lower()
                if first == target or full == target:
                    return i
            return None

        chars = self.dm.list_main_characters()
        matched_idx = _find_index(chars)

        # Pipeline B: auto-add new entry
        if matched_idx is None:
            try:
                self.dm.add_main_character({"firstName": name})
            except Exception as e:
                log.error(f"open_with_character: add_main_character failed: {e}")
                return
            self.autosave(f"✓ เพิ่ม '{name}' แล้ว")
            chars = self.dm.list_main_characters()
            matched_idx = _find_index(chars)

        # Pipeline A: filter search + select row.
        # Don't blockSignals — textChanged drives both list refresh AND clear-button
        # visibility. Letting it fire normally keeps X button visible after auto-fill.
        if self._search_input:
            self._search_input.setText(name)
        else:
            page.refresh(name)

        if matched_idx is None:
            return  # safety — shouldn't happen after auto-add

        # QTreeWidget — use topLevelItem* methods
        for row in range(page.list_widget.topLevelItemCount()):
            item = page.list_widget.topLevelItem(row)
            if item.data(0, Qt.ItemDataRole.UserRole) == matched_idx:
                page.list_widget.setCurrentItem(item)
                page.list_widget.scrollToItem(item)
                break

    def resizeEvent(self, event):
        """Position the resize grip at bottom-right corner of bg widget."""
        super().resizeEvent(event)
        if hasattr(self, "_resize_grip") and self._resize_grip and self.bg:
            margin = 6
            self._resize_grip.move(
                self.bg.width() - self._resize_grip.width() - margin,
                self.bg.height() - self._resize_grip.height() - margin,
            )

    # ─── Drag (header only) ───
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = event.globalPosition().toPoint()
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and not self.old_pos.isNull():
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self.old_pos = QPoint()
        super().mouseReleaseEvent(event)

    # ─── Theming ───
    def _apply_theme(self):
        primary = self.am.get_accent_color()
        secondary = self.am.get_theme_color("secondary", "#888888")
        surface = self.am.get_theme_color("surface_override")
        text_o = self.am.get_theme_color("text_override")
        p = derive_palette(primary, secondary, surface=surface, text_override=text_o)
        self.palette = p

        # Refresh icons that need invert on light theme
        self._update_pin_icon()
        self._update_reload_icon()
        if hasattr(self, "_resize_grip") and self._resize_grip:
            self._resize_grip.set_invert(is_light_theme(p["bg"]))
        # Refresh CharacterAvatar palette in MainCharactersTab
        main_tab = self._tab_pages.get("main")
        if main_tab and hasattr(main_tab, "avatar"):
            main_tab.avatar.set_palette(p)
            # Hover menu is lazy-built — only re-paint if it already exists,
            # otherwise it picks up the current palette on first show.
            _hm = getattr(main_tab, "_hover_menu", None)
            if _hm is not None:
                try:
                    _hm.set_palette(
                        accent=p.get("accent", primary),
                        bg=p.get("btn_bg", "#161b22"),
                        bg2=p.get("bg_titlebar", p.get("btn_bg", "#1c2128")),
                        text=p.get("text", "#e6edf3"),
                        text_dim=p.get("text_dim", "#7d8590"),
                    )
                except Exception as e:
                    log.debug(f"[theme] hover menu repaint skipped: {e}")

        qss = f"""
            QWidget#npc_bg {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {p['bg']}, stop:1 {p['bg_deeper']});
                border-radius: 12px;
                border: 1px solid {p['border_subtle']};
            }}
            QWidget#npc_header {{
                background: {p['bg_titlebar']};
                border-top-left-radius: 12px;
                border-top-right-radius: 12px;
            }}
            QLabel#npc_title {{
                color: {p['text']};
                background: transparent;
            }}
            QLabel#npc_subtitle {{
                color: {p['text_dim']};
                background: transparent;
            }}
            QPushButton#npc_header_btn {{
                background: transparent;
                border: none;
                border-radius: 4px;
                color: {p['text_dim']};
                font-size: 14px;
            }}
            QPushButton#npc_header_btn:hover {{
                background: {p['bg_medium']};
                color: {p['text']};
            }}
            QPushButton#npc_merge_btn {{
                background: {p['btn_bg']};
                color: {p['text']};
                border: 1px solid {p['border_active']};
                border-radius: 4px;
                padding: 4px 10px;
            }}
            QPushButton#npc_merge_btn:hover {{
                background: {p['bg_medium']};
                border: 1px solid {p['accent']};
                color: {p['accent']};
            }}
            QPushButton#npc_close {{
                background: transparent;
                border: none;
                border-radius: 4px;
                color: {p['text_dim']};
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton#npc_close:hover {{
                background: #cc4444;
                color: #ffffff;
            }}
            QFrame#npc_divider {{
                background: {p['separator']};
                border: none;
            }}
            QWidget#npc_tabbar, QWidget#npc_searchbar, QWidget#npc_footer, QWidget#npc_stack {{
                background: transparent;
            }}
            QPushButton#npc_tab_btn {{
                background: {p['btn_bg']};
                color: {p['text']};
                border: 1px solid {p['border_active']};
                border-radius: 5px;
                padding: 8px 22px;
            }}
            QPushButton#npc_tab_btn:hover {{
                background: {p['bg_medium']};
                border: 1px solid {p['accent']};
            }}
            QPushButton#npc_tab_btn[active="true"] {{
                background: {p['accent']};
                color: {p['toggled_text']};
                border: 1px solid {p['accent']};
            }}
            QPushButton#npc_tab_btn[disabled_tab="true"] {{
                background: transparent;
                color: {p['text_dim']};
                border: 1px dashed {p['border_subtle']};
            }}
            QPushButton#npc_tab_btn[disabled_tab="true"]:hover {{
                background: transparent;
                color: {p['text_dim']};
                border: 1px dashed {p['border_subtle']};
            }}
            QLineEdit#npc_search {{
                background: {p['bg_titlebar']};
                color: {p['text']};
                border: 1px solid {p['border_subtle']};
                border-radius: 5px;
                padding: 7px 12px;
                selection-background-color: {p['accent']};
            }}
            QLineEdit#npc_search:focus {{
                border: 1px solid {p['accent']};
            }}
            QPushButton#npc_search_clear {{
                background: {p['btn_bg']};
                color: {p['text_dim']};
                border: 1px solid {p['border_active']};
                border-radius: 6px;
                font-weight: bold;
            }}
            QPushButton#npc_search_clear:hover {{
                background: #e85a5a;
                color: #ffffff;
                border: 1px solid #e85a5a;
            }}
            /* ── Data-font scaler buttons ── */
            QPushButton#npc_font_btn {{
                background: {p['btn_bg']};
                color: {p['text']};
                border: 1px solid {p['border_active']};
                border-radius: 5px;
                font-weight: bold;
            }}
            QPushButton#npc_font_btn:hover {{
                background: {p['bg_medium']};
                border: 1px solid {p['accent']};
                color: {p['accent']};
            }}
            /* ── Filter cycle buttons ── */
            QPushButton#npc_filter_btn {{
                border-radius: 6px;
                padding: 4px 12px;
            }}
            QPushButton#npc_filter_btn[filter_state="off"] {{
                background: {p['btn_bg']};
                color: {p['text_dim']};
                border: 1px solid {p['border_active']};
            }}
            QPushButton#npc_filter_btn[filter_state="off"]:hover {{
                background: {p['bg_medium']};
                color: {p['text']};
            }}
            QPushButton#npc_filter_btn[filter_state="male"] {{
                background: #58a6ff;
                color: #ffffff;
                border: 1px solid #58a6ff;
            }}
            QPushButton#npc_filter_btn[filter_state="female"] {{
                background: #f06292;
                color: #ffffff;
                border: 1px solid #f06292;
            }}
            QPushButton#npc_filter_btn[filter_state="neutral"] {{
                background: #8e8e93;
                color: #ffffff;
                border: 1px solid #8e8e93;
            }}
            QPushButton#npc_filter_btn[filter_state="complete"] {{
                background: #2ea043;
                color: #ffffff;
                border: 1px solid #2ea043;
            }}
            QPushButton#npc_filter_btn[filter_state="incomplete"] {{
                background: #f59e0b;
                color: #ffffff;
                border: 1px solid #f59e0b;
            }}
            QPushButton#npc_filter_btn[filter_state="recent"] {{
                background: #a855f7;
                color: #ffffff;
                border: 1px solid #a855f7;
            }}
            QPushButton#npc_save_btn {{
                background: {p['accent']};
                color: {p['toggled_text']};
                border: none;
                border-radius: 5px;
                padding: 7px 16px;
            }}
            QPushButton#npc_save_btn:hover {{
                background: {p['accent_light']};
            }}
            QLabel#npc_tab_title {{
                color: {p['text']};
                background: transparent;
            }}
            QLabel#npc_tab_desc {{
                color: {p['text_dim']};
                background: transparent;
                padding-right: 6px;
            }}
            QLabel#npc_footer_lbl {{
                color: {p['text_dim']};
                background: transparent;
            }}
            QLabel#npc_list_header {{
                color: {p['text_dim']};
                background: transparent;
                padding: 6px 4px;
                font-weight: bold;
            }}
            QLabel#npc_placeholder {{
                color: {p['text_dim']};
                background: transparent;
            }}
            /* List + details styles inside tab pages */
            QTreeWidget#npc_list {{
                background: {p['bg_titlebar']};
                color: {p['text']};
                border: 1px solid {p['border_subtle']};
                border-radius: 6px;
                outline: none;
                font-family: '{FONT_PRIMARY}';
                font-size: 11pt;
                padding: 4px;
            }}
            QTreeWidget#npc_list::item {{
                padding: 6px 10px;
                border-radius: 3px;
            }}
            QTreeWidget#npc_list::item:hover {{
                background: {p['bg_medium']};
            }}
            QTreeWidget#npc_list::item:selected {{
                background: {p['accent']};
                color: {p['toggled_text']};
            }}
            QTreeWidget#npc_list::branch {{
                background: transparent;
            }}
            QWidget#npc_details {{
                background: {p['bg_titlebar']};
                border: 1px solid {p['border_subtle']};
                border-radius: 6px;
            }}
            QLabel#npc_details_title {{
                color: {p['text']};
                background: transparent;
            }}
            QLabel.npc_field_label {{
                color: {p['text_dim']};
                background: transparent;
            }}
            QLineEdit.npc_field, QComboBox.npc_field {{
                background: {p['btn_bg']};
                color: {p['text']};
                border: 1px solid {p['border_subtle']};
                border-radius: 4px;
                padding: 8px 12px;
                font-family: '{FONT_PRIMARY}';
                font-size: 11pt;
                selection-background-color: {p['accent']};
            }}
            QLineEdit.npc_field:focus, QComboBox.npc_field:focus {{
                border: 1px solid {p['accent']};
            }}
            QTextEdit.npc_textarea {{
                background: {p['btn_bg']};
                color: {p['text']};
                border: 1px solid {p['border_subtle']};
                border-radius: 4px;
                padding: 8px 12px;
                font-family: '{FONT_PRIMARY}';
                font-size: 11pt;
                selection-background-color: {p['accent']};
            }}
            QTextEdit.npc_textarea:focus {{
                border: 1px solid {p['accent']};
            }}
            QLabel#npc_personality_hint {{
                color: {p['text_dim']};
                background: transparent;
                padding: 2px 4px 2px 4px;
            }}
            QComboBox.npc_field::drop-down {{
                border: none;
                width: 24px;
            }}
            QPushButton.npc_action {{
                background: {p['btn_bg']};
                color: {p['text']};
                border: 1px solid {p['border_active']};
                border-radius: 4px;
                padding: 9px 18px;
                font-family: '{FONT_PRIMARY}';
                font-size: 11pt;
            }}
            QPushButton.npc_action:hover {{
                background: {p['bg_medium']};
                border: 1px solid {p['accent']};
            }}
            /* Attention state — for missing-data CTAs like "+ เพิ่มบุคลิก" */
            QPushButton.npc_action[attention="true"] {{
                background: #2ea043;
                color: #ffffff;
                border: 1px solid #2ea043;
                font-weight: bold;
            }}
            QPushButton.npc_action[attention="true"]:hover {{
                background: #3fb950;
                border: 1px solid #3fb950;
            }}
            QPushButton.npc_primary {{
                background: {p['accent']};
                color: {p['toggled_text']};
                border: none;
                border-radius: 5px;
                padding: 12px 22px;
                font-family: '{FONT_PRIMARY}';
                font-size: 12pt;
                font-weight: bold;
            }}
            QPushButton.npc_primary:hover {{
                background: {p['accent_light']};
            }}
            QPushButton.npc_primary:disabled {{
                background: {p['btn_bg']};
                color: {p['text_dim']};
            }}
            QPushButton.npc_danger:disabled {{
                color: {p['text_dim']};
                border: 1px solid {p['border_subtle']};
            }}
            QPushButton.npc_danger {{
                background: transparent;
                color: #e85a5a;
                border: 1px solid #e85a5a;
                border-radius: 4px;
                padding: 9px 18px;
                font-family: '{FONT_PRIMARY}';
                font-size: 11pt;
            }}
            QPushButton.npc_danger:hover {{
                background: #e85a5a;
                color: #ffffff;
            }}
            QPushButton.gender_chip {{
                background: {p['btn_bg']};
                color: {p['text_dim']};
                border: 1px solid {p['border_active']};
                border-radius: 4px;
                padding: 8px 20px;
                font-family: '{FONT_PRIMARY}';
                font-size: 11pt;
            }}
            QPushButton.gender_chip:hover {{
                background: {p['bg_medium']};
                color: {p['text']};
            }}
            QPushButton.gender_chip[active="true"][gender="male"] {{
                background: #58a6ff;
                color: #ffffff;
                border: 1px solid #58a6ff;
            }}
            QPushButton.gender_chip[active="true"][gender="female"] {{
                background: #f06292;
                color: #ffffff;
                border: 1px solid #f06292;
            }}
            QPushButton.gender_chip[active="true"][gender="neutral"] {{
                background: #8e8e93;
                color: #ffffff;
                border: 1px solid #8e8e93;
            }}
        """
        self.setStyleSheet(qss)


# ────────────────────────────────────────────────────────────────────
# Main Characters tab
# ────────────────────────────────────────────────────────────────────
class MainCharactersTab(QWidget):
    """List on the left, details/edit form on the right."""

    GENDERS = ["Male", "Female", "Neutral"]

    def __init__(self, panel: NPCManagerPanel):
        super().__init__()
        self.panel = panel
        self.dm = panel.dm
        self._current_index = -1   # -1 = new entry mode
        self._current_filter = ""  # last search text
        self._build()

    def _build(self):
        outer = QHBoxLayout(self)
        outer.setContentsMargins(16, 4, 16, 10)
        outer.setSpacing(14)

        # ── Left: list (QTreeWidget for proper column alignment) ──
        left = QVBoxLayout()
        left.setSpacing(4)
        head = _build_list_header("NAME", "TYPE")
        left.addLayout(head)

        self.list_widget = _make_tree(["NAME", "TYPE"])
        self.list_widget.itemSelectionChanged.connect(self._on_list_selection)
        self.list_widget.setMinimumWidth(280)
        left.addWidget(self.list_widget, stretch=1)
        outer.addLayout(left, stretch=2)

        # ── Right: details panel ──
        details = QWidget()
        details.setObjectName("npc_details")
        d = QVBoxLayout(details)
        d.setContentsMargins(22, 20, 22, 20)
        d.setSpacing(12)  # tightened from 14 to fit 14 items in panel height (840)

        # ── Avatar (centered at top) — click opens Polaroid view ──
        avatar_row = QHBoxLayout()
        avatar_row.addStretch()
        self.avatar = CharacterAvatar()
        self.avatar.avatar_clicked.connect(self._on_avatar_clicked)
        # Hover menu (lazy-created) — offers file picker / screenshot.
        # Visibility driven by a cursor-position poll (every 80ms) instead of
        # avatar enter/leave events, because the popup menu would steal mouse
        # focus on show, triggering avatar.leaveEvent → grace-close → re-enter
        # = visible flicker loop. See project_pyqt6_gotchas.md.
        self._hover_menu: Optional["_AvatarHoverMenu"] = None
        self._hover_outside_since = 0.0   # timestamp cursor first left both targets
        # Suppress poll for a short window after we explicitly restore the
        # panel (post-screenshot). Without this, the poll instantly re-opens
        # the hover menu if cursor is still over the avatar, and that menu
        # would overlap the Polaroid we're also re-opening. unix-time.
        self._hover_poll_suppress_until = 0.0
        # Pre-declare so any pre-screenshot access doesn't AttributeError.
        self._active_screenshot_overlay = None
        self._hover_poll_timer = QTimer(self)
        self._hover_poll_timer.setInterval(80)
        self._hover_poll_timer.timeout.connect(self._poll_avatar_hover)
        self._hover_poll_timer.start()
        avatar_row.addWidget(self.avatar)
        avatar_row.addStretch()
        d.addLayout(avatar_row)
        d.addSpacing(8)

        # Polaroid overlay — created lazily and parented to this tab so it covers
        # only the right-hand details area (not the entire NPC Manager window).
        self._polaroid: Optional[PolaroidOverlay] = None
        # NB: "Main Characters Details" title removed — redundant with the
        # tab title in the tab bar. Avatar enlarged (80→120) to fill the
        # freed vertical space.

        # Name (firstName + lastName)
        d.addWidget(self._field_label("Name:"))
        name_row = QHBoxLayout()
        name_row.setSpacing(8)
        self.in_first = QLineEdit()
        self.in_first.setProperty("class", "npc_field")
        self.in_first.setObjectName("npc_first")
        self.in_first.setPlaceholderText("First name")
        self.in_first.setMinimumHeight(36)
        self.in_first.setFont(QFont(FONT_PRIMARY, 11))
        self.in_first.textChanged.connect(self._update_primary_enabled)
        self.in_last = QLineEdit()
        self.in_last.setProperty("class", "npc_field")
        self.in_last.setObjectName("npc_last")
        self.in_last.setPlaceholderText("Last name")
        self.in_last.setMinimumHeight(36)
        self.in_last.setFont(QFont(FONT_PRIMARY, 11))
        self.in_last.textChanged.connect(self._update_primary_enabled)
        name_row.addWidget(self.in_first, stretch=2)
        name_row.addWidget(self.in_last, stretch=1)
        d.addLayout(name_row)

        # ── Personality (น้ำเสียง / บุคลิก) — PROMINENT field ──
        # Stored separately in npc.json["character_roles"][firstName]; loaded
        # on selection, saved with the main entry on ADD/UPDATE.
        # Starts at 1 line; user can drag the bottom-right grip to expand.
        d.addWidget(self._field_label("น้ำเสียง / บุคลิก:"))

        self.in_personality = QTextEdit()
        self.in_personality.setObjectName("npc_personality")
        # Use standard textarea styling (matches other fields, not over-emphasized)
        self.in_personality.setProperty("class", "npc_textarea")
        self.in_personality.setPlaceholderText("เขียนน้ำเสียง / สไตล์การพูด...")
        self.in_personality.setFont(QFont(FONT_PRIMARY, 11))
        self.in_personality.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        # 1-line starting height — use fontMetrics().height() (includes ascent +
        # descent so descenders aren't clipped) + QSS padding (16) + border (2)
        # + small buffer so the placeholder isn't visually cut off.
        fm = self.in_personality.fontMetrics()
        self._personality_min_height = fm.height() + 22
        self.in_personality.setFixedHeight(self._personality_min_height)
        # textChanged drives change-detection only (no auto-resize)
        self.in_personality.textChanged.connect(self._update_primary_enabled)
        d.addWidget(self.in_personality)

        # Bottom-right resize grip — drag to expand the textarea vertically
        self._personality_grip = _TextEditResizeGrip(
            self.in_personality,
            min_height=self._personality_min_height,
            max_height=420,
        )

        # Compact hint BELOW the textarea (was on the right; moved per request)
        hint = QLabel(
            "ตัวอย่าง: พูดสุภาพ ลงท้าย ค่ะ/นะคะ • ใช้ราชาศัพท์ \"ข้า/ท่าน\" • "
            "เสียงห้าว ดุดัน • พูดติดอ่าง น่ารัก สดใส"
        )
        hint.setObjectName("npc_personality_hint")
        hint.setWordWrap(True)
        hint.setFont(QFont(FONT_PRIMARY, 9))
        d.addWidget(hint)
        d.addSpacing(6)

        # Gender chips
        d.addWidget(self._field_label("Gender:"))
        self._gender_btns = {}
        gender_row = QHBoxLayout()
        gender_row.setSpacing(8)
        self._gender_group = QButtonGroup(self)
        self._gender_group.setExclusive(True)
        for g in self.GENDERS:
            b = QPushButton(g)
            b.setProperty("class", "gender_chip")
            b.setProperty("active", "false")
            b.setProperty("gender", g.lower())  # male/female/neutral — matches filter colors
            b.setCheckable(True)
            b.setMinimumHeight(36)
            b.setFont(QFont(FONT_PRIMARY, 11))
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _checked, gg=g: self._set_gender(gg))
            self._gender_group.addButton(b)
            gender_row.addWidget(b)
            self._gender_btns[g] = b
        gender_row.addStretch()
        d.addLayout(gender_row)
        # Default gender = Neutral
        self._set_gender("Neutral")

        # Role (job/affiliation — short)
        d.addWidget(self._field_label("Role (อาชีพ/สังกัด):"))
        self.in_role = QLineEdit()
        self.in_role.setProperty("class", "npc_field")
        self.in_role.setPlaceholderText("เช่น Scion, Black mage")
        self.in_role.setMinimumHeight(36)
        self.in_role.setFont(QFont(FONT_PRIMARY, 11))
        self.in_role.textChanged.connect(self._update_primary_enabled)
        d.addWidget(self.in_role)

        # Relationship (combo)
        d.addWidget(self._field_label("Relationship:"))
        self.in_rel = QComboBox()
        self.in_rel.setProperty("class", "npc_field")
        self.in_rel.addItems(["Close Ally", "Ally", "Neutral", "Rival", "Enemy", "Unknown"])
        self.in_rel.setEditable(True)
        self.in_rel.setMinimumHeight(36)
        self.in_rel.setFont(QFont(FONT_PRIMARY, 11))
        self.in_rel.currentTextChanged.connect(self._update_primary_enabled)
        d.addWidget(self.in_rel)

        # Spacer between fields and action buttons
        d.addSpacing(8)
        d.addStretch(1)

        # Action row: ADD/UPDATE (wide) + Delete (compact) — same line saves
        # vertical space and keeps related actions visually grouped.
        action_row = QHBoxLayout()
        action_row.setSpacing(8)
        self.btn_primary = QPushButton("ADD ENTRY")
        self.btn_primary.setProperty("class", "npc_primary")
        self.btn_primary.setMinimumHeight(40)
        self.btn_primary.setFont(QFont(FONT_PRIMARY, 12, QFont.Weight.Bold))
        self.btn_primary.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_primary.setEnabled(False)
        self.btn_primary.clicked.connect(self._on_primary)
        action_row.addWidget(self.btn_primary, stretch=4)

        self.btn_delete = QPushButton("Delete entry")
        self.btn_delete.setProperty("class", "npc_danger")
        self.btn_delete.setMinimumHeight(40)
        self.btn_delete.setFont(QFont(FONT_PRIMARY, 10))
        self.btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_delete.setEnabled(False)
        self.btn_delete.setToolTip("ลบรายการที่เลือก (ต้องเลือกแถวก่อน)")
        self.btn_delete.clicked.connect(self._on_delete)
        action_row.addWidget(self.btn_delete, stretch=1)
        d.addLayout(action_row)

        # Snapshot of selected entry for change-detection (UPDATE mode)
        self._snapshot = None

        outer.addWidget(details, stretch=3)

    def _field_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setProperty("class", "npc_field_label")
        lbl.setFont(QFont(FONT_PRIMARY, 11))
        return lbl

    def _set_gender(self, gender: str):
        self._current_gender = gender
        for g, btn in self._gender_btns.items():
            active = (g == gender)
            btn.setChecked(active)
            btn.setProperty("active", "true" if active else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        # Trigger change-detection (used by UPDATE button enable logic)
        if hasattr(self, "btn_primary"):
            self._update_primary_enabled()

    # ─── Public API ───
    def refresh(self, search_query: str = ""):
        """Reload list from data + apply text + gender + completeness filters."""
        self._current_filter = search_query
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        characters = self.dm.search(search_query, "main")
        # Generate badge icons fresh each refresh so they pick up the current
        # theme accent (cheap — one tiny QPixmap each).
        try:
            accent = self.panel.am.get_accent_color()
        except Exception:
            accent = "#58a6ff"
        badge = _make_avatar_badge_icon(accent, size=22)
        empty_badge = _make_empty_badge_icon(size=22)

        # Pull current filter values from panel
        gender_v = self.panel._gender_filter.value() if hasattr(self.panel, "_gender_filter") else None
        comp_v = self.panel._completeness_filter.value() if hasattr(self.panel, "_completeness_filter") else None
        recent_v = self.panel._recent_filter.value() if hasattr(self.panel, "_recent_filter") else None
        roles_dict = self.dm.data.get("character_roles", {}) or {}

        # Build (idx, character) pairs first so we can sort for recent filter
        all_chars = list(enumerate(self.dm.list_main_characters()))

        # Filter pass
        passed = []
        for i, c in all_chars:
            if c not in characters:
                continue
            # Recent filter — only entries with the _added_at metadata field
            if recent_v == "recent" and not c.get("_added_at"):
                continue
            # Gender filter — "ไม่ระบุ" (Neutral) matches anything that's not
            # explicitly Male/Female (covers Neutral, Unknown, None, missing).
            if gender_v:
                g = (c.get("gender") or "").strip()
                if gender_v == "Neutral":
                    if g in ("Male", "Female"):
                        continue
                else:
                    if g != gender_v:
                        continue
            # Completeness filter
            first = c.get("firstName", "").strip()
            has_role = bool(first and first in roles_dict)
            if comp_v == "complete" and not has_role:
                continue
            if comp_v == "incomplete" and has_role:
                continue
            passed.append((i, c))

        # If recent filter active, sort newest-first
        if recent_v == "recent":
            passed.sort(key=lambda p: p[1].get("_added_at", 0), reverse=True)

        for i, c in passed:
            first = c.get("firstName", "")
            display = first
            if c.get("lastName"):
                display += " " + c["lastName"]
            type_text = c.get("gender", "Neutral")
            row = _new_row([display, type_text], payload=i)
            # Avatar badge at column-0 left edge — themed bg keeps the
            # white-on-transparent SVG-style glyph readable on any theme.
            # Empty placeholder for rows without avatar so all icons line up
            # vertically in the same column.
            row.setIcon(0, badge if c.get("image") else empty_badge)
            self.list_widget.addTopLevelItem(row)
        self.list_widget.blockSignals(False)
        # Reset selection
        self._current_index = -1
        self._reset_form()

    def row_count(self) -> int:
        return self.list_widget.topLevelItemCount()

    # ─── Internal handlers ───
    def _on_list_selection(self):
        items = self.list_widget.selectedItems()
        if not items:
            # Cleared selection (clicked whitespace, etc) → reset to ADD mode
            self._current_index = -1
            self._snapshot = None
            self._reset_form()
            self.btn_delete.setEnabled(False)
            return
        idx = items[0].data(0, Qt.ItemDataRole.UserRole)
        chars = self.dm.list_main_characters()
        if 0 <= idx < len(chars):
            self._current_index = idx
            c = chars[idx]
            first = c.get("firstName", "")
            # Personality lives in npc.json["character_roles"][firstName]
            roles_dict = self.dm.data.get("character_roles", {}) or {}
            personality = roles_dict.get(first, "") if first else ""
            # Snapshot stored values for change detection (BEFORE populating fields)
            self._snapshot = {
                "firstName": first,
                "lastName": c.get("lastName", ""),
                "gender": c.get("gender", "Neutral"),
                "role": c.get("role", ""),
                "relationship": c.get("relationship", "Neutral"),
                "personality": personality,
            }
            self.in_first.setText(first)
            self.in_last.setText(c.get("lastName", ""))
            self._set_gender(c.get("gender", "Neutral"))
            self.in_role.setText(c.get("role", ""))
            rel = c.get("relationship", "Neutral")
            ix = self.in_rel.findText(rel)
            if ix >= 0:
                self.in_rel.setCurrentIndex(ix)
            else:
                self.in_rel.setCurrentText(rel)
            self.in_personality.setPlainText(personality)
            self.btn_primary.setText("UPDATE ENTRY")
            self.btn_delete.setEnabled(True)
            self._refresh_avatar()
            # After populating, button should be DISABLED (no changes yet)
            self._update_primary_enabled()

    def keyPressEvent(self, event):
        """Esc clears selection → back to ADD mode."""
        if event.key() == Qt.Key.Key_Escape:
            self.list_widget.clearSelection()
            event.accept()
            return
        super().keyPressEvent(event)

    def _on_delete(self):
        if self._current_index < 0:
            return  # button should be disabled — defensive
        chars = self.dm.list_main_characters()
        if not (0 <= self._current_index < len(chars)):
            return
        c = chars[self._current_index]
        name = (c.get("firstName", "") + " " + c.get("lastName", "")).strip()
        if confirm_delete(self.panel, "ยืนยันการลบ",
                          f"ต้องการลบตัวละคร  '{name}'  ใช่หรือไม่?\n\n"
                          f"การลบนี้จะนำข้อมูลทั้งหมดของตัวละคร "
                          f"รวมถึงน้ำเสียง / บุคลิก ออกจากฐานข้อมูล"):
            self.dm.delete_main_character(self._current_index)
            self.refresh(self._current_filter)
            self.panel.autosave()  # auto-persist

    def _on_primary(self):
        entry = {
            "firstName": self.in_first.text().strip(),
            "lastName": self.in_last.text().strip(),
            "gender": getattr(self, "_current_gender", "Neutral"),
            "role": self.in_role.text().strip(),
            "relationship": self.in_rel.currentText().strip() or "Neutral",
        }
        if not entry["firstName"]:
            return  # button should be disabled — defensive
        if self._current_index < 0:
            # Add
            ok = self.dm.add_main_character(entry)
            if not ok:
                QMessageBox.warning(self, "ซ้ำ",
                    f"มี '{entry['firstName']} {entry['lastName']}'.strip() อยู่แล้ว")
                return
        else:
            self.dm.update_main_character(self._current_index, entry)
        # Persist personality to character_roles (separate dict in npc.json) —
        # use firstName as the key, drop entry if textarea is empty.
        personality = self.in_personality.toPlainText().strip()
        first = entry["firstName"]
        if personality:
            self.dm.set_character_role(first, personality)
        else:
            # Empty → remove any existing entry to keep dict tidy
            self.dm.delete_character_role(first)
        self.refresh(self._current_filter)
        self.panel.autosave()  # auto-persist

    def _update_primary_enabled(self):
        """ADD/UPDATE button enable rules:
        - ADD mode (no selection): enabled when firstName has text
        - UPDATE mode (selection): enabled only when form values DIFFER from snapshot
        """
        has_first = bool(self.in_first.text().strip())
        if not has_first:
            self.btn_primary.setEnabled(False)
        elif self._current_index < 0 or self._snapshot is None:
            # ADD mode
            self.btn_primary.setEnabled(True)
        else:
            # UPDATE mode — compare current form vs snapshot
            current = {
                "firstName": self.in_first.text().strip(),
                "lastName": self.in_last.text().strip(),
                "gender": getattr(self, "_current_gender", "Neutral"),
                "role": self.in_role.text().strip(),
                "relationship": self.in_rel.currentText().strip() or "Neutral",
                "personality": self.in_personality.toPlainText().strip(),
            }
            self.btn_primary.setEnabled(current != self._snapshot)
        # Update avatar placeholder to first letter of typed name
        if hasattr(self, "avatar"):
            self.avatar.set_placeholder(self.in_first.text().strip())


    # ─── Image handling ───
    def _refresh_avatar(self):
        """Sync avatar widget with current selection's image."""
        if self._current_index < 0:
            self.avatar.set_image(None)
            self.avatar.set_placeholder(self.in_first.text().strip())
            return
        path = self.dm.get_main_character_image_path(self._current_index)
        self.avatar.set_image(path)

    # ── Hover menu (file picker / screenshot) — POLLING-based ──
    # Why polling: a Qt.WindowType.Popup grabs mouse focus on show, which
    # makes the underlying widget (the avatar) receive an immediate leaveEvent.
    # Event-driven show/hide therefore loops (show → leave → grace-close →
    # cursor "re-enters" → show ...), causing visible flicker. The poll just
    # asks "is the cursor over avatar OR menu right now?" every 80ms.
    HOVER_GRACE_S = 0.18  # cursor must be off both targets this long to close

    def _poll_avatar_hover(self):
        """Show menu if cursor is on avatar or on the menu; close after a
        short grace if it's left both. Skips work when no character selected
        OR when this tab is not the currently-visible tab (panel hidden during
        screenshot, user on NPCS/LORE, etc.). Suppressed briefly after a
        screenshot restore so the menu doesn't pop over the re-opened Polaroid."""
        try:
            now = time.time()
            # Hibernate when panel isn't visible (during screenshot, minimized,
            # closed). 80ms × 12.5Hz × 3600s = ~450k pointless calls/hour if we
            # didn't skip these — measurable CPU on idle.
            if not self.isVisible() or not self.panel.isVisible():
                if self._hover_menu is not None and self._hover_menu.isVisible():
                    self._hover_menu.close()
                self.avatar.set_force_hover(False)
                return
            # Skip during post-screenshot restore grace
            if now < self._hover_poll_suppress_until:
                return
            if self._current_index < 0:
                # No character selected → ensure menu is hidden + clear forced hover
                self.avatar.set_force_hover(False)
                if self._hover_menu is not None and self._hover_menu.isVisible():
                    self._hover_menu.close()
                return
            cursor_global = QCursor.pos()
            in_avatar = self._global_in_widget(cursor_global, self.avatar)
            in_menu = (
                self._hover_menu is not None
                and self._hover_menu.isVisible()
                and self._global_in_widget(cursor_global, self._hover_menu)
            )

            if in_avatar or in_menu:
                # Inside one of the targets — show menu (idempotent), reset grace,
                # and force the avatar's accent border ON (Qt's leaveEvent fires
                # spuriously when the popup grabs focus).
                self._hover_outside_since = 0.0
                if self._hover_menu is None:
                    self._build_hover_menu()
                if not self._hover_menu.isVisible():
                    self._hover_menu.show_beside(self.avatar)
                self.avatar.set_force_hover(True)
                return

            # Outside both — start grace timer (one-shot)
            if self._hover_menu is None or not self._hover_menu.isVisible():
                self.avatar.set_force_hover(False)
                return
            if self._hover_outside_since == 0.0:
                self._hover_outside_since = now
            elif now - self._hover_outside_since >= self.HOVER_GRACE_S:
                self._hover_menu.close()
                self._hover_outside_since = 0.0
                self.avatar.set_force_hover(False)
        except Exception as e:
            log.debug(f"[hover-poll] {e}")

    @staticmethod
    def _global_in_widget(global_pt: QPoint, widget: Optional[QWidget]) -> bool:
        if widget is None or not widget.isVisible():
            return False
        try:
            local = widget.mapFromGlobal(global_pt)
            return widget.rect().contains(local)
        except Exception:
            return False

    def _build_hover_menu(self):
        """Lazy-create the hover menu + apply current theme palette."""
        self._hover_menu = _AvatarHoverMenu(self)
        self._hover_menu.pick_image_requested.connect(self._on_change_image)
        self._hover_menu.screenshot_requested.connect(self._on_screenshot_avatar)
        try:
            accent = self.panel.am.get_accent_color()
            pal = self.panel.am.get_palette() if hasattr(self.panel.am, "get_palette") else {}
            self._hover_menu.set_palette(
                accent=accent,
                bg=pal.get("btn_bg", "#161b22"),
                bg2=pal.get("bg_titlebar", pal.get("btn_bg", "#1c2128")),
                text=pal.get("text", "#e6edf3"),
                text_dim=pal.get("text_dim", "#7d8590"),
            )
        except Exception as e:
            log.debug(f"[hover-menu] palette pull skipped: {e}")

    def _on_screenshot_avatar(self):
        """Hide panel → fullscreen crop overlay → save cropped pixmap as
        the selected character's avatar via the existing image pipeline.

        Multi-monitor: pick the screen the NPC Manager is CURRENTLY on (so
        the user gets the screen they're looking at, typically same as the
        game). Falls back to primary if detection fails."""
        if self._current_index < 0:
            return
        try:
            from pyqt_ui.screenshot_tool import ScreenshotCropOverlay  # noqa: F401
        except Exception as e:
            QMessageBox.warning(self, "Screenshot tool",
                f"ไม่สามารถโหลด screenshot tool: {e}")
            return

        char_name = self.in_first.text().strip() or "?"

        # Pick target screen BEFORE hide — `panel.mapToGlobal` is only
        # accurate while shown. screenAt returns the QScreen at a global point.
        target_screen = None
        try:
            from PyQt6.QtGui import QGuiApplication
            center_local = QPoint(self.panel.width() // 2, self.panel.height() // 2)
            center_global = self.panel.mapToGlobal(center_local)
            target_screen = QGuiApplication.screenAt(center_global)
        except Exception as e:
            log.debug(f"[screenshot] screenAt failed, will fallback to primary: {e}")
        if target_screen is None:
            target_screen = QApplication.primaryScreen()

        # Hide NPC Manager temporarily so it doesn't appear in the snapshot.
        # processEvents to make the hide actually paint before grabWindow.
        self.panel.hide()
        QApplication.processEvents()
        # Tiny extra settle so the window is gone before screen capture
        QTimer.singleShot(
            120,
            lambda: self._launch_screenshot_overlay(char_name, target_screen),
        )

    def _launch_screenshot_overlay(self, char_name: str, target_screen=None):
        from pyqt_ui.screenshot_tool import ScreenshotCropOverlay
        # Capture the chosen screen (user's actual monitor, not always primary)
        try:
            screen = target_screen or QApplication.primaryScreen()
            full_pix = screen.grabWindow(0)
        except Exception as e:
            self.panel.show()
            QMessageBox.warning(self, "Screenshot",
                f"จับภาพหน้าจอไม่ได้: {e}")
            return

        try:
            accent = self.panel.am.get_accent_color()
        except Exception:
            accent = "#00d4ff"

        # Construct overlay — guard against constructor exceptions (e.g.,
        # primaryScreen() returns None on a locked session). Without this,
        # panel.hide() above succeeded but panel never gets restored → stuck.
        try:
            overlay = ScreenshotCropOverlay(
                full_pix, char_name, accent_hex="#00d4ff",
                target_screen=screen,
            )
        except Exception as e:
            log.error(f"[screenshot] overlay construct failed: {e}")
            self.panel.show()
            self.panel.raise_()
            self.panel.activateWindow()
            QMessageBox.warning(self, "Screenshot",
                f"สร้าง overlay ไม่สำเร็จ: {e}")
            return
        # WA_DeleteOnClose: drop the captured ~10MB QPixmap as soon as the
        # overlay closes (instead of waiting for GC + Python ref drop). Repeated
        # screenshots otherwise accumulate the background pixmap in memory.
        overlay.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        overlay.crop_confirmed.connect(self._on_screenshot_cropped)
        overlay.crop_cancelled.connect(self._on_screenshot_cancelled)
        # Hold a reference so it isn't garbage-collected
        self._active_screenshot_overlay = overlay
        overlay.show()
        overlay.raise_()
        overlay.activateWindow()

    def _on_screenshot_cropped(self, cropped_pixmap: QPixmap):
        """Got the cropped region — save via existing pipeline + restore panel."""
        try:
            import tempfile
            tmp_path = os.path.join(
                tempfile.gettempdir(),
                f"mbb_avatar_shot_{int(__import__('time').time())}.png",
            )
            ok = cropped_pixmap.save(tmp_path, "PNG")
            if not ok:
                raise RuntimeError("QPixmap.save returned False")
            filename = self.dm.set_main_character_image(self._current_index, tmp_path)
            if not filename:
                raise RuntimeError("set_main_character_image returned empty")
            try:
                os.remove(tmp_path)
            except Exception as _rm_err:
                # Most common: AV scanner holding the file open briefly. Not
                # fatal — Windows clears %TEMP% periodically. Log so we can
                # spot a real leak in the field if it accumulates.
                log.debug(f"[screenshot] tmp cleanup failed: {_rm_err}")
            self._refresh_avatar()
            self.panel.autosave()
            self._update_current_row_badge()
            # Restore panel + show Polaroid with the new shot
            self.panel.show()
            self.panel.raise_()
            self.panel.activateWindow()
            # Suppress hover-poll for 400ms so the menu doesn't re-pop on top
            # of the Polaroid the moment the panel is back (cursor is likely
            # still over the avatar's logical position).
            self._hover_poll_suppress_until = time.time() + 0.4
            QTimer.singleShot(120, self._on_avatar_clicked)
        except Exception as e:
            self.panel.show()
            QMessageBox.warning(self, "Screenshot save",
                f"บันทึก screenshot ไม่สำเร็จ: {e}")
        finally:
            self._active_screenshot_overlay = None

    def _on_screenshot_cancelled(self):
        """User pressed ESC or clicked cancel — just bring NPC Manager back."""
        try:
            self.panel.show()
            self.panel.raise_()
            self.panel.activateWindow()
            # Same grace as the confirmed path — cursor may still be on avatar
            self._hover_poll_suppress_until = time.time() + 0.4
        finally:
            self._active_screenshot_overlay = None

    def _on_avatar_clicked(self):
        """Avatar click — UX:
        - No image yet → skip Polaroid, go straight to file picker (faster path
          for the common "I want to add a photo" intent).
        - Has image → open Polaroid for viewing + change/delete actions."""
        if self._current_index < 0:
            QMessageBox.information(self, "เลือกตัวละครก่อน",
                "ต้องเลือกตัวละครจากลิสต์ก่อน หรือเพิ่มตัวละครใหม่ + บันทึกครั้งหนึ่ง")
            return
        img_path = self.dm.get_main_character_image_path(self._current_index)
        has_image = bool(img_path and os.path.exists(img_path))
        if not has_image:
            # Empty avatar → file picker directly (no need to show empty Polaroid)
            self._on_change_image()
            return
        if self._polaroid is None:
            self._polaroid = PolaroidOverlay(self)
            self._polaroid.change_requested.connect(self._on_change_image)
            self._polaroid.delete_requested.connect(self._on_remove_image)
        # Pass file path → Polaroid loads fresh QPixmap at full resolution from disk
        # (instead of the cached small pixmap from the avatar widget).
        name = self.in_first.text().strip() or "?"
        self._polaroid.show_for(
            image_path=img_path,
            name=name,
            has_image=True,
        )

    def _last_avatar_dir(self) -> str:
        """Read remembered directory for the file picker (per-user, persisted)."""
        try:
            from PyQt6.QtCore import QSettings
            qs = QSettings("MBB", "NPCManager")
            return qs.value("avatar_last_dir", "", type=str) or ""
        except Exception:
            return ""

    def _save_last_avatar_dir(self, path: str):
        """Persist the directory of the last picked file."""
        try:
            from PyQt6.QtCore import QSettings
            qs = QSettings("MBB", "NPCManager")
            qs.setValue("avatar_last_dir", os.path.dirname(path))
        except Exception:
            pass

    def _on_change_image(self):
        """Open file picker → optimize → save → update entry. Auto-saves to disk.
        After a successful upload, re-open the Polaroid so the user immediately
        sees the new photo (better feedback than just refreshing the small avatar)."""
        from PyQt6.QtWidgets import QFileDialog
        if self._current_index < 0:
            return
        # Hide polaroid while picker is up so it doesn't sit behind a modal dialog
        if self._polaroid is not None and self._polaroid.isVisible():
            self._polaroid.hide()
        src, _ = QFileDialog.getOpenFileName(
            self, "เลือกรูปภาพตัวละคร", self._last_avatar_dir(),
            "Image Files (*.png *.jpg *.jpeg *.webp *.bmp *.gif *.tiff)"
        )
        if not src:
            return
        self._save_last_avatar_dir(src)
        filename = self.dm.set_main_character_image(self._current_index, src)
        if not filename:
            QMessageBox.warning(self, "Error", "ไม่สามารถ optimize/บันทึกรูปได้")
            return
        self._refresh_avatar()
        self.panel.autosave()
        # Update the avatar badge on the current row in-place (no full refresh,
        # which would clear selection). Looks instant to the user.
        self._update_current_row_badge()
        # Show the Polaroid with the new image so the user sees the result
        self._on_avatar_clicked()

    def _update_current_row_badge(self):
        """Refresh just the column-0 icon for the currently-selected row, so
        the avatar badge appears/disappears immediately after upload/delete
        without a full list refresh (which would clear selection)."""
        items = self.list_widget.selectedItems()
        if not items:
            return
        try:
            accent = self.panel.am.get_accent_color()
        except Exception:
            accent = "#58a6ff"
        c = self.dm.list_main_characters()[self._current_index] \
            if 0 <= self._current_index < len(self.dm.list_main_characters()) else {}
        if c.get("image"):
            items[0].setIcon(0, _make_avatar_badge_icon(accent, size=22))
        else:
            items[0].setIcon(0, _make_empty_badge_icon(size=22))

    def _on_remove_image(self):
        if self._current_index < 0:
            return
        # Hide polaroid before showing confirm dialog
        if self._polaroid is not None and self._polaroid.isVisible():
            self._polaroid.hide()
        if confirm_delete(self.panel, "ยืนยันการลบรูป",
                          "ต้องการลบรูปภาพของตัวละครนี้ใช่หรือไม่?"):
            self.dm.remove_main_character_image(self._current_index)
            self._refresh_avatar()
            self._update_current_row_badge()
            self.panel.autosave()

    def _reset_form(self):
        self._snapshot = None  # leaving UPDATE mode → no snapshot
        self.in_first.clear()
        self.in_last.clear()
        self.in_role.clear()
        self.in_rel.setCurrentText("Neutral")
        self._set_gender("Neutral")
        if hasattr(self, "in_personality"):
            self.in_personality.clear()
            # Reset to 2-line minimum height after clear
            self.in_personality.setFixedHeight(self._personality_min_height)
        self.btn_primary.setText("ADD ENTRY")
        self._update_primary_enabled()
        if hasattr(self, "btn_delete") and self.btn_delete:
            self.btn_delete.setEnabled(False)
        if hasattr(self, "avatar"):
            self.avatar.set_image(None)
            self.avatar.set_placeholder("?")


# ────────────────────────────────────────────────────────────────────
# NPCsTab — list of {name, role, description}
# ────────────────────────────────────────────────────────────────────
class NPCsTab(QWidget):
    """Generic NPC list (npcs section in npc.json)."""
    def __init__(self, panel: NPCManagerPanel):
        super().__init__()
        self.panel = panel
        self.dm = panel.dm
        self._current_index = -1
        self._current_filter = ""
        self._snapshot = None  # change-detection for UPDATE mode
        self._build()

    def _build(self):
        outer = QHBoxLayout(self)
        outer.setContentsMargins(16, 4, 16, 10)
        outer.setSpacing(14)

        # ── Left: list (QTreeWidget) ──
        left = QVBoxLayout(); left.setSpacing(4)
        left.addLayout(_build_list_header("NAME", "ROLE"))
        self.list_widget = _make_tree(["NAME", "ROLE"])
        self.list_widget.itemSelectionChanged.connect(self._on_list_selection)
        self.list_widget.setMinimumWidth(380)
        left.addWidget(self.list_widget, stretch=1)
        outer.addLayout(left, stretch=3)

        # ── Right: details ──
        details = QWidget(); details.setObjectName("npc_details")
        d = QVBoxLayout(details); d.setContentsMargins(22, 20, 22, 20); d.setSpacing(12)

        title = QLabel("NPCs Details")
        title.setObjectName("npc_details_title")
        title.setFont(QFont(FONT_PRIMARY, 14, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        d.addWidget(title); d.addSpacing(8)

        # Name
        d.addWidget(self._field_label("Name:"))
        self.in_name = QLineEdit()
        self.in_name.setProperty("class", "npc_field")
        self.in_name.setPlaceholderText("ชื่อ NPC")
        self.in_name.setMinimumHeight(36)
        self.in_name.setFont(QFont(FONT_PRIMARY, 11))
        self.in_name.textChanged.connect(self._update_primary_enabled)
        d.addWidget(self.in_name)

        # Role
        d.addWidget(self._field_label("Role:"))
        self.in_role = QLineEdit()
        self.in_role.setProperty("class", "npc_field")
        self.in_role.setPlaceholderText("เช่น Hrothgar, Hunter, Merchant")
        self.in_role.setMinimumHeight(36)
        self.in_role.setFont(QFont(FONT_PRIMARY, 11))
        self.in_role.textChanged.connect(self._update_primary_enabled)
        d.addWidget(self.in_role)

        # Description (multi-line)
        d.addWidget(self._field_label("Description:"))
        self.in_desc = QTextEdit()
        self.in_desc.setProperty("class", "npc_textarea")
        self.in_desc.setPlaceholderText("คำอธิบาย NPC")
        self.in_desc.setFont(QFont(FONT_PRIMARY, 11))
        self.in_desc.textChanged.connect(self._update_primary_enabled)
        d.addWidget(self.in_desc, stretch=1)

        d.addSpacing(8)

        self.btn_primary = QPushButton("ADD ENTRY")
        self.btn_primary.setProperty("class", "npc_primary")
        self.btn_primary.setMinimumHeight(46)
        self.btn_primary.setFont(QFont(FONT_PRIMARY, 12, QFont.Weight.Bold))
        self.btn_primary.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_primary.setEnabled(False)
        self.btn_primary.clicked.connect(self._on_primary)
        d.addWidget(self.btn_primary)

        delete_row = QHBoxLayout()
        delete_row.setContentsMargins(0, 4, 0, 0)
        delete_row.addStretch(1)
        self.btn_delete = QPushButton("Delete entry")
        self.btn_delete.setProperty("class", "npc_danger")
        self.btn_delete.setMinimumHeight(28)
        self.btn_delete.setFont(QFont(FONT_PRIMARY, 9))
        self.btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_delete.setEnabled(False)
        self.btn_delete.clicked.connect(self._on_delete)
        delete_row.addWidget(self.btn_delete)
        d.addLayout(delete_row)

        outer.addWidget(details, stretch=2)

    def _field_label(self, text: str) -> QLabel:
        lbl = QLabel(text); lbl.setProperty("class", "npc_field_label")
        lbl.setFont(QFont(FONT_PRIMARY, 11)); return lbl

    def refresh(self, search_query: str = ""):
        self._current_filter = search_query
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        results = self.dm.search(search_query, "npcs")
        for i, n in enumerate(self.dm.list_npcs()):
            if n not in results: continue
            self.list_widget.addTopLevelItem(_new_row(
                [n.get("name", ""), n.get("role", "")], payload=i))
        self.list_widget.blockSignals(False)
        self._current_index = -1
        self._reset_form()

    def row_count(self) -> int:
        return self.list_widget.topLevelItemCount()

    def _on_list_selection(self):
        items = self.list_widget.selectedItems()
        if not items:
            self._current_index = -1
            self._snapshot = None
            self._reset_form()
            self.btn_delete.setEnabled(False)
            return
        idx = items[0].data(0, Qt.ItemDataRole.UserRole)
        npcs = self.dm.list_npcs()
        if 0 <= idx < len(npcs):
            self._current_index = idx
            n = npcs[idx]
            # Snapshot stored values for change detection
            self._snapshot = {
                "name": n.get("name", ""),
                "role": n.get("role", ""),
                "description": n.get("description", ""),
            }
            self.in_name.setText(n.get("name", ""))
            self.in_role.setText(n.get("role", ""))
            self.in_desc.setPlainText(n.get("description", ""))
            self.btn_primary.setText("UPDATE ENTRY")
            self.btn_delete.setEnabled(True)
            self._update_primary_enabled()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.list_widget.clearSelection()
            event.accept(); return
        super().keyPressEvent(event)

    def _on_delete(self):
        if self._current_index < 0: return
        npcs = self.dm.list_npcs()
        if not (0 <= self._current_index < len(npcs)): return
        name = npcs[self._current_index].get("name", "")
        if confirm_delete(self.panel, "ยืนยันการลบ",
                          f"ต้องการลบ NPC  '{name}'  ใช่หรือไม่?"):
            self.dm.delete_npc(self._current_index)
            self.refresh(self._current_filter)
            self.panel.autosave()

    def _on_primary(self):
        entry = {
            "name": self.in_name.text().strip(),
            "role": self.in_role.text().strip(),
            "description": self.in_desc.toPlainText().strip(),
        }
        if not entry["name"]: return
        if self._current_index < 0:
            ok = self.dm.add_npc(entry)
            if not ok:
                QMessageBox.warning(self, "ซ้ำ", f"มี NPC ชื่อ '{entry['name']}' อยู่แล้ว")
                return
        else:
            self.dm.update_npc(self._current_index, entry)
        self.refresh(self._current_filter)
        self.panel.autosave()

    def _update_primary_enabled(self):
        """ADD: enabled when name not empty. UPDATE: enabled only when changed."""
        has_name = bool(self.in_name.text().strip())
        if not has_name:
            self.btn_primary.setEnabled(False)
        elif self._current_index < 0 or self._snapshot is None:
            self.btn_primary.setEnabled(True)
        else:
            current = {
                "name": self.in_name.text().strip(),
                "role": self.in_role.text().strip(),
                "description": self.in_desc.toPlainText().strip(),
            }
            self.btn_primary.setEnabled(current != self._snapshot)

    def _reset_form(self):
        self._snapshot = None
        self.in_name.clear(); self.in_role.clear(); self.in_desc.clear()
        self.btn_primary.setText("ADD ENTRY")
        self._update_primary_enabled()
        if hasattr(self, "btn_delete"): self.btn_delete.setEnabled(False)


# ────────────────────────────────────────────────────────────────────
# DictTabBase — shared base for dict-style tabs (Lore, Roles, Word Fixes)
# Layout: list of keys on left, key + value editor on right
# ────────────────────────────────────────────────────────────────────
class DictTabBase(QWidget):
    SECTION = ""           # 'lore' | 'roles' | 'fixes'
    DETAILS_TITLE = ""     # right panel title
    KEY_LABEL = "Key:"
    KEY_PLACEHOLDER = ""
    VALUE_LABEL = "Value:"
    VALUE_PLACEHOLDER = ""
    VALUE_MULTILINE = True
    LIST_HEADER_KEY = "TERM"
    LIST_HEADER_VAL = "DEFINITION"

    # Data font size — applied to list rows + right-side details (key/value/labels).
    # Default 18 (1.5x previous 11pt) for readability. User adjusts via panel +/-.
    DATA_FONT_DEFAULT = 18
    DATA_FONT_MIN = 11
    DATA_FONT_MAX = 28

    def __init__(self, panel: NPCManagerPanel):
        super().__init__()
        self.panel = panel
        self.dm = panel.dm
        self._current_key = None  # None = ADD mode, str = EDIT mode
        self._current_filter = ""
        self._snapshot = None     # change-detection for UPDATE mode
        self._data_font_size = self.DATA_FONT_DEFAULT
        self._build()

    # ─── Subclass hooks ───
    def _list_items(self):
        """Return list of (key, value) tuples to display."""
        if self.SECTION == "lore": return self.dm.list_lore()
        if self.SECTION == "roles": return self.dm.list_character_roles()
        if self.SECTION == "fixes": return self.dm.list_word_fixes()
        return []

    def _search_items(self, query):
        return self.dm.search(query, self.SECTION)

    def _set_value(self, key, value) -> bool:
        if self.SECTION == "lore": return self.dm.set_lore(key, value)
        if self.SECTION == "roles": return self.dm.set_character_role(key, value)
        if self.SECTION == "fixes": return self.dm.set_word_fix(key, value)
        return False

    def _delete_value(self, key) -> bool:
        if self.SECTION == "lore": return self.dm.delete_lore(key)
        if self.SECTION == "roles": return self.dm.delete_character_role(key)
        if self.SECTION == "fixes": return self.dm.delete_word_fix(key)
        return False

    # ─── Build ───
    def _build(self):
        outer = QHBoxLayout(self)
        outer.setContentsMargins(16, 4, 16, 10)
        outer.setSpacing(14)

        data_font = QFont(FONT_PRIMARY, self._data_font_size)
        # Inline font-size override — panel QSS sets font-size: 11pt on the
        # input classes which would otherwise win against setFont() at startup.
        input_font_qss = f"font-size: {self._data_font_size}pt;"

        # Left: list (QTreeWidget)
        left = QVBoxLayout(); left.setSpacing(4)
        left.addLayout(_build_list_header(self.LIST_HEADER_KEY, self.LIST_HEADER_VAL))
        self.list_widget = _make_tree([self.LIST_HEADER_KEY, self.LIST_HEADER_VAL])
        self.list_widget.itemSelectionChanged.connect(self._on_list_selection)
        self.list_widget.setMinimumWidth(380)
        self.list_widget.setFont(data_font)  # rows scale with data font
        left.addWidget(self.list_widget, stretch=1)
        outer.addLayout(left, stretch=3)

        # Right: form
        details = QWidget(); details.setObjectName("npc_details")
        d = QVBoxLayout(details); d.setContentsMargins(22, 20, 22, 20); d.setSpacing(12)

        title = QLabel(self.DETAILS_TITLE)
        title.setObjectName("npc_details_title")
        title.setFont(QFont(FONT_PRIMARY, 14, QFont.Weight.Bold))
        title.setStyleSheet("background: transparent;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        d.addWidget(title); d.addSpacing(8)

        # Key
        d.addWidget(self._field_label(self.KEY_LABEL))
        self.in_key = QLineEdit()
        self.in_key.setProperty("class", "npc_field")
        self.in_key.setPlaceholderText(self.KEY_PLACEHOLDER)
        self.in_key.setMinimumHeight(36)
        self.in_key.setFont(data_font)
        self.in_key.setStyleSheet(input_font_qss)
        self.in_key.textChanged.connect(self._update_primary_enabled)
        d.addWidget(self.in_key)

        # Value (multi-line QTextEdit or single-line QLineEdit per VALUE_MULTILINE)
        d.addWidget(self._field_label(self.VALUE_LABEL))
        if self.VALUE_MULTILINE:
            self.in_value = QTextEdit()
            self.in_value.setProperty("class", "npc_textarea")
            self.in_value.setPlaceholderText(self.VALUE_PLACEHOLDER)
            self.in_value.setFont(data_font)
            self.in_value.setStyleSheet(input_font_qss)
            self.in_value.textChanged.connect(self._update_primary_enabled)
            d.addWidget(self.in_value, stretch=1)
        else:
            self.in_value = QLineEdit()
            self.in_value.setProperty("class", "npc_field")
            self.in_value.setPlaceholderText(self.VALUE_PLACEHOLDER)
            self.in_value.setMinimumHeight(36)
            self.in_value.setFont(data_font)
            self.in_value.setStyleSheet(input_font_qss)
            self.in_value.textChanged.connect(self._update_primary_enabled)
            d.addWidget(self.in_value)
            d.addStretch(1)

        d.addSpacing(8)

        self.btn_primary = QPushButton("ADD ENTRY")
        self.btn_primary.setProperty("class", "npc_primary")
        self.btn_primary.setMinimumHeight(46)
        self.btn_primary.setFont(QFont(FONT_PRIMARY, 12, QFont.Weight.Bold))
        self.btn_primary.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_primary.setEnabled(False)
        self.btn_primary.clicked.connect(self._on_primary)
        d.addWidget(self.btn_primary)

        delete_row = QHBoxLayout(); delete_row.setContentsMargins(0, 4, 0, 0)
        delete_row.addStretch(1)
        self.btn_delete = QPushButton("Delete entry")
        self.btn_delete.setProperty("class", "npc_danger")
        self.btn_delete.setMinimumHeight(28)
        self.btn_delete.setFont(QFont(FONT_PRIMARY, 9))
        self.btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_delete.setEnabled(False)
        self.btn_delete.clicked.connect(self._on_delete)
        delete_row.addWidget(self.btn_delete)
        d.addLayout(delete_row)

        outer.addWidget(details, stretch=2)

    def _field_label(self, text):
        # Labels (Term:/Definition:) stay at fixed 11pt — they're chrome, not data.
        lbl = QLabel(text); lbl.setProperty("class", "npc_field_label")
        lbl.setFont(QFont(FONT_PRIMARY, 11))
        return lbl

    # ─── Data-font scaling (list rows + right-side INPUT fields only — not labels) ───
    def set_data_font_size(self, size: int):
        """Apply font size to data the user reads/edits: list rows + Term/Definition
        text inputs. Labels (Term:/Definition:) intentionally stay fixed.

        IMPORTANT: panel-level QSS forces ``font-size: 11pt`` on QLineEdit.npc_field
        and QTextEdit.npc_textarea, which silently overrides setFont() (see
        memory: PyQt6 + Tkinter hybrid gotchas). Use widget-local setStyleSheet
        instead — inline rules win against parent QSS.
        """
        size = max(self.DATA_FONT_MIN, min(self.DATA_FONT_MAX, int(size)))
        if size == self._data_font_size:
            return
        self._data_font_size = size
        f = QFont(FONT_PRIMARY, size)
        # List widget — no QSS class rule, setFont works
        if hasattr(self, "list_widget") and self.list_widget:
            self.list_widget.setFont(f)
        # Input fields — use setStyleSheet to win against the panel's class QSS
        if hasattr(self, "in_key") and self.in_key:
            self.in_key.setFont(f)
            self.in_key.setStyleSheet(f"font-size: {size}pt;")
        if hasattr(self, "in_value") and self.in_value:
            self.in_value.setFont(f)
            self.in_value.setStyleSheet(f"font-size: {size}pt;")

    def inc_data_font_size(self):
        self.set_data_font_size(self._data_font_size + 1)

    def dec_data_font_size(self):
        self.set_data_font_size(self._data_font_size - 1)

    def get_data_font_size(self) -> int:
        return self._data_font_size

    def refresh(self, search_query: str = ""):
        self._current_filter = search_query
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        results = self._search_items(search_query)
        for k, v in results:
            preview = (v[:60] + "…") if len(v) > 60 else v
            self.list_widget.addTopLevelItem(_new_row([k, preview], payload=k))
        self.list_widget.blockSignals(False)
        self._current_key = None
        self._reset_form()

    def row_count(self) -> int:
        return self.list_widget.topLevelItemCount()

    def _on_list_selection(self):
        items = self.list_widget.selectedItems()
        if not items:
            self._current_key = None
            self._snapshot = None
            self._reset_form()
            self.btn_delete.setEnabled(False)
            return
        key = items[0].data(0, Qt.ItemDataRole.UserRole)
        # Find value
        value = ""
        for k, v in self._list_items():
            if k == key:
                value = v
                break
        self._current_key = key
        # Snapshot for change detection
        self._snapshot = {"key": key, "value": value}
        self.in_key.setText(key)
        if isinstance(self.in_value, QTextEdit):
            self.in_value.setPlainText(value)
        else:
            self.in_value.setText(value)
        self.btn_primary.setText("UPDATE ENTRY")
        self.btn_delete.setEnabled(True)
        # After populating, button should be DISABLED until something changes
        self._update_primary_enabled()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.list_widget.clearSelection()
            event.accept(); return
        super().keyPressEvent(event)

    def _on_delete(self):
        if not self._current_key: return
        if confirm_delete(self.panel, "ยืนยันการลบ",
                          f"ต้องการลบ  '{self._current_key}'  ใช่หรือไม่?"):
            self._delete_value(self._current_key)
            self.refresh(self._current_filter)
            self.panel.autosave()

    def _on_primary(self):
        new_key = self.in_key.text().strip()
        if isinstance(self.in_value, QTextEdit):
            new_value = self.in_value.toPlainText().strip()
        else:
            new_value = self.in_value.text().strip()
        if not new_key: return
        # If editing AND key changed → delete old key first
        if self._current_key and self._current_key != new_key:
            self._delete_value(self._current_key)
        ok = self._set_value(new_key, new_value)
        if not ok:
            QMessageBox.warning(self, "บันทึกไม่ได้",
                f"ไม่สามารถเพิ่ม '{new_key}' ได้ (สั้นเกินไป หรือไม่ถูกต้อง)")
            return
        self.refresh(self._current_filter)
        self.panel.autosave()

    def _update_primary_enabled(self):
        """ADD: enabled when key not empty. UPDATE: enabled only when changed."""
        has_key = bool(self.in_key.text().strip())
        if not has_key:
            self.btn_primary.setEnabled(False)
        elif self._current_key is None or self._snapshot is None:
            self.btn_primary.setEnabled(True)
        else:
            current_value = (self.in_value.toPlainText().strip()
                             if isinstance(self.in_value, QTextEdit)
                             else self.in_value.text().strip())
            current = {"key": self.in_key.text().strip(), "value": current_value}
            self.btn_primary.setEnabled(current != self._snapshot)

    def _reset_form(self):
        self._snapshot = None
        self.in_key.clear()
        if isinstance(self.in_value, QTextEdit):
            self.in_value.clear()
        else:
            self.in_value.clear()
        self.btn_primary.setText("ADD ENTRY")
        self._update_primary_enabled()
        if hasattr(self, "btn_delete"): self.btn_delete.setEnabled(False)

    # ─── Public API for cross-tab navigation ───
    def open_with_key(self, key: str):
        """Filter list by key, auto-select if exists, otherwise pre-fill key field
        for a quick add. Called e.g. from MainCharactersTab 'บุคลิก' button."""
        if not key:
            return
        # Set search input on the panel — will trigger refresh
        if self.panel._search_input:
            self.panel._search_input.setText(key)
        # Look for exact match (case-insensitive)
        kl = key.strip().lower()
        match = None
        for k, _ in self._list_items():
            if k.strip().lower() == kl:
                match = k
                break
        if match:
            # Select the matching row in the tree
            for row in range(self.list_widget.topLevelItemCount()):
                item = self.list_widget.topLevelItem(row)
                if item.data(0, Qt.ItemDataRole.UserRole) == match:
                    self.list_widget.setCurrentItem(item)
                    self.list_widget.scrollToItem(item)
                    break
        else:
            # Pre-fill key field for quick add
            self.list_widget.clearSelection()
            self._reset_form()
            self.in_key.setText(key)
            if isinstance(self.in_value, QTextEdit):
                self.in_value.setFocus()
            else:
                self.in_value.setFocus()


class LoreTab(DictTabBase):
    SECTION = "lore"
    DETAILS_TITLE = "Lore Details"
    KEY_LABEL = "Term:"
    KEY_PLACEHOLDER = "เช่น Scions, Eorzea, Garlemald"
    VALUE_LABEL = "Definition:"
    VALUE_PLACEHOLDER = "คำอธิบายของศัพท์ในโลก"
    VALUE_MULTILINE = True
    LIST_HEADER_KEY = "TERM"
    LIST_HEADER_VAL = "DEFINITION"


class RolesTab(DictTabBase):
    SECTION = "roles"
    DETAILS_TITLE = "Character Roles"
    KEY_LABEL = "Name:"
    KEY_PLACEHOLDER = "ชื่อตัวละคร"
    VALUE_LABEL = "Role / Speaking Style:"
    VALUE_PLACEHOLDER = "สไตล์การพูดของตัวละคร"
    VALUE_MULTILINE = True
    LIST_HEADER_KEY = "NAME"
    LIST_HEADER_VAL = "ROLE"


class WordFixesTab(DictTabBase):
    SECTION = "fixes"
    DETAILS_TITLE = "Word Fixes"
    KEY_LABEL = "Wrong (≥ 2 chars):"
    KEY_PLACEHOLDER = "คำผิดที่พบจาก Gemini (อย่างน้อย 2 ตัวอักษร)"
    VALUE_LABEL = "Replace with:"
    VALUE_PLACEHOLDER = "คำที่ถูกต้อง"
    VALUE_MULTILINE = False  # single-line for fixes
    LIST_HEADER_KEY = "WRONG"
    LIST_HEADER_VAL = "→ CORRECT"


# ────────────────────────────────────────────────────────────────────
# Placeholder for tabs not yet built (Phase 2-4)
# ────────────────────────────────────────────────────────────────────
class _PlaceholderTab(QWidget):
    def __init__(self, tab_id: str):
        super().__init__()
        v = QVBoxLayout(self)
        v.setContentsMargins(20, 30, 20, 20)
        lbl = QLabel(f"⏳ Tab '{tab_id.upper()}' กำลังพัฒนา (Phase 2-4)")
        lbl.setObjectName("npc_placeholder")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setFont(QFont(FONT_PRIMARY, 14))
        v.addStretch()
        v.addWidget(lbl)
        v.addStretch()

    def refresh(self, *args, **kwargs):
        pass

    def row_count(self) -> int:
        return 0


# ────────────────────────────────────────────────────────────────────
# Merge tool — diff between current npc.json and a target file
# ────────────────────────────────────────────────────────────────────
class _MergeDiff:
    """Computed diff between a base npc.json dict and a target dict.

    Sections covered: main_characters, npcs, lore, character_roles.
    Skipped: word_fixes (deprecated), _game_info (metadata).

    Each diff entry is a dict:
        {
          'type':       'new' | 'change',
          'key':        <hashable identity (used for tracking selection)>,
          'label':      <display name>,
          'target_val': <full target entry>,
          'base_val':   <base entry or None>,
          'details':    <human-readable summary>,
        }
    Additive only — never reports DELETED rows. Merging is a one-way pull.
    """
    SECTION_ORDER = ["main_characters", "npcs", "lore", "character_roles"]

    def __init__(self, base_data, target_data):
        self.base = base_data or {}
        self.target = target_data or {}
        self.sections = {s: [] for s in self.SECTION_ORDER}
        self._compute()

    def _compute(self):
        # main_characters: identity = (firstName, lastName) lowercase
        self.sections["main_characters"] = self._diff_list(
            "main_characters",
            key_fn=lambda c: (c.get("firstName", "").strip().lower(),
                              c.get("lastName", "").strip().lower()),
            label_fn=lambda c: ((c.get("firstName", "") + " "
                                 + c.get("lastName", "")).strip() or "?"),
            compare_fields=["firstName", "lastName", "gender", "role",
                            "relationship", "image"],
            summary_fn=lambda c: " · ".join(filter(None, [
                c.get("gender", ""), c.get("role", "")])),
        )
        # npcs: identity = name lowercase
        self.sections["npcs"] = self._diff_list(
            "npcs",
            key_fn=lambda n: n.get("name", "").strip().lower(),
            label_fn=lambda n: n.get("name", "") or "?",
            compare_fields=["name", "role", "description"],
            summary_fn=lambda n: (n.get("role", "")
                                  or self._truncate(n.get("description", ""), 50)),
        )
        # lore + character_roles: pure dicts
        self.sections["lore"] = self._diff_dict("lore")
        self.sections["character_roles"] = self._diff_dict("character_roles")

    def _diff_list(self, section, *, key_fn, label_fn, compare_fields, summary_fn):
        base_list = self.base.get(section) or []
        target_list = self.target.get(section) or []
        # Index by identity, dropping entries with empty key
        def _index(seq):
            d = {}
            for e in seq:
                k = key_fn(e)
                if not k or all(not part for part in k) if isinstance(k, tuple) else not k:
                    continue
                d[k] = e
            return d
        base_dict = _index(base_list)
        target_dict = _index(target_list)
        diffs = []
        for key, t in target_dict.items():
            if key not in base_dict:
                diffs.append({
                    "type": "new", "key": key,
                    "label": label_fn(t),
                    "target_val": t, "base_val": None,
                    "details": summary_fn(t),
                })
            else:
                b = base_dict[key]
                changes = []
                for f in compare_fields:
                    bv = b.get(f, "")
                    tv = t.get(f, "")
                    if isinstance(bv, str): bv = bv.strip()
                    if isinstance(tv, str): tv = tv.strip()
                    if bv != tv:
                        changes.append((f, bv, tv))
                if changes:
                    diffs.append({
                        "type": "change", "key": key,
                        "label": label_fn(t),
                        "target_val": t, "base_val": b,
                        "details": self._format_changes(changes),
                    })
        diffs.sort(key=lambda d: (0 if d["type"] == "new" else 1, str(d["label"]).lower()))
        return diffs

    def _diff_dict(self, section):
        base = self.base.get(section) or {}
        target = self.target.get(section) or {}
        diffs = []
        for k, t_val in target.items():
            if k not in base:
                diffs.append({
                    "type": "new", "key": k, "label": k,
                    "target_val": t_val, "base_val": None,
                    "details": self._truncate(str(t_val), 70),
                })
            else:
                bv = base[k]
                tv = t_val
                if isinstance(bv, str): bv = bv.strip()
                if isinstance(tv, str): tv = tv.strip()
                if bv != tv:
                    diffs.append({
                        "type": "change", "key": k, "label": k,
                        "target_val": t_val, "base_val": base[k],
                        "details": (f"{self._truncate(str(base[k]), 28)}"
                                    f"  →  {self._truncate(str(t_val), 28)}"),
                    })
        diffs.sort(key=lambda d: (0 if d["type"] == "new" else 1, str(d["label"]).lower()))
        return diffs

    @staticmethod
    def _format_changes(changes):
        parts = []
        for f, bv, tv in changes:
            parts.append(f"{f}: {_MergeDiff._truncate(str(bv), 14)}"
                         f"→{_MergeDiff._truncate(str(tv), 14)}")
        return "  ·  ".join(parts)

    @staticmethod
    def _truncate(s, n):
        if not s:
            return ""
        return s if len(s) <= n else s[:n] + "…"

    def total_count(self):
        return sum(len(v) for v in self.sections.values())

    def section_summary(self, section):
        diffs = self.sections.get(section, [])
        new_n = sum(1 for d in diffs if d["type"] == "new")
        chg_n = sum(1 for d in diffs if d["type"] == "change")
        parts = []
        if new_n: parts.append(f"{new_n} ใหม่")
        if chg_n: parts.append(f"{chg_n} เปลี่ยนแปลง")
        return ", ".join(parts) if parts else "—"


class _MergeDialog(QDialog):
    """Modal showing a 2-column comparison of BASE vs TARGET npc.json files,
    plus a checklist of every diff entry. User picks rows to merge in.

    Merge semantics (additive — never deletes):
        new entries → append to base
        changed entries → overwrite base values with target values
        word_fixes / _game_info → ignored entirely
    The dialog only mutates the base data on `_on_apply` (when user clicks
    'Merge ที่เลือก'). The caller (panel) handles persisting via autosave().
    """

    SECTION_LABELS = {
        "main_characters": "MAIN CHARACTERS",
        "npcs":            "NPCS",
        "lore":            "LORE",
        "character_roles": "CHARACTER ROLES (น้ำเสียง)",
    }

    def __init__(self, panel, target_path: str, target_data: dict):
        super().__init__(panel)
        self.panel = panel
        self.target_path = target_path
        self.target_data = target_data
        self.diff = _MergeDiff(panel.dm.data, target_data)
        # selection state
        self._selections = []   # list of {section, idx, cb, diff}
        self._select_all_cb = None
        self._merge_btn = None
        self.applied_count = 0  # set on accept — caller reads to know what changed
        self._build()

    def _build(self):
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)
        self.resize(760, 660)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)

        bg = QFrame(self)
        bg.setObjectName("merge_bg")
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setOffset(0, 6)
        shadow.setColor(QColor(0, 0, 0, 200))
        bg.setGraphicsEffect(shadow)
        outer.addWidget(bg)

        inner = QVBoxLayout(bg)
        inner.setContentsMargins(20, 16, 20, 16)
        inner.setSpacing(12)

        # ── Title row ──
        header_row = QHBoxLayout()
        title = QLabel("Merge NPC Database")
        title.setObjectName("merge_title")
        title.setFont(QFont(FONT_PRIMARY, 14, QFont.Weight.Bold))
        header_row.addWidget(title)
        header_row.addStretch()
        btn_close = QPushButton("✕")
        btn_close.setObjectName("merge_close")
        btn_close.setFixedSize(26, 26)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.clicked.connect(self.reject)
        header_row.addWidget(btn_close)
        inner.addLayout(header_row)

        # ── Comparison cards (BASE | TARGET) ──
        # Compute mtimes once so each card can colour its own date relative
        # to the other (newer=green, older=orange, same=neutral).
        base_mtime = self._safe_mtime(self.panel.dm.file_path)
        target_mtime = self._safe_mtime(self.target_path)
        compare_row = QHBoxLayout()
        compare_row.setSpacing(12)
        compare_row.addWidget(self._build_file_card(
            "BASE (ปัจจุบัน)", self.panel.dm.file_path, self.panel.dm.data,
            is_base=True, mtime=base_mtime, other_mtime=target_mtime))
        compare_row.addWidget(self._build_file_card(
            "TARGET (ที่จะ merge)", self.target_path, self.target_data,
            is_base=False, mtime=target_mtime, other_mtime=base_mtime))
        inner.addLayout(compare_row)

        # ── Select-all row ──
        select_row = QHBoxLayout()
        sel_lbl = QLabel("เลือกข้อมูลที่ต้องการ merge เข้าฐานปัจจุบัน:")
        sel_lbl.setObjectName("merge_section_lbl")
        sel_lbl.setFont(QFont(FONT_PRIMARY, 11))
        select_row.addWidget(sel_lbl)
        select_row.addStretch()
        if self.diff.total_count() > 0:
            self._select_all_cb = QCheckBox("เลือกทั้งหมด")
            self._select_all_cb.setObjectName("merge_select_all")
            self._select_all_cb.setFont(QFont(FONT_PRIMARY, 10))
            self._select_all_cb.setCursor(Qt.CursorShape.PointingHandCursor)
            self._select_all_cb.toggled.connect(self._on_select_all_toggled)
            select_row.addWidget(self._select_all_cb)
        inner.addLayout(select_row)

        # ── Diff list ──
        if self.diff.total_count() == 0:
            empty = QLabel("ไม่มีข้อมูลใหม่หรือเปลี่ยนแปลงให้ merge\n"
                           "ไฟล์เป้าหมายไม่ต่างจากฐานปัจจุบัน")
            empty.setObjectName("merge_empty")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setFont(QFont(FONT_PRIMARY, 11))
            empty.setWordWrap(True)
            inner.addWidget(empty, stretch=1)
        else:
            scroll = QScrollArea()
            scroll.setObjectName("merge_scroll")
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.Shape.NoFrame)

            content = QWidget()
            content.setObjectName("merge_scroll_content")
            content_v = QVBoxLayout(content)
            content_v.setContentsMargins(8, 8, 8, 8)
            content_v.setSpacing(2)

            for section in _MergeDiff.SECTION_ORDER:
                diffs = self.diff.sections.get(section, [])
                if not diffs:
                    continue
                hdr_lbl = QLabel(
                    f"{self.SECTION_LABELS[section]}  —  {self.diff.section_summary(section)}"
                )
                hdr_lbl.setObjectName("merge_section_hdr")
                hdr_lbl.setFont(QFont(FONT_PRIMARY, 11, QFont.Weight.Bold))
                content_v.addSpacing(8)
                content_v.addWidget(hdr_lbl)
                for idx, d in enumerate(diffs):
                    content_v.addWidget(self._build_diff_row(section, idx, d))
            content_v.addStretch(1)

            scroll.setWidget(content)
            inner.addWidget(scroll, stretch=1)

        # ── Actions ──
        action_row = QHBoxLayout()
        action_row.setSpacing(10)
        action_row.addStretch()
        btn_cancel = QPushButton("ยกเลิก")
        btn_cancel.setObjectName("merge_btn_cancel")
        btn_cancel.setFont(QFont(FONT_PRIMARY, 11))
        btn_cancel.setMinimumSize(110, 38)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.clicked.connect(self.reject)
        action_row.addWidget(btn_cancel)

        self._merge_btn = QPushButton("Merge ที่เลือก (0)")
        self._merge_btn.setObjectName("merge_btn_apply")
        self._merge_btn.setFont(QFont(FONT_PRIMARY, 11, QFont.Weight.Bold))
        self._merge_btn.setMinimumSize(200, 38)
        self._merge_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._merge_btn.clicked.connect(self._on_apply)
        self._merge_btn.setEnabled(False)
        action_row.addWidget(self._merge_btn)
        inner.addLayout(action_row)

        self._apply_dialog_theme()
        # Center over parent panel
        if self.panel is not None:
            try:
                pg = self.panel.geometry()
                self.move(pg.x() + (pg.width() - self.width()) // 2,
                          pg.y() + (pg.height() - self.height()) // 2)
            except Exception:
                pass

    @staticmethod
    def _safe_mtime(path: str) -> float:
        """Read file mtime, returning 0.0 on any failure (missing file, perm
        error, None path) so callers can compare without try/except chains."""
        try:
            if path and os.path.exists(path):
                return os.path.getmtime(path)
        except Exception:
            pass
        return 0.0

    def _build_file_card(self, title: str, file_path: str, data: dict, *,
                         is_base: bool, mtime: float, other_mtime: float) -> QWidget:
        """Render one of the two comparison cards. mtime/other_mtime are
        used to colour-code the date line (green=newer, orange=older, plain=same)
        — the date is the most decision-critical field so it gets the loudest
        treatment.
        """
        card = QFrame()
        card.setObjectName("merge_file_base" if is_base else "merge_file_target")
        v = QVBoxLayout(card)
        v.setContentsMargins(18, 14, 18, 14)
        v.setSpacing(8)

        t = QLabel(title)
        t.setObjectName("merge_file_title")
        t.setFont(QFont(FONT_PRIMARY, 10, QFont.Weight.Bold))
        v.addWidget(t)

        fname = os.path.basename(file_path) if file_path else "—"
        fn_lbl = QLabel(fname)
        fn_lbl.setObjectName("merge_file_name")
        fn_lbl.setFont(QFont(FONT_PRIMARY, 13, QFont.Weight.Bold))
        fn_lbl.setToolTip(file_path or "")
        v.addWidget(fn_lbl)

        # mtime row — bold + colour-coded vs the other file
        if mtime <= 0:
            mtime_str = "—"
            indicator = ""
            class_name = "merge_file_mtime_neutral"
        else:
            mtime_str = _format_relative_time(mtime)
            if other_mtime <= 0:
                indicator = ""
                class_name = "merge_file_mtime_neutral"
            else:
                delta = mtime - other_mtime
                if abs(delta) < 1.0:
                    indicator = "= "
                    class_name = "merge_file_mtime_same"
                elif delta > 0:
                    indicator = "↑ "  # this file is newer
                    class_name = "merge_file_mtime_newer"
                else:
                    indicator = "↓ "  # this file is older
                    class_name = "merge_file_mtime_older"
        m_lbl = QLabel(f"{indicator}อัปเดต {mtime_str}")
        m_lbl.setObjectName(class_name)
        m_lbl.setFont(QFont(FONT_PRIMARY, 12, QFont.Weight.Bold))
        v.addWidget(m_lbl)

        v.addSpacing(4)

        # Counts — split across two lines, larger font for readability
        main_n = len(data.get("main_characters", []) or [])
        npcs_n = len(data.get("npcs", []) or [])
        lore_n = len(data.get("lore", {}) or {})
        roles_n = len(data.get("character_roles", {}) or {})
        counts1 = QLabel(f"main: {main_n}     npcs: {npcs_n}")
        counts1.setObjectName("merge_file_counts")
        counts1.setFont(QFont(FONT_PRIMARY, 11))
        v.addWidget(counts1)
        counts2 = QLabel(f"lore: {lore_n}     roles: {roles_n}")
        counts2.setObjectName("merge_file_counts")
        counts2.setFont(QFont(FONT_PRIMARY, 11))
        v.addWidget(counts2)
        return card

    def _build_diff_row(self, section: str, idx: int, diff_entry: dict) -> QWidget:
        row = QFrame()
        row.setObjectName("merge_diff_row")
        h = QHBoxLayout(row)
        h.setContentsMargins(10, 4, 10, 4)
        h.setSpacing(8)

        cb = QCheckBox()
        cb.setCursor(Qt.CursorShape.PointingHandCursor)
        cb.toggled.connect(self._update_merge_button)
        h.addWidget(cb)

        is_new = (diff_entry["type"] == "new")
        badge = QLabel("NEW" if is_new else "CHG")
        badge.setObjectName("merge_badge_new" if is_new else "merge_badge_chg")
        badge.setFont(QFont(FONT_MONO, 8, QFont.Weight.Bold))
        badge.setFixedWidth(36)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        h.addWidget(badge)

        lbl = QLabel(str(diff_entry["label"]))
        lbl.setObjectName("merge_diff_label")
        lbl.setFont(QFont(FONT_PRIMARY, 11))
        lbl.setMinimumWidth(160)
        h.addWidget(lbl)

        details = diff_entry.get("details", "")
        d_lbl = QLabel(details)
        d_lbl.setObjectName("merge_diff_details")
        d_lbl.setFont(QFont(FONT_PRIMARY, 10))
        d_lbl.setWordWrap(False)
        # Show full details on hover (for change diffs that get truncated)
        if details:
            d_lbl.setToolTip(details)
        h.addWidget(d_lbl, stretch=1)

        self._selections.append({
            "section": section, "idx": idx, "cb": cb, "diff": diff_entry,
        })
        return row

    def _on_select_all_toggled(self, checked: bool):
        for s in self._selections:
            s["cb"].setChecked(checked)

    def _update_merge_button(self):
        if not self._merge_btn:
            return
        n = sum(1 for s in self._selections if s["cb"].isChecked())
        self._merge_btn.setText(f"Merge ที่เลือก ({n})")
        self._merge_btn.setEnabled(n > 0)

    def _on_apply(self):
        """Apply selected diffs to base data, then accept dialog. Caller
        handles autosave (which propagates the reload to MBB)."""
        applied = 0
        for sel in self._selections:
            if not sel["cb"].isChecked():
                continue
            try:
                self._apply_diff(sel["section"], sel["diff"])
                applied += 1
            except Exception as e:
                log.warning(f"merge apply failed for {sel['section']}/"
                            f"{sel['diff'].get('label')}: {e}")
        self.applied_count = applied
        if applied > 0:
            self.panel.dm._dirty = True
        self.accept()

    def _apply_diff(self, section: str, diff_entry: dict):
        target_val = diff_entry["target_val"]
        if section in ("main_characters", "npcs"):
            self._apply_list_diff(section, diff_entry, target_val)
        elif section in ("lore", "character_roles"):
            # setdefault alone isn't enough — if the key exists but value is
            # wrong type (None / list / corrupted), we'd crash on subscript.
            # Force-reset to {} when type mismatches.
            cur = self.panel.dm.data.get(section)
            if not isinstance(cur, dict):
                cur = {}
                self.panel.dm.data[section] = cur
            cur[diff_entry["key"]] = target_val

    def _apply_list_diff(self, section: str, diff_entry: dict, target_val: dict):
        cur = self.panel.dm.data.get(section)
        if not isinstance(cur, list):
            cur = []
            self.panel.dm.data[section] = cur
        base_list = cur
        if section == "main_characters":
            def key_fn(c):
                return (c.get("firstName", "").strip().lower(),
                        c.get("lastName", "").strip().lower())
        else:  # npcs
            def key_fn(c):
                return c.get("name", "").strip().lower()
        target_key = diff_entry["key"]
        for i, b in enumerate(base_list):
            if key_fn(b) == target_key:
                # Overwrite — but preserve any local _added_at metadata so the
                # 'recently added' filter doesn't get clobbered by the merge.
                preserved = {}
                if "_added_at" in b:
                    preserved["_added_at"] = b["_added_at"]
                base_list[i] = {**target_val, **preserved}
                return
        # Not found in base → append. Preserve target's _added_at if any,
        # otherwise stamp now (so it shows up under "recently added").
        import time
        new_entry = dict(target_val)
        if "_added_at" not in new_entry:
            new_entry["_added_at"] = time.time()
        base_list.append(new_entry)

    def _apply_dialog_theme(self):
        try:
            p = getattr(self.panel, "palette", None)
            if not p:
                p = derive_palette(
                    self.panel.am.get_accent_color(),
                    self.panel.am.get_theme_color("secondary", "#888888"))
        except Exception:
            p = derive_palette("#58a6ff", "#888888")

        qss = f"""
            QFrame#merge_bg {{
                background: {p['bg_titlebar']};
                border: 2px solid {p['accent']};
                border-radius: 10px;
            }}
            QLabel#merge_title {{
                color: {p['text']}; background: transparent;
            }}
            QPushButton#merge_close {{
                background: transparent; border: none; border-radius: 4px;
                color: {p['text_dim']}; font-size: 13px; font-weight: bold;
            }}
            QPushButton#merge_close:hover {{
                background: #cc4444; color: #ffffff;
            }}
            QFrame#merge_file_base, QFrame#merge_file_target {{
                background: {p['btn_bg']};
                border: 1px solid {p['border_subtle']};
                border-radius: 6px;
            }}
            QFrame#merge_file_target {{
                border: 1px solid {p['accent']};
            }}
            QLabel#merge_file_title {{
                color: {p['text_dim']}; background: transparent;
                padding-bottom: 2px;
            }}
            QLabel#merge_file_name {{
                color: {p['text']}; background: transparent;
            }}
            QLabel#merge_file_counts {{
                color: {p['text_dim']}; background: transparent;
            }}
            /* mtime — color/icon indicates relative freshness */
            QLabel#merge_file_mtime_newer {{
                color: #3fb950; background: transparent;  /* green: this file is newer */
            }}
            QLabel#merge_file_mtime_older {{
                color: #f59e0b; background: transparent;  /* orange: this file is older */
            }}
            QLabel#merge_file_mtime_same {{
                color: {p['text']}; background: transparent;  /* neutral: same date */
            }}
            QLabel#merge_file_mtime_neutral {{
                color: {p['text_dim']}; background: transparent;  /* fallback when no comparison */
            }}
            QLabel#merge_section_lbl {{
                color: {p['text']}; background: transparent;
            }}
            QLabel#merge_section_hdr {{
                color: {p['accent']}; background: transparent;
                padding: 6px 4px 4px 0px;
                border-bottom: 1px solid {p['border_subtle']};
            }}
            QLabel#merge_empty {{
                color: {p['text_dim']}; background: transparent;
                padding: 30px 20px;
            }}
            QFrame#merge_diff_row {{
                background: transparent; border-radius: 4px;
            }}
            QFrame#merge_diff_row:hover {{
                background: {p['bg_medium']};
            }}
            QLabel#merge_badge_new {{
                background: #2ea043; color: #ffffff;
                padding: 2px 4px; border-radius: 3px;
            }}
            QLabel#merge_badge_chg {{
                background: #f59e0b; color: #ffffff;
                padding: 2px 4px; border-radius: 3px;
            }}
            QLabel#merge_diff_label {{
                color: {p['text']}; background: transparent;
            }}
            QLabel#merge_diff_details {{
                color: {p['text_dim']}; background: transparent;
            }}
            QScrollArea#merge_scroll {{
                background: {p['bg_deeper']};
                border: 1px solid {p['border_subtle']};
                border-radius: 6px;
            }}
            QWidget#merge_scroll_content {{
                background: {p['bg_deeper']};
            }}
            QPushButton#merge_btn_cancel {{
                background: {p['btn_bg']}; color: {p['text']};
                border: 1px solid {p['border_active']}; border-radius: 6px;
                padding: 8px 18px;
            }}
            QPushButton#merge_btn_cancel:hover {{
                background: {p['bg_medium']}; border: 1px solid {p['accent']};
            }}
            QPushButton#merge_btn_apply {{
                background: {p['accent']}; color: {p['toggled_text']};
                border: none; border-radius: 6px;
                padding: 8px 18px;
            }}
            QPushButton#merge_btn_apply:hover {{
                background: {p['accent_light']};
            }}
            QPushButton#merge_btn_apply:disabled {{
                background: {p['btn_bg']}; color: {p['text_dim']};
            }}
            QCheckBox {{
                color: {p['text']};
                background: transparent;
                spacing: 6px;
            }}
            QCheckBox::indicator {{
                width: 16px; height: 16px;
            }}
        """
        self.setStyleSheet(qss)
