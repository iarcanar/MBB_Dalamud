"""
tui_color_picker.py
===================

TUI background color + alpha picker dialog — extracted from `translated_ui.py`
for size and maintainability.

Contains the `ImprovedColorAlphaPickerWindow` class: a frameless dark-glass
Tkinter Toplevel that lets the user pick the TUI background color and snap
transparency to one of 6 predefined steps (80, 84, 88, 92, 95, 100).

This module is intentionally self-contained — it pulls only what the picker
needs (tkinter, colorchooser, logging, appearance_manager, win32 — the latter
imported lazily inside `apply_rounded_corners`). The parent `translated_ui.py`
remains unmodified at extraction time; integration (i.e. importing this class
from there and removing the duplicate) is performed manually by the user.
"""

import tkinter as tk
from tkinter import colorchooser
import logging

from appearance import appearance_manager


class ImprovedColorAlphaPickerWindow(tk.Toplevel):
    """TUI background color + alpha picker. Frameless dark glass design that
    matches MBB / Theme Manager / Settings panel aesthetic.

    Transparency is step-locked to TRANSPARENCY_STEPS — 6 levels in the 80-100
    range (used heavily, so finer granularity than LOG's 4 steps). Snap-on-drag
    means cheap apply, no flicker, no disk thrash."""

    # 6 levels — second-to-last is 95 (per user preference) before maxing at 100
    TRANSPARENCY_STEPS = (80, 84, 88, 92, 95, 100)

    # Theme palette — match the dark-surface style used by Theme Manager/Settings
    BG_OUTER = "#0d1117"      # outer ring (dark)
    BG_SURFACE = "#161b22"    # inner card
    BG_PANEL = "#1f242c"      # input panels (slider/swatch frames)
    BORDER = "#30363d"        # subtle border
    ACCENT = "#58a6ff"        # accent (Carbon theme blue)
    TEXT = "#e6edf3"          # primary text
    TEXT_DIM = "#7d8590"      # secondary text
    TROUGH = "#30363d"        # slider track
    HANDLE_REST = "#4a525e"   # slider handle when not pressed (slightly > bg)
    HANDLE_HOVER = "#5a6270"  # slider handle on hover

    @classmethod
    def _snap_to_step(cls, value: int) -> int:
        """Round any int 80-100 to the nearest TRANSPARENCY_STEPS entry."""
        return min(cls.TRANSPARENCY_STEPS, key=lambda s: abs(s - value))

    def __init__(
        self,
        parent,
        initial_color,
        initial_alpha,
        settings_ref,
        apply_callback,
        lock_mode,
        main_ui=None  # NEW: Reference to main TranslatedUI for mode detection
    ):
        super().__init__(parent)

        # Pull live accent from MBB's theme (so picker matches active theme)
        try:
            self.ACCENT = appearance_manager.get_accent_color() or self.ACCENT
        except Exception:
            pass

        # ตั้งค่าพื้นฐาน
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        # Outer color = accent — gives a 1px border ring around the inner surface
        self.configure(bg=self.ACCENT)
        self.resizable(False, False)

        # เก็บค่าต่างๆ
        self.selected_color = initial_color
        # Snap incoming alpha to nearest step (e.g. 0.93 → 92, then 0.92)
        snapped_pct = self._snap_to_step(max(80, min(100, int(initial_alpha * 100))))
        self.current_alpha = snapped_pct / 100.0
        self.lock_mode = lock_mode
        self.settings = settings_ref
        self.apply_callback = apply_callback
        self.is_alpha_disabled = lock_mode == 1
        self._choosing_color = False
        self._is_closing = False  # Guard flag to prevent double-close
        self.main_ui = main_ui  # NEW: Store main_ui reference

        # สร้าง UI
        self.setup_ui()
        self.position_window(parent)

        # เพิ่มขอบโค้งมน
        self.after(10, self.apply_rounded_corners)

        # ตั้งค่า event bindings
        self.setup_bindings()

        # ทำให้เป็น modal
        self.grab_set()
        self.focus_set()

    def setup_ui(self):
        """Build the UI — frameless dark card with 1px accent ring (the
        outer Toplevel bg=ACCENT acts as the border; inner main_frame fills
        the card body)."""
        # 1px inset for the accent ring effect
        main_frame = tk.Frame(self, bg=self.BG_SURFACE, padx=18, pady=16)
        main_frame.pack(expand=True, fill=tk.BOTH, padx=1, pady=1)

        # Sized to fit content + clear space below slider so the handle isn't
        # clipped by the rounded-corner window region
        self.geometry("300x244")

        # ── Title with accent underline ──
        title_label = tk.Label(
            main_frame,
            text="ตั้งค่าพื้นหลัง TUI",
            bg=self.BG_SURFACE,
            fg=self.TEXT,
            font=("Anuphan", 13, "bold"),
            anchor="w",
        )
        title_label.pack(fill=tk.X)
        # 2px accent underline below title
        underline = tk.Frame(main_frame, bg=self.ACCENT, height=2)
        underline.pack(fill=tk.X, pady=(4, 14))

        # ── Color section ──
        color_label = tk.Label(
            main_frame,
            text="สีพื้นหลัง",
            bg=self.BG_SURFACE,
            fg=self.TEXT_DIM,
            font=("Anuphan", 9),
            anchor="w",
        )
        color_label.pack(fill=tk.X)

        color_row = tk.Frame(main_frame, bg=self.BG_SURFACE)
        color_row.pack(fill=tk.X, pady=(4, 12))

        # Big preview swatch with subtle border
        swatch_wrap = tk.Frame(color_row, bg=self.BORDER)
        swatch_wrap.pack(side=tk.LEFT)
        self.color_preview = tk.Frame(
            swatch_wrap,
            bg=self.selected_color,
            width=64,
            height=26,
            cursor="hand2",
        )
        self.color_preview.pack(padx=1, pady=1)
        self.color_preview.bind("<Button-1>", self.choose_color)

        # Hex value label next to swatch
        self.color_hex_label = tk.Label(
            color_row,
            text=self.selected_color.upper(),
            bg=self.BG_SURFACE,
            fg=self.TEXT_DIM,
            font=("Consolas", 10),
        )
        self.color_hex_label.pack(side=tk.LEFT, padx=(10, 0))

        # "เปลี่ยน" hint on the right
        change_hint = tk.Label(
            color_row,
            text="คลิกเพื่อเปลี่ยน",
            bg=self.BG_SURFACE,
            fg=self.TEXT_DIM,
            font=("Anuphan", 8),
        )
        change_hint.pack(side=tk.RIGHT)

        # ── Alpha section ──
        alpha_header = tk.Frame(main_frame, bg=self.BG_SURFACE)
        alpha_header.pack(fill=tk.X)
        alpha_text = "ความโปร่งใส" + (" (ปิดอยู่)" if self.is_alpha_disabled else "")
        tk.Label(
            alpha_header,
            text=alpha_text,
            bg=self.BG_SURFACE,
            fg=self.TEXT_DIM,
            font=("Anuphan", 9),
        ).pack(side=tk.LEFT)

        # Current value badge on the right (accent color, prominent)
        self.alpha_value_label = tk.Label(
            alpha_header,
            text=f"{int(self.current_alpha * 100)}%",
            bg=self.BG_SURFACE,
            fg=self.ACCENT,
            font=("Anuphan", 11, "bold"),
        )
        self.alpha_value_label.pack(side=tk.RIGHT)

        # ── Custom Canvas-based slider ──
        # Built in-house instead of tk.Scale because we want:
        #   - bright accent handle while pressed/dragging, dim circle when at rest
        #   - step number labels (1-6) shown only during drag, hidden on release
        # Tk's Scale widget can't deliver any of that.
        self._slider_geom = {
            "w": 260, "h": 42,
            "track_y": 26,           # y-coord of the horizontal track line
            "track_left": 14,        # leftmost x usable for handle center
            "track_right": 246,      # rightmost x usable for handle center
            "handle_r": 9,           # handle circle radius (bigger = grabbier)
            "label_y": 8,            # y-coord of step number labels
        }
        g = self._slider_geom
        self.slider_canvas = tk.Canvas(
            main_frame, width=g["w"], height=g["h"],
            bg=self.BG_SURFACE, highlightthickness=0,
            cursor="hand2",
        )
        # Bigger bottom pady so the handle's bottom half stays well clear of
        # the modal's rounded-corner Win32 region clip (apply_rounded_corners
        # carves a 20×20 corner radius — handle near right edge gets eaten
        # if it's too close to the bottom)
        self.slider_canvas.pack(fill=tk.X, pady=(8, 22))

        # Step number labels (1..6), positioned above each step — hidden until drag
        self._step_label_ids = []
        n_steps = len(self.TRANSPARENCY_STEPS)
        for i in range(n_steps):
            x = g["track_left"] + (g["track_right"] - g["track_left"]) * i / (n_steps - 1)
            lbl_id = self.slider_canvas.create_text(
                x, g["label_y"],
                text=str(i + 1),
                fill=self.TEXT_DIM,
                font=("Consolas", 8, "bold"),
                state="hidden",
            )
            self._step_label_ids.append(lbl_id)

        # Track (full-length, dim)
        self._slider_track_id = self.slider_canvas.create_line(
            g["track_left"], g["track_y"], g["track_right"], g["track_y"],
            fill=self.TROUGH, width=4, capstyle=tk.ROUND,
        )
        # Filled portion (left side of handle, accent)
        self._slider_fill_id = self.slider_canvas.create_line(
            g["track_left"], g["track_y"], g["track_left"], g["track_y"],
            fill=self.ACCENT, width=4, capstyle=tk.ROUND,
        )
        # Handle (circle) — created at left, repositioned by _set_handle_x
        self._slider_handle_id = self.slider_canvas.create_oval(
            0, 0, 0, 0,
            fill=self.HANDLE_REST, outline="",
        )

        # Initial position
        self._is_dragging = False
        self._sync_slider_to_alpha()

        # Mouse events — disabled when alpha is locked (lock_mode 1)
        if not self.is_alpha_disabled:
            self.slider_canvas.bind("<Button-1>", self._on_slider_press)
            self.slider_canvas.bind("<B1-Motion>", self._on_slider_drag)
            self.slider_canvas.bind("<ButtonRelease-1>", self._on_slider_release)
            self.slider_canvas.bind("<Enter>", self._on_slider_hover_enter)
            self.slider_canvas.bind("<Leave>", self._on_slider_hover_leave)
        else:
            self.slider_canvas.config(cursor="")
            # Show all step labels permanently as a "this is locked" hint
            for lbl_id in self._step_label_ids:
                self.slider_canvas.itemconfigure(lbl_id, state="normal")

    # ────────────────── Custom slider helpers ──────────────────
    def _sync_slider_to_alpha(self):
        """Reposition the handle + fill line based on self.current_alpha."""
        if not hasattr(self, "slider_canvas"):
            return
        try:
            g = self._slider_geom
            # Find the index of current step in TRANSPARENCY_STEPS
            current_pct = int(round(self.current_alpha * 100))
            # current_pct should already be one of the steps (snapped on init)
            try:
                idx = self.TRANSPARENCY_STEPS.index(current_pct)
            except ValueError:
                idx = self.TRANSPARENCY_STEPS.index(self._snap_to_step(current_pct))
            n = len(self.TRANSPARENCY_STEPS)
            x = g["track_left"] + (g["track_right"] - g["track_left"]) * idx / (n - 1)
            self._set_handle_x(x)
        except Exception as e:
            logging.debug(f"_sync_slider_to_alpha error: {e}")

    def _set_handle_x(self, x: float):
        """Move handle to absolute canvas x — also updates the filled track."""
        g = self._slider_geom
        x = max(g["track_left"], min(g["track_right"], x))
        r = g["handle_r"]
        y = g["track_y"]
        self.slider_canvas.coords(
            self._slider_handle_id,
            x - r, y - r, x + r, y + r,
        )
        # Fill line from track_left to handle position
        self.slider_canvas.coords(
            self._slider_fill_id,
            g["track_left"], y, x, y,
        )

    def _x_to_pct(self, x: float) -> int:
        """Map canvas x to a transparency percentage (80-100)."""
        g = self._slider_geom
        x = max(g["track_left"], min(g["track_right"], x))
        ratio = (x - g["track_left"]) / max(1, g["track_right"] - g["track_left"])
        # Map 0..1 to 80..100
        return int(round(80 + ratio * 20))

    def _on_slider_hover_enter(self, _event):
        if not self._is_dragging:
            self.slider_canvas.itemconfigure(self._slider_handle_id, fill=self.HANDLE_HOVER)

    def _on_slider_hover_leave(self, _event):
        if not self._is_dragging:
            self.slider_canvas.itemconfigure(self._slider_handle_id, fill=self.HANDLE_REST)

    def _on_slider_press(self, event):
        """Press = engage drag mode: handle turns accent-bright + step labels appear."""
        self._is_dragging = True
        self.slider_canvas.itemconfigure(self._slider_handle_id, fill=self.ACCENT)
        for lbl_id in self._step_label_ids:
            self.slider_canvas.itemconfigure(lbl_id, state="normal")
        self._on_slider_drag(event)  # also process the click as a position change

    def _on_slider_drag(self, event):
        """Drag = snap value to nearest step + reposition handle."""
        raw_pct = self._x_to_pct(event.x)
        snapped = self._snap_to_step(raw_pct)
        # Always reposition handle to snapped position (magnetic feel)
        self._sync_slider_to_alpha_from_pct(snapped)
        # Apply only when value actually changes (no-op short-drag within step)
        new_alpha = snapped / 100.0
        if abs(new_alpha - self.current_alpha) >= 0.001:
            self.current_alpha = new_alpha
            self.alpha_value_label.config(text=f"{snapped}%")
            self.save_immediately()

    def _sync_slider_to_alpha_from_pct(self, pct: int):
        """Position handle + fill from a known step percentage (avoids the
        try/except round-trip in _sync_slider_to_alpha)."""
        try:
            idx = self.TRANSPARENCY_STEPS.index(pct)
        except ValueError:
            idx = 0
        g = self._slider_geom
        n = len(self.TRANSPARENCY_STEPS)
        x = g["track_left"] + (g["track_right"] - g["track_left"]) * idx / (n - 1)
        self._set_handle_x(x)

    def _on_slider_release(self, _event):
        """Release = back to rest: handle dims, step labels hide."""
        self._is_dragging = False
        self.slider_canvas.itemconfigure(self._slider_handle_id, fill=self.HANDLE_REST)
        for lbl_id in self._step_label_ids:
            self.slider_canvas.itemconfigure(lbl_id, state="hidden")

    def setup_bindings(self):
        """ตั้งค่า event bindings"""
        # คลิกข้างนอกเพื่อปิด
        self.bind("<FocusOut>", self.on_focus_out)

        # กดปุ่ม Escape เพื่อปิด
        self.bind("<Escape>", lambda e: self.close_window())

        # ตรวจจับคลิกข้างนอก
        self.bind_all("<Button-1>", self.check_click_outside)

    def choose_color(self, event=None):
        """เปิดหน้าต่างเลือกสี"""
        self._choosing_color = True
        try:
            color_info = colorchooser.askcolor(
                color=self.selected_color, parent=self, title="Choose Background Color"
            )

            if color_info and color_info[1]:
                self.selected_color = color_info[1]
                self.color_preview.config(bg=self.selected_color)
                # Sync hex label to new color
                if hasattr(self, "color_hex_label"):
                    self.color_hex_label.config(text=self.selected_color.upper())
                # บันทึกทันที
                self.save_immediately()
        except Exception as e:
            logging.error(f"Error in color chooser: {e}")
        finally:
            self._choosing_color = False
            # คืน focus หลังปิด color chooser
            self.after(100, self.focus_set)

    # Note: legacy on_alpha_change() removed — the custom Canvas slider above
    # handles snap + apply directly in _on_slider_drag(). No tk.Scale instance
    # exists anymore, so alpha_var / alpha_slider attributes are gone too.

    def save_immediately(self):
        """บันทึกค่าทันทีโดยไม่ต้องรอ"""
        try:
            final_alpha = (
                self.settings.get("bg_alpha", 1.0)
                if self.is_alpha_disabled
                else self.current_alpha
            )

            # Save to mode-specific storage
            if self.main_ui:
                mode = self.main_ui._get_current_mode_name()

                # Save color per mode
                tui_colors = self.settings.get("tui_colors", {})
                tui_colors[mode] = self.selected_color
                self.settings.set("tui_colors", tui_colors)

                # Save alpha per mode
                tui_alphas = self.settings.get("tui_alphas", {})
                tui_alphas[mode] = final_alpha
                self.settings.set("tui_alphas", tui_alphas)

                logging.info(
                    f"💾 Saved {mode} mode: Color={self.selected_color}, Alpha={final_alpha:.2f}"
                )

            # Also save to legacy keys (backward compatibility)
            self.settings.set("bg_color", self.selected_color)
            self.settings.set("bg_alpha", final_alpha)
            self.settings.save_settings()

            # เรียก callback เพื่อใช้งานทันที
            if self.apply_callback:
                self.apply_callback(self.selected_color, final_alpha)

        except Exception as e:
            logging.error(f"Error in save_immediately: {e}")

    def on_focus_out(self, event=None):
        """เมื่อหน้าต่างสูญเสีย focus"""
        # ตรวจสอบว่าไม่ใช่การเปิด color chooser
        if not self._choosing_color:
            self.close_window()

    def check_click_outside(self, event):
        """ตรวจสอบการคลิกข้างนอกหน้าต่าง"""
        if self._choosing_color:
            return

        # ถ้าคลิกข้างนอกพื้นที่หน้าต่าง ให้ปิด
        try:
            x, y = event.x_root, event.y_root
            win_x, win_y = self.winfo_rootx(), self.winfo_rooty()
            win_w, win_h = self.winfo_width(), self.winfo_height()

            if not (win_x <= x <= win_x + win_w and win_y <= y <= win_y + win_h):
                self.close_window()
        except:
            pass

    def apply_rounded_corners(self):
        """เพิ่มขอบโค้งมนสำหรับ Color Picker Dialog"""
        try:
            import win32gui
            import win32con

            # หา HWND ของหน้าต่าง
            hwnd = self.winfo_id()

            # ได้ขนาดหน้าต่าง
            width = self.winfo_width()
            height = self.winfo_height()

            # สร้าง rounded rectangle region — radius reduced from 20 to 12 so
            # corners don't clip widgets near the bottom edges (caught when the
            # canvas slider handle's bottom half got eaten by the right-bottom
            # corner clip on max-value position)
            region = win32gui.CreateRoundRectRgn(0, 0, width, height, 12, 12)

            # ใช้ region กับหน้าต่าง
            win32gui.SetWindowRgn(hwnd, region, True)

        except Exception as e:
            logging.debug(f"Could not apply rounded corners to color picker: {e}")

    def close_window(self):
        """ปิดหน้าต่าง (with race condition protection)"""
        if self._is_closing:
            return  # Already closing, prevent double-close

        self._is_closing = True

        # Schedule actual destruction after current event finishes
        # This prevents race condition with event callbacks
        self.after_idle(self._perform_destroy)

    def _perform_destroy(self):
        """Actually destroy the window (deferred to avoid race condition)"""
        try:
            if self.winfo_exists():  # Check window still exists
                self.unbind_all("<Button-1>")
                self.grab_release()
                self.destroy()
        except tk.TclError as e:
            logging.debug(f"TclError during Color Picker window close: {e}")
        except Exception as e:
            logging.error(f"Error destroying Color Picker window: {e}")

    def position_window(self, parent_widget):
        """จัดตำแหน่งหน้าต่าง - แสดงด้านบนของ parent window"""
        self.update_idletasks()

        # ได้ตำแหน่งและขนาดของ parent window
        parent_x = parent_widget.winfo_rootx()
        parent_y = parent_widget.winfo_rooty()
        parent_w = parent_widget.winfo_width()

        # Use winfo_reqwidth/reqheight (what setup_ui's geometry() requested)
        # NOT winfo_width/winfo_height — same fix as position_relative_to_button.
        win_w = self.winfo_reqwidth()
        win_h = self.winfo_reqheight()
        x = parent_x + (parent_w - win_w) // 2
        y = parent_y - win_h - 10

        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        if x + win_w > screen_w:
            x = screen_w - win_w - 10
        if y + win_h > screen_h:
            y = screen_h - win_h - 10
        if x < 0:
            x = 10
        if y < 0:
            y = 10

        # Position-only geometry — preserves the size set in setup_ui
        self.geometry(f"+{x}+{y}")

    def position_relative_to_button(self, button_widget):
        """จัดตำแหน่งหน้าต่าง - แสดงเหนือปุ่มที่ระบุ"""
        self.update_idletasks()

        # ได้ตำแหน่งและขนาดของปุ่ม
        button_x = button_widget.winfo_rootx()
        button_y = button_widget.winfo_rooty()
        button_w = button_widget.winfo_width()
        button_h = button_widget.winfo_height()

        # Use winfo_reqwidth/reqheight, NOT winfo_width/height. After setup_ui()
        # called self.geometry("300x244"), the requested size is locked but the
        # rendered size (winfo_width/height) can briefly return the natural-pack
        # size before Win32 catches up — re-applying that stale height made the
        # modal SHRINK and clipped the slider handle. reqwidth/reqheight read
        # the requested dimensions from geometry(), which is what we want.
        win_w = self.winfo_reqwidth()
        win_h = self.winfo_reqheight()
        x = button_x + (button_w - win_w) // 2  # ตรงกลางของปุ่ม
        y = button_y - win_h - 10  # เหนือปุ่ม 10px

        # ตรวจสอบไม่ให้เกินขอบจอ
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()

        if x + win_w > screen_w:
            x = screen_w - win_w - 10
        if y < 0:
            y = button_y + button_h + 10  # ถ้าไม่พอที่เหนือ ให้แสดงใต้ปุ่ม
        if x < 0:
            x = 10
        if y + win_h > screen_h:
            y = screen_h - win_h - 10

        # Position-only geometry string — preserves the size set in setup_ui
        # without being clobbered by potentially-stale winfo values.
        self.geometry(f"+{x}+{y}")
