"""Qt capture runner — builds ONE QApplication and renders the requested Qt
recipes. Invoked as a subprocess by __main__ (kept isolated from the Tk runner
to avoid the Tk+Qt hybrid GIL crash).

    python -m tools.ui_capture.run_qt --out DIR --scale 2 --only mbb,log
"""
from __future__ import annotations

import argparse
import os
import sys
import traceback

from . import common
from .recipes_qt import RECIPES


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    ap.add_argument("--scale", type=int, default=common.DEFAULT_SCALE)
    ap.add_argument("--only", default="")
    args = ap.parse_args(argv)

    out_dir = common.ensure_output_dir(args.out)
    names = [n.strip() for n in args.only.split(",") if n.strip()] or list(RECIPES)

    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv[:1])

    # Real settings (loads theme/font from settings.json; self-contained).
    from settings import Settings
    settings = Settings()
    common.block_settings_persistence(settings)

    failures = 0
    for name in names:
        if name not in RECIPES:
            common.log(f"SKIP unknown qt recipe: {name}")
            continue
        widget = None
        try:
            widget = RECIPES[name](settings)
            widget.setWindowOpacity(0.0)  # invisible on screen; render() unaffected
            common.pump_qt(150)
            common.save_qt(widget, os.path.join(out_dir, f"{name}.png"), args.scale)
        except Exception:
            failures += 1
            common.log(f"FAILED {name}:\n{traceback.format_exc()}")
        finally:
            if widget is not None:
                try:
                    widget.close()
                except Exception:
                    pass

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
