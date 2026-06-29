"""Tk capture runner — builds ONE hidden tk.Tk() root and captures the requested
Tk recipes via Win32 PrintWindow. Invoked as a subprocess by __main__ (kept
isolated from the Qt runner to avoid the Tk+Qt hybrid GIL crash).

    python -m tools.ui_capture.run_tk --out DIR --only dialog,mini --dialog-font-size 36
"""
from __future__ import annotations

import argparse
import os
import time
import traceback

from . import common
from .recipes_tk import RECIPES


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    ap.add_argument("--only", default="")
    ap.add_argument("--dialog-font-size", type=int, default=36)
    ap.add_argument("--upscale", type=int, default=1,
                    help="Lanczos upscale after capture (interpolated, not crisp)")
    args = ap.parse_args(argv)

    out_dir = common.ensure_output_dir(args.out)
    names = [n.strip() for n in args.only.split(",") if n.strip()] or list(RECIPES)
    opts = {"dialog_font_size": args.dialog_font_size}

    import tkinter as tk
    root = tk.Tk()
    root.withdraw()

    from settings import Settings
    settings = Settings()
    common.block_settings_persistence(settings)

    def pump(ms: int) -> None:
        end = time.time() + ms / 1000.0
        while time.time() < end:
            try:
                root.update()
            except tk.TclError:
                break
            time.sleep(0.01)

    failures = 0
    for name in names:
        if name not in RECIPES:
            common.log(f"SKIP unknown tk recipe: {name}")
            continue
        win = None
        try:
            win, colorkey = RECIPES[name](root, settings, pump, opts)
            pump(150)
            common.capture_tk_window(
                win, os.path.join(out_dir, f"{name}.png"),
                colorkey=colorkey, upscale=args.upscale,
            )
        except Exception:
            failures += 1
            common.log(f"FAILED {name}:\n{traceback.format_exc()}")
        finally:
            try:
                if win is not None:
                    win.destroy()
            except Exception:
                pass

    try:
        root.destroy()
    except Exception:
        pass
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
