"""
tk_compat.py — minimal Tkinter-method shim over a PyQt6 QWidget.

WHY THIS EXISTS
---------------
MBB.py was written against Tkinter windows and calls Tk-style methods directly
on window objects it holds references to:

  - the Mini UI inner window : self.mini_ui.mini_ui.deiconify() / .geometry() / ...
  - the dialogue TUI root     : self.translated_ui.root.withdraw() / .state() / ...

As those UIs migrate to PyQt6 one at a time we do NOT want to rewrite every Tk
call site in MBB.py — large blast radius, and during the transition those call
sites are still shared with Tk pieces. Instead each migrated window exposes a
`TkWindowShim` that translates the handful of Tk methods MBB.py actually calls
into their Qt equivalents.

SCOPE — only methods that are ACTUALLY called are implemented (verified by grep
2026-06-18). Do NOT add speculative methods; add one when a real call site needs
it. The union currently covers:

  Mini UI inner window  (self.mini_ui.mini_ui.*):
      winfo_exists, state, withdraw, deiconify, lift, geometry (read+write),
      attributes("-topmost", ...), winfo_x, winfo_y, winfo_children, destroy
  Dialogue TUI root     (self.translated_ui.root.*) — used when that lands:
      state, deiconify, withdraw, geometry, update_idletasks, winfo_exists

NOTE on geometry(): QWidget already has a (non-Tk) geometry() returning a QRect,
which is exactly why this shim is a *wrapper object* and NOT a QWidget mixin — a
mixin's Tk-style geometry() would collide with QWidget.geometry(). The wrapper
sidesteps the name clash entirely. Qt's own C++ code calls the (non-virtual) C++
geometry(), never this Python object, so there is no interference either way.
"""

from __future__ import annotations


class TkWindowShim:
    """Translate the small set of Tk window methods MBB.py calls into Qt.

    Wrap the real QWidget once and hand the shim to MBB.py wherever it expects a
    Tk window (e.g. as `MiniUI.mini_ui`). Visibility/geometry calls forward to
    the wrapped widget. Every wrapped-object access is guarded against
    RuntimeError so a call arriving after Qt has deleted the C++ object (app
    shutdown) degrades to a Tk-like "destroyed" answer instead of crashing.
    """

    def __init__(self, widget):
        self._w = widget
        # Mini UI is always-on-top; the dialogue TUI may toggle it. Track the
        # last requested state so attributes("-topmost") reads back correctly.
        self._topmost = True

    # ── existence / state ──────────────────────────────────────────────
    def winfo_exists(self) -> int:
        # Tk returns 0 once a window is destroyed. Touch the wrapped C++ object;
        # PyQt raises RuntimeError if it has been deleted (after destroy()).
        try:
            self._w.isVisible()
            return 1
        except RuntimeError:
            return 0

    def state(self) -> str:
        try:
            return "normal" if self._w.isVisible() else "withdrawn"
        except RuntimeError:
            return "withdrawn"

    # ── show / hide / z-order ──────────────────────────────────────────
    def deiconify(self) -> None:
        self._w.show()

    def withdraw(self) -> None:
        self._w.hide()

    def lift(self) -> None:
        self._w.raise_()

    def destroy(self) -> None:
        # Called from MBB.exit_program's windows_to_close loop. Clean Qt teardown.
        try:
            self._w.hide()
            self._w.deleteLater()
        except RuntimeError:
            pass

    # ── geometry ───────────────────────────────────────────────────────
    def winfo_x(self) -> int:
        return int(self._w.x())

    def winfo_y(self) -> int:
        return int(self._w.y())

    def winfo_width(self) -> int:
        return int(self._w.width())

    def winfo_height(self) -> int:
        return int(self._w.height())

    def geometry(self, spec: str | None = None):
        """Read → "WxH+X+Y"; write ← "WxH+X+Y" / "+X+Y" / "WxH" (Tk format).

        partition('+') correctly handles negative coordinates from multi-monitor
        layouts ("+-1920+0" → x=-1920, y=0).
        """
        if spec is None:
            return (
                f"{self._w.width()}x{self._w.height()}"
                f"+{self._w.x()}+{self._w.y()}"
            )
        try:
            size_part, _, pos_part = spec.partition("+")
            w_str, _, h_str = size_part.partition("x")
            if w_str and h_str:
                self._w.resize(int(w_str), int(h_str))
            if pos_part:
                x_str, _, y_str = pos_part.partition("+")
                if x_str and y_str:
                    self._w.move(int(x_str), int(y_str))
        except (ValueError, RuntimeError):
            pass

    # ── attributes (-topmost is the only one MBB.py uses) ──────────────
    def attributes(self, name: str, *args):
        if name == "-topmost":
            if args:
                self._topmost = bool(args[0])
                # The window already carries WindowStaysOnTopHint from
                # construction; re-assert front position via raise_() to avoid
                # the setWindowFlag() re-show flicker.
                if self._topmost:
                    try:
                        self._w.raise_()
                    except RuntimeError:
                        pass
                return None
            return self._topmost
        return None

    # ── misc Tk no-ops / stubs ─────────────────────────────────────────
    def update_idletasks(self) -> None:
        # Tk flushes pending geometry/layout here. Qt applies setGeometry/move/
        # resize synchronously to the logical geometry, so there is nothing to
        # flush — a no-op is the correct Qt translation.
        pass

    def winfo_children(self):
        # Only reachable from MBB.update_mini_ui_theme (dead code — it iterates
        # children of a non-existent start_button). Return empty so a stray
        # call can never crash.
        return []
