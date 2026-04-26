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
import os
import logging
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QGraphicsDropShadowEffect, QFrame, QTreeWidget, QTreeWidgetItem,
    QStackedWidget, QComboBox, QButtonGroup, QMessageBox, QSizePolicy,
    QTextEdit, QHeaderView, QAbstractItemView,
)
from PyQt6.QtGui import QColor, QFont, QIcon, QPixmap
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
    # Column sizing: first col gets ~40% of width, last col stretches
    header = tree.header()
    header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
    for i in range(1, len(columns)):
        header.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
    return tree


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
# Shows character image (or placeholder) + click to change, with remove option
# ────────────────────────────────────────────────────────────────────
class CharacterAvatar(QWidget):
    avatar_clicked = pyqtSignal()    # emitted on left-click (change image)
    remove_requested = pyqtSignal()  # emitted when user clicks the remove overlay button

    SIZE = 120  # display size in panel — bumped from 80 after removing the
                # redundant "Main Characters Details" title to fill freed space
    HOVER_HOLD_MS = 1000  # ms to hover before remove button appears

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(self.SIZE, self.SIZE)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._pixmap = None
        self._placeholder_text = "?"
        self._accent_color = "#58a6ff"
        self._bg_color = "#161b22"
        self._text_color = "#e6edf3"
        self._hover = False
        self._has_image = False
        self.setToolTip("คลิกเพื่อเปลี่ยนรูปภาพ")

        # Remove button overlay — child widget, hidden by default
        # Positioned at bottom-right after init
        self._btn_remove = QPushButton("🗑", self)
        self._btn_remove.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_remove.setFixedSize(26, 26)
        self._btn_remove.setToolTip("ลบรูปภาพ")
        self._btn_remove.move(self.SIZE - 28, self.SIZE - 28)
        self._btn_remove.hide()
        self._btn_remove.setStyleSheet("""
            QPushButton {
                background: rgba(232, 90, 90, 220);
                color: white;
                border: 1.5px solid white;
                border-radius: 13px;
                font-size: 11pt;
            }
            QPushButton:hover {
                background: #e85a5a;
            }
        """)
        self._btn_remove.clicked.connect(self.remove_requested.emit)

        # Hover-hold timer — only fires after 1s of continuous hover
        self._hover_timer = QTimer(self)
        self._hover_timer.setSingleShot(True)
        self._hover_timer.timeout.connect(self._reveal_remove)

    def set_image(self, image_path: Optional[str]):
        """Load image from disk; pass None / empty to show placeholder."""
        if image_path and os.path.exists(image_path):
            self._pixmap = QPixmap(image_path)
            self._has_image = True
        else:
            self._pixmap = None
            self._has_image = False
        # Hide remove button when image cleared
        self._btn_remove.hide()
        self.update()

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
        # Start hover-hold timer to reveal remove button after 1s (only if image exists)
        if self._has_image:
            self._hover_timer.start(self.HOVER_HOLD_MS)
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self._hover_timer.stop()
        self._btn_remove.hide()
        self.update()
        super().leaveEvent(event)

    def _reveal_remove(self):
        """Called by hover-hold timer — reveals the remove button if still hovered."""
        if self._hover and self._has_image:
            self._btn_remove.show()
            self._btn_remove.raise_()

    def mousePressEvent(self, event):
        # If click landed on the remove button, that button handles it (not us).
        # Otherwise treat as "change image" click.
        if event.button() == Qt.MouseButton.LeftButton:
            self.avatar_clicked.emit()
            event.accept(); return
        super().mousePressEvent(event)

    def paintEvent(self, event):
        from PyQt6.QtGui import QPainter, QPainterPath, QPen, QBrush
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
            x = (self.SIZE - scaled.width()) // 2
            y = (self.SIZE - scaled.height()) // 2
            p.drawPixmap(x, y, scaled)
        else:
            # Placeholder: bg + initial letter (font scales with avatar size)
            p.fillPath(path, QColor(self._bg_color))
            p.setPen(QPen(QColor(self._text_color)))
            font = QFont(FONT_PRIMARY, max(20, int(self.SIZE * 0.35)), QFont.Weight.Bold)
            p.setFont(font)
            p.drawText(rect, int(Qt.AlignmentFlag.AlignCenter), self._placeholder_text)

        # Border — theme-aware: dark themes lighten bg, light themes darken bg
        p.setClipping(False)
        if self._hover:
            border_color = QColor(self._accent_color)
        else:
            from pyqt_ui.styles import _luminance
            bg_q = QColor(self._bg_color)
            try:
                if _luminance(self._bg_color) > 0.5:
                    border_color = bg_q.darker(125)   # light theme → darker rim
                else:
                    border_color = bg_q.lighter(160)  # dark theme → lighter rim
            except Exception:
                border_color = bg_q.lighter(140)
        p.setPen(QPen(border_color, 2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(rect)

        # Subtle "click to change" hint on hover (only if no image yet, OR before remove btn appears)
        if self._hover and not self._btn_remove.isVisible():
            overlay = QColor(0, 0, 0, 70)
            p.setClipPath(path)
            p.fillRect(self.rect(), overlay)
            p.setClipping(False)
            p.setPen(QPen(QColor("#ffffff")))
            p.setFont(QFont(FONT_PRIMARY, 8, QFont.Weight.Bold))
            p.drawText(rect, int(Qt.AlignmentFlag.AlignCenter), "เปลี่ยนรูป")

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
        self._is_pinned = False
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
        subtitle = QLabel("ฐานข้อมูลตัวละคร")
        subtitle.setObjectName("npc_subtitle")
        subtitle.setFont(QFont(FONT_PRIMARY, 11))
        h.addWidget(subtitle)
        h.addStretch()

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
        return wrap

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

    def autosave(self, message: str = "✓ บันทึกแล้ว") -> bool:
        """Persist current data to npc.json. Backup created only on first save
        of this session (avoids backup spam on rapid edits). Shows toast on success.

        Args:
            message: Custom toast text (e.g. "✓ เพิ่ม 'X' แล้ว" for fresh-add flow)
        """
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
        flags = self.windowFlags()
        if self._is_pinned:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        else:
            flags &= ~Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self._update_pin_icon()
        self.show()  # re-show after flag change

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
        if hasattr(self, "_resize_grip") and self._resize_grip:
            self._resize_grip.set_invert(is_light_theme(p["bg"]))
        # Refresh CharacterAvatar palette in MainCharactersTab
        main_tab = self._tab_pages.get("main")
        if main_tab and hasattr(main_tab, "avatar"):
            main_tab.avatar.set_palette(p)

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

        # ── Avatar (centered at top) — click to change, hover-hold 1s for remove ──
        avatar_row = QHBoxLayout()
        avatar_row.addStretch()
        self.avatar = CharacterAvatar()
        self.avatar.avatar_clicked.connect(self._on_change_image)
        self.avatar.remove_requested.connect(self._on_remove_image)
        avatar_row.addWidget(self.avatar)
        avatar_row.addStretch()
        d.addLayout(avatar_row)
        d.addSpacing(8)
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
            self.list_widget.addTopLevelItem(_new_row([display, type_text], payload=i))
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

    def _on_change_image(self):
        """Open file picker → optimize → save → update entry. Auto-saves to disk."""
        from PyQt6.QtWidgets import QFileDialog
        if self._current_index < 0:
            QMessageBox.information(self, "เลือกตัวละครก่อน",
                "ต้องเลือกตัวละครจากลิสต์ก่อน หรือเพิ่มตัวละครใหม่ + บันทึกครั้งหนึ่ง")
            return
        src, _ = QFileDialog.getOpenFileName(
            self, "เลือกรูปภาพตัวละคร", "",
            "Image Files (*.png *.jpg *.jpeg *.webp *.bmp *.gif *.tiff)"
        )
        if not src:
            return
        filename = self.dm.set_main_character_image(self._current_index, src)
        if not filename:
            QMessageBox.warning(self, "Error", "ไม่สามารถ optimize/บันทึกรูปได้")
            return
        self._refresh_avatar()
        self.panel.autosave()

    def _on_remove_image(self):
        if self._current_index < 0:
            return
        if confirm_delete(self.panel, "ยืนยันการลบรูป",
                          "ต้องการลบรูปภาพของตัวละครนี้ใช่หรือไม่?"):
            self.dm.remove_main_character_image(self._current_index)
            self._refresh_avatar()
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

    def __init__(self, panel: NPCManagerPanel):
        super().__init__()
        self.panel = panel
        self.dm = panel.dm
        self._current_key = None  # None = ADD mode, str = EDIT mode
        self._current_filter = ""
        self._snapshot = None     # change-detection for UPDATE mode
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

        # Left: list (QTreeWidget)
        left = QVBoxLayout(); left.setSpacing(4)
        left.addLayout(_build_list_header(self.LIST_HEADER_KEY, self.LIST_HEADER_VAL))
        self.list_widget = _make_tree([self.LIST_HEADER_KEY, self.LIST_HEADER_VAL])
        self.list_widget.itemSelectionChanged.connect(self._on_list_selection)
        self.list_widget.setMinimumWidth(380)
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
        self.in_key.setFont(QFont(FONT_PRIMARY, 11))
        self.in_key.textChanged.connect(self._update_primary_enabled)
        d.addWidget(self.in_key)

        # Value (multi-line QTextEdit or single-line QLineEdit per VALUE_MULTILINE)
        d.addWidget(self._field_label(self.VALUE_LABEL))
        if self.VALUE_MULTILINE:
            self.in_value = QTextEdit()
            self.in_value.setProperty("class", "npc_textarea")
            self.in_value.setPlaceholderText(self.VALUE_PLACEHOLDER)
            self.in_value.setFont(QFont(FONT_PRIMARY, 11))
            self.in_value.textChanged.connect(self._update_primary_enabled)
            d.addWidget(self.in_value, stretch=1)
        else:
            self.in_value = QLineEdit()
            self.in_value.setProperty("class", "npc_field")
            self.in_value.setPlaceholderText(self.VALUE_PLACEHOLDER)
            self.in_value.setMinimumHeight(36)
            self.in_value.setFont(QFont(FONT_PRIMARY, 11))
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
        lbl = QLabel(text); lbl.setProperty("class", "npc_field_label")
        lbl.setFont(QFont(FONT_PRIMARY, 11)); return lbl

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
