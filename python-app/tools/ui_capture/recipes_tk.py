"""Tkinter UI recipes — dialog TUI + mini UI.

Convention: a recipe is `build(root, settings, pump, opts) -> (tk_window, colorkey)`
  - root:   a hidden tk.Tk() shared by all Tk recipes
  - settings: a Settings() instance (in-memory only — NEVER saved to disk here)
  - pump(ms): drive the Tk event loop for `ms` so typewriter/layout settle
  - opts:   dict of runner flags (e.g. dialog_font_size)
  - returns: the Toplevel to capture + an optional "#rrggbb" colour-key to drop
             to alpha (None = capture opaque, as the app actually looks)

Tk cannot re-rasterise at 2× like Qt, so "higher resolution" for the dialog TUI
is achieved by driving a LARGER font_size (more real pixels of crisp text), not
by upscaling. Register every recipe in RECIPES at the bottom.
"""
from __future__ import annotations

import tkinter as tk

from . import samples


def build_dialog(root, settings, pump, opts):
    from translated_ui import Translated_UI
    from loggings import LoggingManager

    # Bigger font → larger, sharper native render (in-memory only, not saved).
    font_size = int(opts.get("dialog_font_size", 36))
    settings.set("font_size", font_size, save_immediately=False)

    lm = LoggingManager(settings)
    win = tk.Toplevel(root)
    noop = lambda *a, **k: None

    tui = Translated_UI(
        win, noop, noop, None, noop, noop, settings, noop, lm,
        character_names=set(samples.CHARACTER_NAMES),
        main_app=None, font_settings=None,
    )
    # No PyQt6 overlays in this isolated process — force the Tkinter path.
    tui.dissolve_overlay = None
    tui.choice_overlay = None

    win.geometry("+120+120")
    tui.update_text(samples.DIALOG, chat_type=61)
    pump(400)
    # Skip the typewriter animation → show the complete line for the shot.
    try:
        tui.show_full_text()
    except Exception:
        pass
    pump(500)
    return win, None


def build_mini(root, settings, pump, opts):
    from mini_ui import MiniUI

    mini = MiniUI(root, lambda: None)
    try:
        mini.set_toggle_translation_callback(lambda: None)
    except Exception:
        pass
    win = getattr(mini, "mini_ui", None) or root
    # create_mini_ui() ends with withdraw(); map it on-screen so PrintWindow has
    # painted content to capture (an unmapped overrideredirect window is black).
    try:
        win.deiconify()
        win.geometry("+120+120")
        win.lift()
        win.update_idletasks()
    except Exception:
        pass
    pump(500)
    # Keep a reference alive on the window so the MiniUI isn't GC'd mid-capture.
    win._mbb_mini_ref = mini
    return win, None


RECIPES = {
    "dialog": build_dialog,
    "mini": build_mini,
}
