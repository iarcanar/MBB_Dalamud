"""
QtFontManager — Qt-native font registration and discovery.

Replaces the Tkinter-based FontManager for all PyQt6 UI components.
Registers bundled .ttf/.otf files with QFontDatabase and merges
with system-installed fonts.
"""
import os
import logging
from typing import List, Dict, Optional

from PyQt6.QtGui import QFontDatabase, QFont

log = logging.getLogger("mbb-qt")


class QtFontManager:
    """Register bundled fonts with Qt and provide a unified font list."""

    def __init__(self, fonts_dir: Optional[str] = None):
        self._fonts_dir = fonts_dir or self._default_fonts_dir()
        # font_id -> list of Qt family names returned by addApplicationFont
        self._registered: Dict[int, List[str]] = {}
        # display_name -> qt_family_name (for bundled fonts whose names differ)
        self._alias: Dict[str, str] = {}
        # All available Qt family names (bundled + system)
        self._families: List[str] = []

        self._register_bundled()
        self._build_family_list()

    # ------------------------------------------------------------------
    # Init helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _default_fonts_dir() -> str:
        """Return the ``fonts/`` directory next to the python-app root."""
        from resource_utils import resource_path
        return resource_path("fonts")

    def _register_bundled(self):
        """Scan fonts_dir and register every .ttf / .otf with Qt."""
        if not os.path.isdir(self._fonts_dir):
            log.warning("QtFontManager: fonts dir not found: %s", self._fonts_dir)
            return

        for fname in sorted(os.listdir(self._fonts_dir)):
            if not fname.lower().endswith((".ttf", ".otf")):
                continue
            fpath = os.path.join(self._fonts_dir, fname)
            font_id = QFontDatabase.addApplicationFont(fpath)
            if font_id < 0:
                log.warning("QtFontManager: failed to register %s", fname)
                continue
            families = QFontDatabase.applicationFontFamilies(font_id)
            self._registered[font_id] = list(families)
            log.info(
                "QtFontManager: registered %s -> %s",
                fname,
                ", ".join(families) if families else "(no families)",
            )

    def _build_family_list(self):
        """Merge bundled font families + system fonts, sorted, no dupes."""
        bundled = set()
        for fams in self._registered.values():
            bundled.update(fams)

        system = set(QFontDatabase.families())

        all_families = sorted(bundled | system)
        self._families = all_families

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_available_fonts(self) -> List[str]:
        """Return all font families available in Qt (bundled + system)."""
        return list(self._families)

    def get_bundled_fonts(self) -> List[str]:
        """Return only the families that came from bundled font files."""
        out = []
        for fams in self._registered.values():
            out.extend(fams)
        return sorted(set(out))

    def resolve_family(self, name: str) -> str:
        """
        Given a display name (which may be a legacy Tkinter-style name),
        return the closest Qt family name.

        Falls back to *name* itself so QFont can try the system resolver.
        """
        # Exact match in Qt families
        if name in self._families:
            return name

        # Check alias table
        if name in self._alias:
            return self._alias[name]

        # Fuzzy: try stripping weight keywords
        for suffix in ("Medium", "Light", "Thin", "Bold", "Regular",
                       "SemiBold", "ExtraBold", "ExtraLight"):
            base = name.replace(suffix, "").strip()
            if base in self._families:
                self._alias[name] = base
                return base

        # Fuzzy: case-insensitive substring match
        name_lower = name.lower()
        for fam in self._families:
            if name_lower in fam.lower() or fam.lower() in name_lower:
                self._alias[name] = fam
                return fam

        return name  # Let Qt fall back

    def make_font(self, family: str, size: int, weight: int = -1) -> QFont:
        """Create a QFont using the resolved family name."""
        resolved = self.resolve_family(family)
        font = QFont(resolved, size)
        if weight > 0:
            font.setWeight(QFont.Weight(weight))
        return font
