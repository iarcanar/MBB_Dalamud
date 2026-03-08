"""Theme-aware QSS for MBB Main Window — derives full palette from primary+secondary"""

import colorsys

# ─── Default Dark Palette (fallback constants) ───
BG_DARK = "#1a1a1a"
BG_DEEPER = "#141414"
BG_TITLEBAR = "#111111"
BG_MEDIUM = "#2a2a2a"
BG_SURFACE = "#222222"

ACCENT_DEFAULT = "#ffffff"
ACCENT_CYAN = "#ffffff"  # Legacy alias
ACCENT_CYAN_DIM = "#cccccc"
ACCENT_MAGENTA = "#888888"

TEXT_PRIMARY = "#e0e0e0"
TEXT_SECONDARY = "#888888"
TEXT_DIM = "#555555"

BORDER_SUBTLE = "#2a2a2a"
BORDER_ACTIVE = "#3a3a3a"
SEPARATOR_COLOR = "#2a2a2a"

ERROR_RED = "#cc4444"
SUCCESS_GREEN = "#4CAF50"
STATUS_IDLE = "#555555"

# ─── Legacy aliases ───
CYBER_BG_BOTTOM = BG_DEEPER
CYBER_TEXT = TEXT_PRIMARY
CYBER_TEXT_DIM = TEXT_SECONDARY
CYBER_CYAN = ACCENT_DEFAULT
CYBER_MAGENTA = ACCENT_MAGENTA
CYBER_ERROR_RED = ERROR_RED
CYBER_BOTTOM_BG = BG_DEEPER
CYBER_BTN_BG = BG_SURFACE

# ─── Typography ───
FONT_PRIMARY = "Segoe UI"
FONT_ACCENT = "Segoe UI"
FONT_MONO = "Consolas"


# ─── Color Utilities ───

def _hex_to_rgb(hex_color: str):
    """Convert '#RRGGBB' to (r, g, b) floats 0..1"""
    h = hex_color.lstrip("#")
    if len(h) != 6:
        h = "1a1a1a"
    return tuple(int(h[i:i+2], 16) / 255.0 for i in (0, 2, 4))


def _rgb_to_hex(r: float, g: float, b: float) -> str:
    """Convert (r, g, b) floats 0..1 to '#RRGGBB'"""
    return "#{:02x}{:02x}{:02x}".format(
        max(0, min(255, int(r * 255))),
        max(0, min(255, int(g * 255))),
        max(0, min(255, int(b * 255))),
    )


def _adjust_lightness(hex_color: str, factor: float) -> str:
    """Scale lightness of a hex color by factor (HLS), preserving hue+saturation."""
    r, g, b = _hex_to_rgb(hex_color)
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    l = max(0.0, min(1.0, l * factor))
    r2, g2, b2 = colorsys.hls_to_rgb(h, l, s)
    return _rgb_to_hex(r2, g2, b2)


def _luminance(hex_color: str) -> float:
    """WCAG relative luminance (0=black, 1=white)."""
    r, g, b = _hex_to_rgb(hex_color)

    def linearize(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * linearize(r) + 0.7152 * linearize(g) + 0.0722 * linearize(b)


def derive_palette(primary: str, secondary: str) -> dict:
    """Derive a full UI palette from primary (background) + secondary (accent) colors.

    Returns a dict matching get_main_window_qss() keyword arguments.
    """
    # ── Background family (from primary) ──
    bg = primary
    bg_deeper = _adjust_lightness(primary, 0.7)
    bg_titlebar = _adjust_lightness(primary, 0.6)
    bg_surface = _adjust_lightness(primary, 1.15)
    bg_medium = _adjust_lightness(primary, 1.4)

    # ── Borders ──
    border_subtle = _adjust_lightness(primary, 1.3)
    border_active = _adjust_lightness(primary, 1.6)
    separator = _adjust_lightness(primary, 1.2)

    # ── Text (auto-contrast via WCAG luminance) ──
    lum = _luminance(primary)
    if lum > 0.35:
        text = "#1a1a1a"
        text_dim = "#555555"
    else:
        text = "#e0e0e0"
        text_dim = "#888888"

    # ── Accent (from secondary) ──
    accent = secondary
    accent_light = _adjust_lightness(secondary, 1.3)

    # ── Toggle active text (auto-contrast vs secondary) ──
    toggled_text = "#1a1a1a" if _luminance(secondary) > 0.35 else "#ffffff"

    # ── Button surface ──
    btn_bg = bg_surface

    return dict(
        accent=accent, accent_light=accent_light,
        secondary=secondary, bg=bg, btn_bg=btn_bg,
        text=text, text_dim=text_dim,
        bg_deeper=bg_deeper, bg_titlebar=bg_titlebar,
        bg_medium=bg_medium, border_subtle=border_subtle,
        border_active=border_active, separator=separator,
        toggled_text=toggled_text,
    )


def get_main_window_qss(accent="#ffffff", accent_light="#ffffff",
                         secondary="#888888", bg=BG_DARK, btn_bg=BG_SURFACE,
                         text=TEXT_PRIMARY, text_dim=TEXT_SECONDARY,
                         bg_deeper=BG_DEEPER, bg_titlebar=BG_TITLEBAR,
                         bg_medium=BG_MEDIUM, border_subtle=BORDER_SUBTLE,
                         border_active=BORDER_ACTIVE, separator=SEPARATOR_COLOR,
                         toggled_text="#000000"):
    """Generate QSS for MBB main window. All colors parameterized for theming."""

    return f"""
        /* ══════ BACKGROUND ══════ */
        QWidget#bg {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {bg}, stop:1 {bg_deeper});
            border-radius: 12px;
            border: 1px solid {border_subtle};
        }}

        /* ══════ DIVIDERS ══════ */
        QFrame#divider {{
            background: {separator};
            max-height: 1px;
            min-height: 1px;
            border: none;
        }}

        /* ══════ HEADER ══════ */
        QWidget#header {{
            background: {bg_titlebar};
            border-top-left-radius: 12px;
            border-top-right-radius: 12px;
        }}
        QLabel#version {{
            color: {text_dim};
            background: transparent;
            font-family: '{FONT_MONO}';
            font-size: 7pt;
            padding-top: 4px;
        }}
        QPushButton#header_btn {{
            background: transparent;
            border: none;
            border-radius: 4px;
            color: {text_dim};
            font-size: 14px;
        }}
        QPushButton#header_btn:hover {{
            background: {bg_medium};
            color: {text};
        }}
        QPushButton#btn_close {{
            background: transparent;
            border: none;
            border-radius: 4px;
            color: {text_dim};
            font-size: 13px;
            font-weight: bold;
        }}
        QPushButton#btn_close:hover {{
            background: {ERROR_RED};
            color: #ffffff;
        }}

        /* ══════ CONTROL PANEL ══════ */
        QWidget#control_panel {{
            background: transparent;
        }}

        /* ── Status dot ── */
        QLabel#status_dot {{
            color: {STATUS_IDLE};
            background: transparent;
            font-size: 16px;
        }}
        QLabel#status_dot[active="true"] {{
            color: {SUCCESS_GREEN};
        }}

        /* ── Status text ── */
        QLabel#status {{
            color: {text};
            background: transparent;
            font-family: '{FONT_PRIMARY}';
            font-size: 10pt;
        }}
        QLabel#status[active="true"] {{
            color: {SUCCESS_GREEN};
        }}

        /* ── Stop/Start button (small, subtle) ── */
        QPushButton#btn_primary {{
            background: {btn_bg};
            color: {text_dim};
            border: 1px solid {border_subtle};
            border-radius: 4px;
            font-family: '{FONT_PRIMARY}';
            font-size: 9pt;
            padding: 4px 14px;
        }}
        QPushButton#btn_primary:hover {{
            background: {bg_medium};
            color: {text};
            border: 1px solid {border_active};
        }}
        QPushButton#btn_primary[active="true"] {{
            background: {btn_bg};
            color: {ERROR_RED};
            border: 1px solid {border_subtle};
        }}
        QPushButton#btn_primary[active="true"]:hover {{
            background: {bg_medium};
            color: #ff6666;
            border: 1px solid {ERROR_RED};
        }}

        /* ── Info rows (Claude widget pattern) ── */
        QLabel#info_key {{
            color: {text_dim};
            background: transparent;
            font-family: '{FONT_PRIMARY}';
            font-size: 10pt;
        }}
        QLabel#info_value {{
            color: {text};
            background: transparent;
            font-family: '{FONT_PRIMARY}';
            font-size: 10pt;
        }}

        /* ── Status info (model + dalamud) ── */
        QLabel#status_info {{
            color: {text_dim};
            background: transparent;
            font-family: 'Consolas';
            font-size: 8pt;
        }}

        /* ══════ BOTTOM BAR ══════ */
        QWidget#bottom_bar {{
            background: {bg_titlebar};
            border-bottom-left-radius: 12px;
            border-bottom-right-radius: 12px;
        }}

        /* ── Toggle Buttons (TUI/LOG/MINI) ── */
        QPushButton#toggle_btn {{
            background: {btn_bg};
            color: {text_dim};
            border: 1px solid {border_subtle};
            border-radius: 4px;
            font-family: '{FONT_PRIMARY}';
            font-size: 10pt;
            font-weight: bold;
            padding: 7px 0px;
        }}
        QPushButton#toggle_btn:hover {{
            background: {bg_medium};
            color: {text};
            border: 1px solid {border_active};
        }}
        QPushButton#toggle_btn[toggled="true"] {{
            background: {accent};
            color: {toggled_text};
            border: 1px solid {accent};
        }}

        /* ── Utility Buttons ── */
        QPushButton#utility_btn {{
            background: {btn_bg};
            color: {text};
            border: 1px solid {border_subtle};
            border-radius: 4px;
            font-family: '{FONT_PRIMARY}';
            font-size: 9pt;
            padding: 5px 14px;
        }}
        QPushButton#utility_btn:hover {{
            background: {bg_medium};
            color: {text};
            border: 1px solid {border_active};
        }}
        QPushButton#utility_btn[toggled="true"] {{
            background: {accent};
            color: {toggled_text};
            border: 1px solid {accent};
        }}

        /* ── Zone Change Button ── */
        QPushButton#zone_btn {{
            background: {btn_bg};
            border: 1px solid {border_subtle};
            border-radius: 4px;
            color: {text_dim};
            padding: 1px 6px;
        }}
        QPushButton#zone_btn:hover {{
            background: {bg_medium};
            color: {text};
            border: 1px solid {border_active};
        }}

        /* ── Icon Buttons (Settings, Theme) ── */
        QPushButton#icon_btn {{
            background: transparent;
            border: none;
            border-radius: 4px;
            color: {text_dim};
        }}
        QPushButton#icon_btn:hover {{
            background: {bg_medium};
            color: {text};
        }}

        /* ── Info Label (footer) ── */
        QLabel#info {{
            color: {text_dim};
            background: transparent;
            font-family: '{FONT_MONO}';
            font-size: 8pt;
            padding: 2px 4px;
        }}
    """


def get_glass_overrides():
    """Return QSS overrides for glass (transparent) mode."""
    return """
        /* ── Background ── */
        QWidget#bg {
            background: transparent;
            border: 1px solid rgba(255, 255, 255, 10);
        }
        QWidget#header {
            background: rgba(10, 10, 10, 51);
            border-top-left-radius: 12px;
            border-top-right-radius: 12px;
        }
        QWidget#bottom_bar {
            background: rgba(10, 10, 10, 51);
            border-bottom-left-radius: 12px;
            border-bottom-right-radius: 12px;
        }
        QFrame#divider {
            background: rgba(42, 42, 42, 77);
        }

        /* ── Glass: Toggle buttons (TUI/LOG/MINI) ── */
        QPushButton#toggle_btn {
            background: transparent;
            border: none;
            color: rgba(255, 255, 255, 50);
        }
        QPushButton#toggle_btn:hover {
            background: rgba(255, 255, 255, 8);
            color: rgba(255, 255, 255, 130);
            border: none;
        }
        QPushButton#toggle_btn[toggled="true"] {
            background: transparent;
            border: none;
            color: rgba(255, 255, 255, 90);
        }

        /* ── Glass: Utility button (NPC Manager) ── */
        QPushButton#utility_btn {
            background: transparent;
            border: none;
            color: rgba(255, 255, 255, 50);
        }
        QPushButton#utility_btn:hover {
            background: rgba(255, 255, 255, 8);
            color: rgba(255, 255, 255, 130);
            border: none;
        }
        QPushButton#utility_btn[toggled="true"] {
            background: transparent;
            border: none;
            color: rgba(255, 255, 255, 90);
        }

        /* ── Glass: Start/Stop button ── */
        QPushButton#btn_primary {
            background: transparent;
            border: none;
            color: rgba(255, 255, 255, 50);
        }
        QPushButton#btn_primary:hover {
            background: rgba(255, 255, 255, 8);
            color: rgba(255, 255, 255, 130);
            border: none;
        }
        QPushButton#btn_primary[active="true"] {
            background: transparent;
            border: none;
            color: rgba(255, 80, 80, 60);
        }

        /* ── Glass: Zone Change button ── */
        QPushButton#zone_btn {
            background: transparent;
            border: none;
            color: rgba(255, 255, 255, 40);
        }
        QPushButton#zone_btn:hover {
            background: rgba(255, 255, 255, 8);
            color: rgba(255, 255, 255, 130);
            border: none;
        }

        /* ── Glass: Icon buttons (Theme/Settings) ── */
        QPushButton#icon_btn {
            color: rgba(255, 255, 255, 40);
        }
        QPushButton#icon_btn:hover {
            background: rgba(255, 255, 255, 8);
            color: rgba(255, 255, 255, 130);
        }

        /* ── Glass: Header buttons (Glass/Pin) ── */
        QPushButton#header_btn {
            color: rgba(255, 255, 255, 40);
        }
        QPushButton#header_btn:hover {
            background: rgba(255, 255, 255, 8);
            color: rgba(255, 255, 255, 130);
        }

        /* ── Glass: Close button ── */
        QPushButton#btn_close {
            color: rgba(255, 255, 255, 40);
        }
        QPushButton#btn_close:hover {
            background: rgba(220, 50, 50, 120);
            color: #ffffff;
        }

        /* ── Glass: Control Panel labels ── */
        QLabel#status_dot {
            color: rgba(255, 255, 255, 40);
        }
        QLabel#status_dot[active="true"] {
            color: rgba(100, 200, 100, 60);
        }
        QLabel#status {
            color: rgba(255, 255, 255, 50);
        }
        QLabel#info_key {
            color: rgba(255, 255, 255, 35);
        }
        QLabel#info_value {
            color: rgba(255, 255, 255, 50);
        }
        QLabel#status_info {
            color: rgba(255, 255, 255, 30);
        }
        QLabel#version {
            color: rgba(255, 255, 255, 35);
        }
    """
