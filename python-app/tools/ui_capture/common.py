"""Shared capture helpers — paths, Qt high-res render, Tk window capture.

This module is import-safe from BOTH a Qt process and a Tk process; it only
imports the heavy backend lazily inside the functions that need it.
"""
from __future__ import annotations

import os
import sys

# ── Make the python-app root importable regardless of CWD ──────────────
# tools/ui_capture/common.py  →  python-app/ is two levels up.
APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if APP_ROOT not in sys.path:
    sys.path.insert(0, APP_ROOT)

# Default output folder for website source art.
OUTPUT_DIR = os.path.abspath(os.path.join(APP_ROOT, "..", "docs", "ui_capture"))

DEFAULT_SCALE = 2


def block_settings_persistence(settings) -> None:
    """Neutralise ALL disk writes on a Settings instance.

    The captured UIs call settings.set()/save_settings() during layout (e.g. the
    TUI saves its window position, overlays save geometry). In a capture run those
    are throw-away values — letting them reach settings.json would CORRUPT the
    user's real saved positions/font. Every write funnels through save_settings(),
    so a single no-op patch covers set(), set_logs_settings(), etc.
    """
    settings.save_settings = lambda *a, **k: None
    log("settings persistence disabled (capture run is read-only)")


def ensure_output_dir(path: str | None = None) -> str:
    out = path or OUTPUT_DIR
    os.makedirs(out, exist_ok=True)
    return out


def log(msg: str) -> None:
    print(f"[ui-capture] {msg}", flush=True)


# ════════════════════════════════════════════════════════════════════════
# Qt backend
# ════════════════════════════════════════════════════════════════════════
def render_qt_widget(widget, scale: int = DEFAULT_SCALE):
    """Render a QWidget to a transparent ARGB QImage at `scale`× resolution.

    Uses a device-pixel-ratio image so text/borders are re-rasterised crisply
    at the higher resolution (NOT interpolated-upscaled). Honours the widget's
    translucent background — transparent regions stay transparent.
    """
    from PyQt6.QtCore import QPoint, Qt
    from PyQt6.QtGui import QImage, QRegion
    from PyQt6.QtWidgets import QWidget

    widget.ensurePolished()
    w = max(1, widget.width())
    h = max(1, widget.height())

    img = QImage(w * scale, h * scale, QImage.Format.Format_ARGB32_Premultiplied)
    img.setDevicePixelRatio(scale)
    img.fill(Qt.GlobalColor.transparent)

    widget.render(
        img,
        QPoint(0, 0),
        QRegion(),
        QWidget.RenderFlag.DrawWindowBackground | QWidget.RenderFlag.DrawChildren,
    )
    return img


def save_qt(widget, path: str, scale: int = DEFAULT_SCALE) -> str:
    """Render + save a QWidget as a transparent PNG. Returns the path."""
    img = render_qt_widget(widget, scale)
    if not img.save(path, "PNG"):
        raise RuntimeError(f"QImage.save failed for {path}")
    log(f"saved {os.path.basename(path)}  {img.width()}x{img.height()} (×{scale})")
    return path


def pump_qt(ms: int = 120) -> None:
    """Let Qt process layout/paint events so render() sees a settled widget."""
    from PyQt6.QtCore import QEventLoop, QTimer
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        return
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


# ════════════════════════════════════════════════════════════════════════
# Tk backend (Windows PrintWindow → PIL, optional colour-key → alpha)
# ════════════════════════════════════════════════════════════════════════
def capture_tk_window(tk_window, path: str, colorkey: str | None = None,
                      upscale: int = 1) -> str:
    """Capture a Tk Toplevel's own surface via Win32 PrintWindow.

    Captures the window's rendered content even if occluded (PW_RENDERFULLCONTENT),
    so it does not matter that the window sits off-screen / behind others.

    Args:
        colorkey: if set (e.g. "#010101"), pixels of this colour become fully
                  transparent — mirrors Tk's 1-bit `-transparentcolor` key so the
                  rounded-corner background drops out to alpha.
        upscale: integer Lanczos upscale AFTER capture. Tk cannot re-rasterise at
                 higher DPI, so this is interpolation — prefer driving a larger
                 font_size instead. 1 = native (recommended).
    """
    import win32con
    import win32gui
    import win32ui
    from ctypes import windll
    from PIL import Image

    # winfo_id() returns the Tk child frame HWND; walk up to the real
    # top-level HWND so we capture the whole window surface.
    hwnd = tk_window.winfo_id()
    parent = win32gui.GetParent(hwnd)
    while parent:
        hwnd = parent
        parent = win32gui.GetParent(hwnd)

    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    w, h = right - left, bottom - top
    if w <= 0 or h <= 0:
        raise RuntimeError(f"window has non-positive size {w}x{h}")

    hwnd_dc = win32gui.GetWindowDC(hwnd)
    mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
    save_dc = mfc_dc.CreateCompatibleDC()
    bmp = win32ui.CreateBitmap()
    bmp.CreateCompatibleBitmap(mfc_dc, w, h)
    save_dc.SelectObject(bmp)

    # PW_RENDERFULLCONTENT = 0x00000002 — render layered/DWM content too.
    windll.user32.PrintWindow(hwnd, save_dc.GetSafeHdc(), 0x00000002)

    info = bmp.GetInfo()
    bits = bmp.GetBitmapBits(True)
    img = Image.frombuffer("RGB", (info["bmWidth"], info["bmHeight"]),
                           bits, "raw", "BGRX", 0, 1).convert("RGBA")

    win32gui.DeleteObject(bmp.GetHandle())
    save_dc.DeleteDC()
    mfc_dc.DeleteDC()
    win32gui.ReleaseDC(hwnd, hwnd_dc)

    if colorkey:
        img = _colorkey_to_alpha(img, colorkey)
    if upscale and upscale > 1:
        img = img.resize((img.width * upscale, img.height * upscale),
                         Image.LANCZOS)

    img.save(path, "PNG")
    log(f"saved {os.path.basename(path)}  {img.width}x{img.height}"
        + (f" (×{upscale} upscaled)" if upscale > 1 else ""))
    return path


def _colorkey_to_alpha(img, colorkey: str, tolerance: int = 8):
    """Make pixels matching `colorkey` (#rrggbb) transparent."""
    from PIL import Image

    ck = colorkey.lstrip("#")
    kr, kg, kb = int(ck[0:2], 16), int(ck[2:4], 16), int(ck[4:6], 16)
    px = img.load()
    for y in range(img.height):
        for x in range(img.width):
            r, g, b, a = px[x, y]
            if abs(r - kr) <= tolerance and abs(g - kg) <= tolerance and abs(b - kb) <= tolerance:
                px[x, y] = (r, g, b, 0)
    return img
