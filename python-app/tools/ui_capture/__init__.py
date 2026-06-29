"""MBB UI capture toolkit.

Instantiates each MBB UI component in isolation (no running MBB.py app) and
renders it to a high-resolution transparent PNG for use as website source art.

Two backends, kept in SEPARATE processes to avoid the documented Tk+Qt hybrid
GIL crash:
  - Qt pieces  (main window, battle/cutscene overlay, choice overlay, logs)
  - Tk pieces  (dialog TUI, mini UI)

Run:
    python -m tools.ui_capture            # capture everything
    python -m tools.ui_capture --list     # list available recipes
    python -m tools.ui_capture --only mbb,log,choice
    python -m tools.ui_capture --scale 3

Add a new UI: drop one recipe function into recipes_qt.py or recipes_tk.py and
register it in that module's RECIPES dict. Nothing else needs to change.
See .claude/skills/ui-capture/SKILL.md for the full how-to.
"""
