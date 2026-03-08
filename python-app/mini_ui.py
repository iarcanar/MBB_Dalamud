import logging
import tkinter as tk
from PIL import Image, ImageDraw, ImageTk
from appearance import appearance_manager
from resource_utils import resource_path

# ── MBB Monochrome Dark Palette ──
_BG_DARK = "#1a1a1a"
_BG_DEEPER = "#141414"
_BG_HOVER = "#2a2a2a"
_BORDER_SUBTLE = "#2a2a2a"
_TEXT_SECONDARY = "#888888"
_STATUS_IDLE = "#555555"
_STATUS_ACTIVE = "#4CAF50"
_HIGHLIGHT_COLOR = "#e0e0e0"


class MiniUI:
    def __init__(self, root, show_main_ui_callback):
        self.root = root
        self.show_main_ui_callback = show_main_ui_callback
        self.blink_interval = 500
        self.blink_timer = None
        self.mini_ui = None
        self.blink_icon = None
        self.black_icon = None
        self.mini_ui_blink_label = None
        self.mini_loading_label = None
        self.mini_ui_blinking = False
        self.is_translating = False
        self.toggle_translation_callback = None

        # Icon and button references for vertical layout
        self.play_icon = None
        self.pause_icon = None
        self.play_pause_button = None

        # Status dot (PIL-rendered smooth circle)
        self._dot_label = None
        self._dot_idle_img = None
        self._dot_active_img = None

        self._create_dot_images()
        self.load_icons()
        self.create_mini_ui()

    def _create_dot_images(self):
        """Create smooth anti-aliased dot images using PIL supersampling"""
        dot_size = 10
        scale = 4  # render at 4x then downscale for smooth edges
        big = dot_size * scale
        for color_hex, attr in [(_STATUS_IDLE, "_dot_idle_img"),
                                (_STATUS_ACTIVE, "_dot_active_img")]:
            img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            r = int(color_hex[1:3], 16)
            g = int(color_hex[3:5], 16)
            b = int(color_hex[5:7], 16)
            draw.ellipse([0, 0, big - 1, big - 1], fill=(r, g, b, 255))
            img = img.resize((dot_size, dot_size), Image.LANCZOS)
            setattr(self, attr, ImageTk.PhotoImage(img))

    def load_icons(self):
        icon_size = (15, 15)
        self.blink_icon = ImageTk.PhotoImage(
            Image.open(resource_path("assets/red_icon.png")).resize(icon_size)
        )
        self.black_icon = ImageTk.PhotoImage(
            Image.open(resource_path("assets/black_icon.png")).resize(icon_size)
        )
        toggle_icon_size = (32, 32)
        self.expand_icon = ImageTk.PhotoImage(
            Image.open(resource_path("assets/expand.png")).resize(toggle_icon_size)
        )
        play_pause_size = (22, 22)
        self.play_icon = ImageTk.PhotoImage(
            Image.open(resource_path("assets/play.png")).resize(play_pause_size)
        )
        self.pause_icon = ImageTk.PhotoImage(
            Image.open(resource_path("assets/pause.png")).resize(play_pause_size)
        )

    def create_mini_ui(self):
        """Create vertical Mini UI with MBB monochrome dark theme"""
        if self.mini_ui and self.mini_ui.winfo_exists():
            self.mini_ui.destroy()

        self.mini_ui = tk.Toplevel(self.root)
        self.mini_ui.geometry("50x176")
        self.mini_ui.overrideredirect(True)
        self.mini_ui.attributes("-topmost", True)
        self.mini_ui.configure(bg=_BG_DARK)
        self.mini_ui.withdraw()

        # Main frame — 1px subtle border
        main_frame = tk.Frame(
            self.mini_ui,
            bg=_BG_DARK,
            highlightthickness=1,
            highlightbackground=_BORDER_SUBTLE,
            highlightcolor=_BORDER_SUBTLE,
        )
        main_frame.pack(expand=True, fill=tk.BOTH, padx=0, pady=0)

        # ── Expand button (top) ──
        toggle_button = tk.Button(
            main_frame,
            image=self.expand_icon,
            command=self.show_main_ui_callback,
            bg=_BG_DARK,
            activebackground=_BG_HOVER,
            bd=0,
            highlightthickness=0,
            cursor="hand2",
        )
        toggle_button.pack(side=tk.TOP, pady=(16, 10))

        # ── Play/Pause button (middle) ──
        self.play_pause_button = tk.Button(
            main_frame,
            image=self.play_icon,
            command=self._handle_toggle_translation,
            bg=_BG_DARK,
            activebackground=_BG_HOVER,
            bd=0,
            highlightthickness=0,
            cursor="hand2",
        )
        self.play_pause_button.pack(side=tk.TOP, pady=(10, 6))

        # ── Loading indicator ──
        self.mini_loading_label = tk.Label(
            main_frame,
            text="",
            bg=_BG_DARK,
            fg=_TEXT_SECONDARY,
            font=("Consolas", 8, "bold"),
        )
        self.mini_loading_label.pack(side=tk.TOP, pady=(0, 0))

        # ── Status dot (PIL anti-aliased smooth circle) ──
        self._dot_label = tk.Label(
            main_frame,
            image=self._dot_idle_img,
            bg=_BG_DARK,
            bd=0,
        )
        self._dot_label.pack(side=tk.TOP, pady=(12, 16))

        # Keep blink_label reference for API compatibility
        self.mini_ui_blink_label = self._dot_label

        # ── Hover effects ──
        def on_hover_enter(widget):
            widget.config(bg=_BG_HOVER)

        def on_hover_leave(widget):
            widget.config(bg=_BG_DARK)

        self.play_pause_button.bind("<Enter>", lambda e: on_hover_enter(self.play_pause_button))
        self.play_pause_button.bind("<Leave>", lambda e: on_hover_leave(self.play_pause_button))
        toggle_button.bind("<Enter>", lambda e: on_hover_enter(toggle_button))
        toggle_button.bind("<Leave>", lambda e: on_hover_leave(toggle_button))

        # Store toggle_button ref for theme updates
        self._toggle_button = toggle_button

        # ── Window dragging ──
        self.mini_ui.bind("<Button-1>", self.start_move_mini_ui)
        self.mini_ui.bind("<B1-Motion>", self.do_move_mini_ui)
        self.mini_ui.bind("<Double-Button-1>", lambda e: self.show_main_ui_from_mini())

        # Apply asymmetric rounded corners
        self.mini_ui.after(100, self.apply_asymmetric_rounded_corners)

    def apply_asymmetric_rounded_corners(self):
        """
        Apply rounded corners ONLY to the right side (top-right, bottom-right).
        Left side remains sharp since it touches the screen edge.
        Uses ctypes gdi32 directly (win32gui lacks CreateRectRgn).
        """
        try:
            from ctypes import windll

            gdi32 = windll.gdi32
            user32 = windll.user32
            RGN_OR = 2

            self.mini_ui.update_idletasks()
            hwnd = user32.GetParent(self.mini_ui.winfo_id())

            width = self.mini_ui.winfo_width()   # 50
            height = self.mini_ui.winfo_height()  # 176
            corner = 10  # ellipse size for ~5px radius

            # Left half: sharp rectangle (no rounding)
            left_rgn = gdi32.CreateRectRgn(0, 0, width // 2, height)

            # Right half: rounded rect, starts overlapping left to hide its left corners
            right_rgn = gdi32.CreateRoundRectRgn(
                width // 2 - corner // 2, 0,
                width + 1, height + 1,
                corner, corner,
            )

            # Combine: left sharp + right rounded
            combined = gdi32.CreateRectRgn(0, 0, 0, 0)
            gdi32.CombineRgn(combined, left_rgn, right_rgn, RGN_OR)
            user32.SetWindowRgn(hwnd, combined, True)

            # Cleanup temp regions (SetWindowRgn owns combined)
            gdi32.DeleteObject(left_rgn)
            gdi32.DeleteObject(right_rgn)

        except Exception as e:
            print(f"Error applying asymmetric rounded corners: {e}")

    def get_monitor_bounds_for_window(self, window_x, window_y):
        """
        Detect which monitor contains the given window coordinates.
        Returns the monitor's left edge X coordinate.
        """
        try:
            import ctypes
            from ctypes import wintypes, windll, Structure

            class RECT(Structure):
                _fields_ = [
                    ('left', wintypes.LONG),
                    ('top', wintypes.LONG),
                    ('right', wintypes.LONG),
                    ('bottom', wintypes.LONG)
                ]

            class MONITORINFO(Structure):
                _fields_ = [
                    ('cbSize', wintypes.DWORD),
                    ('rcMonitor', RECT),
                    ('rcWork', RECT),
                    ('dwFlags', wintypes.DWORD)
                ]

            hwnd = windll.user32.GetParent(self.root.winfo_id())
            monitor = windll.user32.MonitorFromWindow(hwnd, 2)
            info = MONITORINFO()
            info.cbSize = ctypes.sizeof(MONITORINFO)
            result = windll.user32.GetMonitorInfoW(monitor, ctypes.byref(info))

            if result:
                return info.rcMonitor.left
            return 0

        except Exception:
            return 0

    def show_loading(self):
        try:
            if hasattr(self, "mini_loading_label") and self.mini_loading_label:
                if self.mini_loading_label.winfo_exists():
                    self.mini_loading_label.config(text="...")
        except tk.TclError:
            pass
        except Exception as e:
            print(f"Error in show_loading: {e}")

    def hide_loading(self):
        try:
            if hasattr(self, "mini_loading_label") and self.mini_loading_label:
                if self.mini_loading_label.winfo_exists():
                    self.mini_loading_label.config(text="")
        except tk.TclError:
            pass
        except Exception as e:
            print(f"Error in hide_loading: {e}")

    def lighten_color(self, color, factor=1.3):
        if not isinstance(color, str) or not color.startswith("#"):
            return color
        try:
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)
            r = min(int(r * factor), 255)
            g = min(int(g * factor), 255)
            b = min(int(b * factor), 255)
            return f"#{r:02x}{g:02x}{b:02x}"
        except Exception:
            return color

    def add_highlight_border(self):
        """White border flash effect when Mini UI appears"""
        try:
            main_frame = None
            for child in self.mini_ui.winfo_children():
                if isinstance(child, tk.Frame):
                    main_frame = child
                    break

            if main_frame:
                original_color = main_frame.cget("highlightbackground")
                original_thickness = main_frame.cget("highlightthickness")

                main_frame.configure(
                    highlightthickness=2, highlightbackground=_HIGHLIGHT_COLOR
                )

                self.mini_ui.after(
                    1200,
                    lambda: main_frame.configure(
                        highlightthickness=1,
                        highlightbackground=_BORDER_SUBTLE,
                    ),
                )
        except Exception as e:
            print(f"Error adding highlight effect: {e}")

    def update_theme(self, accent_color=None, highlight_color=None):
        """Update MiniUI with MBB monochrome theme"""
        try:
            bg_c = _BG_DARK

            if not self.mini_ui or not self.mini_ui.winfo_exists():
                return

            self.mini_ui.configure(bg=bg_c)
            main_frame = None
            for child in self.mini_ui.winfo_children():
                if isinstance(child, tk.Frame):
                    main_frame = child
                    main_frame.configure(
                        bg=bg_c,
                        highlightbackground=_BORDER_SUBTLE,
                    )
                    break

            if main_frame:
                for widget in main_frame.winfo_children():
                    if isinstance(widget, tk.Button):
                        widget.configure(bg=bg_c, activebackground=_BG_HOVER)
                    elif isinstance(widget, tk.Label):
                        widget.configure(bg=bg_c)

            # Rebind hover effects
            if hasattr(self, "play_pause_button") and self.play_pause_button:
                self.play_pause_button.unbind("<Enter>")
                self.play_pause_button.unbind("<Leave>")
                self.play_pause_button.bind(
                    "<Enter>", lambda e: self.play_pause_button.config(bg=_BG_HOVER)
                )
                self.play_pause_button.bind(
                    "<Leave>", lambda e: self.play_pause_button.config(bg=bg_c)
                )

            if hasattr(self, "_toggle_button") and self._toggle_button:
                self._toggle_button.unbind("<Enter>")
                self._toggle_button.unbind("<Leave>")
                self._toggle_button.bind(
                    "<Enter>", lambda e: self._toggle_button.config(bg=_BG_HOVER)
                )
                self._toggle_button.bind(
                    "<Leave>", lambda e: self._toggle_button.config(bg=bg_c)
                )

            logging.info("MiniUI theme updated.")

        except Exception as e:
            print(f"Error updating mini UI theme: {e}")
            logging.error(f"Error updating mini UI theme: {e}")

    def _handle_toggle_translation(self):
        if self.toggle_translation_callback:
            self.toggle_translation_callback()

    def _set_status_dot(self, color):
        """Update the status dot image (smooth PIL-rendered)"""
        try:
            if self._dot_label:
                img = self._dot_active_img if color == _STATUS_ACTIVE else self._dot_idle_img
                self._dot_label.config(image=img)
        except tk.TclError:
            pass

    def update_translation_status(self, is_translating):
        """Update translation status and switch play/pause icon."""
        try:
            self.is_translating = is_translating
            self.mini_ui_blinking = is_translating

            if is_translating:
                if hasattr(self, 'play_pause_button') and self.play_pause_button:
                    self.play_pause_button.config(image=self.pause_icon)
                self._set_status_dot(_STATUS_ACTIVE)
            else:
                if hasattr(self, 'play_pause_button') and self.play_pause_button:
                    self.play_pause_button.config(image=self.play_icon)
                self._set_status_dot(_STATUS_IDLE)

            if hasattr(self, "mini_ui") and self.mini_ui.winfo_exists():
                self.mini_ui.update_idletasks()

        except tk.TclError:
            pass
        except Exception as e:
            print(f"Error in update_translation_status: {e}")

    def set_toggle_translation_callback(self, callback):
        self.toggle_translation_callback = callback

    def start_blinking(self):
        """Show solid green dot when translating"""
        try:
            self.stop_blinking()
            self.mini_ui_blinking = True
            self._set_status_dot(_STATUS_ACTIVE)
        except tk.TclError:
            pass
        except Exception as e:
            print(f"Error in start_blinking: {e}")

    def stop_blinking(self):
        """Stop and reset to idle gray dot"""
        try:
            self.mini_ui_blinking = False

            if hasattr(self, "blink_timer_id") and self.blink_timer_id:
                try:
                    if hasattr(self, "mini_ui") and self.mini_ui and self.mini_ui.winfo_exists():
                        self.mini_ui.after_cancel(self.blink_timer_id)
                except (tk.TclError, Exception):
                    pass
                self.blink_timer_id = None

            self._set_status_dot(_STATUS_IDLE)
        except tk.TclError:
            pass
        except Exception as e:
            print(f"Error in stop_blinking: {e}")

    def start_move_mini_ui(self, event):
        self.mini_x = event.x_root - self.mini_ui.winfo_x()
        self.mini_y = event.y_root - self.mini_ui.winfo_y()

    def do_move_mini_ui(self, event):
        x = event.x_root - self.mini_x
        y = event.y_root - self.mini_y
        self.mini_ui.geometry(f"+{x}+{y}")

    def show_main_ui_from_mini(self):
        if hasattr(self, "mini_ui"):
            self.mini_ui.withdraw()
        self.show_main_ui_callback()

    def position_at_center_of_main(self, main_x, main_y, main_width, main_height):
        """Position mini UI at left edge of monitor containing main UI."""
        monitor_left_edge = self.get_monitor_bounds_for_window(main_x, main_y)
        self.mini_ui.geometry(f"+{monitor_left_edge}+{main_y}")
        self.add_highlight_border()

    def blink_mini_ui(self):
        """Legacy blink animation (kept for compatibility)"""
        if (
            self.mini_ui_blinking
            and hasattr(self, "mini_ui")
            and self.mini_ui
            and self.mini_ui.winfo_exists()
        ):
            try:
                timer_val = getattr(self, "blink_timer", 0) or 0
                img = self._dot_idle_img if timer_val % 2 == 0 else self._dot_active_img
                if self._dot_label:
                    self._dot_label.config(image=img)
                self.blink_timer = timer_val + 1

                self.blink_timer_id = self.mini_ui.after(
                    self.blink_interval, self.blink_mini_ui
                )
            except Exception as e:
                print(f"Error in blink animation: {e}")
                self.stop_blinking()
        else:
            self.stop_blinking()
