"""Orchestrator CLI — captures Qt + Tk UI pieces into transparent PNGs.

Runs the Qt recipes and the Tk recipes in SEPARATE subprocesses so the two GUI
toolkits never share a process (the documented Tk+Qt hybrid GIL crash).

    python -m tools.ui_capture                 # everything
    python -m tools.ui_capture --list
    python -m tools.ui_capture --only mbb,log,choice
    python -m tools.ui_capture --scale 3
    python -m tools.ui_capture --only dialog --dialog-font-size 48

Output defaults to docs/ui_capture/ (one <name>.png per recipe).
"""
from __future__ import annotations

import argparse
import subprocess
import sys

from . import common
from .recipes_qt import RECIPES as QT_RECIPES
from .recipes_tk import RECIPES as TK_RECIPES


def _split(names):
    """Partition requested names into (qt_subset, tk_subset, unknown)."""
    qt, tk, unknown = [], [], []
    for n in names:
        if n in QT_RECIPES:
            qt.append(n)
        elif n in TK_RECIPES:
            tk.append(n)
        else:
            unknown.append(n)
    return qt, tk, unknown


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m tools.ui_capture")
    ap.add_argument("--only", default="",
                    help="comma-separated recipe names (default: all)")
    ap.add_argument("--scale", type=int, default=common.DEFAULT_SCALE,
                    help="Qt render scale (2 or 3). Tk is native res.")
    ap.add_argument("--out", default=None, help=f"output dir (default {common.OUTPUT_DIR})")
    ap.add_argument("--dialog-font-size", type=int, default=36,
                    help="font size driving the Tk dialog TUI's native resolution")
    ap.add_argument("--upscale", type=int, default=1,
                    help="Lanczos upscale for Tk captures (interpolated; default 1)")
    ap.add_argument("--list", action="store_true", help="list recipes and exit")
    args = ap.parse_args(argv)

    if args.list:
        print("Qt recipes:", ", ".join(QT_RECIPES))
        print("Tk recipes:", ", ".join(TK_RECIPES))
        return 0

    requested = [n.strip() for n in args.only.split(",") if n.strip()]
    if not requested:
        requested = list(QT_RECIPES) + list(TK_RECIPES)
    qt, tk, unknown = _split(requested)
    for u in unknown:
        common.log(f"SKIP unknown recipe: {u}")

    out_dir = common.ensure_output_dir(args.out)
    rc = 0

    if qt:
        common.log(f"Qt capture → {', '.join(qt)}")
        rc |= subprocess.call(
            [sys.executable, "-m", "tools.ui_capture.run_qt",
             "--out", out_dir, "--scale", str(args.scale), "--only", ",".join(qt)],
            cwd=common.APP_ROOT,
        )
    if tk:
        common.log(f"Tk capture → {', '.join(tk)}")
        rc |= subprocess.call(
            [sys.executable, "-m", "tools.ui_capture.run_tk",
             "--out", out_dir, "--only", ",".join(tk),
             "--dialog-font-size", str(args.dialog_font_size),
             "--upscale", str(args.upscale)],
            cwd=common.APP_ROOT,
        )

    common.log(f"done → {out_dir}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
