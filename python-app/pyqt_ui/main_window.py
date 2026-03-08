"""
MBBMainWindow (PyQt6) - Frameless main window for MBB Dalamud
Compact monochrome design with glass mode
"""
import os
import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFrame, QGraphicsDropShadowEffect, QApplication,
    QLabel,
)
from PyQt6.QtGui import QColor, QIcon, QPixmap
from PyQt6.QtCore import Qt, QPoint, QTimer

from pyqt_ui.header_bar import HeaderBar
from pyqt_ui.control_panel import ControlPanel
from pyqt_ui.bottom_bar import BottomBar
from pyqt_ui.styles import get_main_window_qss, get_glass_overrides
from pyqt_ui.signals import MBBSignals

try:
    import win32gui
    import win32con
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

log = logging.getLogger("mbb-qt")

# Visible panel size (the dark bg area)
BG_W = 296
BG_H = 265
# Base shadow margin (right + bottom)
MARGIN_BASE = 12


class MBBMainWindow(QWidget):
    """PyQt6 frameless main window for MBB application"""

    def __init__(self, app_controller):
        super().__init__()
        self.app = app_controller
        self.old_pos = QPoint()
        self._taskbar_icon_done = False
        self._is_topmost = True
        self._is_glass = False

        # Signals for thread-safe UI updates
        self.signals = MBBSignals()
        self._connect_signals()

        # Component references
        self.header_bar = None
        self.control_panel = None
        self.bottom_bar = None
        self.bg = None
        self.shadow = None

        self._init_window()
        self._build_ui()

    def _init_window(self):
        self.setWindowTitle("MagicBabel")
        # Size is set dynamically in _build_ui after loading the logo
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        from resource_utils import resource_path
        icon_path = resource_path("assets/mbb_icon.png")
        try:
            self.setWindowIcon(QIcon(icon_path))
        except Exception:
            pass

    def _build_ui(self):
        from resource_utils import resource_path
        from appearance import appearance_manager

        # ── Load logo first to calculate margins ──
        logo_w = int(BG_W * 0.6)
        logo_path = resource_path("assets/mbb_meteor.png")
        logo_pixmap = None
        logo_h = int(logo_w * 0.73)  # fallback
        if os.path.exists(logo_path):
            logo_pixmap = QPixmap(logo_path).scaledToWidth(
                logo_w, Qt.TransformationMode.SmoothTransformation,
            )
            logo_h = logo_pixmap.height()

        # ── Calculate asymmetric margins so logo fits within widget ──
        # Logo right edge at bg center → logo extends left by (logo_w - BG_W//2)
        logo_overflow_left = max(0, logo_w - BG_W // 2)
        # Logo extends above bg by half its height
        logo_overflow_top = logo_h // 2

        margin_left = logo_overflow_left + 4
        margin_top = logo_overflow_top + 4
        margin_right = MARGIN_BASE
        margin_bottom = MARGIN_BASE

        win_w = margin_left + BG_W + margin_right
        win_h = margin_top + BG_H + margin_bottom
        self.setFixedSize(win_w, win_h)

        # ── Outer layout ──
        outer = QVBoxLayout(self)
        outer.setContentsMargins(margin_left, margin_top, margin_right, margin_bottom)

        # Background frame
        self.bg = QWidget()
        self.bg.setObjectName("bg")
        outer.addWidget(self.bg)

        # Drop shadow (clean black)
        self.shadow = QGraphicsDropShadowEffect()
        self.shadow.setBlurRadius(24)
        self.shadow.setColor(QColor(0, 0, 0, 160))
        self.shadow.setOffset(0, 4)
        self.bg.setGraphicsEffect(self.shadow)

        # Main layout
        main = QVBoxLayout(self.bg)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        # ── Header Bar ──
        self.header_bar = HeaderBar(
            callbacks={
                "toggle_topmost": self._on_toggle_topmost,
                "toggle_glass": self._on_toggle_glass,
                "exit_program": self._on_exit,
            },
            appearance_manager=appearance_manager,
            asset_path_func=resource_path,
        )
        main.addWidget(self.header_bar)
        self.header_bar.update_pin_state(self._is_topmost)

        # ── Divider ──
        divider1 = QFrame()
        divider1.setObjectName("divider")
        divider1.setFixedHeight(1)
        main.addWidget(divider1)

        # ── Control Panel ──
        self.control_panel = ControlPanel(
            callbacks={
                "toggle_translation": self._on_toggle_translation,
                "manual_zone_change": self._on_manual_zone_change,
            },
            appearance_manager=appearance_manager,
        )
        main.addWidget(self.control_panel)

        # ── Spacer + Divider ──
        main.addStretch(1)

        divider2 = QFrame()
        divider2.setObjectName("divider")
        divider2.setFixedHeight(1)
        main.addWidget(divider2)

        # ── Bottom Bar ──
        self.bottom_bar = BottomBar(
            callbacks={
                "toggle_tui": self._on_toggle_tui,
                "toggle_log": self._on_toggle_log,
                "toggle_mini": self._on_toggle_mini,
                "toggle_npc_manager": self._on_toggle_npc_manager,
                "toggle_theme": self._on_toggle_theme,
                "toggle_settings": self._on_toggle_settings,
            },
            appearance_manager=appearance_manager,
            button_state_manager=self.app.button_state_manager,
            asset_path_func=resource_path,
        )
        main.addWidget(self.bottom_bar)

        # ── Logo Overlay (mbb_meteor) ──
        # Right edge at bg center, overflow half height above bg top.
        self._logo_label = QLabel(self)
        if logo_pixmap:
            self._logo_label.setPixmap(logo_pixmap)
        self._logo_label.setFixedSize(logo_w, logo_h)
        self._logo_label.setStyleSheet("background: transparent;")
        self._logo_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        bg_center_x = margin_left + BG_W // 2
        logo_x = bg_center_x - logo_w
        logo_y = margin_top - logo_h // 2
        self._logo_label.move(logo_x, logo_y)
        self._logo_label.raise_()

        # Override header left margin — logo covers left half of header
        header_margin_left = BG_W // 2 - 14
        header_layout = self.header_bar.layout()
        if header_layout:
            header_layout.setContentsMargins(header_margin_left, 0, 4, 0)

        # Apply initial theme
        self._apply_theme()

    def _connect_signals(self):
        self.signals.status_update.connect(self._on_status_signal)
        self.signals.translation_state.connect(self._on_translation_state_signal)
        self.signals.swap_text_update.connect(self._on_swap_text_signal)
        self.signals.info_update.connect(self._on_info_signal)
        self.signals.theme_changed.connect(self._apply_theme)

    # ── Signal Slots ──

    def _on_status_signal(self, text: str):
        if self.control_panel:
            self.control_panel.set_status(text)

    def _on_translation_state_signal(self, is_translating: bool):
        if self.control_panel:
            self.control_panel.set_translating(is_translating)

    def _on_swap_text_signal(self, text: str):
        if self.control_panel:
            self.control_panel.set_swap_text(text)

    def _on_info_signal(self, text: str):
        if self.control_panel:
            self.control_panel.set_status_info(text)

    # ── Callback Bridges ──

    def _on_toggle_topmost(self):
        self._is_topmost = not self._is_topmost
        if HAS_WIN32:
            # Win32 API: toggle topmost โดยไม่ต้อง recreate window (ไม่กระพริบ)
            hwnd = int(self.winId())
            insert_after = win32con.HWND_TOPMOST if self._is_topmost else win32con.HWND_NOTOPMOST
            win32gui.SetWindowPos(
                hwnd, insert_after, 0, 0, 0, 0,
                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE,
            )
        else:
            # Fallback: Qt method (จะกระพริบเล็กน้อย)
            self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, self._is_topmost)
            self.show()
        if self.header_bar:
            self.header_bar.update_pin_state(self._is_topmost)
        if hasattr(self.app, "toggle_topmost_from_qt"):
            self.app.toggle_topmost_from_qt(self._is_topmost)

    def _on_toggle_theme(self):
        if hasattr(self.app, "toggle_theme"):
            self.app.toggle_theme()

    def _on_toggle_glass(self):
        self._is_glass = not self._is_glass
        self._apply_theme()
        if self.header_bar:
            self.header_bar.update_glass_state(self._is_glass)
        log.debug("Glass mode: %s", "ON" if self._is_glass else "OFF")

    def _on_exit(self):
        if hasattr(self.app, "exit_program"):
            self.app.exit_program()

    def _on_toggle_translation(self):
        if hasattr(self.app, "toggle_translation"):
            self.app.toggle_translation()

    def _on_manual_zone_change(self):
        if hasattr(self.app, "manual_zone_change"):
            self.app.manual_zone_change()
        if self.control_panel:
            self.control_panel.flash_zone_change()

    def _on_toggle_tui(self):
        if hasattr(self.app, "toggle_translated_ui"):
            self.app.toggle_translated_ui()

    def _on_toggle_log(self):
        if hasattr(self.app, "toggle_translated_logs"):
            self.app.toggle_translated_logs()

    def _on_toggle_mini(self):
        if hasattr(self.app, "toggle_mini_ui"):
            self.app.toggle_mini_ui()

    def _on_toggle_npc_manager(self):
        if hasattr(self.app, "toggle_npc_manager"):
            self.app.toggle_npc_manager()

    def _on_toggle_settings(self):
        if hasattr(self.app, "toggle_settings"):
            self.app.toggle_settings()

    # ── Theme ──

    def _apply_theme(self):
        from appearance import appearance_manager as am
        from pyqt_ui.styles import derive_palette

        primary = am.get_accent_color()       # สีหลัก → พื้นหลัง
        secondary = am.get_theme_color("secondary", "#888888")  # สีรอง → ไฮไลท์

        palette = derive_palette(primary, secondary)
        qss = get_main_window_qss(**palette)

        if self._is_glass:
            qss += get_glass_overrides()

        self.setStyleSheet(qss)

        if self.shadow:
            if self._is_glass:
                self.shadow.setBlurRadius(16)
                self.shadow.setColor(QColor(0, 0, 0, 60))
            else:
                self.shadow.setBlurRadius(24)
                self.shadow.setColor(QColor(0, 0, 0, 160))

    @staticmethod
    def _hex_to_rgb(hex_color: str):
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    # ── Drag Support ──

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPosition().toPoint()

    # ── Taskbar Icon ──

    def showEvent(self, event):
        super().showEvent(event)
        if not self._taskbar_icon_done:
            self._taskbar_icon_done = True
            QTimer.singleShot(50, self._setup_taskbar_icon)
            # Apply initial topmost state via Win32 API (after taskbar icon setup)
            QTimer.singleShot(100, self._apply_initial_topmost)

    def _setup_taskbar_icon(self):
        try:
            from resource_utils import resource_path

            # Set window icon via QIcon (supports ICO/PNG)
            icon_path = resource_path("assets/mbb_icon.ico")
            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))

            if not HAS_WIN32:
                return

            # Force window to appear in taskbar (not as tool window)
            hwnd = int(self.winId())
            ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            ex_style |= win32con.WS_EX_APPWINDOW
            ex_style &= ~win32con.WS_EX_TOOLWINDOW
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex_style)

            win32gui.SetWindowPos(
                hwnd, None, 0, 0, 0, 0,
                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE
                | win32con.SWP_NOZORDER | win32con.SWP_FRAMECHANGED,
            )
            log.debug("Taskbar icon set OK")
        except Exception as e:
            log.error("Taskbar icon failed: %s", e)

    def _apply_initial_topmost(self):
        """Apply initial topmost state via Win32 API (called once after window is shown)"""
        if not HAS_WIN32 or not self._is_topmost:
            return
        try:
            hwnd = int(self.winId())
            win32gui.SetWindowPos(
                hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0,
                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE,
            )
            log.debug("Initial topmost applied via Win32 API")
        except Exception as e:
            log.error("Failed to apply initial topmost: %s", e)

    # ── Window Position Memory ──

    def save_position(self):
        return {"x": self.x(), "y": self.y()}

    def restore_position(self, pos: dict):
        x = pos.get("x", 100)
        y = pos.get("y", 100)
        screen = QApplication.primaryScreen()
        if screen:
            geom = screen.availableGeometry()
            x = max(0, min(x, geom.width() - self.width()))
            y = max(0, min(y, geom.height() - self.height()))
        self.move(x, y)
