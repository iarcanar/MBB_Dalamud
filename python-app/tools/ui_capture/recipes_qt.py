"""Qt UI recipes — each returns a populated, laid-out QWidget ready to render.

Convention: a recipe is `build(settings) -> QWidget`. It must
  1. construct the widget,
  2. inject sample content,
  3. trigger layout (the runner sets windowOpacity(0) BEFORE calling, so any
     internal show()/show_for_mode() stays invisible on screen yet render()
     still paints the full widget at full alpha).

Register every recipe in RECIPES at the bottom. Adding a new UI = one entry.
"""
from __future__ import annotations

from . import samples


# ── Minimal stand-in for the MagicBabelApp controller ────────────────────
# MBBMainWindow only touches `app.button_state_manager` during construction;
# the toggle_* methods are wired as click callbacks and never fire during a
# render. __getattr__ returns a no-op for anything else, defensively.
class _StubBSM:
    def __getattr__(self, name):
        return lambda *a, **k: None


class _StubApp:
    def __init__(self):
        self.button_state_manager = _StubBSM()

    def __getattr__(self, name):
        return lambda *a, **k: None


# ── Recipes ──────────────────────────────────────────────────────────────
def build_main_window(settings):
    from pyqt_ui.main_window import MBBMainWindow
    win = MBBMainWindow(_StubApp())
    return win


def build_battle(settings):
    from pyqt_ui.dissolve_overlay import DissolveOverlay
    ov = DissolveOverlay(settings)
    ov.set_mode("battle")
    ov.set_text(samples.BATTLE_TEXT, speaker=samples.BATTLE_SPEAKER)
    ov.show_for_mode("battle")
    return ov


def build_cutscene(settings):
    from pyqt_ui.dissolve_overlay import DissolveOverlay
    ov = DissolveOverlay(settings)
    ov.set_mode("cutscene")
    ov.set_text(samples.CUTSCENE_TEXT, speaker="")
    ov.show_for_mode("cutscene")
    return ov


def build_choice(settings):
    from pyqt_ui.choice_overlay import ChoiceOverlay
    ov = ChoiceOverlay(settings)
    ov.show_choice(samples.CHOICE_HEADER, samples.CHOICE_OPTIONS)
    return ov


def build_logs(settings):
    from pyqt_ui.translated_logs import Translated_Logs
    from . import common
    logs = Translated_Logs(settings)
    for msg in samples.LOG_MESSAGES:
        logs.add_message(msg)
    logs.show()
    # Fit window height to the bubbles so there's no empty tail in the art.
    common.pump_qt(150)
    chrome = max(0, logs.height() - logs.scroll.height())
    content_h = logs._bubbles_container.sizeHint().height()
    logs.resize(logs.width(), chrome + content_h + 12)
    common.pump_qt(80)
    return logs


def build_settings(settings):
    from pyqt_ui.settings_panel import SettingsPanel
    from appearance import appearance_manager
    noop = lambda *a, **k: None
    panel = SettingsPanel(settings, noop, noop, appearance_manager)
    panel.show()
    return panel


def build_font(settings):
    from pyqt_ui.font_panel import FontPanel
    from pyqt_ui.qt_font_manager import QtFontManager
    from appearance import appearance_manager
    panel = FontPanel(settings, QtFontManager(), appearance_manager)
    panel.show()
    return panel


RECIPES = {
    "mbb": build_main_window,
    "battle": build_battle,
    "cutscene": build_cutscene,
    "choice": build_choice,
    "log": build_logs,
    "settings": build_settings,
    "font": build_font,
}
