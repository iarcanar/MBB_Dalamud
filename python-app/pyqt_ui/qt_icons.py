"""
qt_icons.py — load monochrome SVG UI icons tinted to the active theme colour.

The bundled SVGs (assets/icons/*.svg) are authored white; we render them to a
QPixmap via QSvgRenderer then recolour every visible pixel with tint_pixmap()
(alpha preserved → opacity-0.4 sub-paths stay as a soft second tone). So one
asset works on every theme — no per-theme icon variants needed.

load_icon()/load_pixmap() return None when the file or QtSvg is unavailable, so
callers can keep their existing text/emoji glyph as a fallback.
"""
import logging
import os

from PyQt6.QtGui import QPixmap, QPainter, QIcon
from PyQt6.QtCore import Qt

from resource_utils import resource_path
from pyqt_ui.styles import tint_pixmap

log = logging.getLogger("mbb-qt")

_RENDER_PX = 64  # render SVG at this size, then QIcon downscales smoothly

try:
    from PyQt6.QtSvg import QSvgRenderer
    _HAVE_SVG = True
except Exception as e:  # pragma: no cover
    _HAVE_SVG = False
    log.warning(f"[qt_icons] QtSvg unavailable, icons fall back to glyphs: {e}")


def load_pixmap(name: str, color: str = "#ffffff", px: int = _RENDER_PX):
    """Render assets/icons/<name>.svg → QPixmap tinted to `color`, or None on failure."""
    if not _HAVE_SVG:
        return None
    path = resource_path(os.path.join("assets", "icons", f"{name}.svg"))
    if not os.path.exists(path):
        log.warning(f"[qt_icons] missing icon: {path}")
        return None
    renderer = QSvgRenderer(path)
    if not renderer.isValid():
        log.warning(f"[qt_icons] invalid svg: {path}")
        return None
    pm = QPixmap(px, px)
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    renderer.render(painter)
    painter.end()
    return tint_pixmap(pm, color)


def load_icon(name: str, color: str = "#ffffff", px: int = _RENDER_PX):
    """Same as load_pixmap but returns a QIcon (None on failure)."""
    pm = load_pixmap(name, color, px)
    return QIcon(pm) if pm is not None else None


def save_tinted_png(name: str, color: str, out_path: str, px: int = _RENDER_PX):
    """Render assets/icons/<name>.svg tinted to `color`, save as PNG to out_path.
    Returns out_path on success, None on failure. Used for QSS `image: url(...)`
    targets (e.g. a QComboBox down-arrow) which can't tint a raw asset themselves,
    so we bake a per-theme PNG instead."""
    pm = load_pixmap(name, color, px)
    if pm is None:
        return None
    try:
        if pm.save(out_path, "PNG"):
            return out_path
    except Exception as e:  # pragma: no cover
        log.warning(f"[qt_icons] save_tinted_png failed: {e}")
    return None
