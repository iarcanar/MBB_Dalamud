import re
import threading
import time
import tkinter as tk
from tkinter import ttk, colorchooser, messagebox
from PIL import ImageTk, Image, ImageDraw, ImageFilter, ImageFont
import logging
import os
import math
from typing import Optional, Dict, List, Tuple, Callable, Any, Union
from dataclasses import dataclass
from appearance import appearance_manager
from settings import Settings
from asset_manager import AssetManager
import win32gui
import win32con
import win32api
from ctypes import windll, byref, sizeof, c_int
from font_manager import FontObserver
from resource_utils import resource_path

logging.basicConfig(level=logging.INFO)


class ShadowConfig:
    """Centralized shadow configuration for TUI text rendering"""

    # *** SHADOW PARAMETERS - MODIFY HERE FOR ALL SHADOWS ***
    SHADOW_BLUR_RADIUS = 8  # From TUI_shadow_test.py - balanced combination
    SHADOW_SPREAD = 6  # From TUI_shadow_test.py - balanced combination
    SHADOW_OFFSET_X = 0  # No offset - same position as text
    SHADOW_OFFSET_Y = 0  # No offset - same position as text
    SHADOW_OPACITY = 0.8  # Shadow transparency
    SHADOW_COLOR = "#000000"  # Shadow color

    # *** INTELLIGENT SCALING ***
    BASE_FONT_SIZE = 24  # Reference font size for scaling
    SPREAD_PRESERVATION_RATIO = 0.25  # Preserve visual consistency

    @classmethod
    def get_scaled_params(cls, font_size):
        """Return shadow parameters scaled for specific font size"""
        scale_factor = font_size / cls.BASE_FONT_SIZE
        # Use square root scaling for gentler spread preservation
        spread_scale = math.sqrt(scale_factor)
        radius_scale = scale_factor * 0.8  # Slightly less aggressive radius scaling

        return {
            "blur_radius": max(2, int(cls.SHADOW_BLUR_RADIUS * radius_scale)),
            "spread": max(1, int(cls.SHADOW_SPREAD * spread_scale)),
            "offset_x": int(cls.SHADOW_OFFSET_X * spread_scale),
            "offset_y": int(cls.SHADOW_OFFSET_Y * spread_scale),
            "opacity": cls.SHADOW_OPACITY,
            "color": cls.SHADOW_COLOR,
        }


class BlurShadowEngine:
    """Advanced blur shadow system for TUI text rendering"""

    def __init__(self):
        self._shadow_cache = {}
        self.max_cache_size = 50
        self.cache_hits = 0
        self.cache_misses = 0

    def _get_cache_key(self, text, font_info, shadow_params):
        """Generate cache key for shadow texture"""
        font_str = (
            f"{font_info[0]}-{font_info[1]}"
            if isinstance(font_info, tuple)
            else str(font_info)
        )
        params_str = f"{shadow_params['blur_radius']}-{shadow_params['spread']}-{shadow_params['offset_x']}-{shadow_params['offset_y']}"
        return f"{text[:50]}-{font_str}-{params_str}"

    def _cleanup_cache(self):
        """Clean up cache when it gets too large"""
        if len(self._shadow_cache) > self.max_cache_size:
            # Remove oldest 20% of cache entries
            items_to_remove = max(1, len(self._shadow_cache) // 5)
            oldest_keys = list(self._shadow_cache.keys())[:items_to_remove]
            for key in oldest_keys:
                del self._shadow_cache[key]

    def generate_shadow_texture(self, text, font_path, font_size, shadow_params):
        """Generate blurred shadow texture using 'Blur on Solid Shape' technique"""
        try:
            # Check cache first
            cache_key = self._get_cache_key(text, (font_path, font_size), shadow_params)
            if cache_key in self._shadow_cache:
                self.cache_hits += 1
                return self._shadow_cache[cache_key]

            self.cache_misses += 1

            # Load font
            try:
                if font_path and os.path.exists(font_path):
                    font = ImageFont.truetype(font_path, font_size)
                else:
                    # Fallback to system fonts
                    fallback_fonts = [
                        "C:/Windows/Fonts/tahomabd.ttf",
                        "C:/Windows/Fonts/leelawbd.ttf",
                    ]
                    font = None
                    for fallback in fallback_fonts:
                        if os.path.exists(fallback):
                            font = ImageFont.truetype(fallback, font_size)
                            break
                    if not font:
                        font = ImageFont.load_default()
            except Exception:
                font = ImageFont.load_default()

            # Calculate image dimensions with padding for spread and blur
            padding = shadow_params["spread"] + shadow_params["blur_radius"] + 10

            # Create dummy image to measure text
            dummy_img = Image.new("RGBA", (1, 1))
            draw = ImageDraw.Draw(dummy_img)
            text_bbox = draw.textbbox(
                (0, 0), text, font=font, stroke_width=shadow_params["spread"]
            )
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]

            img_width = text_width + padding * 2
            img_height = text_height + padding * 2

            # 1. Create shadow source layer (Solid Shape)
            shadow_source = Image.new("RGBA", (img_width, img_height), (0, 0, 0, 0))
            shadow_draw = ImageDraw.Draw(shadow_source)

            # Draw both fill and stroke in shadow color to create solid shape
            # Use same position as text (no offset) following TUI_shadow_test.py
            shadow_draw.text(
                (padding - text_bbox[0], padding - text_bbox[1]),
                text,
                font=font,
                fill=shadow_params["color"],  # Fill with shadow color
                stroke_width=shadow_params["spread"],
                stroke_fill=shadow_params["color"],  # Stroke with same shadow color
            )

            # 2. Apply Gaussian blur to the solid shape
            blurred_shadow = shadow_source.filter(
                ImageFilter.GaussianBlur(radius=shadow_params["blur_radius"])
            )

            # 3. Apply additional smoothing to reduce harsh edges
            # Apply a slight blur to anti-alias edges
            blurred_shadow = blurred_shadow.filter(ImageFilter.SMOOTH)

            # 4. Apply opacity to shadow
            if shadow_params["opacity"] < 1.0:
                # Create alpha mask for opacity with smoother transition
                alpha = blurred_shadow.split()[-1]  # Get alpha channel
                alpha = alpha.point(lambda p: int(p * shadow_params["opacity"]))
                blurred_shadow.putalpha(alpha)

            # Cache the result
            self._shadow_cache[cache_key] = blurred_shadow
            self._cleanup_cache()

            return blurred_shadow

        except Exception as e:
            logging.error(f"Error generating shadow texture: {e}")
            # Return transparent image as fallback
            return Image.new("RGBA", (100, 50), (0, 0, 0, 0))

    def create_shadow_on_canvas(
        self, canvas, text, x, y, font_info, width=None, anchor="nw", tags=None
    ):
        """Create shadow directly on canvas using blur shadow technique"""
        try:
            logging.debug(
                f"Shadow creation attempt - text: '{text[:50]}...', font: {font_info}"
            )

            # Get font information
            if isinstance(font_info, tuple) and len(font_info) >= 2:
                font_name, font_size = font_info[0], font_info[1]
            else:
                font_name, font_size = "TkDefaultFont", 12

            logging.debug(f"Extracted font info - name: {font_name}, size: {font_size}")

            # Get scaled shadow parameters
            shadow_params = ShadowConfig.get_scaled_params(font_size)
            logging.debug(f"Shadow params: {shadow_params}")

            # Generate shadow texture
            shadow_texture = self.generate_shadow_texture(
                text, None, font_size, shadow_params
            )

            if shadow_texture is None:
                logging.error("Shadow texture generation returned None")
                return None

            logging.debug(f"Shadow texture size: {shadow_texture.size}")

            # Convert to PhotoImage for Tkinter
            shadow_photo = ImageTk.PhotoImage(shadow_texture)

            # Create shadow on canvas
            shadow_item = canvas.create_image(
                x, y, image=shadow_photo, anchor=anchor, tags=tags
            )

            logging.debug(f"Shadow item created on canvas: {shadow_item}")

            # Keep reference to prevent garbage collection
            if not hasattr(canvas, "_shadow_images"):
                canvas._shadow_images = []
            canvas._shadow_images.append(shadow_photo)
            # Prevent unbounded growth
            if len(canvas._shadow_images) > 50:
                canvas._shadow_images = canvas._shadow_images[-20:]

            return shadow_item

        except Exception as e:
            logging.error(f"Error creating shadow on canvas: {e}")
            import traceback

            logging.error(traceback.format_exc())
            return None


@dataclass
class UIState:
    """Class for managing UI state"""

    is_locked: bool = False
    is_typing: bool = False
    blinking: bool = False
    arrow_visible: bool = False
    arrow_blinking: bool = False
    buttons_visible: bool = True
    full_text: str = ""
    typing_timer: Optional[str] = None
    last_name: Optional[str] = None
    # เพิ่มตัวแปรใหม่สำหรับการทำ fade out
    fade_timer_id: Optional[str] = None  # เก็บ ID ของ timer
    is_fading: bool = False  # สถานะกำลัง fade out หรือไม่
    last_activity_time: float = 0  # เวลาที่มีการอัพเดตข้อความล่าสุด
    just_faded_out: bool = False  # เพิ่มตัวแปรใหม่เพื่อติดตามว่าเพิ่งมีการ fade out สมบูรณ์
    fadeout_enabled: bool = True  # เพิ่มสถานะเปิด/ปิดฟีเจอร์ fade out

    # Auto-hide TUI feature (child of fadeout)
    auto_hide_after_fade: bool = True  # ซ่อน TUI หลังจาก text fade เสร็จ (sync กับ fadeout)
    window_hide_timer_id: Optional[str] = None  # Timer สำหรับซ่อน TUI
    is_window_hidden: bool = False  # สถานะ TUI ถูกซ่อนหรือไม่


class ResizeThrottler:
    """Advanced resize throttling with adaptive delays"""

    def __init__(self, delay_ms=16):  # 60fps = 16ms
        self.delay_ms = delay_ms
        self.pending_resize = None
        self.last_resize_time = 0
        self.resize_frequency = 0
        self.adaptive_delay = delay_ms

    def throttle_resize(self, callback, *args):
        current_time = time.time() * 1000  # Convert to milliseconds

        # Calculate resize frequency for adaptive throttling
        if self.last_resize_time > 0:
            time_diff = current_time - self.last_resize_time
            self.resize_frequency = 1000 / time_diff if time_diff > 0 else 0

            # Adaptive delay: Higher frequency = longer delay
            if self.resize_frequency > 60:  # Very fast resizing
                self.adaptive_delay = 32  # 30fps
            elif self.resize_frequency > 30:  # Fast resizing
                self.adaptive_delay = 24  # 42fps
            else:
                self.adaptive_delay = self.delay_ms  # Normal 60fps

        # Cancel pending resize if exists
        if self.pending_resize:
            try:
                callback.__self__.root.after_cancel(self.pending_resize)
            except:
                pass

        # Schedule new resize with adaptive delay
        self.pending_resize = callback.__self__.root.after(
            int(self.adaptive_delay), lambda: self._execute_resize(callback, *args)
        )

        self.last_resize_time = current_time

    def _execute_resize(self, callback, *args):
        self.pending_resize = None
        callback(*args)


class TextRenderCache:
    """Intelligent caching system for text rendering"""

    def __init__(self, max_cache_size=50):
        self.text_cache = {}  # Cache rendered text layouts
        self.geometry_cache = {}  # Cache text measurements
        self.max_cache_size = max_cache_size
        self.access_times = {}  # LRU tracking

    def get_cache_key(self, text: str, width: int, font: str) -> str:
        """Generate cache key for text layout"""
        return f"{hash(text)}_{width}_{hash(font)}"

    def get_cached_layout(self, text: str, width: int, font: str) -> Optional[Dict]:
        """Get cached text layout if available"""
        cache_key = self.get_cache_key(text, width, font)

        if cache_key in self.text_cache:
            # Update access time for LRU
            self.access_times[cache_key] = time.time()
            return self.text_cache[cache_key]

        return None

    def cache_layout(self, text: str, width: int, font: str, layout_data: Dict) -> None:
        """Cache text layout with LRU management"""
        cache_key = self.get_cache_key(text, width, font)

        # Remove oldest entries if cache is full
        if len(self.text_cache) >= self.max_cache_size:
            self._cleanup_old_entries()

        # Store layout data
        self.text_cache[cache_key] = layout_data
        self.access_times[cache_key] = time.time()

    def _cleanup_old_entries(self) -> None:
        """Remove 25% of least recently used entries"""
        if not self.access_times:
            return

        # Sort by access time and remove oldest 25%
        sorted_entries = sorted(self.access_times.items(), key=lambda x: x[1])
        entries_to_remove = len(sorted_entries) // 4

        for cache_key, _ in sorted_entries[:entries_to_remove]:
            self.text_cache.pop(cache_key, None)
            self.access_times.pop(cache_key, None)


class UIComponents:
    """Class for managing UI components references"""

    def __init__(self):
        self.main_frame: Optional[tk.Frame] = None
        self.text_frame: Optional[tk.Frame] = None
        self.canvas: Optional[tk.Canvas] = None
        self.control_area: Optional[tk.Frame] = None
        self.scrollbar: Optional[ttk.Scrollbar] = None
        self.buttons: Dict[str, tk.Button] = {}
        self.text_container: Optional[int] = None  # Canvas text item ID
        self.outline_container: List[int] = []  # Canvas outline item IDs
        self.arrow_label: Optional[tk.Label] = None
        self.arrow_canvas: Optional[tk.Canvas] = None
        self.arrow_item: Optional[int] = None


class ImprovedColorAlphaPickerWindow(tk.Toplevel):
    """Color picker ใหม่ที่บันทึกทันทีและปิดเมื่อคลิกข้างนอก"""

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

        # ตั้งค่าพื้นฐาน
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(bg="#2D2D2D")
        self.resizable(False, False)

        # เก็บค่าต่างๆ
        self.selected_color = initial_color
        self.current_alpha = initial_alpha
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
        """สร้าง UI ของ Color Picker"""
        # ลดขนาดความกว้างและปรับ padding
        main_frame = tk.Frame(self, bg="#2D2D2D", padx=12, pady=12)
        main_frame.pack(expand=True, fill=tk.BOTH)

        # กำหนดขนาดหน้าต่างให้แสดง alpha slider ครบ
        self.geometry("240x170")

        # หัวข้อ
        title_label = tk.Label(
            main_frame,
            text="TUI Color Setting",
            bg="#2D2D2D",
            fg="white",
            font=("Bai Jamjuree Medium", 12, "bold"),
        )
        title_label.pack(pady=(0, 10))

        # ส่วนเลือกสี
        color_frame = tk.Frame(main_frame, bg="#2D2D2D")
        color_frame.pack(fill=tk.X, pady=5)

        tk.Label(
            color_frame,
            text="Color:",
            width=8,
            anchor="w",
            bg="#2D2D2D",
            fg="white",
            font=("Bai Jamjuree Light", 10),
        ).pack(side=tk.LEFT)

        self.color_preview = tk.Frame(
            color_frame,
            bg=self.selected_color,
            width=60,
            height=22,
            relief=tk.SOLID,
            bd=1,
            cursor="hand2",
        )
        self.color_preview.pack(side=tk.RIGHT, padx=(10, 0))
        self.color_preview.bind("<Button-1>", self.choose_color)

        # ส่วนความโปร่งใส
        alpha_frame = tk.Frame(main_frame, bg="#2D2D2D")
        alpha_frame.pack(fill=tk.X, pady=5)

        alpha_text = "Alpha:" + (" (Disabled)" if self.is_alpha_disabled else "")
        tk.Label(
            alpha_frame,
            text=alpha_text,
            width=8,
            anchor="w",
            bg="#2D2D2D",
            fg="white",
            font=("Bai Jamjuree Light", 10),
        ).pack(side=tk.LEFT)

        # Clamp alpha to 80-100% range (keep background nearly solid for readability)
        alpha_percentage = max(80, min(100, int(self.current_alpha * 100)))
        self.alpha_var = tk.IntVar(value=alpha_percentage)
        self.alpha_slider = tk.Scale(
            alpha_frame,
            from_=80,  # Minimum 80%
            to=100,    # Maximum 100%
            orient=tk.HORIZONTAL,
            variable=self.alpha_var,
            command=self.on_alpha_change,
            length=90,
            bg="#2D2D2D",
            fg="#F5F5F5",  # เปลี่ยนเป็นสีเกือบขาว
            highlightthickness=0,
            troughcolor="#E8E8E8",  # เปลี่ยนสี trough เป็นสีเกือบขาว
            activebackground="#E8E8E8",  # เอา hover effect ออก ให้เหมือนสี trough
            sliderrelief=tk.FLAT,
            showvalue=0,
            state=tk.DISABLED if self.is_alpha_disabled else tk.NORMAL,
        )
        self.alpha_slider.pack(side=tk.LEFT, padx=(10, 5))

        self.alpha_value_label = tk.Label(
            alpha_frame,
            text=f"{self.alpha_var.get()}%",
            width=4,
            bg="#2D2D2D",
            fg="white",
            font=("Consolas", 10),
        )
        self.alpha_value_label.pack(side=tk.RIGHT)

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
                # บันทึกทันที
                self.save_immediately()
        except Exception as e:
            logging.error(f"Error in color chooser: {e}")
        finally:
            self._choosing_color = False
            # คืน focus หลังปิด color chooser
            self.after(100, self.focus_set)

    def on_alpha_change(self, value):
        """เมื่อเปลี่ยนค่าความโปร่งใส"""
        val = int(float(value))
        self.alpha_value_label.config(text=f"{val}%")
        self.current_alpha = val / 100.0
        # บันทึกทันที
        self.save_immediately()

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

            # สร้าง rounded rectangle region - เพิ่มความโค้งมน
            region = win32gui.CreateRoundRectRgn(0, 0, width, height, 20, 20)

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

        # วางตรงกลางด้านบนของ parent window
        win_w = self.winfo_width()
        x = parent_x + (parent_w - win_w) // 2  # ตรงกลาง
        y = parent_y - self.winfo_height() - 10  # ด้านบน (ยกขึ้นมา)

        # ตรวจสอบไม่ให้เกินขอบจอ
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        win_w = self.winfo_width()
        win_h = self.winfo_height()

        if x + win_w > screen_w:
            x = screen_w - win_w - 10
        if y + win_h > screen_h:
            y = screen_h - win_h - 10
        if x < 0:
            x = 10
        if y < 0:
            y = 10

        self.geometry(f"{win_w}x{win_h}+{x}+{y}")

    def position_relative_to_button(self, button_widget):
        """จัดตำแหน่งหน้าต่าง - แสดงเหนือปุ่มที่ระบุ"""
        self.update_idletasks()

        # ได้ตำแหน่งและขนาดของปุ่ม
        button_x = button_widget.winfo_rootx()
        button_y = button_widget.winfo_rooty()
        button_w = button_widget.winfo_width()
        button_h = button_widget.winfo_height()

        # วางตรงกลางเหนือปุ่ม
        win_w = self.winfo_width()
        win_h = self.winfo_height()
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

        self.geometry(f"{win_w}x{win_h}+{x}+{y}")


class RichTextFormatter:
    """Rich Text Formatting System for TUI supporting *italic* text with font switching"""

    def __init__(self):
        self.italic_font_path = resource_path("fonts/FC Minimal.ttf")
        self.italic_font_name = "FC Minimal"  # ชื่อฟอนต์จริงจาก metadata

        # Dynamic italic fonts list (can be updated by external tools)
        self.italic_fonts = [
            "FC Minimal Medium",     # First choice - รองรับภาษาไทยและ italic
            "FC Minimal",            # Second choice - รองรับภาษาไทย
            "Times New Roman",       # Fallback - Windows standard
            "Arial",
            "Calibri",
            "Georgia",
            "Verdana"
        ]

    def parse_rich_text(self, text: str) -> list:
        """
        Parse text with *italic* and **bold** markers into segments with font information

        Args:
            text: Text with formatting markers like "This is *italic* and **bold** text"

        Returns:
            List of dicts with 'text' and 'font_style' keys
            Example: [
                {'text': 'This is ', 'font_style': 'normal'},
                {'text': 'italic', 'font_style': 'italic'},
                {'text': ' and ', 'font_style': 'normal'},
                {'text': 'bold', 'font_style': 'bold'},
                {'text': ' text', 'font_style': 'normal'}
            ]
        """
        logging.info(f"🔍 PARSE_RICH_TEXT: Input text = '{text}'")
        segments = []
        current_pos = 0

        import re
        # Find all patterns in order of appearance
        # **text** for bold (must be checked first to avoid conflict with *text*)
        bold_pattern = r'\*\*([^*]+)\*\*'
        # *text* for italic
        italic_pattern = r'\*([^*]+)\*'

        # Combine patterns and find all matches
        all_matches = []

        # Find bold patterns first
        for match in re.finditer(bold_pattern, text):
            all_matches.append({
                'start': match.start(),
                'end': match.end(),
                'text': match.group(1),
                'style': 'bold',
                'full_match': match.group(0)
            })

        # Find italic patterns (but exclude those already captured by bold)
        for match in re.finditer(italic_pattern, text):
            # Check if this match overlaps with any bold match
            overlaps = False
            for bold_match in all_matches:
                if (match.start() >= bold_match['start'] and match.end() <= bold_match['end']):
                    overlaps = True
                    break

            if not overlaps:
                all_matches.append({
                    'start': match.start(),
                    'end': match.end(),
                    'text': match.group(1),
                    'style': 'italic',
                    'full_match': match.group(0)
                })

        # Sort matches by position
        all_matches.sort(key=lambda x: x['start'])

        logging.info(f"🔍 PARSE_RICH_TEXT: Found {len([m for m in all_matches if m['style'] == 'italic'])} italic and {len([m for m in all_matches if m['style'] == 'bold'])} bold patterns")

        for i, match in enumerate(all_matches):
            # Add normal text before the current pattern
            if match['start'] > current_pos:
                normal_text = text[current_pos:match['start']]
                if normal_text:
                    segments.append({
                        'text': normal_text,
                        'font_style': 'normal'
                    })

            # Add formatted text
            segments.append({
                'text': match['text'],
                'font_style': match['style']
            })

            current_pos = match['end']

        # Add remaining normal text
        if current_pos < len(text):
            remaining_text = text[current_pos:]
            if remaining_text:
                segments.append({
                    'text': remaining_text,
                    'font_style': 'normal'
                })

        # If no patterns found, return the whole text as normal
        if not segments:
            segments.append({
                'text': text,
                'font_style': 'normal'
            })

        return segments

    def get_font_tuple(self, base_font_tuple, font_style: str):
        """
        Get appropriate font tuple based on style

        Args:
            base_font_tuple: Tuple like ("Anuphan", 20)
            font_style: 'normal', 'italic', 'bold', or 'name'

        Returns:
            Font tuple for tkinter
        """
        font_family, font_size = base_font_tuple

        if font_style == 'italic':
            return ("FC Minimal Medium", font_size, "italic")
        elif font_style == 'bold':
            return (font_family, font_size, "bold")
        elif font_style == 'name':
            return base_font_tuple  # Names use base font (normal weight)
        else:
            return base_font_tuple

    def has_rich_text_markers(self, text: str) -> bool:
        """Check if text contains rich text formatting markers (*italic* or **bold**)"""
        return '*' in text

    def parse_rich_text_with_names(self, text: str, names=None) -> list:
        """Parse text for *italic*, **bold**, and character names.
        Returns segments with font_style: 'normal', 'bold', 'italic', 'name'."""
        segments = self.parse_rich_text(text)
        if not names:
            return segments

        sorted_names = sorted([n for n in names if len(n) >= 2], key=len, reverse=True)
        if not sorted_names:
            return segments

        result = []
        for segment in segments:
            style = segment['font_style']
            if style in ('normal', 'italic'):
                sub_segs = self._split_text_by_names(segment['text'], sorted_names)
                for sub_type, sub_text in sub_segs:
                    if sub_type == 'name':
                        result.append({'text': sub_text, 'font_style': 'name'})
                    else:
                        result.append({'text': sub_text, 'font_style': style})
            else:
                result.append(segment)

        return result

    def _split_text_by_names(self, text: str, sorted_names: list) -> list:
        """Split text by character names with word boundary check."""
        if not sorted_names:
            return [('normal', text)]
        result = []
        remaining = text
        while remaining:
            earliest_pos = len(remaining)
            earliest_name = None
            for name in sorted_names:
                pos = remaining.find(name)
                if pos != -1 and pos < earliest_pos:
                    is_word = True
                    if pos > 0 and (remaining[pos - 1].isalnum() or remaining[pos - 1] == "'"):
                        is_word = False
                    end_pos = pos + len(name)
                    if end_pos < len(remaining) and (remaining[end_pos].isalnum() or remaining[end_pos] == "'"):
                        is_word = False
                    if is_word:
                        earliest_pos = pos
                        earliest_name = name
            if earliest_name is None:
                result.append(('normal', remaining))
                break
            if earliest_pos > 0:
                result.append(('normal', remaining[:earliest_pos]))
            result.append(('name', earliest_name))
            remaining = remaining[earliest_pos + len(earliest_name):]
        return result


class Translated_UI(FontObserver):
    """Main class for translation window UI"""

    # 🎨 ตัวแปรกลางสำหรับขอบโค้งมน - เปลี่ยนที่นี่ที่เดียว!
    ROUNDED_CORNER_RADIUS = 15  # px (6=ละเอียด, 10=ปกติ, 15=ชัดเจน, 20=โค้งมาก)

    def __init__(
        self,
        root: tk.Tk,
        toggle_translation: Callable,
        stop_translation: Callable,
        previous_dialog_callback: Callable,
        toggle_main_ui: Callable,
        toggle_ui: Callable,
        settings: Settings,
        switch_area: Callable,
        logging_manager: Any,
        character_names: Optional[set] = None,
        main_app=None,
        font_settings=None,
        toggle_npc_manager_callback=None,
        on_close_callback=None,  # ✅ เพิ่ม callback สำหรับการปิดหน้าต่าง
    ):
        self.root = root
        self.toggle_translation = toggle_translation
        self.stop_translation = stop_translation
        self.previous_dialog_callback = previous_dialog_callback
        self.toggle_main_ui = toggle_main_ui
        self.toggle_ui = toggle_ui
        self.settings = settings
        self.switch_area = switch_area
        self.logging_manager = logging_manager
        self.names = character_names or set()
        self.lock_mode = 0
        self.main_app = main_app

        # ✅ เก็บ callback ที่ได้รับมา
        self.toggle_npc_manager_callback = toggle_npc_manager_callback
        self.on_close_callback = on_close_callback  # ✅ เพิ่ม callback สำหรับการปิดหน้าต่าง
        self.previous_dialog_callback = None  # ✅ เพิ่ม callback สำหรับ Previous Dialog System
        
        # 🔍 DEBUG: Log callback status
        print(f"DEBUG: TranslatedUI initialized with toggle_npc_manager_callback: {toggle_npc_manager_callback is not None}")
        if toggle_npc_manager_callback:
            print(f"DEBUG: toggle_npc_manager_callback type: {type(toggle_npc_manager_callback)}")
        else:
            print(f"DEBUG: No NPC manager callback provided!")

        self.font_settings = font_settings
        self.state = UIState()
        self.force_hover_active = False
        self.force_hover_trigger_timer = None
        self.components = UIComponents()

        # Initialize font properties for rich text support from settings
        self.current_font_family = self.settings.get("font", "Anuphan")  # From settings
        self.current_font_size = self.settings.get("font_size", 20)  # From settings

        # *** RICH TEXT FORMATTING SYSTEM ***
        # Initialize rich text formatting system for *italic* text support
        self.rich_text_formatter = RichTextFormatter()

        # *** PHASE 1-2: TUI PERFORMANCE OPTIMIZATION ***
        # Initialize performance optimization components
        self.resize_throttler = ResizeThrottler(delay_ms=16)  # 60fps throttling
        self.text_render_cache = TextRenderCache(max_cache_size=50)

        # *** BLUR SHADOW ENGINE ***
        # Initialize advanced blur shadow system
        self.shadow_engine = BlurShadowEngine()

        self._last_safe_width = None  # Cache width to avoid unnecessary updates
        self._last_text = None  # Track text changes for differential updates

        # Frame rate monitoring
        self.frame_times = []
        self.last_frame_time = time.time()
        self.x: Optional[int] = None
        self.y: Optional[int] = None
        self.force_image = None
        self.force_m_image = None
        self.load_icons()
        self.last_resize_time = 0
        self.resize_throttle = 0.016
        self.current_bg_alpha = self.get_user_transparency()  # ใช้ centralized method

        # *** TUI AUTO HIDE ICONS SYSTEM ***
        # Initialize auto hide icons feature
        self.auto_hide_enabled = self.settings.get("tui_auto_hide_icons", {}).get("enabled", True)
        self.icons_visible = False
        self.fade_in_timer = None
        self.fade_out_timer = None
        self.hover_active = False
        self.fade_animation_id = None
        self.current_alpha = 0.0  # Start with hidden icons

        # Enhanced tracking for robust hover detection
        self.last_ui_geometry = None
        self.last_ui_position = (0, 0)
        self.last_ui_size = (0, 0)
        self.binding_refresh_timer = None
        self.hover_monitor_timer = None
        self.mouse_inside_ui = False
        self.last_mouse_position = (0, 0)
        self.ui_widgets_cache = []  # Cache of all UI widgets for binding

        # Position and size change tracking
        self.is_moving = False
        self.is_resizing = False
        self.move_end_timer = None
        self.resize_end_timer = None
        self.position_change_threshold = 5  # pixels
        self.size_change_threshold = 5  # pixels

        # Display mode tracking for dynamic TUI sizing based on ChatType
        self.current_chat_type = 61  # Default to dialogue
        self.default_width = None    # Store default width from settings
        self.default_height = None   # Store default height from settings
        self.cutscene_mode_active = False
        self.battle_mode_active = False  # Flag สำหรับ Battle Chat Mode
        self.choice_mode_active = False  # Flag สำหรับ Choice Dialog Mode
        self._deferred_render_id = None  # Timer ID for deferred text rendering after mode switch

        # Position tracking for dialogue mode
        self.dialogue_position_x = None  # Store X position before switching to cutscene
        self.dialogue_position_y = None  # Store Y position before switching to cutscene

        # Position tracking for each mode (separate memory)
        self.mode_positions = {
            "dialog": {"x": None, "y": None},
            "battle": {"x": None, "y": None},
            "cutscene": {"x": None, "y": None}
        }

        # Load saved positions from settings
        saved_positions = self.settings.get("tui_positions", {})
        for mode in ["dialog", "battle", "cutscene"]:
            if mode in saved_positions and isinstance(saved_positions[mode], dict):
                self.mode_positions[mode] = saved_positions[mode].copy()
                logging.info(f"💾 Loaded saved {mode} position: {saved_positions[mode]}")

        # Log flood prevention for clear_displayed_text
        self._text_cleared = False  # Track if text was already cleared

        self.setup_ui()
        self.setup_bindings()
        self._setup_character_name_binding()

        # Initialize auto-hide system after UI setup
        if self.auto_hide_enabled:
            self.setup_enhanced_auto_hide_system()
            # Schedule initial icon hiding after UI is fully ready
            self.root.after(100, lambda: self.set_icons_alpha(0.0))
            # Check immediate mouse position after setup
            self.root.after(200, self.check_mouse_position_immediate)

        if self.font_settings:
            self.font_settings.add_observer(self)

        logging.info("TranslatedUI initialized successfully")

    def _debug_character_click(self, event, character_name):
        """DEBUG: Handle character name click with comprehensive logging"""
        try:
            print(f"🔍 DEBUG: Character clicked - Name: '{character_name}', Event: {event}")
            print(f"🔍 DEBUG: Canvas coordinates - x: {event.x}, y: {event.y}")
            print(f"🔍 DEBUG: toggle_npc_manager_callback exists: {self.toggle_npc_manager_callback is not None}")
            
            if self.toggle_npc_manager_callback:
                print(f"🔍 DEBUG: Calling toggle_npc_manager_callback with character: '{character_name}'")
                result = self.toggle_npc_manager_callback(character_name)
                print(f"🔍 DEBUG: toggle_npc_manager_callback returned: {result}")
            else:
                print(f"🔍 DEBUG: No toggle_npc_manager_callback available!")
                
            # Also log to the logging manager if available
            if hasattr(self, 'logging_manager') and self.logging_manager:
                self.logging_manager.log_info(f"Character name clicked: {character_name}")
                
        except Exception as e:
            print(f"❌ DEBUG ERROR: Error handling character click: {e}")
            import traceback
            print(f"❌ DEBUG TRACEBACK: {traceback.format_exc()}")
            
            # Try to show error with messagebox if available
            try:
                from tkinter import messagebox
                messagebox.showerror("Character Click Error", f"Error handling character click: {e}")
            except ImportError:
                print(f"❌ DEBUG: Cannot import messagebox to show error dialog")
            except Exception as inner_e:
                print(f"❌ DEBUG: Error showing messagebox: {inner_e}")

    def _trigger_delayed_hover_force(self):
        """
        ถูกเรียกหลังจาก hover delay เพื่อสั่ง force translate จริงๆ
        และตรวจสอบอีกครั้งว่ายังควรสั่งทำงานหรือไม่ (เมาส์ยังอยู่บนปุ่ม)
        """
        try:
            # ตรวจสอบว่าเมาส์ยังอยู่บนปุ่ม force หรือไม่ (เป็นการตรวจสอบซ้ำอีกชั้น)
            force_button = self.components.buttons.get("force")
            if not force_button or not force_button.winfo_exists():
                self.force_hover_trigger_timer = None
                return

            # หากเมาส์ยังอยู่บนปุ่ม (ตรวจสอบจาก state ของปุ่ม widget)
            # วิธีตรวจสอบว่าเมาส์ยังอยู่บน widget นั้นซับซ้อนเล็กน้อยถ้าจะทำอย่างแม่นยำ
            # เราอาจจะใช้ state ง่ายๆ ที่ตั้งไว้ตอน on_enter และเคลียร์ตอน on_leave
            # หรือในที่นี้ เราจะถือว่าถ้า timer ไม่ถูก cancel ก็คือยังต้องการให้ทำงาน
            if (
                self.force_hover_active and self.force_hover_trigger_timer is not None
            ):  # ตรวจสอบ timer ด้วย
                # Previous dialog called from right-click
                self.show_previous_dialog()

            self.force_hover_trigger_timer = None  # เคลียร์ timer หลังทำงาน
        except Exception as e:
            logging.error(f"Error in _trigger_delayed_hover_force: {e}")
            self.force_hover_trigger_timer = None

    def on_font_changed(self, font_name: str, font_size: int) -> None:
        """
        รับการแจ้งเตือนเมื่อมีการเปลี่ยนแปลงฟอนต์

        Args:
            font_name: ชื่อฟอนต์ใหม่
            font_size: ขนาดฟอนต์ใหม่
        """
        try:
            # อัพเดตฟอนต์ในหน้าต่างแสดงผลการแปล
            self.update_font(font_name)
            self.adjust_font_size(font_size)
            logging.info(f"TranslatedUI: อัพเดตฟอนต์เป็น {font_name} ขนาด {font_size}")
        except Exception as e:
            logging.error(f"TranslatedUI: เกิดข้อผิดพลาดในการอัพเดตฟอนต์: {e}")

    def create_rounded_rectangle(self, canvas, x1, y1, x2, y2, radius=25, **kwargs):
        """
        สร้างสี่เหลี่ยมมุมโค้งใน Canvas

        Args:
            canvas: Canvas ที่จะวาด
            x1, y1: พิกัดมุมบนซ้าย
            x2, y2: พิกัดมุมล่างขวา
            radius: รัศมีของมุมโค้ง
            **kwargs: พารามิเตอร์เพิ่มเติมสำหรับ create_polygon

        Returns:
            int: ID ของรูปที่วาด
        """
        points = [
            x1 + radius,
            y1,
            x2 - radius,
            y1,
            x2,
            y1,
            x2,
            y1 + radius,
            x2,
            y2 - radius,
            x2,
            y2,
            x2 - radius,
            y2,
            x1 + radius,
            y2,
            x1,
            y2,
            x1,
            y2 - radius,
            x1,
            y1 + radius,
            x1,
            y1,
        ]

        return canvas.create_polygon(points, **kwargs, smooth=True)

    def load_icons(self) -> None:
        """Load and prepare all required icons"""
        try:
            # Load confirm icon for character names
            self.confirm_icon = AssetManager.load_icon("confirm.png", (28, 28))

            # Load lock/unlock icons
            button_size = 20
            force_button_size = 25  # เพิ่มขนาดปุ่ม Force เป็น 25px

            # โหลดไอคอนตามไฟล์ที่กำหนดใหม่
            # สถานะปกติแสดงพื้นหลัง ขยับได้
            self.unlock_image = AssetManager.load_icon(
                "normal.png", (button_size, button_size)
            )

            # สถานะซ่อนพื้นหลังและล็อกด้วย
            self.bg_lock_trans_image = AssetManager.load_icon(
                "lock.png", (button_size, button_size)
            )

            # สถานะล็อก+แสดงพื้นหลัง
            self.bg_lock_image = AssetManager.load_icon(
                "BG_lock.png", (button_size, button_size)
            )

            # คงไว้สำหรับความเข้ากันได้กับโค้ดเดิม - อาจใช้ในส่วนอื่น
            self.lock_image = self.unlock_image

            # ใช้ไฟล์ force.png ที่มีอยู่ - ปรับขนาดให้ใหญ่ขึ้น
            self.force_image = AssetManager.load_icon(
                "s_force.png", (force_button_size, force_button_size)
            )

            # เพิ่มการโหลดไอคอนใหม่ s_force_m.png
            try:
                self.force_m_image = AssetManager.load_icon(
                    "s_force_m.png", (force_button_size, force_button_size)
                )
            except Exception as e:
                logging.error(f"Error loading s_force_m.png: {e}")
                self.force_m_image = (
                    self.force_image
                )  # Fallback to original if not found

            # โหลดรูปภาพ fade.png สำหรับปุ่ม fade out
            self.fadeout_image = AssetManager.load_icon(
                "fade.png", (button_size, button_size)
            )

            # ★ เพิ่ม: โหลดไอคอน TUI_BG.png สำหรับปุ่ม color picker
            try:
                self.tui_bg_image = AssetManager.load_icon(
                    "TUI_BG.png", (button_size, button_size)
                )
            except Exception as e:
                logging.error(f"Error loading TUI_BG.png: {e}")
                # สร้างไอคอนสำรองถ้าโหลดไม่ได้
                self.tui_bg_image = None

            # โหลดรูปภาพลูกศรแบบปกติ
            self.arrow_image = AssetManager.load_icon("arrow.png", (20, 20))

        except Exception as e:
            logging.error(f"Error loading icons: {e}")
            self.confirm_icon = None
            self.arrow_image = None
            self.fadeout_image = None
            self.tui_bg_image = None
            # Set fallback icon values if needed

    def apply_rounded_corners_to_ui(self, radius=None, clear_first=False):
        """🎨 ทำให้หน้าต่าง UI มีขอบโค้งมนแบบละเอียด

        Args:
            radius: รัศมีของขอบโค้ง (None = ใช้ค่า default จาก ROUNDED_CORNER_RADIUS)
            clear_first: ล้าง region เดิมก่อนสร้างใหม่ (สำหรับการ resize)
        """
        # ใช้ค่า default ถ้าไม่ระบุ
        if radius is None:
            radius = self.ROUNDED_CORNER_RADIUS
        try:
            # 🔒 เพิ่ม: ป้องกันการเรียกซ้ำขณะที่ยังทำงานอยู่
            if (
                hasattr(self, "_applying_rounded_corners")
                and self._applying_rounded_corners
            ):
                logging.debug("🔄 กำลังทำ rounded corners อยู่แล้ว - ข้าม")
                return

            # 🔒 เพิ่ม: Throttling - ไม่ให้เรียกบ่อยเกินไป
            import time

            current_time = time.time()
            if hasattr(self, "_last_rounded_corners_time"):
                time_diff = current_time - self._last_rounded_corners_time
                if time_diff < 0.05:  # ห้ามเรียกบ่อยกว่า 50ms
                    logging.debug(
                        f"🕒 Throttling rounded corners (เหลือ {0.05 - time_diff:.2f}s)"
                    )
                    return

            self._applying_rounded_corners = True
            self._last_rounded_corners_time = current_time

            logging.info(f"🎨 เริ่มใส่ขอบโค้งมน radius {radius}px...")

            # รอให้หน้าต่างแสดงผลและ settle ก่อน
            self.root.update_idletasks()

            # ดึงค่า HWND ของหน้าต่าง
            hwnd = windll.user32.GetParent(self.root.winfo_id())
            logging.info(f"🪟 HWND ที่ได้: {hwnd}")

            if hwnd:
                # Clear existing region first if requested
                if clear_first:
                    try:
                        win32gui.SetWindowRgn(hwnd, 0, True)
                        logging.debug("🧹 ล้าง region เดิมแล้ว")
                    except Exception as clear_error:
                        logging.warning(f"⚠️ ไม่สามารถล้าง region เดิม: {clear_error}")

                # สร้างภูมิภาค (region) โค้งมนตามขนาดปัจจุบัน
                width = self.root.winfo_width()
                height = self.root.winfo_height()
                logging.info(f"📏 ขนาดหน้าต่าง: {width}x{height}")

                # สร้าง rounded rectangle region
                region = win32gui.CreateRoundRectRgn(
                    0, 0, width + 1, height + 1, radius, radius
                )

                if region and region != 0:  # 🔒 เพิ่ม: ตรวจสอบว่า region ถูกสร้างสำเร็จ
                    logging.info(f"🔄 สร้าง region: {region}")

                    # ใช้ region กับหน้าต่าง
                    result = win32gui.SetWindowRgn(hwnd, region, True)
                    logging.info(f"✅ SetWindowRgn ผลลัพธ์: {result}")

                    # 🔒 หมายเหตุ: ไม่ต้อง DeleteObject หลัง SetWindowRgn
                    # เพราะ Windows จะเป็นเจ้าของและจัดการ region เองโดยอัตโนมัติ
                    # การเรียก DeleteObject จะทำให้เกิด warning

                    logging.info(f"🎊 ใส่ขอบโค้งมนสำเร็จ! radius={radius}px")
                else:
                    logging.error("❌ ไม่สามารถสร้าง region ได้")
            else:
                logging.warning("⚠️ ไม่พบ HWND หน้าต่าง")

        except Exception as e:
            # ไม่ให้ error นี้ทำให้โปรแกรมหยุดทำงาน
            logging.error(f"❌ Error applying rounded corners to UI: {e}")
            import traceback

            traceback.print_exc()
        finally:
            # 🔒 เพิ่ม: ปล่อย lock ในทุกกรณี
            self._applying_rounded_corners = False

    def get_user_transparency(self):
        """Get user's transparency setting from color picker"""
        return self.settings.get("bg_alpha", 0.97)  # Default 97%

    def restore_user_transparency(self):
        """Restore TUI transparency to user's setting"""
        alpha = self.get_user_transparency()
        self.root.attributes("-alpha", alpha)
        self.current_bg_alpha = alpha  # Sync instance variable
        logging.info(f"Restored user transparency: {alpha:.2f}")

    def setup_ui(self) -> None:
        """Initialize and setup all UI components"""
        self.root.title("Translated Text")

        # Store default dimensions for display mode switching
        self.default_width = self.settings.get('width')
        self.default_height = self.settings.get('height')

        self.root.geometry(
            f"{self.default_width}x{self.default_height}"
        )
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bd=0, highlightthickness=0)  # กำหนดกรอบเป็น 0

        # Main frame setup (*** ไม่ต้องตั้ง bg ที่นี่ ***)
        self.components.main_frame = tk.Frame(
            self.root,
            bd=0,
            highlightthickness=0,
        )
        self.components.main_frame.pack(fill=tk.BOTH, expand=True)

        # Text frame setup (*** ไม่ต้องตั้ง bg ที่นี่ ***)
        self.components.text_frame = tk.Frame(
            self.components.main_frame,
            bd=0,
            highlightthickness=0,
            # Removed width setting, let it expand
        )
        self.components.text_frame.pack(
            side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0)
        )  # ลด padx ขวา

        # Control frame setup (*** ไม่ต้องตั้ง bg ที่นี่ ***)
        self.components.control_area = tk.Frame(
            self.components.main_frame,
            bd=0,
            highlightthickness=0,
            width=30,  # เพิ่มความกว้างเล็กน้อยสำหรับปุ่ม
        )
        self.components.control_area.pack(
            side=tk.RIGHT, fill=tk.Y, padx=(0, 5)
        )  # เพิ่ม padx ขวาเล็กน้อย
        self.components.control_area.pack_propagate(False)

        # Setup main components
        self.setup_canvas_and_text()
        self.setup_scrollbar()
        self.setup_buttons()
        self.setup_window_resizing()

        # *** เพิ่ม: เรียกใช้ _apply_background_color_and_alpha เพื่อตั้งค่าพื้นหลังเริ่มต้น ***
        # ดึงค่าสีและ alpha ปัจจุบันจาก settings หรือค่า default
        initial_bg = self.settings.get("bg_color", appearance_manager.bg_color)
        initial_alpha = self.get_user_transparency()  # ใช้ centralized method
        self.current_bg_alpha = initial_alpha  # อัพเดทค่า alpha ปัจจุบันใน instance ด้วย

        # เรียกใช้เมธอดเพื่อกำหนดค่าเริ่มต้น (สำคัญ)
        self._apply_background_color_and_alpha(initial_bg, initial_alpha)

        # ★ หมายเหตุ: ไม่ต้องอัพเดตสีปุ่ม color picker เพราะใช้ไอคอน TUI_BG.png แล้ว

        # 🎨 เพิ่ม: ใส่ขอบโค้งมนแบบละเอียดหลังจาก setup UI เสร็จสิ้น
        self.root.after(50, self.apply_rounded_corners_to_ui)

    def _get_current_mode_name(self):
        """Return current mode name: 'dialog', 'battle', 'cutscene', or 'choice'"""
        if getattr(self, 'choice_mode_active', False):
            return "choice"
        elif self.battle_mode_active:
            return "battle"
        elif self.cutscene_mode_active:
            return "cutscene"
        else:
            return "dialog"

    def _save_current_position_to_settings(self):
        """Save current TUI position for current mode to settings"""
        try:
            mode = self._get_current_mode_name()
            x = self.root.winfo_x()
            y = self.root.winfo_y()

            # Update memory
            self.mode_positions[mode] = {"x": x, "y": y}

            # Update settings
            tui_positions = self.settings.get("tui_positions", {})
            tui_positions[mode] = {"x": x, "y": y}
            self.settings.set("tui_positions", tui_positions)
            self.settings.save_settings()

            logging.info(f"💾 Saved {mode} position: x={x}, y={y}")
        except Exception as e:
            logging.error(f"Error saving position: {e}")

    def _load_mode_settings(self, mode):
        """Load color and alpha for specified mode (size is auto-calculated per mode)"""
        try:
            logging.info(f"📂 Loading settings for {mode} mode")

            # Load color & alpha only (NOT size - each mode uses auto-calculated size)
            tui_colors = self.settings.get("tui_colors", {})
            tui_alphas = self.settings.get("tui_alphas", {})

            color = tui_colors.get(mode, "#0a0a0f")
            alpha = tui_alphas.get(mode, 0.97)

            self._apply_background_color_and_alpha(color, alpha)

            # Update instance variables
            self.current_bg_color = color
            self.current_bg_alpha = alpha

            logging.info(f"  Color: {color}, Alpha: {alpha}")
        except Exception as e:
            logging.error(f"Error loading mode settings: {e}")

    def set_display_mode_for_chat_type(self, chat_type: int):
        """
        Adjust TUI display based on chat type with full customization
        Supports: size, background color, transparency, and lock mode

        Args:
            chat_type: The ChatType from text hook
                61 = Dialogue (default settings)
                71 = Cutscene (80% width, optional background changes)

        Returns:
            bool: True if geometry changed, False if mode was already correct
        """
        try:
            # Skip if already in correct mode
            if self.current_chat_type == chat_type:
                return False

            # 🔧 FIX: Clear canvas when leaving choice mode to prevent ghost visuals
            # Choice text stays visible during the 50ms defer window before new text renders
            was_choice_mode = getattr(self, 'choice_mode_active', False)
            prev_chat_type = self.current_chat_type

            # 💾 Save current mode position BEFORE switching
            if self.root.winfo_exists():
                self._save_current_position_to_settings()

            self.current_chat_type = chat_type
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()

            if chat_type == 68 and self.settings.get("enable_battle_chat_mode", True):
                # ========== BATTLE CHAT MODE ==========
                # บันทึกตำแหน่งเดิม
                if not self.battle_mode_active and not self.cutscene_mode_active:
                    self.dialogue_position_x = self.root.winfo_x()
                    self.dialogue_position_y = self.root.winfo_y()
                    logging.info(f"💾 Saved dialogue position: ({self.dialogue_position_x}, {self.dialogue_position_y})")

                # ความกว้าง 60%
                new_width = int(screen_width * 0.6)

                # ความสูงสำหรับ 2 บรรทัด (ประมาณ 100-120px)
                font_size = self.settings.get("font_size", 24) + 2
                line_height = font_size * 1.4
                new_height = int(line_height * 2 + 60)  # 2 lines + extra padding (increased from 40)

                # 🎯 Use saved position OR default position
                saved_pos = self.mode_positions["battle"]
                if saved_pos["x"] is not None and saved_pos["y"] is not None:
                    x = saved_pos["x"]
                    y = saved_pos["y"]
                    logging.info(f"⚔️ Using saved battle position: ({x}, {y})")
                else:
                    # Default: 10% from top, centered
                    x = (screen_width - new_width) // 2
                    y = int(screen_height * 0.10)
                    logging.info(f"⚔️ Using default battle position: ({x}, {y})")

                self.root.resizable(True, True)
                self.root.geometry(f"{new_width}x{new_height}+{x}+{y}")
                self.root.resizable(False, False)

                self.battle_mode_active = True
                self.cutscene_mode_active = False
                self.choice_mode_active = False

                # Load battle mode settings (color, alpha)
                self._load_mode_settings("battle")

                logging.info(f"⚔️ Switched to BATTLE CHAT mode: {new_width}x{new_height} at ({x}, {y})")

            elif chat_type == 71:  # Cutscene mode
                # บันทึกตำแหน่งปัจจุบันก่อนสลับ (เฉพาะครั้งแรก)
                if not self.cutscene_mode_active:
                    self.dialogue_position_x = self.root.winfo_x()
                    self.dialogue_position_y = self.root.winfo_y()
                    logging.info(f"💾 Saved dialogue position: ({self.dialogue_position_x}, {self.dialogue_position_y})")

                # ========== SIZE CHANGES ==========

                # ความกว้าง 90%
                new_width = int(screen_width * 0.9)

                # ความสูงสำหรับ 2 บรรทัด (เหมือน Battle mode แต่สูงกว่า 30px)
                font_size = self.settings.get("font_size", 24) + 2
                line_height = font_size * 1.4
                new_height = int(line_height * 2 + 90)  # 2 lines + extra padding (increased by 30px)

                # 🎯 Use saved position OR default position
                saved_pos = self.mode_positions["cutscene"]
                if saved_pos["x"] is not None and saved_pos["y"] is not None:
                    x = saved_pos["x"]
                    y = saved_pos["y"]
                    logging.info(f"🎬 Using saved cutscene position: ({x}, {y})")
                else:
                    # Default: bottom of screen, centered
                    x = (screen_width - new_width) // 2
                    bottom_margin = int(screen_height * 0.05)  # 5% margin from bottom
                    y = screen_height - new_height - bottom_margin
                    logging.info(f"🎬 Using default cutscene position: ({x}, {y})")

                # CRITICAL: Unlock window before resizing
                self.root.resizable(True, False)  # Allow horizontal resize only
                self.root.geometry(f"{new_width}x{new_height}+{x}+{y}")
                self.root.resizable(False, False)  # Lock back after resize

                # Load cutscene mode settings (color, alpha)
                self._load_mode_settings("cutscene")

                # ========== BACKGROUND CHANGES (OPTIONAL) ==========
                # Option 1: Keep user settings (recommended for v1)
                # No background changes - use existing settings

                # Option 2: Apply cutscene-specific background (for future)
                # Uncomment to enable:
                # cutscene_bg_color = "#1a1a1a"  # Darker background
                # cutscene_alpha = 0.85          # Slightly more transparent
                # cutscene_lock_mode = 0         # Normal mode
                # self._apply_background_color_and_alpha(cutscene_bg_color, cutscene_alpha)
                # self.lock_mode = cutscene_lock_mode

                # Option 3: Transparent cutscene mode (for future)
                # Uncomment to enable:
                # self._apply_background_color_and_alpha("#000000", 0.0)
                # self.lock_mode = 1  # Hidden background mode

                self.cutscene_mode_active = True
                self.battle_mode_active = False
                self.choice_mode_active = False
                logging.info(f"🎬 Switched to CUTSCENE mode: {new_width}x{new_height} at ({x}, {y})")

            elif chat_type == 70:  # Choice mode (0x0046)
                # ========== CHOICE MODE ==========
                # Same size as dialog but positioned ABOVE current dialog position
                # so it doesn't block the in-game choice buttons

                # Get current dialog position as reference
                current_y = self.root.winfo_y()
                current_x = self.root.winfo_x()
                current_height = self.root.winfo_height()

                # Calculate height for choice display (needs more lines)
                font_size = self.settings.get("font_size", 24) + 2
                line_height = font_size * 1.4
                # Header + up to 4 choices + padding
                choice_height = int(line_height * 5 + 60)

                # Position above the current dialog position
                choice_y = current_y - choice_height - 10  # 10px gap above dialog
                if choice_y < 0:
                    choice_y = 10  # Don't go off screen

                self.root.resizable(True, True)
                self.root.geometry(f"{self.default_width}x{choice_height}+{current_x}+{choice_y}")
                self.root.resizable(False, False)

                self.choice_mode_active = True
                self.cutscene_mode_active = False
                self.battle_mode_active = False
                logging.info(f"🎯 Switched to CHOICE mode: {self.default_width}x{choice_height} at ({current_x}, {choice_y})")

            else:  # Dialogue mode (61) or default
                # ========== RESTORE DEFAULT SETTINGS ==========
                # 🎯 Use saved position OR default position
                saved_pos = self.mode_positions["dialog"]
                if saved_pos["x"] is not None and saved_pos["y"] is not None:
                    restore_x = saved_pos["x"]
                    restore_y = saved_pos["y"]
                    logging.info(f"💬 Using saved dialog position: ({restore_x}, {restore_y})")
                else:
                    # Default: bottom of screen, centered
                    restore_x = (screen_width - self.default_width) // 2
                    bottom_margin = int(screen_height * 0.05)  # 5% margin from bottom
                    restore_y = screen_height - self.default_height - bottom_margin
                    logging.info(f"💬 Using default dialog position: ({restore_x}, {restore_y})")

                # CRITICAL: Unlock window before resizing
                self.root.resizable(True, False)  # Allow horizontal resize only
                self.root.geometry(f"{self.default_width}x{self.default_height}+{restore_x}+{restore_y}")
                self.root.resizable(False, False)  # Lock back after resize

                # Load dialog mode settings (color, alpha)
                self._load_mode_settings("dialog")

                # Restore background settings (if they were changed in cutscene mode)
                # If cutscene mode changed background, restore here:
                # default_bg = self.settings.get("bg_color", appearance_manager.bg_color)
                # default_alpha = self.get_user_transparency()
                # self._apply_background_color_and_alpha(default_bg, default_alpha)
                # self.lock_mode = 0

                self.cutscene_mode_active = False
                self.battle_mode_active = False
                self.choice_mode_active = False
                logging.info(f"💬 Switched to DIALOGUE mode: {self.default_width}x{self.default_height} at ({restore_x}, {restore_y})")

            # 🔧 FIX: Clear canvas when switching away from choice mode
            # This prevents stale choice text from being visible during the
            # 50ms defer window before new text renders
            if was_choice_mode and chat_type != 70:
                if hasattr(self.components, 'canvas') and self.components.canvas:
                    self.components.canvas.delete("all")
                    self.components.outline_container = []
                    self.components.text_container = None
                    logging.info("🧹 Cleared canvas on exit from choice mode")

            # CRITICAL: Force Tk to process geometry change immediately
            # Without this, winfo_width() returns stale values and text
            # centering in battle/cutscene mode uses the OLD window width
            self.root.update_idletasks()

            # CRITICAL: Reconfigure text width to match new window size
            if hasattr(self.components, 'text_container') and self.components.text_container:
                new_text_width = int(self.root.winfo_width() * 0.95)
                self.components.canvas.itemconfig(self.components.text_container, width=new_text_width)
                logging.info(f"🔧 Reconfigured text width to: {new_text_width}px")

            # 🎨 CRITICAL: Reapply rounded corners after geometry change
            # Without this, corners become square after mode switching
            self.root.after(100, self.apply_rounded_corners_to_ui)
            logging.info(f"🎨 Scheduled rounded corners reapplication after mode switch")

            return True  # Geometry changed

        except Exception as e:
            logging.error(f"Error setting display mode for ChatType {chat_type}: {e}")
            return False

    def _get_text_color(self):
        """Return text color based on current mode"""
        if self.battle_mode_active:
            logging.info("⚔️ Battle mode active - using orange text (#FF6B00)")
            return "#FF6B00"  # ส้มสด (Vibrant Orange)
        elif self.cutscene_mode_active:
            logging.info("🎬 Cutscene mode active - using gold text (#FFD700)")
            return "#FFD700"  # ทอง (Gold)
        else:
            logging.info("💬 Dialogue mode active - using white text")
            return "white"

    def _get_text_anchor(self):
        """Return text anchor based on current mode"""
        if self.battle_mode_active or self.cutscene_mode_active:
            return "n"  # North = center-aligned
        else:
            return "nw"  # Northwest = left-aligned

    def _needs_rich_text(self, text: str) -> bool:
        """Check if text needs rich text processing (has markers OR character names)"""
        if '*' in text:
            return True
        if hasattr(self, 'names') and self.names:
            for name in self.names:
                if len(name) >= 2 and name in text:
                    return True
        return False

    def _create_text_shadows(self, x, y, anchor, font, text="",
                             width=None, tags=None):
        """Create text shadow using canvas multi-ring outlines.

        Returns list of canvas item IDs.
        """
        return self._create_text_shadows_canvas(x, y, anchor, font, text, width, tags)

    def _create_text_shadows_canvas(self, x, y, anchor, font, text="",
                                    width=None, tags=None):
        """FALLBACK: Canvas multi-ring text outlines (revert target).

        Lock mode 1: circular 3-ring graduated shadow.
        Other modes: standard 8-point thin outline.
        """
        canvas = self.components.canvas
        ids = []

        if getattr(self, 'lock_mode', 0) == 1:
            layers = [
                ([(-3, 0), (3, 0), (0, -3), (0, 3),
                  (-2, -2), (2, -2), (-2, 2), (2, 2),
                  (-3, -1), (3, -1), (-3, 1), (3, 1),
                  (-1, -3), (1, -3), (-1, 3), (1, 3)],
                 "#111111"),
                ([(-2, 0), (2, 0), (0, -2), (0, 2),
                  (-2, -1), (2, -1), (-2, 1), (2, 1),
                  (-1, -2), (1, -2), (-1, 2), (1, 2)],
                 "#080808"),
                ([(-1, -1), (-1, 0), (-1, 1),
                  (0, -1),           (0, 1),
                  (1, -1),  (1, 0),  (1, 1)],
                 "#000000"),
            ]
        else:
            layers = [
                ([(-1, -1), (-1, 0), (-1, 1),
                  (0, -1),           (0, 1),
                  (1, -1),  (1, 0),  (1, 1)],
                 "#000000"),
            ]

        kwargs = {"anchor": anchor, "font": font, "text": text}
        if width is not None:
            kwargs["width"] = width
        if tags is not None:
            kwargs["tags"] = tags

        for positions, color in layers:
            for dx, dy in positions:
                item = canvas.create_text(
                    x + dx, y + dy, fill=color, **kwargs)
                ids.append(item)
        return ids

    def setup_canvas_and_text(self) -> None:
        """Setup canvas and text display area with fonts and styling"""

        # Canvas setup (*** ไม่ต้องตั้ง bg ที่นี่ ***)
        self.components.canvas = tk.Canvas(
            self.components.text_frame,
            bd=0,
            highlightthickness=0,
            relief="flat",
        )
        self.components.canvas.pack(
            side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 50), pady=(10, 20)
        )

        # Initialize text properties (เหมือนเดิม)
        font_name = self.settings.get("font", "Anuphan")
        font_size = self.settings.get("font_size", 24)
        text_width = int(self.root.winfo_width() * 0.95)

        # สร้าง text container (เหมือนเดิม)
        self.components.text_container = self.components.canvas.create_text(
            10,
            10,
            anchor="nw",
            font=(font_name, font_size),
            fill=appearance_manager.fg_color,
            width=text_width,
            text="",
        )
        self.components.outline_container = []

        # สร้าง Canvas สำหรับลูกศร (*** ไม่ต้องตั้ง bg ที่นี่ ***)
        arrow_canvas_width = 20
        arrow_canvas_height = 20
        self.components.arrow_canvas = tk.Canvas(
            self.components.text_frame,
            width=arrow_canvas_width,
            height=arrow_canvas_height,
            highlightthickness=0,
            bd=0,
        )

        # สร้างรูปภาพลูกศร (เหมือนเดิม)
        self.components.arrow_item = self.components.arrow_canvas.create_image(
            arrow_canvas_width // 2,
            arrow_canvas_height // 2,
            image=self.arrow_image,
            anchor="center",
        )

        # วางตำแหน่งและซ่อนตอนเริ่มต้น (เหมือนเดิม)
        self.components.arrow_canvas.place(relx=0.85, rely=0.85, anchor="center")
        self.components.arrow_canvas.place_forget()

        # *** ไม่ต้องเรียก _apply_background_color_and_alpha ที่นี่ เพราะ setup_ui เรียกแล้ว ***

    def setup_scrollbar(self) -> None:
        """Setup and configure custom scrollbar with minimal flat design"""
        # กำหนดสีพื้นหลังปัจจุบันจาก settings
        bg_color = self.settings.get("bg_color", appearance_manager.bg_color)

        # ตั้งค่าความกว้างเริ่มต้นและความกว้างเมื่อขยายของ scrollbar
        self.scrollbar_default_width = 4
        self.scrollbar_expanded_width = 15  # ความกว้างที่ขยายแล้ว
        self.scrollbar_expansion_zone = 30  # ระยะห่างจากขอบขวาที่จะเริ่มตรวจจับเมาส์ (px)
        self.scrollbar_is_expanded = False  # สถานะการขยาย
        self.scrollbar_resize_timer = None  # timer สำหรับการหน่วงเวลาก่อนหด
        self.scrollbar_animation_timer = None  # timer สำหรับการทำ animation
        self.scrollbar_current_width = self.scrollbar_default_width  # ความกว้างปัจจุบัน
        self.scrollbar_animation_step = 0  # ขั้นตอนของ animation
        self.scrollbar_animation_steps = 10  # จำนวนขั้นตอนทั้งหมดของ animation
        self.scrollbar_animation_speed = 15  # ความเร็วของ animation (ms)
        self.scrollbar_updating = False  # ป้องกันการอัพเดตซ้ำซ้อน

        # สร้าง Canvas สำหรับใช้เป็น scrollbar แทน ttk.Scrollbar
        self.components.scrollbar_canvas = tk.Canvas(
            self.components.text_frame,
            width=self.scrollbar_default_width,
            height=100,  # ความสูงจะถูกปรับในภายหลัง
            highlightthickness=0,
            bd=0,
        )

        # วาง scrollbar ในตำแหน่งที่เหมาะสม (ขวาสุด เริ่มที่ 25% ของความสูง)
        self.components.scrollbar_canvas.place(
            relx=1.0, rely=0.25, relheight=0.45, anchor="ne", x=-5
        )

        # สร้างส่วน thumb (แท่งเลื่อน) ด้วยสี่เหลี่ยมสีเทาเข้ม
        self.components.scrollbar_thumb = (
            self.components.scrollbar_canvas.create_rectangle(
                0,
                0,
                self.scrollbar_default_width,
                30,  # ขนาดเริ่มต้น จะถูกปรับในภายหลัง
                fill="#333333",  # สีเทาเข้ม
                outline="",  # ไม่มีเส้นขอบ
                tags=("thumb",),
            )
        )

        # สร้างฟังก์ชันสำหรับอัพเดตตำแหน่ง thumb ตาม scrollbar
        def update_thumb(*args):
            try:
                # ป้องกันการอัพเดตระหว่างกำลังทำ animation
                if self.scrollbar_updating:
                    return

                if len(args) == 2:
                    # สไลเดอร์จะส่งค่า 2 ค่า: ตำแหน่งเริ่มต้นและสิ้นสุดของส่วนที่มองเห็น
                    start, end = float(args[0]), float(args[1])

                    # คำนวณความสูงของ scrollbar canvas
                    canvas_height = self.components.scrollbar_canvas.winfo_height()

                    # คำนวณขนาดและตำแหน่งของ thumb
                    thumb_height = max(20, canvas_height * (end - start))  # ขั้นต่ำ 20px
                    y_position = start * canvas_height

                    # ดึงความกว้างปัจจุบันของ scrollbar
                    current_width = self.components.scrollbar_canvas.winfo_width()

                    # อัพเดตขนาดและตำแหน่งของ thumb
                    self.components.scrollbar_canvas.coords(
                        self.components.scrollbar_thumb,
                        0,
                        y_position,
                        current_width,  # ใช้ความกว้างปัจจุบัน
                        y_position + thumb_height,
                    )

                    # แสดง/ซ่อน scrollbar ตามความจำเป็น
                    if end >= 0.99:  # หมายถึงเลื่อนสุดแล้ว
                        self.hide_overflow_arrow()
                    elif start > 0 or end < 1.0:  # มีการเลื่อน
                        self.show_overflow_arrow()
            except Exception as e:
                logging.error(f"Error updating scrollbar thumb: {e}")

        # ผูกการทำงานของ scrollbar กับ canvas
        self.components.canvas.configure(yscrollcommand=update_thumb)

        # สร้างฟังก์ชันเมื่อคลิกที่ scrollbar
        def on_scrollbar_click(event):
            try:
                # ตั้งค่าสถานะกำลังปรับเปลี่ยน
                self.scrollbar_updating = True

                canvas_height = self.components.scrollbar_canvas.winfo_height()
                # คำนวณตำแหน่งคลิกเทียบกับความสูงทั้งหมด
                click_ratio = event.y / canvas_height

                # เลื่อนไปยังตำแหน่งที่คลิก
                self.components.canvas.yview_moveto(click_ratio)

                # รอให้การอัพเดตเสร็จสิ้นแล้วค่อยรีเซ็ตสถานะ
                self.root.after(50, lambda: setattr(self, "scrollbar_updating", False))
            except Exception as e:
                logging.error(f"Error in scrollbar click: {e}")
                self.scrollbar_updating = False

        # ฟังก์ชันสำหรับการลากแถบเลื่อน
        def on_scrollbar_drag(event):
            try:
                # ตั้งค่าสถานะกำลังปรับเปลี่ยน
                self.scrollbar_updating = True

                canvas_height = self.components.scrollbar_canvas.winfo_height()
                # คำนวณตำแหน่งลากเทียบกับความสูงทั้งหมด
                drag_ratio = event.y / canvas_height
                # เลื่อนไปยังตำแหน่งที่ลาก (ไม่เกินขอบเขต)
                self.components.canvas.yview_moveto(max(0, min(1, drag_ratio)))

                # รีเซ็ตสถานะหลังจากเสร็จสิ้นการอัพเดต
                self.root.after(50, lambda: setattr(self, "scrollbar_updating", False))
            except Exception as e:
                logging.error(f"Error in scrollbar drag: {e}")
                self.scrollbar_updating = False

        # ผูกการทำงานเมื่อคลิกและลากที่ scrollbar
        self.components.scrollbar_canvas.bind("<Button-1>", on_scrollbar_click)
        self.components.scrollbar_canvas.bind("<B1-Motion>", on_scrollbar_drag)

        # เพิ่ม hover effect
        def on_scrollbar_enter(event):
            # ดำเนินการต่อเมื่อไม่ได้กำลังปรับแถบเลื่อนอยู่
            if not self.scrollbar_updating:
                self.components.scrollbar_canvas.itemconfig(
                    self.components.scrollbar_thumb, fill="#444444"  # สว่างขึ้นเมื่อ hover
                )
                self.expand_scrollbar(True)  # ขยายแถบเลื่อนเมื่อเมาส์อยู่เหนือแถบ

        def on_scrollbar_leave(event):
            # ดำเนินการต่อเมื่อไม่ได้กำลังปรับแถบเลื่อนอยู่
            if not self.scrollbar_updating:
                self.components.scrollbar_canvas.itemconfig(
                    self.components.scrollbar_thumb, fill="#333333"  # กลับเป็นสีเดิม
                )
                self.expand_scrollbar(False)  # หดแถบเลื่อนเมื่อเมาส์ออกจากแถบ

        # ผูกการทำงานเมื่อ hover บน scrollbar
        self.components.scrollbar_canvas.bind("<Enter>", on_scrollbar_enter)
        self.components.scrollbar_canvas.bind("<Leave>", on_scrollbar_leave)

        # ผูกการทำงานเมื่อเมาส์เคลื่อนที่ใน text_frame เพื่อตรวจสอบว่าอยู่ใกล้ scrollbar หรือไม่
        self.components.text_frame.bind("<Motion>", self.check_mouse_near_scrollbar)

        # ผูกฟังก์ชัน scroll กับ canvas
        def on_scrollbar_scroll(event):
            # เปลี่ยนตำแหน่ง scroll ของ canvas
            self.components.canvas.yview_scroll(-1 * (event.delta // 120), "units")

        # Configure canvas scroll region เริ่มต้น
        self.components.canvas.configure(
            scrollregion=(0, 0, 0, self.components.text_frame.winfo_height() + 50),
        )

    def check_mouse_near_scrollbar(self, event):
        """
        ตรวจสอบว่าเมาส์อยู่ใกล้แถบเลื่อนหรือไม่ และควบคุมการขยาย

        Args:
            event: Mouse motion event
        """
        try:
            # ถ้ากำลังมีการปรับเปลี่ยนแถบเลื่อนอยู่ ให้ข้ามการทำงานไปก่อน
            if getattr(self, "scrollbar_updating", False):
                return

            # ถ้า scrollbar_canvas ยังไม่ถูกสร้างหรือไม่แสดง ให้ออกจากฟังก์ชัน
            if (
                not hasattr(self.components, "scrollbar_canvas")
                or not self.components.scrollbar_canvas.winfo_ismapped()
            ):
                return

            # ตรวจสอบว่าเมาส์อยู่ทางขวาของ frame หรือไม่
            frame_width = self.components.text_frame.winfo_width()

            # คำนวณระยะห่างจากขอบขวา
            distance_from_right = frame_width - event.x

            # ถ้าเมาส์อยู่ใกล้ขอบขวาภายในระยะที่กำหนด
            if distance_from_right <= self.scrollbar_expansion_zone:
                # ขยายแถบเลื่อน
                self.expand_scrollbar(True)
            else:
                # ตรวจสอบว่าเมาส์ได้ออกจาก scrollbar canvas แล้วหรือไม่
                try:
                    cursor_over_scrollbar = (
                        self.components.scrollbar_canvas.winfo_containing(
                            event.x_root, event.y_root
                        )
                        == self.components.scrollbar_canvas
                    )
                except Exception:
                    cursor_over_scrollbar = False

                # หดแถบเลื่อนถ้าเมาส์ไม่ได้อยู่เหนือ scrollbar
                if not cursor_over_scrollbar:
                    self.expand_scrollbar(False)

        except Exception as e:
            logging.error(f"Error checking mouse near scrollbar: {e}")

    def expand_scrollbar(self, expand: bool):
        """
        ขยายหรือหดแถบเลื่อนพร้อม animation และจัดการการหน่วงเวลาเพื่อลดการกะพริบ

        Args:
            expand: True เพื่อขยาย, False เพื่อหด
        """
        try:
            # ถ้าไม่มี scrollbar หรือกำลังมี animation ทำงานอยู่ ให้ข้ามไป
            if (
                not hasattr(self.components, "scrollbar_canvas")
                or not self.components.scrollbar_canvas.winfo_exists()
                or self.scrollbar_updating
            ):
                return

            # --- ตรรกะการจัดการ Delay และ Debouncing ---

            if expand:
                # 1. เมื่อต้องการ "ขยาย"

                # ยกเลิก timer ที่จะหดแถบเลื่อน (ถ้ามี)
                # เพื่อป้องกันไม่ให้แถบเลื่อนหดกลับในขณะที่เมาส์ยังอยู่ใกล้ๆ
                if self.scrollbar_resize_timer is not None:
                    self.root.after_cancel(self.scrollbar_resize_timer)
                    self.scrollbar_resize_timer = None

                # ถ้าแถบเลื่อนยังไม่ถูกขยาย ให้เริ่ม animation ขยายทันที
                if not self.scrollbar_is_expanded:
                    self._start_scrollbar_animation(True)

            else:
                # 2. เมื่อต้องการ "หด"

                # แทนที่จะหดทันที ให้ตั้งเวลาหน่วง (debounce) 1 วินาที
                # เพื่อให้โอกาสผู้ใช้ขยับเมาส์กลับเข้ามาใกล้ๆ ได้โดยไม่เกิดการกะพริบ
                if self.scrollbar_resize_timer is None:
                    self.scrollbar_resize_timer = self.root.after(
                        1000,  # หน่วงเวลา 1 วินาที (1000 ms)
                        lambda: self._start_scrollbar_animation(False),
                    )

        except Exception as e:
            logging.error(f"Error in expand_scrollbar: {e}")

    def _start_scrollbar_animation(self, expand):
        """
        เริ่มการทำ animation ขยาย/หดแถบเลื่อน

        Args:
            expand: True เพื่อขยาย, False เพื่อหด
        """
        try:
            # ตั้งค่าสถานะกำลังปรับเปลี่ยน
            self.scrollbar_updating = True

            # รีเซ็ต timer resize เพื่อป้องกันการทำงานซ้ำซ้อน
            if self.scrollbar_resize_timer is not None:
                self.root.after_cancel(self.scrollbar_resize_timer)
                self.scrollbar_resize_timer = None

            # รีเซ็ต animation timer เดิม (ถ้ามี) เพื่อเริ่มใหม่
            if self.scrollbar_animation_timer is not None:
                self.root.after_cancel(self.scrollbar_animation_timer)
                self.scrollbar_animation_timer = None

            # อัปเดตสถานะการขยาย
            self.scrollbar_is_expanded = expand

            # กำหนดค่าเริ่มต้นของ animation
            self.scrollbar_animation_step = 0

            # เริ่มทำ animation
            self._animate_scrollbar_resize(expand)

        except Exception as e:
            logging.error(f"Error starting scrollbar animation: {e}")
            self.scrollbar_updating = False

    def _animate_scrollbar_resize(self, expand):
        """
        ทำ animation การเปลี่ยนขนาดแถบเลื่อน

        Args:
            expand: True เพื่อขยาย, False เพื่อหด
        """
        try:
            # คำนวณขนาดสำหรับขั้นตอน animation ปัจจุบัน
            if expand:
                # ขยายจากขนาดเล็กไปใหญ่
                progress = (
                    self.scrollbar_animation_step / self.scrollbar_animation_steps
                )
                new_width = (
                    self.scrollbar_default_width
                    + (self.scrollbar_expanded_width - self.scrollbar_default_width)
                    * progress
                )
            else:
                # หดจากขนาดใหญ่ไปเล็ก
                progress = (
                    self.scrollbar_animation_step / self.scrollbar_animation_steps
                )
                new_width = (
                    self.scrollbar_expanded_width
                    - (self.scrollbar_expanded_width - self.scrollbar_default_width)
                    * progress
                )

            # ปัดเศษให้เป็นจำนวนเต็ม
            new_width = int(new_width)

            # อัปเดตความกว้างของ canvas
            self.components.scrollbar_canvas.config(width=new_width)

            # อัปเดตความกว้างของ thumb
            thumb_coords = self.components.scrollbar_canvas.coords(
                self.components.scrollbar_thumb
            )
            if thumb_coords and len(thumb_coords) >= 4:
                # อัปเดตเฉพาะความกว้าง (ตำแหน่งที่ 3 ในลิสต์พิกัด)
                thumb_coords[2] = new_width
                self.components.scrollbar_canvas.coords(
                    self.components.scrollbar_thumb, *thumb_coords
                )

            # อัปเดตสีของ thumb ตามความคืบหน้าของ animation
            if expand:
                # ค่อยๆ เปลี่ยนสีเมื่อขยาย: #333333 (51) -> #555555 (85)
                r = int(51 + progress * 34)
                g = int(51 + progress * 34)
                b = int(51 + progress * 34)
            else:
                # ค่อยๆ เปลี่ยนสีเมื่อหด: #555555 (85) -> #333333 (51)
                r = int(85 - progress * 34)
                g = int(85 - progress * 34)
                b = int(85 - progress * 34)

            thumb_color = f"#{r:02x}{g:02x}{b:02x}"
            self.components.scrollbar_canvas.itemconfig(
                self.components.scrollbar_thumb, fill=thumb_color
            )

            # เพิ่มขั้นตอน animation
            self.scrollbar_animation_step += 1

            # ตรวจสอบว่าต้องทำ animation ต่อหรือไม่
            if self.scrollbar_animation_step <= self.scrollbar_animation_steps:
                # ทำ animation ต่อ
                self.scrollbar_animation_timer = self.root.after(
                    self.scrollbar_animation_speed,
                    lambda: self._animate_scrollbar_resize(expand),
                )
            else:
                # จบ animation
                self.scrollbar_animation_timer = None

                # อัปเดตค่าที่ถูกต้องตามสถานะสุดท้าย (ป้องกันการคำนวณผิดพลาด)
                final_width = (
                    self.scrollbar_expanded_width
                    if expand
                    else self.scrollbar_default_width
                )
                final_color = "#555555" if expand else "#333333"

                self.components.scrollbar_canvas.config(width=final_width)

                # ปรับ thumb ให้สอดคล้องกับความกว้างสุดท้าย
                thumb_coords = self.components.scrollbar_canvas.coords(
                    self.components.scrollbar_thumb
                )
                if thumb_coords and len(thumb_coords) >= 4:
                    thumb_coords[2] = final_width
                    self.components.scrollbar_canvas.coords(
                        self.components.scrollbar_thumb, *thumb_coords
                    )

                self.components.scrollbar_canvas.itemconfig(
                    self.components.scrollbar_thumb, fill=final_color
                )

                # รีเซ็ตสถานะการปรับเปลี่ยน
                self.scrollbar_updating = False

        except Exception as e:
            logging.error(f"Error animating scrollbar resize: {e}")
            self.scrollbar_updating = False

    def custom_scrollbar_command(self, *args):
        """
        คำสั่งสำหรับจัดการ scrollbar แบบกำหนดเอง

        Args:
            *args: ตำแหน่ง scroll (start, end) ที่ได้จาก canvas
        """
        # ส่งค่าไปยัง scrollbar จริง
        self.components.scrollbar.set(*args)

        # ถ้ามี custom scrollbar ให้อัพเดตตำแหน่ง thumb
        if hasattr(self.components, "scrollbar_canvas") and hasattr(
            self.components, "scrollbar_thumb"
        ):
            try:
                # คำนวณตำแหน่งของ thumb ตามสัดส่วนการเลื่อน
                start, end = float(args[0]), float(args[1])
                canvas_height = self.components.scrollbar_canvas.winfo_height()

                # คำนวณความสูงและตำแหน่งของ thumb
                thumb_height = max(30, canvas_height * (end - start))  # ขั้นต่ำ 30px
                y_position = start * canvas_height

                # อัพเดตขนาดและตำแหน่งของ thumb
                self.components.scrollbar_canvas.coords(
                    self.components.scrollbar_thumb,
                    0,
                    y_position,
                    6,
                    y_position + thumb_height,
                )

                # แสดง/ซ่อน scrollbar ตามความจำเป็น
                if end >= 0.99:  # หมายถึงเลื่อนสุดแล้ว
                    self.hide_overflow_arrow()
                elif start > 0 or end < 1.0:  # มีการเลื่อน
                    self.show_overflow_arrow()

            except Exception as e:
                logging.error(f"Error updating custom scrollbar: {e}")

    def apply_rounded_corners_to_scrollbar(self) -> None:
        """ทำให้ scrollbar มีขอบโค้งมนโดยใช้ win32gui"""
        try:
            # รอให้ scrollbar แสดงผล
            self.root.update_idletasks()

            # ตรวจสอบว่า scrollbar มีอยู่จริง
            if (
                not hasattr(self.components, "scrollbar")
                or not self.components.scrollbar.winfo_exists()
            ):
                return

            # ดึง HWND ของ scrollbar
            scrollbar_hwnd = self.components.scrollbar.winfo_id()
            if not scrollbar_hwnd:
                return

            # ปรับขอบให้โค้งมน
            scrollbar_width = self.components.scrollbar.winfo_width() or 6
            scrollbar_height = self.components.scrollbar.winfo_height()

            # สร้างภูมิภาค (region) โค้งมน - ใช้ครึ่งหนึ่งของความกว้างเป็นรัศมี
            radius = scrollbar_width // 2
            region = win32gui.CreateRoundRectRgn(
                0, 0, scrollbar_width, scrollbar_height, radius, radius
            )

            # กำหนดภูมิภาคให้กับ scrollbar
            win32gui.SetWindowRgn(scrollbar_hwnd, region, True)
        except Exception as e:
            logging.error(f"Error applying rounded corners to scrollbar: {e}")

    def setup_buttons(self) -> None:
        """Initialize and setup all control buttons"""
        button_size = 20
        force_button_size = 25
        # ดึงสีพื้นหลังจาก settings (*** ไม่ต้องตั้ง bg ให้ปุ่มที่นี่ ***)
        # saved_bg_color = self.settings.get("bg_color", appearance_manager.bg_color)

        # Close button
        self.components.buttons["close"] = tk.Button(
            self.components.control_area,
            text="X",
            command=self.close_window,
            # bg=saved_bg_color, # <--- ลบออก
            fg="white",  # สีข้อความยังคงเดิม
            bd=0,
            width=1,
            font=(self.settings.get("font"), 12),
            cursor="hand2",
            # activebackground=saved_bg_color, # <--- ลบออก
        )
        self.components.buttons["close"].pack(side=tk.TOP, pady=(5, 5))

        # Lock/Unlock button
        self.components.buttons["lock"] = tk.Button(
            self.components.control_area,
            image=self.unlock_image,
            command=self.toggle_lock,
            # bg=saved_bg_color, # <--- ลบออก
            bd=0,
            highlightthickness=0,
            relief="flat",
            compound="center",
            cursor="hand2",
            # activebackground=saved_bg_color, # <--- ลบออก
        )
        self.components.buttons["lock"].pack(side=tk.TOP, pady=5)

        # ★ Color picker button - ใช้ไอคอน TUI_BG.png แทนการแสดงสี
        if hasattr(self, "tui_bg_image") and self.tui_bg_image:
            self.components.buttons["color"] = tk.Button(
                self.components.control_area,
                image=self.tui_bg_image,  # ใช้ไอคอนแทนสี
                command=self.show_color_picker,  # เปลี่ยนชื่อฟังก์ชัน
                bd=1,
                relief="solid",
                highlightthickness=0,
                cursor="hand2",
                width=button_size,
                height=button_size,
            )
        else:
            # สำรองถ้าไอคอนโหลดไม่ได้
            self.components.buttons["color"] = tk.Button(
                self.components.control_area,
                text="BG",
                command=self.show_color_picker,
                bd=1,
                relief="solid",
                width=1,
                height=1,
                cursor="hand2",
                fg="white",
                font=("Arial", 8, "bold"),
            )
        self.components.buttons["color"].pack(side=tk.TOP, pady=5)

        # Force translate button - HIDDEN (keeping code for future use)
        # Uncomment the following lines to restore force translate button:
        # self.components.buttons["force"] = tk.Button(
        #     self.components.control_area,
        #     image=self.force_image,  # ไอคอนเริ่มต้น
        #     command=self._toggle_force_hover_mode,  # <--- command ใหม่
        #     bd=0,
        #     highlightthickness=0,
        #     relief="flat",
        #     compound="center",
        #     cursor="hand2",
        #     width=force_button_size,
        #     height=force_button_size,
        # )
        # self.components.buttons["force"].pack(side=tk.TOP, pady=5)
        # self.components.buttons["force"].bind(
        #     "<Enter>", self._on_force_button_hover_enter
        # )
        # self.components.buttons["force"].bind(
        #     "<Leave>", self._on_force_button_hover_leave
        # )

        # ปุ่ม fade out
        self.components.buttons["fadeout"] = tk.Button(
            self.components.control_area,
            image=self.fadeout_image,
            command=self.toggle_fadeout,
            # bg=saved_bg_color, # <--- ลบออก
            bd=0,
            highlightthickness=0,
            relief="flat",
            compound="center",
            cursor="hand2",
            # activebackground=saved_bg_color, # <--- ลบออก
        )
        self.components.buttons["fadeout"].pack(side=tk.TOP, pady=5)

        # Phase 5: auto-hide ทำงานแบบอัตโนมัติกับ fade out แล้ว (ไม่ต้องใช้ right-click)

    def _toggle_force_hover_mode(self):
        """สลับโหมด hover-to-execute สำหรับปุ่ม Force และเปลี่ยนไอคอน"""
        try:
            self.force_hover_active = not self.force_hover_active
            force_button = self.components.buttons.get("force")
            if force_button and force_button.winfo_exists():
                if self.force_hover_active:
                    if self.force_m_image:
                        force_button.config(image=self.force_m_image)
                    else:  # Fallback if s_force_m.png failed to load
                        force_button.config(
                            image=self.force_image
                        )  # or some indicator text
                    self.show_feedback_message(
                        "ชี้เพื่อสั่งแปล: เปิด", bg_color="#4CAF50", font_size=10
                    )
                    if hasattr(self, "logging_manager") and self.logging_manager:
                        self.logging_manager.log_info(
                            "Force button hover-to-execute: ON"
                        )
                else:
                    force_button.config(image=self.force_image)
                    self.show_feedback_message(
                        "ชี้เพื่อสั่งแปล: ปิด", bg_color="#C62828", font_size=10
                    )
                    if hasattr(self, "logging_manager") and self.logging_manager:
                        self.logging_manager.log_info(
                            "Force button hover-to-execute: OFF"
                        )
        except Exception as e:
            logging.error(f"Error in _toggle_force_hover_mode: {e}")

    def scrollbar_command(self, *args) -> None:
        """
        จัดการการเลื่อน scrollbar และการแสดงลูกศร
        Args:
            *args: ตำแหน่ง scroll (start, end) ที่ได้จาก canvas
        """
        try:
            # อัพเดต thumb ของ scrollbar ที่สร้างเอง
            if hasattr(self.components, "scrollbar_canvas") and hasattr(
                self.components, "scrollbar_thumb"
            ):
                if len(args) == 2:
                    start, end = float(args[0]), float(args[1])

                    # คำนวณความสูงของ scrollbar canvas
                    canvas_height = self.components.scrollbar_canvas.winfo_height()

                    # คำนวณขนาดและตำแหน่งของ thumb
                    thumb_height = max(20, canvas_height * (end - start))
                    y_position = start * canvas_height

                    # อัพเดตขนาดและตำแหน่งของ thumb
                    self.components.scrollbar_canvas.coords(
                        self.components.scrollbar_thumb,
                        0,
                        y_position,
                        4,
                        y_position + thumb_height,
                    )

            # Calculate scroll position percentage - ปรับการตรวจสอบให้แม่นยำขึ้น
            scroll_position = float(args[1]) if len(args) > 1 else 0

            # ปรับค่าเกณฑ์ในการตรวจสอบว่าเลื่อนจนสุดหรือยัง
            # เดิมใช้ 0.95 (95%) เปลี่ยนเป็น 0.98 (98%) เพื่อซ่อนลูกศรเร็วขึ้น
            max_scroll = 0.98  # เพิ่มจาก 0.95 เป็น 0.98

            # Get canvas content boundaries
            bbox = self.components.canvas.bbox("all")
            if bbox is not None:
                # ปรับเงื่อนไขให้เข้มงวดขึ้น เพื่อซ่อนลูกศรเร็วขึ้น
                if scroll_position >= max_scroll:
                    self.hide_overflow_arrow()
                elif bbox[3] > self.components.canvas.winfo_height():
                    self.show_overflow_arrow()
            else:
                self.hide_overflow_arrow()

        except (TypeError, IndexError) as e:
            logging.warning(f"Error in scrollbar_command: {str(e)}")
            self.hide_overflow_arrow()

    def scroll_to_bottom(self) -> None:
        """
        เลื่อนข้อความลงไปด้านล่างสุดอย่างรวดเร็ว
        """
        try:
            if not hasattr(self.components, "canvas") or not self.components.canvas:
                return

            # ตรวจสอบ bounding box ของเนื้อหาทั้งหมด
            bbox = self.components.canvas.bbox("all")
            if not bbox:
                return

            # กำหนดตำแหน่งที่ต้องเลื่อนไป
            # ใช้ค่าสูงมากเพื่อให้แน่ใจว่าเลื่อนลงสุด
            # แต่ไม่เพิ่มพื้นที่ว่างมากเกินไป
            self.components.canvas.yview_moveto(1.0)

            # ซ่อนลูกศร overflow ทันที
            self.hide_overflow_arrow()

            # ทำให้แน่ใจว่า UI ได้รับการอัพเดต
            self.root.update_idletasks()
        except Exception as e:
            logging.error(f"Error in scroll_to_bottom: {e}")

    def setup_bindings(self) -> None:
        """Setup all event bindings for the UI"""
        # Basic UI interactions
        self.root.bind("<Button-1>", self.on_click)
        self.root.bind("<ButtonRelease-1>", self.stop_move)
        self.root.bind("<B1-Motion>", self.on_drag)
        self.components.canvas.bind("<Button-1>", self.show_full_text)
        self.components.canvas.bind("<Configure>", self.on_canvas_configure_enhanced)
        self.components.canvas.bind("<MouseWheel>", self.on_mousewheel)

        # เพิ่ม binding สำหรับคลิกขวา
        self.root.bind("<Button-3>", self.on_right_click)
        self.components.canvas.bind("<Button-3>", self.on_right_click)
        self.components.main_frame.bind("<Button-3>", self.on_right_click)
        self.components.text_frame.bind("<Button-3>", self.on_right_click)

        # กรณีผู้ใช้งาน Windows อีกรูปแบบของคลิกขวา
        self.root.bind("<App>", self.on_right_click)

        # Add mousewheel binding to all frames
        for widget in [
            self.components.main_frame,
            self.components.text_frame,
            self.root,
        ]:
            widget.bind("<MouseWheel>", self.on_mousewheel)

        # Resize bindings
        self.resize_handle.bind("<Button-1>", self.start_resize)
        self.resize_handle.bind("<B1-Motion>", self.on_resize)
        self.resize_handle.bind("<ButtonRelease-1>", self.stop_resize)

        # Hover events for relevant widgets
        widgets_to_bind = [
            self.components.main_frame,
            self.components.text_frame,
            self.components.canvas,
            self.root,
        ]

        for widget in widgets_to_bind:
            widget.bind("<Enter>", self.on_hover_enter)

    def on_right_click(self, event: tk.Event) -> None:
        """
        จัดการเหตุการณ์คลิกขวาเพื่อแสดง previous dialog
        Args:
            event: Mouse right-click event
        """
        try:
            # ตรวจสอบว่าผู้ใช้เปิดใช้งาน previous dialog ด้วย r-click ไว้หรือไม่
            if not self.settings.get("enable_previous_dialog", True):
                return

            # ตรวจสอบว่า shortcut เป็น r-click หรือไม่
            previous_shortcut = self.settings.get_shortcut("previous_dialog", "r-click")
            if previous_shortcut != "r-click":
                return

            # เรียกใช้ previous dialog
            if hasattr(self, 'previous_dialog_callback') and callable(self.previous_dialog_callback):
                # Try to call the callback
                try:
                    # Check if there's history available first
                    if hasattr(self, 'main_app') and self.main_app and hasattr(self.main_app, 'dialog_history') and self.main_app.dialog_history:
                        self.previous_dialog_callback()
                    else:
                        self.show_feedback_message("No previous dialog available", bg_color="#FF8C00")
                except Exception as e:
                    self.show_feedback_message("Previous Dialog error", bg_color="#FF4444")
                    logging.error(f"📄 [RIGHT-CLICK] Previous dialog callback error: {e}")
            else:
                # Fallback: แสดงข้อความแจ้งเตือน เมื่อไม่พร้อมใช้งาน
                self.show_feedback_message("Previous Dialog not available", bg_color="#FF8C00")
                logging.warning("📄 [RIGHT-CLICK] Previous dialog callback not found")

            # Log การใช้งาน
            if hasattr(self, "logging_manager") and self.logging_manager:
                self.logging_manager.log_info(
                    "Previous dialog triggered by right-click"
                )

        except Exception as e:
            logging.error(f"Error in on_right_click: {e}")

    def show_feedback_message(
        self,
        message: str,
        bg_color: str = "#C62828",
        x_offset: int = 10,
        y_offset: int = 10,
        duration: int = 800,
        font_size: int = 10,
    ):
        """
        แสดงข้อความชั่วคราวแบบมี fade effect

        Args:
            message: ข้อความที่ต้องการแสดง
            bg_color: สีพื้นหลังของข้อความ (default: สีแดง)
            x_offset: ตำแหน่ง x เทียบกับเมาส์ (default: 10)
            y_offset: ตำแหน่ง y เทียบกับเมาส์ (default: 10)
            duration: ระยะเวลาที่แสดงก่อน fade out (ms) (default: 800)
            font_size: ขนาดตัวอักษร (default: 10)
        """
        try:
            # ทำลาย feedback ตัวเก่าถ้ามี
            if hasattr(self, '_active_feedback') and self._active_feedback:
                try:
                    if self._active_feedback.winfo_exists():
                        self._active_feedback.destroy()
                except tk.TclError:
                    pass
                self._active_feedback = None

            # ตำแหน่งของหน้าต่าง
            x_pos = self.root.winfo_pointerx() + x_offset
            y_pos = self.root.winfo_pointery() + y_offset

            # สร้าง visual feedback
            feedback = tk.Toplevel(self.root)
            feedback.overrideredirect(True)
            feedback.attributes("-topmost", True)
            feedback.attributes("-alpha", 0.8)
            feedback.configure(bg=bg_color)
            self._active_feedback = feedback

            # สร้าง label แสดงผล
            label = tk.Label(
                feedback,
                text=message,
                fg="white",
                bg=bg_color,
                font=("Anuphan", font_size, "bold"),
                padx=15,
                pady=8,
            )
            label.pack()

            # จัดตำแหน่งให้อยู่ใกล้ตำแหน่งที่คลิก
            feedback.geometry(f"+{x_pos}+{y_pos}")

            # Fade effect ผ่าน root.after() (ไม่ใช้ thread — ป้องกัน Tk threading error)
            def fade_step(step=10):
                try:
                    if not feedback.winfo_exists():
                        return
                    if step < 0:
                        feedback.destroy()
                        if self._active_feedback is feedback:
                            self._active_feedback = None
                        return
                    feedback.attributes("-alpha", step / 10.0)
                    self.root.after(30, lambda: fade_step(step - 1))
                except tk.TclError:
                    pass

            self.root.after(duration, fade_step)

        except Exception as e:
            logging.error(f"Error in show_feedback_message: {e}")

    def is_mouse_in_ui(self, event: tk.Event) -> bool:
        """
        Check if mouse is within any UI component
        Args:
            event: Mouse event containing coordinates
        Returns:
            bool: True if mouse is within UI bounds
        """
        x, y = event.x_root, event.y_root
        widgets_to_check = [
            self.components.main_frame,
            self.components.text_frame,
            self.components.canvas,
            self.root,
        ]

        for widget in widgets_to_check:
            try:
                widget_x = widget.winfo_rootx()
                widget_y = widget.winfo_rooty()
                widget_width = widget.winfo_width()
                widget_height = widget.winfo_height()

                if (
                    widget_x <= x <= widget_x + widget_width
                    and widget_y <= y <= widget_y + widget_height
                ):
                    return True
            except Exception:
                continue
        return False

    def show_overflow_arrow(self) -> None:
        """Show and start blinking the overflow arrow indicator"""
        # ไม่แสดง overflow arrow ใน Battle Chat mode
        if self.battle_mode_active:
            return

        if not self.state.arrow_visible:
            self.state.arrow_visible = True
            # แสดง canvas แทนการ lift
            self.components.arrow_canvas.place(relx=0.85, rely=0.85, anchor="center")
            self.blink_arrow()

    def hide_overflow_arrow(self) -> None:
        """Hide and stop blinking the overflow arrow indicator"""
        self.state.arrow_visible = False
        self.state.arrow_blinking = False
        # ซ่อน canvas แทนการ lower
        self.components.arrow_canvas.place_forget()

    def blink_arrow(self) -> None:
        """Start arrow blinking animation if not already blinking"""
        if self.state.arrow_visible and not self.state.arrow_blinking:
            self.state.arrow_blinking = True
            self.do_blink()

    def do_blink(self) -> None:
        """Handle arrow blinking animation with simple show/hide effect"""
        if self.state.arrow_visible and self.state.arrow_blinking:
            # เช็คว่าลูกศรกำลังแสดงอยู่หรือไม่ (เพิ่มตัวแปรไว้ติดตามสถานะ)
            if not hasattr(self, "arrow_is_visible"):
                self.arrow_is_visible = True

            # สลับสถานะการแสดง/ซ่อน
            self.arrow_is_visible = not self.arrow_is_visible

            # แสดงหรือซ่อน Canvas ตามสถานะปัจจุบัน
            if self.arrow_is_visible:
                self.components.arrow_canvas.place(
                    relx=0.85, rely=0.85, anchor="center"
                )
            else:
                self.components.arrow_canvas.place_forget()

            # ตั้งเวลาสำหรับการกะพริบครั้งต่อไป
            self.root.after(500, self.do_blink)
        else:
            # เมื่อหยุดกะพริบ ให้แสดงลูกศรถ้าควรแสดง
            if hasattr(self, "arrow_is_visible"):
                self.arrow_is_visible = True
            if self.state.arrow_visible:
                self.components.arrow_canvas.place(
                    relx=0.85, rely=0.85, anchor="center"
                )

    def update_text(
        self, text: str, is_lore_text: bool = False, force_choice_mode: bool = False, chat_type: int = 61
    ) -> None:
        """
        Update the displayed text with Rich Text support for *italic* formatting
        Args:
            text: Text to display (may contain *italic* markers)
            is_lore_text: Whether this is lore text
            force_choice_mode: Force choice mode (ignored for Rich Text)
            chat_type: ChatType from text hook (61=dialogue, 71=cutscene)
        """
        try:
            # 🚫 FILTER ERROR MESSAGES: Don't display API errors in TUI
            if text and "[Error:" in text:
                logging.warning(f"⚠️ Blocked error message from displaying in TUI: {text}")
                return

            # Reset text cleared flag when new text arrives
            self._text_cleared = False

            # Save chat_type for choice detection in _original_update_text
            self._current_chat_type = chat_type

            # Set display mode based on chat type BEFORE showing text
            geometry_changed = self.set_display_mode_for_chat_type(chat_type)

            # Phase 6: Auto-show TUI เมื่อมีข้อความใหม่
            if text and text.strip():  # ตรวจสอบว่ามีข้อความจริง
                self.show_tui_on_new_translation()

            # Cancel any pending deferred render
            if hasattr(self, '_deferred_render_id') and self._deferred_render_id:
                self.root.after_cancel(self._deferred_render_id)
                self._deferred_render_id = None

            logging.info(f"📝 Processing text through normal flow (ChatType {chat_type}): {text}")

            if geometry_changed:
                # 🔧 FIX GHOST RE-RENDER: Immediately update stored text BEFORE deferring render.
                # Without this, self.dialogue_text and self.state.full_text still hold OLD text
                # (e.g., choice text) during the 50ms defer window. Any code path that reads
                # these variables (lock mode redraw, text_container recovery, name update)
                # would re-render the stale text as a "ghost".
                self.state.full_text = text
                self.dialogue_text = text

                # Defer rendering so Tk processes geometry change first
                # Without this, canvas.winfo_width() returns stale (old) values
                # causing wrong text centering and wrapping in battle/cutscene modes
                self._deferred_render_id = self.root.after(
                    50, lambda: self._original_update_text(text, is_lore_text)
                )
            else:
                self._original_update_text(text, is_lore_text)
        except Exception as e:
            logging.error(f"Error in text update: {e}")
            # Fallback to original method
            self._original_update_text(
                text, is_lore_text=is_lore_text
            )

    def _update_text_with_rich_support(self, text: str, is_lore_text: bool = False) -> None:
        """
        Complete Rich Text processing path with full DB verification

        This is a COMPLETE replacement path, not an enhancement
        """
        try:
            # *** FIX: Set processing flag to prevent conflicts ***
            self._rich_text_processing = True

            logging.info(f"🎨 RICH_PATH: Complete Rich Text processing for: {text}")

            if not text:
                return

            # *** REPLICATE ORIGINAL METHOD LOGIC WITH RICH TEXT SUPPORT ***

            # Handle Thai: prefix
            if text and text.startswith("Thai:"):
                text = text[5:].strip()
                logging.info(f"Removed 'Thai:' prefix, new text: {text}")

            # Reset fade state
            if self.state.is_fading:
                self.state.is_fading = False
                # 🎯 TRANSPARENCY FIX: Restore user transparency when fade is interrupted by new text
                self.restore_user_transparency()

            # Cancel fade timer if exists
            if self.state.fade_timer_id:
                self.root.after_cancel(self.state.fade_timer_id)
                self.state.fade_timer_id = None

            # Update last activity time
            self.state.last_activity_time = time.time()

            # Reset just_faded_out state if exists
            if hasattr(self.state, "just_faded_out"):
                self.state.just_faded_out = False

            # Reset text colors to white
            if self.components.text_container:
                self.components.canvas.itemconfig(
                    self.components.text_container, fill="white"
                )

            for outline in self.components.outline_container:
                try:
                    if self.components.canvas.type(outline) == "text":
                        self.components.canvas.itemconfig(outline, fill="#000000")
                except tk.TclError:
                    pass

            # Handle newlines
            processed_text = self.preprocess_thai_text(text)
            logging.info(
                f"DEBUG: After preprocess, text has {processed_text.count('<NL>')} <NL> tags and {processed_text.count(chr(10))} newlines"
            )

            # Extract speaker and dialogue
            if ":" in processed_text:
                speaker_name, dialogue_text = processed_text.split(":", 1)
                extracted_speaker = speaker_name.strip()
                extracted_dialogue = dialogue_text.strip()
            else:
                extracted_speaker = ""
                extracted_dialogue = processed_text

            # *** CRITICAL: Apply character verification (same as original) ***
            if hasattr(self, "names") and self.names:
                if extracted_speaker:
                    extracted_speaker = self.highlight_special_names(extracted_speaker, self.names)
                extracted_dialogue = self.highlight_special_names(extracted_dialogue, self.names)
                logging.info("✅ RICH_PATH: Character verification applied")

            # Clear the canvas first
            self.components.canvas.delete("all")

            # Apply background
            current_bg_color = getattr(self, 'current_bg_color', '#0d0d0b')
            current_bg_alpha = getattr(self, 'current_bg_alpha', 0.97)
            self._apply_background_color_and_alpha(current_bg_color, current_bg_alpha)

            # Get UI settings
            dialogue_font = (self.current_font_family, self.current_font_size)
            available_width = max(50, self.components.canvas.winfo_width() - 20)

            # Store dialogue text
            self.dialogue_text = extracted_dialogue

            # Display with Rich Text formatting
            if extracted_speaker:
                dialogue_y = 50
                # Display speaker name
                self.display_speaker_name(extracted_speaker, dialogue_font)
                # Display dialogue with Rich Text
                self._update_rich_text_dialogue(extracted_dialogue, dialogue_font, dialogue_y, available_width)
            else:
                # Display direct text with Rich Text
                self._update_rich_text_dialogue(extracted_dialogue, dialogue_font, 10, available_width)

            # Start fade timer
            if self.state.fadeout_enabled:
                self.start_fade_timer()
                logging.info("🕒 RICH_PATH: Started fade timer")

            # *** FIX: Clear processing flag ***
            self._rich_text_processing = False
            logging.info("🏁 RICH_PATH: Complete processing finished")

        except Exception as e:
            logging.error(f"Error in Rich Text complete processing: {e}")
            # *** FIX: Clear flag on error too ***
            self._rich_text_processing = False
            # Fallback to original method
            self._original_update_text(text, is_lore_text)

    def _apply_rich_text_to_completed_dialogue(self) -> None:
        """
        Apply Rich Text formatting to dialogue after normal typewriter effect completes
        This integrates Rich Text into the normal flow without path separation
        """
        try:
            logging.info("🔧 INTEGRATED: Converting completed normal text to Rich Text")

            # Get current dialogue dimensions and positioning from existing text_container
            if not self.components.text_container:
                logging.warning("No text_container found for Rich Text conversion")
                return

            # Get current text position and width
            text_bbox = self.components.canvas.bbox(self.components.text_container)
            if not text_bbox:
                logging.warning("Could not get text bbox for Rich Text conversion")
                return

            x, y, _, _ = text_bbox

            # Get current canvas width for text width calculation
            available_width = max(50, self.components.canvas.winfo_width() - 20)

            # 🔧 FIXED: Use reliable font info instead of parsing font string
            dialogue_font = (self.current_font_family, self.current_font_size)

            # Clear existing text objects AND outlines (they will be replaced with Rich Text segments)
            # 🔧 FIXED: Clear outlines to prevent double shadow effects
            if self.components.text_container:
                self.components.canvas.delete(self.components.text_container)
                self.components.text_container = None

            # Clear existing outlines to prevent shadow positioning issues
            for outline_id in self.components.outline_container:
                try:
                    self.components.canvas.delete(outline_id)
                except:
                    pass
            self.components.outline_container = []

            # Apply character verification to dialogue text first (CRITICAL for character names)
            if hasattr(self, "names") and self.names:
                self.dialogue_text = self.highlight_special_names(self.dialogue_text, self.names)
                logging.info("✅ RICH_TEXT: Character verification applied")

            # Apply Rich Text formatting to the dialogue
            logging.info(f"🎨 INTEGRATED: Creating Rich Text segments for: {self.dialogue_text}")
            self._update_rich_text_dialogue(self.dialogue_text, dialogue_font, y, available_width)

            logging.info("✅ INTEGRATED: Rich Text conversion completed successfully")

        except Exception as e:
            logging.error(f"Error in integrated Rich Text conversion: {e}")
            # On error, the original text should still be visible

    def update_text_differential(self, new_text: str) -> None:
        """SPEED-OPTIMIZED text update for rapid translation"""
        try:
            if not new_text:
                return

            # Clean text preparation
            if new_text.startswith("Thai:"):
                new_text = new_text[5:].strip()

            # OPTIMIZATION 1: Skip expensive similarity checking for rapid updates
            # Check if this is rapid consecutive update (same text within 100ms)
            current_time = time.time() * 1000
            if (
                hasattr(self, "_last_update_time")
                and hasattr(self, "_last_text")
                and self._last_text == new_text
                and (current_time - self._last_update_time) < 100
            ):
                # Same text within 100ms - skip entirely
                return

            self._last_update_time = current_time

            # OPTIMIZATION 2: Fast-path for new translations (most common case)
            if not hasattr(self, "_last_text") or not self._last_text:
                # First text or empty previous - direct update
                self._perform_fast_text_update(new_text)
                self._last_text = new_text
                return

            # OPTIMIZATION 3: Simple length-based comparison instead of expensive similarity
            old_len = len(self._last_text)
            new_len = len(new_text)
            length_diff = abs(new_len - old_len)

            # If length difference is small, try simple comparison
            if length_diff < 50:  # Small change
                # Quick check if just appending/prepending
                if new_text.startswith(self._last_text[: min(20, old_len)]):
                    # Likely appending text - use fast update
                    self._perform_fast_text_update(new_text)
                elif self._last_text.startswith(new_text[: min(20, new_len)]):
                    # Likely truncating text - use fast update
                    self._perform_fast_text_update(new_text)
                else:
                    # Content changed - full update
                    self._perform_fast_text_update(new_text)
            else:
                # Large change - direct update
                self._perform_fast_text_update(new_text)

            self._last_text = new_text

        except Exception as e:
            logging.error(f"Error in differential text update: {e}")
            # Fallback to original update method
            self._original_update_text(new_text)

    def _text_needs_update(self, new_text: str) -> bool:
        """Check if text actually needs updating"""
        return not hasattr(self, "_last_text") or self._last_text != new_text

    def _apply_cached_text_layout(self, cached_layout: Dict) -> None:
        """Apply cached text layout"""
        # For now, fall back to full update
        # This would be implemented with specific layout data
        pass

    def _calculate_text_similarity(self, old_text: str, new_text: str) -> float:
        """Calculate similarity ratio between texts"""
        try:
            from difflib import SequenceMatcher

            return SequenceMatcher(None, old_text, new_text).ratio()
        except:
            return 0.0

    def _perform_differential_update(self, old_text: str, new_text: str) -> None:
        """Update only changed parts of text"""
        try:
            # For now, fall back to optimized full update
            # True differential updates would require more complex layout tracking
            self._perform_full_text_update_optimized(new_text)
        except Exception as e:
            logging.error(f"Error in differential update: {e}")
            self._perform_full_text_update_optimized(new_text)

    def _perform_full_text_update_optimized(self, text: str) -> None:
        """Optimized full text update with minimal flicker"""
        try:
            if not self.components.canvas or not self.components.canvas.winfo_exists():
                return

            # Temporarily disable auto-scroll during update
            original_scroll = self.components.canvas.yview()

            # Use the original update method but with optimizations
            self._original_update_text(text)

            # Restore scroll position if needed
            if original_scroll[0] > 0 or original_scroll[1] < 1:
                self.root.after_idle(
                    lambda: self.components.canvas.yview_moveto(original_scroll[0])
                )

        except Exception as e:
            logging.error(f"Error in optimized full text update: {e}")

    def _cache_current_text_layout(self, text: str, width: int, font: str) -> None:
        """Cache current text layout for future use"""
        try:
            # Create layout data from current canvas state
            layout_data = {
                "text": text,
                "width": width,
                "font": font,
                "timestamp": time.time(),
            }

            self.text_render_cache.cache_layout(text, width, font, layout_data)
        except Exception as e:
            logging.error(f"Error caching text layout: {e}")

    def _perform_fast_text_update(self, text: str) -> None:
        """EMERGENCY FIX: Use original method for reliability"""
        try:
            # Use original method to fix display issues
            self._original_update_text(text)
        except Exception as e:
            logging.error(f"Error in fast text update: {e}")
            # Final fallback
            self._original_update_text(text)

    def _handle_normal_text_fast(
        self, text: str, dialogue_font: tuple, available_width: int
    ) -> None:
        """Fast normal text handling without heavy processing"""
        try:
            # Clear previous content
            self.components.canvas.delete("all")
            self.components.outline_container = []

            # Calculate text positioning based on mode
            text_anchor = self._get_text_anchor()
            if text_anchor == "n":  # Center-aligned for battle/cutscene
                canvas_width = self.components.canvas.winfo_width()
                text_x = canvas_width // 2
            else:  # Left-aligned for dialogue
                text_x = 10

            # Check for speaker name pattern
            if ": " in text:
                parts = text.split(": ", 1)
                speaker = parts[0].strip()
                # Safety: strip rich text markers and zero-width chars from speaker name
                speaker = speaker.replace("**", "").replace("*", "").replace("\u200b", "").replace("\u200c", "").strip()
                dialogue = parts[1].strip() if len(parts) > 1 else ""

                # Display speaker name
                if speaker:
                    # Speaker color: battle/cutscene = mono-color, dialogue = cyan/purple
                    # All speakers use normal weight (no bold) for compatibility
                    mode_color = self._get_text_color()
                    if mode_color != "white":
                        # Battle/Cutscene: mono-color
                        name_color = mode_color
                        speaker_font = dialogue_font
                    elif "?" in speaker:
                        name_color = "#a855f7"
                        speaker_font = dialogue_font
                    else:
                        name_color = "#38bdf8"
                        speaker_font = dialogue_font

                    # Create name shadows (lock-mode aware)
                    shadows = self._create_text_shadows(
                        text_x, 10, text_anchor, speaker_font,
                        text=speaker, tags=("name_outline",),
                    )
                    self.components.outline_container.extend(shadows)

                    self.components.canvas.create_text(
                        text_x,
                        10,
                        anchor=text_anchor,
                        font=speaker_font,
                        fill=name_color,
                        text=speaker,
                        tags=("name",),
                    )

                # Display dialogue with shadows
                if dialogue:
                    dialogue_y = 35

                    # Create dialogue shadows (lock-mode aware)
                    shadows = self._create_text_shadows(
                        text_x, dialogue_y, text_anchor, dialogue_font,
                        text="", width=available_width, tags=("text_outline",),
                    )
                    self.components.outline_container.extend(shadows)

                    # Create main dialogue text with Rich Text support
                    # Use single text object as placeholder for text_container compatibility
                    self.components.text_container = self.components.canvas.create_text(
                        text_x,
                        dialogue_y,
                        anchor=text_anchor,
                        font=dialogue_font,
                        fill=self._get_text_color(),
                        text="",
                        width=available_width,
                        tags=("text", "rich_text_main"),
                    )

                    # For speed: Show text immediately instead of typewriter effect with Rich Text support
                    self._update_rich_text_dialogue(dialogue, dialogue_font, dialogue_y, available_width)
            else:
                # No speaker - direct dialogue
                # Create text shadows (lock-mode aware)
                shadows = self._create_text_shadows(
                    text_x, 10, text_anchor, dialogue_font,
                    text="", width=available_width, tags=("text_outline",),
                )
                self.components.outline_container.extend(shadows)

                # Create main text
                self.components.text_container = self.components.canvas.create_text(
                    text_x,
                    10,
                    anchor=text_anchor,
                    font=dialogue_font,
                    fill=self._get_text_color(),
                    text="",
                    width=available_width,
                    tags=("text",),
                )

                # For speed: Show text immediately instead of typewriter effect
                # 🔧 FIXED: Check for Rich Text / names before updating
                if hasattr(self, 'rich_text_formatter') and self._needs_rich_text(text):
                    # Rich Text case: Store text and apply Rich Text formatting
                    logging.info(f"🎨 FAST_UPDATE: Applying Rich Text to: {text}")
                    self.dialogue_text = text
                    self._apply_rich_text_to_completed_dialogue()
                else:
                    # Normal text case: Update shadow texts first
                    for outline in self.components.outline_container:
                        item_type = self.components.canvas.type(outline)
                        if item_type == "text":
                            self.components.canvas.itemconfig(outline, text=text)

                    # Update main text
                    self.components.canvas.itemconfig(
                        self.components.text_container, text=text
                    )

        except Exception as e:
            logging.error(f"Error in fast normal text handling: {e}")

    def _handle_choice_text_fast(
        self, text: str, dialogue_font: tuple, available_width: int
    ) -> None:
        """Fast choice text handling"""
        try:
            # Use existing choice handling but skip heavy processing
            self._handle_choice_text(
                text, dialogue_font, dialogue_font, available_width
            )
        except Exception as e:
            logging.error(f"Error in fast choice text handling: {e}")
            self._original_update_text(text)

    def _original_update_text(self, text: str, is_lore_text: bool = False) -> None:
        """
        Original update text method (preserved for fallback)
        """
        try:
            # *** FIX: Prevent conflicting updates during Rich Text processing ***
            if hasattr(self, '_rich_text_processing') and self._rich_text_processing:
                logging.info(f"SKIPPED: Original update blocked during Rich Text processing: {text[:50]}...")
                return

            logging.info(f"Updating text in UI: {text}")
            logging.info(
                f"DEBUG: Raw text has {text.count('<NL>')} <NL> tags and {text.count(chr(10))} newlines"
            )

            if not text:
                return

            # คำข้อความระบุภาษาออก ก่อนแสดงผลการแปล
            if text and text.startswith("Thai:"):
                text = text[5:].strip()  # ตัด "Thai:" และช่องว่างออก
                logging.info(f"Removed 'Thai:' prefix, new text: {text}")

            # รีเซ็ตสถานะการทำ fade out
            if self.state.is_fading:
                self.state.is_fading = False
                # 🎯 TRANSPARENCY FIX: Restore user transparency when fade is interrupted
                self.restore_user_transparency()

            # ยกเลิก timer fade out ถ้ามี
            if self.state.fade_timer_id:
                self.root.after_cancel(self.state.fade_timer_id)
                self.state.fade_timer_id = None

            # บันทึกเวลาปัจจุบันเป็นเวลาล่าสุดที่มีการอัพเดตข้อความ
            self.state.last_activity_time = time.time()

            # รีเซ็ตสถานะ just_faded_out ถ้ามี
            if hasattr(self.state, "just_faded_out"):
                self.state.just_faded_out = False

            # รีเซ็ตสีข้อความให้เป็นสีเดิม (กรณีที่กำลัง fade อยู่)
            if self.components.text_container:
                self.components.canvas.itemconfig(
                    self.components.text_container, fill=self._get_text_color()
                )

            for outline in self.components.outline_container:
                if self.components.canvas.type(outline) == "text":
                    self.components.canvas.itemconfig(
                        outline, fill="#000000"
                    )  # รีเซ็ตสีเงาเป็นสีดำ

            # รีเซ็ตสีของชื่อตัวละครที่อาจกำลัง fade out
            for name_item in self.components.canvas.find_withtag("name"):
                text_content = self.components.canvas.itemcget(name_item, "text")
                if text_content:
                    # Get base color
                    base_color = "#a855f7" if "?" in text_content else "#38bdf8"
                    # Override for battle/cutscene modes
                    if self.battle_mode_active:
                        name_color = "#FF6B00"  # ส้มสด (Vibrant Orange)
                    elif self.cutscene_mode_active:
                        name_color = "#FFD700"  # ทอง (Gold)
                    else:
                        name_color = base_color

                    # เช็คว่าเป็น text item ก่อนอัพเดตสี (ข้าม shadow images)
                    item_type = self.components.canvas.type(name_item)
                    if item_type == "text":
                        self.components.canvas.itemconfig(name_item, fill=name_color)

            # รีเซ็ตเครื่องหมาย confirm ที่อาจถูกซ่อนไว้ในระหว่าง fade out
            for confirm_icon in self.components.canvas.find_withtag("confirm_icon"):
                self.components.canvas.itemconfig(confirm_icon, state="normal")

            for outline in self.components.outline_container:
                if self.components.canvas.type(outline) == "text":
                    self.components.canvas.itemconfig(
                        outline, fill="#000000"
                    )  # รีเซ็ตสีเงาเป็นสีดำ

            # ประมวลผลข้อความภาษาไทยก่อนแสดงผล
            text = self.preprocess_thai_text(text)
            logging.info(
                f"DEBUG: After preprocess, text has {text.count('<NL>')} <NL> tags and {text.count(chr(10))} newlines"
            )

            # ล้าง canvas เพื่อเตรียมเนื้อหาใหม่ - เพิ่มการลบทั้งหมดแทนการอัพเดตเฉพาะข้อความ
            self.components.canvas.delete("all")
            self.components.outline_container = []
            self.components.text_container = None

            # Base configuration
            outline_offset = 1
            outline_color = "#000000"
            outline_positions = [
                (-1, -1),
                (-1, 0),
                (-1, 1),
                (0, -1),
                (0, 1),
                (1, -1),
                (1, 0),
                (1, 1),
            ]

            # เริ่มการแสดงผลที่ด้านบนของ canvas
            self.components.canvas.yview_moveto(0)

            # Get font sizes - ย้ายขึ้นมาก่อนการตรวจสอบเงื่อนไข
            current_font_size = self.settings.get("font_size", 24)

            # 🎬 MODE-BASED FONT SIZING: Adjust font size based on active mode
            if self.battle_mode_active:
                adjusted_font_size = current_font_size + 2  # +2pt for battle
                small_font_size = int(adjusted_font_size * 0.7)
                dialogue_font = (self.settings.get("font"), adjusted_font_size)
                logging.info(f"⚔️ Battle mode: Using enlarged font {adjusted_font_size}pt (+2pt from {current_font_size}pt)")
            elif self.cutscene_mode_active:
                adjusted_font_size = current_font_size + 4  # +4pt for cutscene
                small_font_size = int(adjusted_font_size * 0.7)
                dialogue_font = (self.settings.get("font"), adjusted_font_size)
                logging.info(f"🎬 Cutscene mode: Using enlarged font {adjusted_font_size}pt (+4pt from {current_font_size}pt)")
            else:
                adjusted_font_size = current_font_size
                small_font_size = int(current_font_size * 0.7)
                dialogue_font = (self.settings.get("font"), current_font_size)

            # Create font configurations
            small_font = (self.settings.get("font"), small_font_size)

            self.state.full_text = text
            available_width = self.components.canvas.winfo_width() - 40

            # 🎯 CHOICE DETECTION — pipe format OR chat_type 70 from C# choice addon
            is_choice_dialogue = self._is_choice_dialogue(text)
            if not is_choice_dialogue and getattr(self, '_current_chat_type', 0) == 70:
                is_choice_dialogue = True
                logging.info("[CHOICE] Detected via chat_type=70 (translated text, no pipes)")

            # 💬 COMMENTED: Choice dialog detection patterns - ปิดการใช้งานเพื่อความเรียบง่าย
            """
            # รูปแบบที่ถูกต้องของ "What will you say?" รวมถึงคำที่อาจเกิดจาก OCR ผิดพลาด
            english_patterns = [
                "What will you say?",
                "What will you say",
                "Whatwill you say?",
                "What willyou say?",
                "What will yousay?",
                "Whatwillyou say?",
                "What wiIl you say?",  # ตัว I อาจถูก OCR เป็น l
                "What wilI you say?",  # ตัว l อาจถูก OCR เป็น I
            ]

            # รูปแบบภาษาไทย - เฉพาะที่ MBB.py ส่งมาเท่านั้น
            thai_patterns = ["คุณจะพูดว่าอย่างไร?", "คุณจะพูดว่าอย่างไร"]

            # รวมทั้งหมดเป็นรายการเดียว
            choice_patterns = english_patterns + thai_patterns

            # ตรวจสอบแบบเข้มงวด - ต้องเป็นข้อความที่ขึ้นต้นด้วยรูปแบบเหล่านี้เท่านั้น
            logging.info(f"Checking choice patterns against text start: '{text[:50]}'")

            for pattern in choice_patterns:
                # ตรวจสอบว่าข้อความเริ่มต้นด้วยรูปแบบนี้หรือไม่
                text_start = text.strip()
                pattern_lower = pattern.lower()

                if (
                    text_start.startswith(pattern)
                    or text_start.lower().startswith(pattern_lower)
                    or text_start.startswith(pattern.rstrip("?"))
                    or text_start.lower().startswith(pattern_lower.rstrip("?"))
                ):

                    is_choice_dialogue = True
                    logging.info(
                        f"Choice detected by pattern match: '{pattern}' in '{text_start[:30]}...'"
                    )
                    break

            # เพิ่มการตรวจสอบพิเศษสำหรับ "คุณจะพูดว่าอย่างไร?" โดยเฉพาะ
            if not is_choice_dialogue:
                if "คุณจะพูด" in text[:30] and (
                    "ว่า" in text[:30] or "อย่างไร" in text[:30]
                ):
                    is_choice_dialogue = True
                    logging.info(
                        "Choice detected by Thai keyword matching: คุณจะพูด + ว่า/อย่างไร"
                    )

            logging.info(
                f"Final choice detection result: {is_choice_dialogue} for text: '{text[:100]}...'"
            )
            """

            # ดำเนินการตามประเภทของข้อความ
            if is_choice_dialogue:
                self._handle_choice_text(
                    text,
                    small_font,
                    dialogue_font,
                    available_width,
                    outline_positions,
                    outline_offset,
                    outline_color,
                )
            else:
                self._handle_normal_text(
                    text,
                    small_font,
                    dialogue_font,
                    available_width,
                    outline_positions,
                    outline_offset,
                    outline_color,
                    is_lore_text=is_lore_text,
                )

        except Exception as e:
            logging.error(f"Error in update_text: {e}")
            self._show_error(str(e))

    def update_character_names(self, new_names):
        """อัพเดตรายชื่อตัวละครและรีเฟรช UI"""
        self.names = new_names

        # รีเฟรชการแสดงผลข้อความปัจจุบัน
        if hasattr(self, "state") and self.state.full_text:
            current_text = self.state.full_text
            current_type = getattr(self, 'current_chat_type', 61)
            self.update_text(current_text, chat_type=current_type)

    def _is_choice_dialogue(self, text: str) -> bool:
        """Detect if text is a choice dialogue based on pipe-separated format from C#

        Format: "What will you say? | Choice1 | Choice2 | ..."
        """
        # Check for pipe-separated format
        if " | " in text:
            parts = text.split(" | ")
            if len(parts) >= 2:
                # Check if first part matches "What will you say?" patterns
                first_part = parts[0].strip().lower()
                # English patterns
                if "what will you say" in first_part:
                    return True
                # Thai patterns
                if "คุณจะพูดว่าอย่างไร" in first_part or "คุณจะพูด" in first_part:
                    return True
        return False

    def _handle_choice_text(
        self,
        text: str,
        small_font: tuple,
        dialogue_font: tuple,
        available_width: int,
        outline_positions: list,
        outline_offset: int,
        outline_color: str,
    ) -> None:
        """
        Handle choice dialogue text display
        Args:
            text: Full text to display
            small_font: Font tuple for header
            dialogue_font: Font tuple for choices
            available_width: Available width for text
            outline_positions: List of outline position offsets
            outline_offset: Outline offset value
            outline_color: Color for text outline
        """
        logging.info(f"_handle_choice_text called with text: '{text[:100]}...'")

        # กำหนด header ตามภาษา
        header = ""
        choices_text = ""

        import re

        # 🎯 Parse pipe-separated format from C#: "Header | Choice1 | Choice2 | ..."
        if " | " in text:
            parts = [p.strip() for p in text.split(" | ")]
            if len(parts) >= 2:
                header_text = parts[0]  # "What will you say?"
                choice_texts = parts[1:]  # ["Choice1", "Choice2", ...]

                # Check if header should NOT be translated (keep as English)
                english_headers = [
                    "What will you say?",
                    "What will you say",
                    "Whatwill you say?",
                    "What willyou say?"
                ]

                # Keep English header if it matches pattern
                display_header = header_text
                for pattern in english_headers:
                    if pattern.lower() in header_text.lower():
                        display_header = "What will you say?"  # Normalize to standard format
                        logging.info(f"[CHOICE] Keeping English header: {display_header}")
                        break

                header = display_header
                choices_text = "\n".join(choice_texts)
                logging.info(f"[CHOICE] Parsed pipe format - Header: '{header}', Choices: {len(choice_texts)}")
        else:
            # Fallback: Parse newline-separated format
            processed_text = text.strip()

            # แทนที่ special newline patterns เป็น \n ปกติ
            processed_text = processed_text.replace("<NL>", "\n")
            processed_text = processed_text.replace("\r\n", "\n")
            processed_text = processed_text.replace("\r", "\n")

            # ลบ \n ซ้ำๆ
            processed_text = re.sub(r"\n+", "\n", processed_text)

            lines = processed_text.split("\n")
            logging.info(f"Split into {len(lines)} lines after processing")

            if len(lines) >= 2:
                # ถือว่าบรรทัดแรกเป็น header เสมอ
                first_line = lines[0].strip()
                remaining_lines = lines[1:]

                # ตรวจสอบว่าบรรทัดแรกมีลักษณะเป็น header หรือไม่
                if (
                    "?" in first_line
                    or any(
                        word in first_line
                        for word in ["พูด", "ว่า", "ไร", "ดี", "อะไร", "จะ", "คุณ", "ท่าน"]
                    )
                    or len(first_line.split()) <= 8
                ):  # บรรทัดสั้นมักเป็น header
                    header = first_line
                    choices_text = "\n".join(remaining_lines)
                    logging.info(f"Using first line as header: '{header}'")
                else:
                    # ถ้าบรรทัดแรกไม่เหมือน header ให้ใช้ header เริ่มต้น
                    header = "คุณจะพูดว่าอย่างไร?"
                    choices_text = processed_text
                    logging.info(f"Using default header, full text as choices")
            else:
                # ถ้ามีบรรทัดเดียว ให้ใช้ header เริ่มต้น
                header = "คุณจะพูดว่าอย่างไร?"
                choices_text = processed_text
                logging.info(f"Single line text, using default header")

        # ลบช่องว่างไม่จำเป็นจากต้นข้อความตัวเลือก
        choices_text = choices_text.lstrip("\n").lstrip()
        logging.info(f"Cleaned choices_text: '{choices_text[:100]}...'")

        # แยกตัวเลือกด้วยการขึ้นบรรทัดใหม่และรูปแบบอื่นๆ
        choices = []

        # วิธีที่ 1: แยกด้วย newlines
        if "\n" in choices_text:
            raw_choices = [
                choice.strip() for choice in choices_text.split("\n") if choice.strip()
            ]

            # ตรวจสอบบรรทัดที่ยาวเกินไปและแยกต่อด้วยเครื่องหมายวรรคตอน
            processed_choices = []
            for choice in raw_choices:
                # ถ้าบรรทัดยาวเกิน 100 ตัวอักษร และมีเครื่องหมายวรรคตอนหลายตัว ให้แยกต่อ
                if (
                    len(choice) > 100
                    and choice.count("!") + choice.count("?") + choice.count(".") >= 2
                ):
                    # แยกด้วยเครื่องหมายสิ้นสุดประโยค
                    sub_choices = re.split(r"(?<=[.!?])\s+", choice)
                    valid_sub_choices = []
                    for sub_choice in sub_choices:
                        sub_choice = sub_choice.strip()
                        # เก็บเฉพาะข้อความที่มีความยาวเหมาะสม (10-150 ตัวอักษร)
                        if 10 <= len(sub_choice) <= 150:
                            valid_sub_choices.append(sub_choice)

                    if len(valid_sub_choices) > 1:  # แยกได้จริง
                        processed_choices.extend(valid_sub_choices)
                        logging.info(
                            f"Split long choice into {len(valid_sub_choices)} parts: {[s[:30]+'...' for s in valid_sub_choices]}"
                        )
                    else:
                        processed_choices.append(choice)  # ไม่แยก ใช้ต้นฉบับ
                else:
                    processed_choices.append(choice)

            choices = processed_choices
            logging.info(
                f"Found {len(choices)} choices by newline split (after processing long lines)"
            )
        # วิธีที่ 2: แยกด้วย numbered patterns (1. 2. 3.)
        elif re.search(r"\d+\.", choices_text):
            numbered_choices = re.split(r"(?=\d+\.)", choices_text)
            choices = [choice.strip() for choice in numbered_choices if choice.strip()]
            logging.info(f"Found {len(choices)} choices by numbered pattern")
        # วิธีที่ 3: แยกด้วย bullet points
        elif re.search(r"[•◆○□■★☆\-\*]", choices_text):
            bullet_choices = re.split(r"(?=[•◆○□■★☆\-\*])", choices_text)
            choices = [choice.strip() for choice in bullet_choices if choice.strip()]
            logging.info(f"Found {len(choices)} choices by bullet pattern")
        elif choices_text:
            # ถ้าไม่มี pattern ใดๆ แต่มีข้อความ ให้ถือว่าเป็น choice เดียว
            choices = [choices_text]
            logging.info(f"Single choice found: '{choices_text[:50]}...'")

        # ถ้าไม่มี choices เลย ให้ใช้ทั้งก้อน
        if not choices:
            choices = [processed_text]
            header = "คุณจะพูดว่าอย่างไร?"
            logging.info("No choices parsed, using full text as single choice")

        # กรองคำ header ที่ไม่ต้องการออกจากตัวเลือก และป้องกัน header ซ้ำ
        filtered_choices = []
        unwanted_headers = [
            "ท่านจะว่าอย่างไร",
            "จะว่าอย่างไรดี",
            "ท่านจะพูดอะไร",
            "คุณจะว่าอย่างไร",
            "พูดอะไรดี",
            "What will you say",
            "คุณจะพูดว่าอย่างไร",
            "ท่านจะพูดว่าอย่างไร",
            "ท่านจะกล่าวว่าอย่างไร",
            "คุณจะกล่าวว่าอย่างไร",
            "เจ้าจะกล่าวว่าอย่างไร",
            "จะกล่าวว่าอย่างไร",
        ]

        # ตรวจสอบว่า header ปัจจุบันซ้ำกับ choices หรือไม่
        header_lower = header.lower().strip()

        # เก็บข้อความที่ผ่านการกรองแล้วเพื่อตรวจสอบการซ้ำซ้อน
        seen_choices = set()

        for choice in choices:
            # ลบ header ที่ไม่ต้องการออก
            cleaned_choice = choice.strip()
            should_skip = False

            # ตรวจสอบว่าตัวเลือกนี้ซ้ำกับ header หรือไม่
            if cleaned_choice.lower().strip() == header_lower:
                should_skip = True
                logging.info(f"Skipped duplicate header in choices: '{cleaned_choice}'")
            else:
                # ตรวจสอบ unwanted headers อื่นๆ แต่ให้ระวังไม่ตัดจากกลางประโยค
                for unwanted in unwanted_headers:
                    if cleaned_choice.lower().startswith(unwanted.lower()):
                        # ตรวจสอบว่าเป็น header แยกต่างหาก หรือ เป็นส่วนหนึ่งของประโยคยาว
                        remainder = cleaned_choice[len(unwanted) :].strip()

                        # ถ้าส่วนที่เหลือสั้น หรือ ไม่มีเนื้อหาสมบูรณ์ ให้ข้าม
                        if len(remainder) <= 5:
                            should_skip = True
                            break
                        # ถ้าส่วนที่เหลือเป็นแค่เครื่องหมายวรรคตอน ให้ข้าม
                        elif remainder.startswith(("?", ":", "!", ".")):
                            should_skip = True
                            break
                        # ถ้าส่วนที่เหลือเป็นประโยคสมบูรณ์ (มีกริยาหรือข้อความยาว) ให้ใช้ทั้งหมด
                        elif len(remainder) > 15 or any(
                            word in remainder
                            for word in [
                                "การ",
                                "เรา",
                                "จะ",
                                "ไม่",
                                "ให้",
                                "ได้",
                                "มา",
                                "ไป",
                            ]
                        ):
                            # ไม่ตัด header ออกเพราะเป็นส่วนหนึ่งของประโยคยาว
                            logging.info(
                                f"Keeping full choice (has substantial content): '{cleaned_choice[:50]}...'"
                            )
                            break
                        else:
                            # ตัด header ออกเฉพาะกรณีที่เหลือเป็นข้อความสั้นๆ แยกจากกัน
                            cleaned_choice = remainder.lstrip("?:!. ").strip()
                            logging.info(f"Trimmed header '{unwanted}' from choice")
                            break

            # ตรวจสอบการซ้ำซ้อนโดยใช้ similarity
            if not should_skip and cleaned_choice:
                # ตรวจสอบว่าข้อความนี้คล้ายกับที่มีอยู่แล้วหรือไม่
                is_duplicate = False
                choice_words = set(cleaned_choice.lower().split())

                for existing_choice in seen_choices:
                    existing_words = set(existing_choice.lower().split())

                    # ถ้าคำซ้ำกัน > 70% ถือเป็น duplicate
                    if choice_words and existing_words:
                        overlap = len(choice_words.intersection(existing_words))
                        similarity = overlap / max(
                            len(choice_words), len(existing_words)
                        )

                        if similarity > 0.7:
                            is_duplicate = True
                            logging.info(
                                f"Skipped duplicate choice (similarity: {similarity:.2f}): '{cleaned_choice[:30]}...' vs '{existing_choice[:30]}...'"
                            )
                            break

                if not is_duplicate:
                    filtered_choices.append(cleaned_choice)
                    seen_choices.add(cleaned_choice)
                    logging.info(f"Added filtered choice: '{cleaned_choice[:50]}...'")

        # ใช้ choices ที่กรองแล้ว
        choices = filtered_choices if filtered_choices else choices
        logging.info(f"Final choices count after filtering: {len(choices)}")

        # เพิ่มบุลเล็ตให้แต่ละตัวเลือก (ถ้ายังไม่มี)
        formatted_choices = []
        for choice in choices:
            # ตรวจสอบว่าตัวเลือกนี้มีบุลเล็ตหรือตัวเลขนำหน้าแล้วหรือไม่
            has_prefix = False
            for prefix in ["•", "◆", "○", "□", "■", "★", "☆", "-", "*"]:
                if choice.strip().startswith(prefix):
                    has_prefix = True
                    break

            # ตรวจสอบว่าเริ่มต้นด้วยตัวเลขตามด้วยจุดหรือวงเล็บปิด
            if re.match(r"^\d+[\.\)\-]", choice.strip()):
                has_prefix = True

            if not has_prefix:
                formatted_choices.append(f"• {choice}")
            else:
                formatted_choices.append(choice)

        # รวมตัวเลือกเข้าด้วยกันด้วยการขึ้นบรรทัดใหม่
        choices_display = "\n".join(formatted_choices)

        # ถ้าไม่มีตัวเลือก แสดงเฉพาะ header
        if not formatted_choices:
            choices_display = ""

        # ปรับเงาเป็นสองชั้น
        # ใช้เงาเหมือนข้อความปกติ (แก้ไขปัญหาเงาหนาเกินไป)
        # สร้างเงาสำหรับ header ด้วย 8-point shadow system (reverted)
        outline_offset = ShadowConfig.get_scaled_params(small_font[1])["offset_x"] or 1
        outline_color = ShadowConfig.SHADOW_COLOR

        # 8-point outline positions
        outline_positions = [
            (-1, -1),
            (-1, 0),
            (-1, 1),
            (0, -1),
            (0, 1),
            (1, -1),
            (1, 0),
            (1, 1),
        ]

        # 🎯 Use BOLD font for header (gold color)
        header_font = (self.settings.get("font"), int(small_font[1] * 1.2), "bold")

        for dx, dy in outline_positions:
            self.components.canvas.create_text(
                10 + dx * outline_offset,
                10 + dy * outline_offset,
                anchor="nw",
                font=header_font,
                fill=outline_color,
                text=header,
                width=available_width,
                tags=("header_outline",),
            )

        # Create header text with static header (GOLD BOLD)
        header_text = self.components.canvas.create_text(
            10,
            10,
            anchor="nw",
            font=header_font,
            fill="#FFD700",  # Gold color for header
            text=header,
            width=available_width,
            tags=("header_text",),  # เพิ่ม tag เพื่อค้นหาได้ง่าย
        )

        # Calculate position for choices
        header_bbox = self.components.canvas.bbox(header_text)
        choices_y = header_bbox[3] + 12

        # สร้างเงาสำหรับตัวเลือกด้วย 8-point shadow system (reverted)
        self.components.outline_container = []
        outline_offset = (
            ShadowConfig.get_scaled_params(dialogue_font[1])["offset_x"] or 1
        )
        outline_color = ShadowConfig.SHADOW_COLOR

        # 8-point outline positions
        outline_positions = [
            (-1, -1),
            (-1, 0),
            (-1, 1),
            (0, -1),
            (0, 1),
            (1, -1),
            (1, 0),
            (1, 1),
        ]

        for dx, dy in outline_positions:
            outline = self.components.canvas.create_text(
                10 + dx * outline_offset,
                choices_y + dy * outline_offset,
                anchor="nw",
                font=dialogue_font,
                fill=outline_color,
                text=choices_display,
                width=available_width,
                tags=("choices_outline",),
            )
            self.components.outline_container.append(outline)

        # Create choices text container - แสดงข้อความตัวเลือกทันทีโดยไม่ใช้ typewriter effect
        self.components.text_container = self.components.canvas.create_text(
            10,
            choices_y,
            anchor="nw",
            font=dialogue_font,
            fill="white",
            text=choices_display,
            width=available_width,
            tags=("choices",),
        )

        # สำคัญ: ปิดการใช้งาน typewriter effect สำหรับ choice dialogue
        self.state.is_typing = False
        self.dialogue_text = choices_display

        # ตรวจสอบ overflow
        self.check_text_overflow()

        # *** REVERSED: Start fade timer only if fade out is enabled ***
        if self.state.fadeout_enabled:
            self.start_fade_timer()

    def _handle_normal_text(
        self,
        text: str,
        small_font: tuple,
        dialogue_font: tuple,
        available_width: int,
        outline_positions: list,
        outline_offset: int,
        outline_color: str,
        is_lore_text: bool = False,
    ) -> None:
        """
        จัดการแสดงผลข้อความปกติที่ไม่ใช่ choice dialogue
        Args:
            text: ข้อความที่จะแสดง
            small_font: ฟอนต์สำหรับชื่อ
            dialogue_font: ฟอนต์สำหรับบทสนทนา
            available_width: ความกว้างที่มีให้แสดงผล
            outline_positions: ตำแหน่งของเส้นขอบ
            outline_offset: ระยะห่างของเส้นขอบ
            outline_color: สีของเส้นขอบ
        """
        try:
            # Check if text contains speaker name
            if not is_lore_text and ":" in text:
                name, dialogue = text.split(":", 1)
                name = name.strip()
                # Safety: strip rich text markers and zero-width chars from speaker name
                name = name.replace("**", "").replace("*", "").replace("\u200b", "").replace("\u200c", "").strip()
                dialogue = dialogue.strip()

                # ฟังก์ชันช่วยปรับข้อความภาษาไทยให้แสดงผลได้ดีขึ้น - แก้ไขการเว้นวรรคผิดปกติ
                def adjust_thai_text(text):
                    # ฟังก์ชันนี้แก้ไขใหม่เพื่อป้องกันการเว้นวรรคมากเกินไป

                    # 1. ป้องกันคำที่ไม่ควรถูกตัดกลาง แต่ไม่ต้องเพิ่มช่องว่าง
                    # ใช้วิธีการตรวจจับคำแทนการเพิ่มช่องว่าง
                    critical_thai_words = [
                        "การ",
                        "และ",
                        "หรือ",
                        "ที่",
                        "ของ",
                        "ให้",
                        "ใน",
                        "จาก",
                        "กับ",
                        "เป็น",
                        "จะ",
                        "ได้",
                        "มี",
                        "ไม่",
                        "ต้อง",
                        "เรา",
                        "พวก",
                        "เขา",
                    ]

                    # 2. แยกคำภาษาอังกฤษออกจากคำไทยเฉพาะกรณีจำเป็น
                    # ใช้เฉพาะกับคำสำคัญที่อาจทำให้เข้าใจผิด
                    english_words = [
                        "the",
                        "a",
                        "an",
                        "of",
                        "for",
                        "from",
                        "to",
                        "in",
                        "on",
                        "with",
                    ]

                    result = text

                    # 3. ลบช่องว่างซ้ำที่อาจเกิดจากการประมวลผลก่อนหน้า
                    result = re.sub(r"\s+", " ", result)

                    # 4. แก้ไขข้อความที่อาจถูกตัดกลางคำ แต่ไม่เพิ่มช่องว่างเกินจำเป็น
                    # เพิ่มเฉพาะกรณีที่จะทำให้การอ่านง่ายขึ้น

                    # 5. ป้องกันการตัดคำระหว่างตัวเลขกับหน่วยนับ
                    result = re.sub(r"(\d+)([^\s\d])", r"\1 \2", result)

                    return result

                # ปรับข้อความไทยให้แสดงผลได้ดีขึ้น
                dialogue = adjust_thai_text(dialogue)

                # [เพิ่ม] ไฮไลท์ชื่อเฉพาะในข้อความที่มีชื่อผู้พูด
                if hasattr(self, "names") and self.names:
                    dialogue = self.highlight_special_names(dialogue, self.names)

                # 🎬 CENTER ALIGNMENT: Battle Chat & Cutscene modes
                if self.battle_mode_active or self.cutscene_mode_active:
                    # Center position for battle/cutscene modes
                    name_y = 10
                    name_x = available_width // 2
                    name_anchor = "n"  # North = center-aligned
                    text_anchor = "n"
                    mode_name = "Battle" if self.battle_mode_active else "Cutscene"
                    logging.info(f"⚔️🎬 {mode_name} mode: Using center alignment (x={name_x})")
                else:
                    # Default left-aligned for dialogue mode
                    name_y = 10
                    name_x = 10
                    name_anchor = "nw"  # Northwest = left-aligned
                    text_anchor = "nw"

                # Speaker color: battle/cutscene = mono-color, dialogue = cyan/purple
                # All speakers use normal weight (no bold) for compatibility
                mode_color = self._get_text_color()
                if mode_color != "white":
                    # Battle/Cutscene: mono-color
                    name_color = mode_color
                    speaker_font = small_font
                elif "?" in name:
                    name_color = "#a855f7"
                    speaker_font = small_font
                else:
                    name_color = "#38bdf8"
                    speaker_font = small_font

                # สร้างเงาสำหรับชื่อตัวละคร (lock-mode aware)
                shadows = self._create_text_shadows(
                    name_x, name_y, name_anchor, speaker_font,
                    text=name, tags=("name_outline",),
                )
                self.components.outline_container.extend(shadows)

                # Create name text
                name_text = self.components.canvas.create_text(
                    name_x,
                    name_y,
                    anchor=name_anchor,
                    font=speaker_font,
                    fill=name_color,
                    text=name,
                    tags=("name",),
                )

                # Add confirmation icon for verified names
                if name in self.names:
                    name_bbox = self.components.canvas.bbox(name_text)
                    icon_x = name_bbox[2] + 8
                    icon_y = name_y + ((name_bbox[3] - name_bbox[1]) // 2)

                    self.components.canvas.create_image(
                        icon_x,
                        icon_y,
                        image=self.confirm_icon,
                        anchor="w",
                        tags=("confirm_icon",),
                    )

                # Calculate dialogue position
                name_bbox = self.components.canvas.bbox(name_text)

                # ปรับความกว้างของพื้นที่แสดงข้อความภาษาไทย - ใช้ 95% ของความกว้างที่มี
                thai_text_width = int(available_width * 0.95)

                # กำหนดตำแหน่งของข้อความบทสนทนา
                dialogue_y = name_bbox[3] + (small_font[1] * 0.3)

                # 🎬 CENTER ALIGNMENT: Battle Chat & Cutscene modes
                if self.battle_mode_active or self.cutscene_mode_active:
                    dialogue_x = available_width // 2  # Center for battle/cutscene
                else:
                    dialogue_x = 10  # Left-aligned for dialogue

                # รีเซ็ต outline_container เพื่อเตรียมสร้างเงาใหม่
                self.components.outline_container = []

                # สร้างเงาสำหรับข้อความบทสนทนา (lock-mode aware)
                shadows = self._create_text_shadows(
                    dialogue_x, dialogue_y, text_anchor, dialogue_font,
                    text="", width=thai_text_width, tags=("dialogue_outline",),
                )
                self.components.outline_container.extend(shadows)

                # Create dialogue text container
                self.components.text_container = self.components.canvas.create_text(
                    dialogue_x,
                    dialogue_y,
                    anchor=text_anchor,
                    font=dialogue_font,
                    fill=self._get_text_color(),
                    text="",
                    width=thai_text_width,
                    tags=("dialogue",),
                )

            else:  # Text without speaker name
                # กำหนดข้อความทั้งหมดเป็น dialogue
                dialogue = text.strip()

                # ปรับข้อความไทยให้แสดงผลได้ดีขึ้น - ใช้ฟังก์ชันเดียวกับด้านบน
                def adjust_thai_text(text):
                    # ฟังก์ชันนี้แก้ไขใหม่เพื่อป้องกันการเว้นวรรคมากเกินไป

                    # 1. ป้องกันคำที่ไม่ควรถูกตัดกลาง แต่ไม่ต้องเพิ่มช่องว่าง
                    # ใช้วิธีการตรวจจับคำแทนการเพิ่มช่องว่าง
                    critical_thai_words = [
                        "การ",
                        "และ",
                        "หรือ",
                        "ที่",
                        "ของ",
                        "ให้",
                        "ใน",
                        "จาก",
                        "กับ",
                        "เป็น",
                        "จะ",
                        "ได้",
                        "มี",
                        "ไม่",
                        "ต้อง",
                        "เรา",
                        "พวก",
                        "เขา",
                    ]

                    # 2. แยกคำภาษาอังกฤษออกจากคำไทยเฉพาะกรณีจำเป็น
                    # ใช้เฉพาะกับคำสำคัญที่อาจทำให้เข้าใจผิด
                    english_words = [
                        "the",
                        "a",
                        "an",
                        "of",
                        "for",
                        "from",
                        "to",
                        "in",
                        "on",
                        "with",
                    ]

                    result = text

                    # 3. ลบช่องว่างซ้ำที่อาจเกิดจากการประมวลผลก่อนหน้า
                    result = re.sub(r"\s+", " ", result)

                    # 4. แก้ไขข้อความที่อาจถูกตัดกลางคำ แต่ไม่เพิ่มช่องว่างเกินจำเป็น
                    # เพิ่มเฉพาะกรณีที่จะทำให้การอ่านง่ายขึ้น

                    # 5. ป้องกันการตัดคำระหว่างตัวเลขกับหน่วยนับ
                    result = re.sub(r"(\d+)([^\s\d])", r"\1 \2", result)

                    return result

                dialogue = adjust_thai_text(dialogue)

                # [เพิ่ม] ไฮไลท์ชื่อเฉพาะในข้อความ
                if hasattr(self, "names") and self.names:
                    dialogue = self.highlight_special_names(dialogue, self.names)

                # ปรับความกว้างของพื้นที่แสดงข้อความภาษาไทย - ใช้ 95% ของความกว้างที่มี
                thai_text_width = int(available_width * 0.95)

                # รีเซ็ต outline_container ก่อนสร้างเงาใหม่
                self.components.outline_container = []

                # ตำแหน่งเริ่มต้นสำหรับข้อความที่ไม่มีชื่อคนพูด
                dialogue_y = 10

                # 🎬 CENTER ALIGNMENT: Battle Chat & Cutscene modes (no speaker)
                if self.battle_mode_active or self.cutscene_mode_active:
                    dialogue_x = available_width // 2  # Center for battle/cutscene
                    text_anchor = "n"  # North = center-aligned
                    mode_name = "Battle" if self.battle_mode_active else "Cutscene"
                    logging.info(f"⚔️🎬 {mode_name} mode (no speaker): Using center alignment (x={dialogue_x})")
                else:
                    dialogue_x = 10  # Left-aligned for dialogue
                    text_anchor = "nw"  # Northwest = left-aligned

                # สร้างเงาสำหรับข้อความทั้งหมด (lock-mode aware)
                shadows = self._create_text_shadows(
                    dialogue_x, dialogue_y, text_anchor, dialogue_font,
                    text="", width=thai_text_width, tags=("text_outline",),
                )
                self.components.outline_container.extend(shadows)

                # สร้างข้อความหลัก
                self.components.text_container = self.components.canvas.create_text(
                    dialogue_x,
                    dialogue_y,
                    anchor=text_anchor,
                    font=dialogue_font,
                    fill=self._get_text_color(),
                    text="",
                    width=thai_text_width,
                    tags=("text",),
                )

            # Start typewriter effect with dialogue text
            self.dialogue_text = dialogue
            if hasattr(self, "type_writer_timer") and self.type_writer_timer:
                self.root.after_cancel(self.type_writer_timer)
                self.type_writer_timer = None

            # ENABLE TYPEWRITER EFFECT for Dalamud mode
            # User requested typewriter effect to work with text hook integration
            self.state.is_typing = True
            self.type_writer_effect(dialogue)

        except Exception as e:
            self.logging_manager.log_error(f"Error in handle normal text: {e}")

    def type_writer_effect(self, text: str, index: int = 0, delay: int = 15) -> None:
        """
        Create typewriter effect with adaptive speed for better performance
        Args:
            text: Text to display
            index: Current character index
            delay: Delay between characters in milliseconds
        """
        try:
            if not self.state.is_typing:
                return

            if index < len(text):
                # เพิ่ม batch size เริ่มต้นสำหรับภาษาไทย
                batch_size = 3  # เพิ่มจาก 2 เป็น 3

                # ตรวจสอบว่าเป็นข้อความภาษาไทยแบบเร็ว
                is_thai = bool(
                    re.search(
                        r"[\u0E00-\u0E7F]", text[index : min(index + 20, len(text))]
                    )
                )

                if is_thai:
                    # ใช้ batch size ที่ใหญ่ขึ้นสำหรับข้อความไทย
                    batch_size = 5
                elif len(text) > 100:
                    batch_size = 4

                # ปรับ delay ตามอักขระ
                current_char = text[index : index + 1] if index < len(text) else ""
                if current_char in ".!?":
                    adjusted_delay = delay * 3
                elif current_char in ", ":
                    adjusted_delay = delay * 2
                else:
                    adjusted_delay = delay

                # คำนวณตำแหน่งถัดไปแบบง่าย
                next_index = min(index + batch_size, len(text))

                # ตรวจสอบ ZWSP แบบเร็ว
                if next_index < len(text) and text[next_index] == "\u200b":
                    # ข้าม ZWSP ไปเลย
                    next_index += 1

                # แสดงข้อความถึงตำแหน่งที่คำนวณได้
                next_text = text[:next_index]

                # อัพเดต UI - ลดการเรียกใช้ itemconfig
                if self.components.outline_container:
                    # อัพเดต outline แบบ batch (ข้าม shadow images)
                    for i in range(0, len(self.components.outline_container), 3):
                        outline = self.components.outline_container[i]
                        # เช็คว่าเป็น text item หรือ image item
                        item_type = self.components.canvas.type(outline)
                        if item_type == "text":
                            self.components.canvas.itemconfig(outline, text=next_text)
                            if i == 0:  # tag_lower เฉพาะครั้งแรก
                                self.components.canvas.tag_lower(outline)

                # อัพเดตข้อความหลัก
                self.components.canvas.itemconfig(
                    self.components.text_container, text=next_text
                )

                # ลดการเรียก update_idletasks
                if index % 20 == 0:  # อัพเดททุกๆ 20 ตัวอักษร
                    self.root.update_idletasks()

                if self.state.is_typing:
                    self.type_writer_timer = self.root.after(
                        int(adjusted_delay),
                        lambda: self.type_writer_effect(text, next_index, delay),
                    )
            else:
                # การพิมพ์ข้อความเสร็จสิ้น
                self.state.is_typing = False

                # *** INTEGRATED: Check for Rich Text / names after typewriter completes ***
                if hasattr(self, 'rich_text_formatter') and hasattr(self, 'dialogue_text'):
                    if self._needs_rich_text(self.dialogue_text):
                        logging.info(f"🎨 POST-TYPEWRITER: Applying Rich Text to completed text: {self.dialogue_text}")
                        self._apply_rich_text_to_completed_dialogue()

                self.check_text_overflow()

                # เริ่ม fade timer
                self.state.last_activity_time = time.time()
                if self.state.fade_timer_id:
                    self.root.after_cancel(self.state.fade_timer_id)
                self.state.fade_timer_id = self.root.after(
                    10000, self.check_and_start_fade
                )

        except Exception as e:
            logging.error(f"Error in type_writer_effect: {e}")
            self.state.is_typing = False

    def is_already_rich_text_processed(self, text):
        """Check if text already has rich text formatting applied"""
        if not text:
            return False

        # Check for nested brackets (multiple levels)
        bracket_count = text.count('『')
        if bracket_count != text.count('』'):
            return True  # Malformed brackets indicate processing issues

        # Check for multiple brackets around same name (nested pattern)
        import re
        nested_pattern = r'『+([^』]+)』+'
        matches = re.findall(nested_pattern, text)
        for match in matches:
            # If any name has more than single brackets, it's already processed
            single_bracket_pattern = f'『{re.escape(match)}』'
            nested_bracket_pattern = f'『『{re.escape(match)}』』'
            if nested_bracket_pattern in text:
                return True

        return False

    def show_full_text(self, event: Optional[tk.Event] = None) -> None:
        """
        Show complete text immediately without typewriter effect
        Args:
            event: Optional tkinter event
        """
        # 🚫 CRITICAL: Prevent action if text is already complete
        if not self.state.is_typing:
            logging.info("🚫 CLICK_IGNORED: Text already complete, ignoring click")
            return

        # ยกเลิก timer ที่กำลังทำงานอยู่
        if hasattr(self, "type_writer_timer") and self.type_writer_timer:
            self.root.after_cancel(self.type_writer_timer)
            self.type_writer_timer = None

        # ยกเลิกสถานะ typing
        self.state.is_typing = False

        # ยกเลิกการ fade out ถ้ากำลังทำอยู่
        if self.state.is_fading:
            self.state.is_fading = False

            # รีเซ็ตสีของข้อความและชื่อกลับเป็นสีเดิม
            if self.components.text_container:
                self.components.canvas.itemconfig(
                    self.components.text_container, fill="white"
                )

            # รีเซ็ตสีของเงาเป็นสีดำ (ข้าม shadow images)
            for outline in self.components.outline_container:
                item_type = self.components.canvas.type(outline)
                if item_type == "text":
                    self.components.canvas.itemconfig(outline, fill="#000000")

            # รีเซ็ตสีของชื่อตัวละคร
            for name_item in self.components.canvas.find_withtag("name"):
                text = self.components.canvas.itemcget(name_item, "text")
                name_color = "#a855f7" if "?" in text else "#38bdf8"
                # เช็คว่าเป็น text item ก่อนอัพเดตสี (ข้าม shadow images)
                item_type = self.components.canvas.type(name_item)
                if item_type == "text":
                    self.components.canvas.itemconfig(name_item, fill=name_color)
                    
                    # 🔍 DEBUG: Add character name click debugging
                    print(f"🔍 DEBUG: Found name item {name_item} with text: '{text}' (type: {item_type})")
                    
                    # 🔍 DEBUG: Check if click binding exists
                    bindings = self.components.canvas.tag_bind(name_item, "<Button-1>")
                    print(f"🔍 DEBUG: Name item {name_item} click bindings: {bindings}")
                    
                    # 🔍 DEBUG: Add/update character name click binding
                    try:
                        self.components.canvas.tag_bind(name_item, "<Button-1>", 
                            lambda event, character_name=text: self._debug_character_click(event, character_name))
                        print(f"🔍 DEBUG: Added click binding for character: '{text}'")
                    except Exception as e:
                        print(f"❌ DEBUG ERROR: Failed to bind character click for '{text}': {e}")

        # ตรวจสอบว่ามีข้อความที่จะแสดงหรือไม่
        # เพิ่มการตรวจสอบว่าเพิ่งมีการ fade out สมบูรณ์หรือไม่
        if (not hasattr(self, "dialogue_text") or not self.dialogue_text) or (
            hasattr(self.state, "just_faded_out") and self.state.just_faded_out
        ):
            # ล้างสถานะ just_faded_out ถ้ามี
            if hasattr(self.state, "just_faded_out"):
                self.state.just_faded_out = False
            return

        # ตรวจสอบว่า text_container ยังมีอยู่หรือไม่
        if self.components.text_container is None:
            if hasattr(self, "dialogue_text") and self.dialogue_text:
                # ถ้า text_container ถูกลบไปแล้ว แต่ยังมี dialogue_text อยู่
                # ให้สร้าง text_container ใหม่ — ส่ง chat_type เพื่อรักษา mode
                current_type = getattr(self, 'current_chat_type', 61)
                self.update_text(self.dialogue_text, chat_type=current_type)
            return

        # Handle choice text
        if self.dialogue_text.startswith(
            "คุณจะพูดว่าอย่างไร?"
        ) or self.dialogue_text.startswith("What will you say?"):
            parts = self.dialogue_text.split("\n", 1)
            header = parts[0].strip()
            choices = parts[1].strip() if len(parts) > 1 else ""

            # Update header
            for item in self.components.canvas.find_withtag("header_outline"):
                self.components.canvas.itemconfig(item, text=header)

            # Update choices (ข้าม shadow images)
            for outline in self.components.outline_container:
                item_type = self.components.canvas.type(outline)
                if item_type == "text":
                    self.components.canvas.itemconfig(outline, text=choices)
            self.components.canvas.itemconfig(
                self.components.text_container, text=choices
            )
        else:
            # Handle normal text
            is_combined = ":" in self.dialogue_text and any(
                name in self.dialogue_text.split(":")[0]
                for name in getattr(self, "names", set())
            )

            if is_combined:
                name, message = self.dialogue_text.split(":", 1)
                display_text = message.strip()
            else:
                display_text = self.dialogue_text

            # 🔧 ENHANCED: Better Rich Text / names reapplication detection
            if (hasattr(self, 'rich_text_formatter') and
                self._needs_rich_text(display_text) and
                not self.is_already_rich_text_processed(display_text)):
                # Rich Text case: Apply formatting only if not already formatted
                logging.info(f"🎨 SHOW_FULL_TEXT: Applying Rich Text to: {display_text[:50]}...")
                self._apply_rich_text_to_completed_dialogue()
            elif self.is_already_rich_text_processed(display_text):
                # Already has Rich Text formatting applied - skip reapplication
                logging.info(f"🚫 SHOW_FULL_TEXT: Skipping Rich Text reapplication (already processed): {display_text[:50]}...")
                # Do nothing - keep existing Rich Text as is
            else:
                # Normal text case: Update all text elements (ข้าม shadow images)
                for outline in self.components.outline_container:
                    item_type = self.components.canvas.type(outline)
                    if item_type == "text":
                        self.components.canvas.itemconfig(outline, text=display_text)
                self.components.canvas.itemconfig(
                    self.components.text_container, text=display_text
                )

        # เพิ่มการตรวจสอบว่า text_container ไม่เป็น None ก่อนใช้ tag_raise
        if self.components.text_container:
            # เพิ่มบรรทัดนี้เพื่อให้ข้อความอยู่ด้านบนสุด
            self.components.canvas.tag_raise(self.components.text_container)

            # Organize layers and check overflow
            self.components.canvas.tag_lower("dialogue_outline")
            if self.components.canvas.find_withtag("name_outline"):
                self.components.canvas.tag_lower("name_outline")

            # ส่วนท้ายของฟังก์ชัน เพิ่มโค้ดเพื่อเริ่ม timer ใหม่
            self.check_text_overflow()

            # บันทึกเวลาปัจจุบันเป็นเวลาล่าสุดที่มีการอัพเดตข้อความ
            self.state.last_activity_time = time.time()

            # รีเซ็ต timer สำหรับ fade out (เฉพาะเมื่อเปิดใช้งาน)
            if self.state.fade_timer_id:
                self.root.after_cancel(self.state.fade_timer_id)
            if self.state.fadeout_enabled:
                self.state.fade_timer_id = self.root.after(10000, self.check_and_start_fade)

    def preprocess_thai_text(self, text: str) -> str:
        """
        ประมวลผลข้อความภาษาไทยก่อนแสดงผล เพื่อปรับปรุงการตัดคำให้สวยงาม
        Args:
            text: ข้อความต้นฉบับ
        Returns:
            str: ข้อความที่ปรับปรุงแล้ว
        """
        if not text:
            return ""

        # เพิ่ม caching เพื่อลดการประมวลผลซ้ำ
        if not hasattr(self, "_thai_text_cache"):
            self._thai_text_cache = {}

        # ตรวจสอบว่าเคยประมวลผลข้อความนี้แล้วหรือไม่
        cache_key = hash(text)
        if cache_key in self._thai_text_cache:
            return self._thai_text_cache[cache_key]

        ZWSP = "\u200b"  # Zero-Width Space

        # ใช้ list comprehension และ str.join แทนการใช้ replace หลายครั้ง
        # ทำให้เร็วขึ้นมาก
        result = text

        # รวมคำที่ต้องแทรก ZWSP ทั้งหมดในครั้งเดียว
        all_words = []

        # Special words (English)
        special_words = [
            "Teleport",
            "teleport",
            "Aether",
            "Eorzea",
            "Hydaelyn",
            "Garlean",
            "Limsa Lominsa",
            "Ul'dah",
            "Gridania",
            "Ishgard",
            "Doma",
            "Eikons",
            "Tataru",
            "Estinien",
            "Venat",
            "Sharlayan",
            "Endwalker",
            "Thavnair",
            "Radz-at-Han",
            "Garlemald",
            "Amaurot",
            "Azem",
        ]

        # ใช้ dict เพื่อเก็บ mapping ของคำที่ต้องแทนที่
        replacements = {}
        for word in special_words:
            replacements[word] = f"{word}{ZWSP}"

        # ทำการแทนที่ทั้งหมดในครั้งเดียวด้วย regex
        import re

        pattern = re.compile(
            r"\b(" + "|".join(re.escape(word) for word in replacements.keys()) + r")\b"
        )
        result = pattern.sub(lambda m: replacements[m.group(0)], result)

        # จัดการคำไทยที่สำคัญ - ใช้วิธีที่เร็วกว่า
        thai_words_with_zwsp = {
            "ครับ": f"ครับ{ZWSP}",
            "ค่ะ": f"ค่ะ{ZWSP}",
            "นะ": f"นะ{ZWSP}",
            "จ้ะ": f"จ้ะ{ZWSP}",
            "จ้า": f"จ้า{ZWSP}",
            "สิ": f"สิ{ZWSP}",
            "เถอะ": f"เถอะ{ZWSP}",
            "เลย": f"เลย{ZWSP}",
            "ด้วย": f"ด้วย{ZWSP}",
            "แล้ว": f"แล้ว{ZWSP}",
            "บ้าง": f"บ้าง{ZWSP}",
        }

        # ใช้ single regex pass สำหรับคำไทย
        thai_pattern = re.compile(
            r"\b("
            + "|".join(re.escape(word) for word in thai_words_with_zwsp.keys())
            + r")\b"
        )
        result = thai_pattern.sub(lambda m: thai_words_with_zwsp[m.group(0)], result)

        # ลดการใช้ regex ที่ซ้ำซ้อน
        # รวมการจัดการเครื่องหมายวรรคตอนในครั้งเดียว
        result = re.sub(r"([!?:;)\]}])(?![ \u200B])", r"\1" + ZWSP, result)
        result = re.sub(
            r"([,\.])([^\d\s\u200B\.\,\:\;\!\?])", r"\1" + ZWSP + r"\2", result
        )
        result = re.sub(r"(\d)([^\s\d\u200B\.\,])", r"\1" + ZWSP + r"\2", result)

        # ลบช่องว่างซ้ำและ ZWSP ที่ไม่จำเป็น แต่คงไว้ newlines
        result = re.sub(r"[ \t]+", " ", result)  # จับเฉพาะ space และ tab ไม่รวม newlines
        result = re.sub(ZWSP + r"{2,}", ZWSP, result)

        # เก็บผลลัพธ์ใน cache
        self._thai_text_cache[cache_key] = result.strip()

        # จำกัดขนาด cache ไม่ให้ใหญ่เกินไป
        if len(self._thai_text_cache) > 100:
            # ลบ cache เก่าออก
            self._thai_text_cache.clear()

        return result.strip()

    def clear_text_cache(self):
        """ล้าง cache ของข้อความที่ประมวลผลแล้ว"""
        if hasattr(self, "_thai_text_cache"):
            self._thai_text_cache.clear()

    def detect_thai_word_boundaries(
        self, text: str, start_index: int, look_ahead: int = 10
    ) -> int:
        """
        ตรวจสอบขอบเขตของคำในภาษาไทยเพื่อหาจุดตัดที่เหมาะสม

        Args:
            text: ข้อความที่ต้องการตรวจสอบ
            start_index: ตำแหน่งเริ่มต้นที่จะตรวจสอบ
            look_ahead: จำนวนตัวอักษรที่จะมองไปข้างหน้า

        Returns:
            int: ตำแหน่งที่เหมาะสมในการตัดข้อความ
        """
        if start_index >= len(text):
            return start_index

        # สัญลักษณ์ที่สามารถใช้เป็นจุดตัดได้
        break_chars = [
            " ",
            "\n",
            "\t",
            ".",
            ",",
            "!",
            "?",
            ":",
            ";",
            ")",
            "]",
            "}",
            '"',
            "'",
            "\u200b",  # <--- เพิ่ม Zero-Width Space เข้าไปในรายการนี้
        ]

        # ถ้าตำแหน่งปัจจุบันเป็นจุดตัดที่เหมาะสมอยู่แล้ว
        if text[start_index] in break_chars:
            return start_index + 1

        # สระนำหน้าในภาษาไทย - ต้องอยู่กับพยัญชนะเสมอ
        leading_vowels = ["เ", "แ", "โ", "ใ", "ไ"]

        # สระที่ต้องอยู่กับพยัญชนะ
        vowels = ["ะ", "า", "ิ", "ี", "ึ", "ื", "ุ", "ู", "็", "ั"]

        # วรรณยุกต์ที่ต้องอยู่กับพยัญชนะ
        tone_marks = ["่", "้", "๊", "๋"]

        # ตัวสะกดและตัวการันต์
        end_chars = [
            "ก",
            "ข",
            "ค",
            "ง",
            "จ",
            "ช",
            "ซ",
            "ฌ",
            "ญ",
            "ฎ",
            "ฏ",
            "ฐ",
            "ฑ",
            "ฒ",
            "ณ",
            "ด",
            "ต",
            "ถ",
            "ท",
            "ธ",
            "น",
            "บ",
            "ป",
            "ผ",
            "ฝ",
            "พ",
            "ฟ",
            "ภ",
            "ม",
            "ย",
            "ร",
            "ล",
            "ว",
            "ศ",
            "ษ",
            "ส",
            "ห",
            "ฬ",
            "อ",
            "ฮ",
            "์",
        ]

        # ตรวจสอบกรณีพิเศษ: สระนำหน้า
        if start_index > 0 and text[start_index - 1] in leading_vowels:
            # ไม่ควรตัดหลังสระนำหน้า
            return start_index + 1

        # ตรวจสอบกรณีพิเศษ: พยัญชนะตามด้วยสระหรือวรรณยุกต์
        if start_index < len(text) - 1:
            # ถ้าตัวถัดไปเป็นสระหรือวรรณยุกต์ ไม่ควรตัดตรงนี้
            if text[start_index + 1] in vowels + tone_marks:
                # ให้ข้ามไป 2 ตัวอักษร (พยัญชนะ+สระ/วรรณยุกต์)
                if start_index + 2 < len(text):
                    # ตรวจสอบต่อไปว่ามีวรรณยุกต์ต่อจากสระหรือไม่
                    if text[start_index + 2] in tone_marks:
                        # ข้ามทั้งหมด (พยัญชนะ+สระ+วรรณยุกต์)
                        return start_index + 3
                return start_index + 2

        # ตรวจสอบกรณีพิเศษ: ตัวสะกดหรือตัวการันต์
        if text[start_index] in end_chars:
            next_char_pos = start_index + 1
            # ตรวจดูว่ามีการันต์ตามหลังหรือไม่
            if next_char_pos < len(text) and text[next_char_pos] == "์":
                return next_char_pos + 1

        # ตรวจสอบในช่วง look_ahead
        end_index = min(start_index + look_ahead, len(text))

        # หาจุดตัดที่เหมาะสมในช่วงที่กำหนด
        for i in range(start_index, end_index):
            if text[i] in break_chars:
                return i + 1

        # กรณีเป็นตัวอักษรไทย ให้หาตำแหน่งที่จบคำ
        if re.search(r"[\u0E00-\u0E7F]", text[start_index:end_index]):
            # ค้นหาจุดที่คาดว่าจะเป็นการจบคำ (อาจเป็นช่องว่างหรือพยัญชนะตัวใหม่)
            for i in range(start_index + 1, end_index):
                # พบช่องว่าง
                if text[i] == " ":
                    return i + 1

                # ตรวจสอบว่าเป็นจุดเริ่มต้นคำใหม่หรือไม่
                if i > 0:
                    prev_char = text[i - 1]
                    curr_char = text[i]

                    # ถ้าตัวอักษรปัจจุบันเป็นพยัญชนะ และตัวก่อนหน้าไม่ใช่สระนำหน้า
                    if (
                        curr_char not in vowels + tone_marks + leading_vowels
                        and prev_char not in leading_vowels
                    ):
                        # และตัวก่อนหน้าไม่ใช่พยัญชนะที่มีสระอยู่ด้านบน
                        if prev_char not in vowels + tone_marks:
                            # น่าจะเป็นจุดเริ่มต้นคำใหม่
                            return i

        # ถ้าไม่พบจุดตัดที่เหมาะสม ให้ใช้ตำแหน่งสุดท้ายที่มองหา
        return end_index

    def is_same_thai_word(self, text: str, pos1: int, pos2: int) -> bool:
        """
        ตรวจสอบว่าตำแหน่ง 2 ตำแหน่งอยู่ในคำเดียวกันในภาษาไทยหรือไม่

        Args:
            text: ข้อความที่ต้องการตรวจสอบ
            pos1: ตำแหน่งแรก
            pos2: ตำแหน่งที่สอง

        Returns:
            bool: True ถ้าอยู่ในคำเดียวกัน, False ถ้าอยู่คนละคำ
        """
        if pos1 >= len(text) or pos2 >= len(text) or pos1 < 0 or pos2 < 0:
            return False

        # ตรวจสอบจุดแบ่งคำ (ช่องว่าง, เครื่องหมายวรรคตอน)
        break_chars = [" ", "\n", "\t", ".", ",", "!", "?", ":", ";"]

        # หาตำแหน่งต่ำสุดและสูงสุด
        min_pos = min(pos1, pos2)
        max_pos = max(pos1, pos2)

        # ตรวจสอบว่ามีจุดแบ่งคำระหว่างตำแหน่งทั้งสองหรือไม่
        for i in range(min_pos, max_pos + 1):
            if i < len(text) and text[i] in break_chars:
                return False

        # ตรวจสอบเพิ่มเติมสำหรับภาษาไทย
        if re.search(r"[\u0E00-\u0E7F]", text[min_pos : max_pos + 1]):
            # สระนำหน้าในภาษาไทย
            leading_vowels = ["เ", "แ", "โ", "ใ", "ไ"]

            # ตรวจสอบการเริ่มต้นคำใหม่
            for i in range(min_pos + 1, max_pos + 1):
                # ถ้าพบพยัญชนะที่ไม่มีสระนำหน้า อาจเป็นคำใหม่
                if re.match(r"[ก-ฮ]", text[i]) and (
                    i == 0 or text[i - 1] not in leading_vowels
                ):
                    # ตรวจสอบด้วยว่าตัวก่อนหน้าไม่ใช่ตัวสะกด (ต้องมีช่องว่างคั่น)
                    if i > 0 and not re.match(r"[ก-ฮ]", text[i - 1]):
                        return False

        # ถ้าผ่านการตรวจสอบทั้งหมด ถือว่าอยู่ในคำเดียวกัน
        return True

    def check_text_overflow(self) -> None:
        """ตรวจสอบว่ามีเนื้อหาเกินขอบเขตของ canvas หรือไม่และจัดการการแสดง scrollbar"""
        try:
            # ตรวจสอบว่ามี canvas หรือไม่
            if not hasattr(self.components, "canvas") or not self.components.canvas:
                return

            self.components.canvas.update_idletasks()

            # ตรวจสอบ bounding box ของ canvas
            bbox = self.components.canvas.bbox("all")

            # ถ้าไม่มี items หรือ bbox เป็น None ให้ซ่อน overflow arrow และออกจากฟังก์ชัน
            if not bbox:
                self.hide_overflow_arrow()
                if hasattr(self.components, "scrollbar_canvas"):
                    self.components.scrollbar_canvas.place_forget()
                return

            # ลดช่องว่างด้านล่างที่เกินมา
            # เดิมมีการเพิ่ม bottom padding 30px - ลดลงเหลือแค่ 5px
            content_height = bbox[3] + 5  # เปลี่ยนจาก 30 เป็น 5
            canvas_height = self.components.canvas.winfo_height()

            if content_height > canvas_height:
                self.show_overflow_arrow()
                # ตรวจสอบว่ามี scrollbar canvas หรือไม่
                if hasattr(self.components, "scrollbar_canvas"):
                    # แสดง scrollbar canvas
                    self.components.scrollbar_canvas.place(
                        relx=1.0, rely=0.25, relheight=0.45, anchor="ne", x=-35
                    )
                    # อัพเดต scroll region - ลดการเพิ่มพื้นที่เกิน
                    # เดิมเพิ่มอีก 10% (factor 1.1) ทำให้มีพื้นที่เหลือด้านล่างมาก
                    self.components.canvas.configure(
                        scrollregion=(
                            0,
                            0,
                            0,
                            content_height * 1.02,
                        )  # ลดจาก 1.1 เป็น 1.02
                    )
            else:
                self.hide_overflow_arrow()
                if hasattr(self.components, "scrollbar_canvas"):
                    self.components.scrollbar_canvas.place_forget()
        except Exception as e:
            logging.error(f"Error in check_text_overflow: {e}")
            self.hide_overflow_arrow()
            if hasattr(self.components, "scrollbar_canvas"):
                self.components.scrollbar_canvas.place_forget()

    def update_scrollbar_position(self) -> None:
        """ปรับตำแหน่ง scrollbar ให้เหมาะสมกับขนาดหน้าต่างปัจจุบัน"""
        try:
            if (
                not hasattr(self.components, "scrollbar")
                or not self.components.scrollbar
            ):
                return

            # ตรวจสอบว่า scrollbar กำลังถูกแสดงอยู่หรือไม่
            if not self.components.scrollbar.winfo_ismapped():
                return

            # คำนวณพื้นที่ที่มีเนื้อหาเกินขอบเขต
            bbox = self.components.canvas.bbox("all")
            if not bbox:
                return

            content_height = bbox[3]
            canvas_height = self.components.canvas.winfo_height()

            # คำนวณสัดส่วนของเนื้อหาที่มองเห็นได้
            visible_ratio = min(1.0, canvas_height / content_height)

            # ปรับความสูงของ scrollbar ตามสัดส่วนที่มองเห็นได้ แต่ไม่น้อยกว่า 0.15
            # และไม่เกิน 0.45 (ครึ่งหนึ่งของความสูงเดิม)
            new_height = max(0.15, min(0.45, visible_ratio * 0.45))

            # ปรับตำแหน่งตามขนาดความสูงใหม่
            # ถ้า relheight ลดลง ให้ปรับ rely ให้อยู่ตรงกลางมากขึ้น
            new_rely = 0.25 + ((0.45 - new_height) / 2)

            self.components.scrollbar.place(
                relx=1.0, rely=new_rely, relheight=new_height, anchor="ne", x=-35
            )

        except Exception as e:
            logging.error(f"Error updating scrollbar position: {e}")

    def adjust_font_size(self, size: int) -> None:
        """
        Adjust font size for all text elements
        Args:
            size: New font size
        """
        try:
            # Update current font size for rich text support
            self.current_font_size = size

            font = (self.settings.get("font"), size)

            # Update text container font
            if self.components.text_container:
                self.components.canvas.itemconfig(
                    self.components.text_container, font=font
                )

            # Update outlines font - ต้องอัพเดตทั้งหมด
            for tag in [
                "name_outline",
                "dialogue_outline",
                "text_outline",
                "choices_outline",
                "header_outline",
            ]:
                for outline in self.components.canvas.find_withtag(tag):
                    try:
                        if self.components.canvas.type(outline) == "text":
                            self.components.canvas.itemconfig(outline, font=font)
                    except tk.TclError:
                        pass

            self.check_text_overflow()
            logging.info(f"Font size adjusted to: {size}")

        except (ValueError, TypeError) as e:
            logging.error(f"Error adjusting font size: {e}")
            # Fallback to default size
            self.adjust_font_size(24)

    def update_font(self, font_name: str) -> None:
        """
        Update font family for all text elements
        Args:
            font_name: New font family name
        """
        # Update current font family for rich text support
        self.current_font_family = font_name

        font = (font_name, self.settings.get("font_size"))

        # Update text container font
        if self.components.text_container:
            self.components.canvas.itemconfig(self.components.text_container, font=font)

        # Update outlines font - ต้องอัพเดตทั้งหมด
        for tag in [
            "name_outline",
            "dialogue_outline",
            "text_outline",
            "choices_outline",
            "header_outline",
        ]:
            for outline in self.components.canvas.find_withtag(tag):
                try:
                    if self.components.canvas.type(outline) == "text":
                        self.components.canvas.itemconfig(outline, font=font)
                except tk.TclError:
                    pass

        # 🎨 FONT CHANGE: Re-apply Rich Text if current text has markers or names
        if (hasattr(self, 'dialogue_text') and self.dialogue_text and
            hasattr(self, 'rich_text_formatter') and
            self._needs_rich_text(self.dialogue_text)):
            logging.info(f"🎨 FONT CHANGE: Re-applying Rich Text after font change to {font_name}")
            self._apply_rich_text_to_completed_dialogue()

        self.check_text_overflow()
        logging.info(f"Font updated to: {font_name}")

    def _show_error(self, error_message: str) -> None:
        """
        Display error message in the canvas
        Args:
            error_message: Error message to display
        """
        self.components.canvas.delete("all")
        font = (self.settings.get("font"), self.settings.get("font_size"))
        self.components.text_container = self.components.canvas.create_text(
            10,
            10,
            anchor="nw",
            font=font,
            fill="red",
            width=self.components.text_frame.winfo_width() - 20,
            text=f"Error: {error_message}",
        )
        self.check_text_overflow()

    def update_transparency(self, alpha: float) -> None:
        """
        Update window transparency
        Args:
            alpha: Transparency value (0.0 to 1.0)
        """
        self.root.attributes("-alpha", alpha)

    def close_window(self) -> None:
        """Close the translation window without stopping translation"""
        # *** TUI INDEPENDENCE: ไม่หยุดการแปลเมื่อปิด TUI - การแปลทำงานอิสระ ***
        # TUI เป็นแค่หน้าต่างแสดงผล ไม่ควรมีผลต่อการทำงานของระบบแปล
        pass  # เอาการเรียก stop_translation() ออก

        if self.root.winfo_exists():
            if self.root.state() != "withdrawn":
                self.root.withdraw()
                logging.info("Translated UI closed by user")

                # ✅ เรียก callback เพื่อแจ้ง MBB.py ให้ปิด highlight ปุ่ม TUI
                if self.on_close_callback:
                    try:
                        self.on_close_callback()
                        logging.info(
                            "Called on_close_callback to notify main UI about TUI closure."
                        )
                    except Exception as e:
                        logging.error(f"Error executing on_close_callback: {e}")
            else:
                logging.info("Translated UI already hidden")
        else:
            logging.warning("Translated UI window does not exist")

        # รีเซ็ต flag
        if hasattr(self, '_closing_from_f9'):
            delattr(self, '_closing_from_f9')

    def toggle_lock(self, event: Optional[tk.Event] = None) -> None:
        """Toggle UI lock state and apply background transparency correctly."""
        # เคลียร์ canvas ก่อนเปลี่ยนสถานะ ป้องกันเงาค้าง
        if hasattr(self.components, "canvas") and self.components.canvas:
            self.components.canvas.delete("all")
            self.components.outline_container = []
            self.components.text_container = None

        # ดึงค่าสีและ alpha ปัจจุบันจาก settings
        current_bg_color = self.settings.get("bg_color", appearance_manager.bg_color)
        current_bg_alpha = self.get_user_transparency()  # ใช้ centralized method

        # ตรวจสอบว่าตัวแปร lock_mode ถูกกำหนดค่าแล้วหรือไม่
        if not hasattr(self, "lock_mode"):
            self.lock_mode = 0

        # ตรรกะการหมุนเวียน 3 สถานะ
        if not self.state.is_locked:  # ไม่ล็อก -> ล็อกพร้อมซ่อนพื้นหลัง (สถานะ 1)
            self.state.is_locked = True
            self.lock_mode = 1
            self.components.buttons["lock"].config(image=self.bg_lock_trans_image)
            logging.info(f"Changing to lock mode 1 (hidden background)")

            # ใช้เมธอดนี้ในการตั้งค่า - ค่า alpha ไม่สำคัญในโหมดนี้เพราะใช้ transparentcolor
            self._apply_background_color_and_alpha(current_bg_color, current_bg_alpha)

        elif (
            self.state.is_locked and self.lock_mode == 1
        ):  # ซ่อนพื้นหลัง -> ล็อกพร้อมแสดงพื้นหลัง (สถานะ 2)
            self.state.is_locked = True
            self.lock_mode = 2
            self.components.buttons["lock"].config(image=self.bg_lock_image)
            logging.info(f"Changing to lock mode 2 (visible background, locked)")

            # ใช้เมธอดในการตั้งค่าพื้นหลังให้แสดงตามปกติ
            self._apply_background_color_and_alpha(current_bg_color, current_bg_alpha)

        elif (
            self.state.is_locked and self.lock_mode == 2
        ):  # แสดงพื้นหลัง -> ปลดล็อก (สถานะ 0)
            self.state.is_locked = False
            self.lock_mode = 0
            self.components.buttons["lock"].config(image=self.unlock_image)
            logging.info(f"Changing to lock mode 0 (unlocked)")

            # ใช้เมธอดในการตั้งค่าพื้นหลังให้แสดงตามปกติ
            self._apply_background_color_and_alpha(current_bg_color, current_bg_alpha)

        # วาดข้อความใหม่เสมอหลังเปลี่ยนโหมด lock เพื่อให้แน่ใจว่าข้อความแสดงถูกต้อง
        if hasattr(self, "state") and self.state.full_text:
            # ใช้ after เพื่อให้ UI มีเวลาปรับปรุงพื้นหลังก่อนวาดข้อความ
            # ป้องกันการเรียก old text ที่อาจทำให้เกิด error และข้อความสีแดง
            current_text = self.state.full_text
            current_type = getattr(self, 'current_chat_type', 61)

            def redraw_text():
                try:
                    # ตรวจสอบว่าข้อความยังใหม่อยู่ก่อนวาด
                    if hasattr(self, "state") and self.state.full_text == current_text:
                        self.update_text(current_text, chat_type=current_type)
                except Exception as e:
                    logging.warning(
                        f"Failed to redraw text after lock mode change: {e}"
                    )
                    # ไม่แสดง error message แดง เพียงแค่ clear canvas
                    if hasattr(self.components, "canvas"):
                        self.components.canvas.delete("all")

            self.root.after(50, redraw_text)

    def show_color_picker(self):
        """แสดง Color Picker แบบใหม่ที่มีการปรับปรุงแล้ว"""
        current_bg = self.settings.get("bg_color", appearance_manager.bg_color)
        current_alpha = self.get_user_transparency()  # ใช้ centralized method
        current_lock_mode = getattr(self, "lock_mode", 0)

        # สร้าง Color Picker ใหม่
        picker = ImprovedColorAlphaPickerWindow(
            self.root,
            current_bg,
            current_alpha,
            self.settings,
            self._apply_background_color_and_alpha,
            current_lock_mode,
            self  # Pass main_ui reference for per-mode saving
        )

        # ปรับตำแหน่งให้แสดงเหนือปุ่มสี
        picker.position_relative_to_button(self.components.buttons["color"])

    def change_bg_color(self):
        """Deprecated: ใช้ show_color_picker() แทน"""
        self.show_color_picker()

    def _apply_background_color_and_alpha(self, hex_color, alpha):
        """Applies the background color and alpha to the UI, handling transparency."""
        try:
            logging.info(f"Applying background: Color={hex_color}, Alpha={alpha}")

            # กำหนดว่าเป็นโหมดไหน
            lock_mode = getattr(self, "lock_mode", 0)

            # ตั้งค่าสีพื้นหลังให้กับทุก widget ก่อน (ทุกโหมด)
            widgets_to_update = [
                self.root,
                self.components.main_frame,
                self.components.text_frame,
                self.components.canvas,
                self.components.control_area,
                getattr(self.components, "arrow_canvas", None),
                getattr(self, "resize_handle", None),
            ]
            for widget in widgets_to_update:
                if widget and widget.winfo_exists():
                    try:
                        widget.configure(bg=hex_color)
                        if isinstance(widget, (tk.Frame, tk.Canvas)):
                            widget.configure(bd=0, highlightthickness=0)
                    except tk.TclError as e:
                        logging.debug(f"Error setting bg color for widget: {e}")

            # อัปเดตสีปุ่มด้วย
            if hasattr(self.components, "buttons"):
                for button in self.components.buttons.values():
                    if button and button.winfo_exists():
                        try:
                            button.configure(bg=hex_color, activebackground=hex_color)
                        except tk.TclError as e:
                            logging.debug(f"Error setting button color: {e}")

            # สำคัญ: ยกเลิกการตั้งค่า transparentcolor ก่อนเสมอเพื่อป้องกันปัญหา
            try:
                self.root.attributes("-transparentcolor", "")
            except tk.TclError:
                pass

            # 1. กรณีโหมด lock 1 (ซ่อนพื้นหลัง) - ใช้ transparentcolor
            if lock_mode == 1:
                try:
                    # ต้องตั้งค่า alpha เป็น 1.0 ก่อนใช้ transparentcolor เสมอ
                    self.root.attributes("-alpha", 1.0)
                    # รอให้ UI อัพเดตก่อนตั้งค่า transparentcolor
                    self.root.update_idletasks()
                    # สั่งให้สีพื้นหลังเป็นโปร่งใส
                    self.root.attributes("-transparentcolor", hex_color)
                    logging.info(f"Lock Mode 1: Set transparentcolor to {hex_color}")
                except tk.TclError as e:
                    logging.error(f"Failed to set transparentcolor in Lock Mode 1: {e}")

            # 2. กรณีโหมด 0 หรือ 2 และต้องการความโปร่งใส
            elif lock_mode != 1 and alpha < 1.0:
                try:
                    # บันทึก alpha ไว้ในตัวแปร
                    self.current_bg_alpha = alpha

                    # ตั้งค่าความโปร่งใสในระดับหน้าต่าง
                    self.root.attributes("-alpha", alpha)
                    logging.info(f"Set window alpha to {alpha}")

                    # ปรับปรุงการแสดงข้อความให้ชัดเจน
                    if (
                        hasattr(self.components, "text_container")
                        and self.components.text_container
                    ):
                        self.components.canvas.itemconfigure(
                            self.components.text_container, fill="white"
                        )
                        # ทำให้ชื่อตัวละครชัดเจน
                        for name_item in self.components.canvas.find_withtag("name"):
                            text = self.components.canvas.itemcget(name_item, "text")
                            name_color = "#a855f7" if "?" in text else "#38bdf8"
                            self.components.canvas.itemconfig(
                                name_item, fill=name_color
                            )
                        # ทำให้เส้นขอบข้อความเข้มขึ้น (skip image items)
                        for outline in self.components.outline_container:
                            try:
                                if self.components.canvas.type(outline) == "text":
                                    self.components.canvas.itemconfig(outline, width=2)
                            except tk.TclError:
                                pass
                except tk.TclError as e:
                    logging.error(f"Failed to set alpha in normal mode: {e}")

            # 3. กรณีโหมด 0 หรือ 2 และไม่ต้องการความโปร่งใส (alpha = 1.0)
            else:
                try:
                    # ยกเลิกความโปร่งใส
                    self.root.attributes("-alpha", 1.0)
                except tk.TclError as e:
                    logging.error(f"Failed to reset alpha: {e}")

            # ★ หมายเหตุ: ไม่ต้องอัพเดตสีปุ่ม color picker เพราะใช้ไอคอน TUI_BG.png แล้ว

            # วาดข้อความใหม่เพื่อให้แน่ใจว่าข้อความแสดงถูกต้อง (ใช้ delay มากขึ้น)
            if hasattr(self, "state") and self.state.full_text:
                # ป้องกันการเรียก old text ที่อาจทำให้เกิด error และข้อความสีแดง
                current_text = self.state.full_text

                def redraw_after_bg_change():
                    try:
                        # ตรวจสอบว่าข้อความยังใหม่อยู่ก่อนวาด
                        if (
                            hasattr(self, "state")
                            and self.state.full_text == current_text
                        ):
                            # 🔧 FIX: ส่ง current_chat_type เพื่อรักษา mode ปัจจุบัน
                            # ป้องกันปัญหา UI หดกลับเป็น dialogue mode เมื่อปรับ alpha ใน cutscene mode
                            current_type = getattr(self, 'current_chat_type', 61)
                            self.update_text(current_text, chat_type=current_type)
                    except Exception as e:
                        logging.warning(
                            f"Failed to redraw text after background change: {e}"
                        )
                        # ไม่แสดง error message แดง เพียงแค่ clear canvas
                        if hasattr(self.components, "canvas"):
                            self.components.canvas.delete("all")

                self.root.after(50, redraw_after_bg_change)

        except Exception as e:
            logging.error(f"Error applying background color/alpha: {e}")
            import traceback

            traceback.print_exc()

        # 🎨 เพิ่ม: ใส่ขอบโค้งมนหลังจากอัปเดตสีพื้นหลัง
        self.root.after(100, self.apply_rounded_corners_to_ui)

    def setup_window_resizing(self) -> None:
        """Initialize window resize functionality"""
        # ดึงสีพื้นหลังจาก settings (*** ไม่ต้องตั้ง bg ให้ handle ที่นี่ ***)
        # saved_bg_color = self.settings.get("bg_color", appearance_manager.bg_color)

        # สร้าง resize handle ด้วย Canvas
        resize_canvas_size = 20
        self.resize_handle = tk.Canvas(
            self.components.main_frame,  # ควรอยู่บน main_frame ไม่ใช่ root โดยตรง
            width=resize_canvas_size,
            height=resize_canvas_size,
            # bg=saved_bg_color, # <--- ลบออก
            highlightthickness=0,
            bd=0,
            cursor="sizing",
        )

        # โหลดไฟล์ resize.png (เหมือนเดิม)
        try:
            self.resize_icon_img = AssetManager.load_icon("resize.png", (20, 20))
            self.resize_icon = self.resize_handle.create_image(
                resize_canvas_size // 2,
                resize_canvas_size // 2,
                image=self.resize_icon_img,
                anchor="center",
            )
        except Exception as e:
            logging.error(f"Error loading resize icon: {e}")
            self.resize_icon = self.resize_handle.create_text(
                resize_canvas_size // 2,
                resize_canvas_size // 2,
                text="⇲",
                font=("Arial", 12, "bold"),
                fill="white",  # ใช้สีขาวเพื่อให้เห็นบนพื้นหลังสีต่างๆ
                anchor="center",
            )

        self.resize_handle.place(relx=1, rely=1, anchor="se")

        # Bindings อยู่ใน setup_bindings() แล้ว — ไม่ bind ซ้ำที่นี่

        # Initialize resize state
        self.is_resizing = False
        self.last_resize_time = 0
        self.resize_throttle = 0.016
        self.resize_preview_rect = None

    def start_resize(self, event: tk.Event) -> None:
        """
        Initialize window resize operation
        Args:
            event: Mouse event containing initial coordinates
        """
        self.is_resizing = True
        self.resize_x = event.x_root
        self.resize_y = event.y_root
        self.resize_w = self.root.winfo_width()
        self.resize_h = self.root.winfo_height()

        # บันทึกตำแหน่ง window เพื่อ lock ไว้ระหว่าง resize
        self.resize_anchor_x = self.root.winfo_x()
        self.resize_anchor_y = self.root.winfo_y()

        # บันทึกขนาดหน้าต่างก่อนเริ่มปรับขนาด เพื่อใช้เป็นจุดอ้างอิง
        self.original_geometry = self.root.geometry()

        # หากมีพรีวิวอยู่แล้ว ให้ลบออก
        if hasattr(self, "resize_preview") and self.resize_preview is not None:
            self.root.after_cancel(self.resize_preview)
            self.resize_preview = None

        # เก็บสถานะสิ่งที่กำลังแสดงอยู่เพื่อกู้คืนหลังปรับขนาดเสร็จ
        self.pre_resize_text = None
        if (
            hasattr(self.components, "text_container")
            and self.components.text_container
        ):
            self.pre_resize_text = self.components.canvas.itemcget(
                self.components.text_container, "text"
            )

        # Professional UI: Silent resize initialization
        # print("\rStarting window resize...", end="", flush=True)  # Can be enabled for debugging

    def on_resize(self, event: tk.Event) -> None:
        """
        Handle window resizing with throttling - ปรับปรุงประสิทธิภาพ
        Args:
            event: Mouse event containing current coordinates
        """
        if not self.is_resizing:
            return

        try:
            # คำนวณขนาดใหม่
            dx = event.x_root - self.resize_x
            dy = event.y_root - self.resize_y

            # ค่าความสูงต่ำสุดลดลงจาก 200px เป็น 120px
            # ค่าความกว้างต่ำสุดยังคงเป็น 300px
            new_width = max(300, self.resize_w + dx)
            new_height = max(120, self.resize_h + dy)  # ปรับลดค่าความสูงต่ำสุด

            # กำหนดขนาดใหม่ พร้อม lock ตำแหน่ง
            self.root.geometry(f"{int(new_width)}x{int(new_height)}+{self.resize_anchor_x}+{self.resize_anchor_y}")

            current_time = time.time()

            # *** PROFESSIONAL UI: Remove intrusive resize messages ***
            # Silent resize - no overlay text that interferes with content
            # Only log to console for debugging if needed
            if (
                current_time - self.last_resize_time > 0.1
            ):  # Update throttling every 100ms
                # Optional: Minimal console logging (can be disabled in production)
                # print(f"\rResize: {int(new_width)}x{int(new_height)}px", end="", flush=True)
                self.last_resize_time = current_time

                # ไม่อัพเดตขอบโค้งมนระหว่าง drag — จะใส่กลับตอน stop_resize
                # (SetWindowRgn + update_idletasks หนักเกินไปสำหรับทุก frame)

                # *** REMOVED: Intrusive resize message overlay ***
                # Professional UI should not show "กำลังปรับขนาด" text
                # that interferes with existing translation content

        except Exception as e:
            logging.error(f"Error during resize: {e}")
            # Professional UI: Log errors silently
            # print(f"\rResize error: {e}")  # Can be enabled for debugging

    def stop_resize(self, event: Optional[tk.Event] = None) -> None:
        """
        End window resize operation and save final settings
        Args:
            event: Optional mouse event
        """
        if not self.is_resizing:
            return

        try:
            # บันทึกขนาดสุดท้ายลงใน settings
            final_w = self.root.winfo_width()
            final_h = self.root.winfo_height()

            self.settings.set("width", final_w)
            self.settings.set("height", final_h)
            self.settings.save_settings()

            # ตั้งค่า flag เพื่อบอกว่าหยุดการปรับขนาดแล้ว
            self.is_resizing = False

            # *** REMOVED: Reset resize message (no longer needed) ***
            # self.resize_message_shown = False  # Not needed anymore

            # ตั้งเวลาสำหรับการอัพเดตเนื้อหาหลังจากขนาดหน้าต่างคงที่แล้ว
            def update_content_after_resize():
                try:
                    # อัพเดต canvas กับ scroll region
                    self.on_canvas_configure({"width": final_w - 40})

                    # Re-render ข้อความตามขนาดใหม่
                    if hasattr(self, 'dialogue_text') and self.dialogue_text:
                        current_type = getattr(self, 'current_chat_type', 61)
                        self.update_text(self.dialogue_text, chat_type=current_type)

                    # ตรวจสอบข้อความเกินขอบเขต
                    try:
                        self.check_text_overflow()
                        self.update_scrollbar_position()
                    except Exception as e:
                        logging.error(f"Error checking text overflow after resize: {e}")

                except Exception as e:
                    logging.error(f"Error updating content after resize: {e}")

            # รอ 100ms ก่อนอัพเดตเนื้อหา เพื่อให้การแสดงผลมีความนิ่ง
            self.root.after(100, update_content_after_resize)
            # 🎨 เพิ่ม: อัปเดตขอบโค้งมนหลังจากปรับขนาดเสร็จ
            self.root.after(150, self.apply_rounded_corners_to_ui)

        except Exception as e:
            logging.error(f"Error in stop_resize: {e}")
            # Professional UI: Log errors silently
            # print(f"\rStop resize error: {e}")  # Can be enabled for debugging

        self.is_resizing = False

    def force_check_overflow(self) -> None:
        """Force check text overflow and update UI accordingly"""
        try:
            self.check_text_overflow()
        except Exception as e:
            logging.error(f"Error forcing check overflow: {e}")

    def on_canvas_configure_enhanced(
        self, event: Union[tk.Event, Dict[str, int]]
    ) -> None:
        """Enhanced canvas configure with modern smoothing techniques"""
        try:
            # Use throttler to prevent excessive resize calls
            self.resize_throttler.throttle_resize(self._perform_canvas_resize, event)

        except Exception as e:
            logging.error(f"Error in enhanced canvas configure: {e}")
            # Fallback to original method
            self._perform_canvas_resize(event)

    def _perform_canvas_resize(self, event: Union[tk.Event, Dict[str, int]]) -> None:
        """Actual resize operation with optimizations"""
        try:
            # Calculate available width with improved method
            if isinstance(event, tk.Event):
                available_width = event.width - 20
            else:
                available_width = event.get("width", 300) - 20

            safe_width = max(
                100, int(available_width * 0.95)
            )  # Minimum width protection

            # Cache width to avoid unnecessary updates
            if (
                hasattr(self, "_last_safe_width")
                and self._last_safe_width == safe_width
            ):
                return  # No change needed

            self._last_safe_width = safe_width

            # Update text container width efficiently
            if (
                hasattr(self.components, "text_container")
                and self.components.text_container
                and self.components.canvas.winfo_exists()
            ):

                # Update text container width
                self.components.canvas.itemconfig(
                    self.components.text_container, width=safe_width
                )

                # Update outline widths efficiently
                if (
                    hasattr(self.components, "outline_container")
                    and self.components.outline_container
                ):
                    for outline in self.components.outline_container:
                        if outline:
                            try:
                                if self.components.canvas.type(outline) == "text":
                                    self.components.canvas.itemconfig(outline, width=safe_width)
                            except tk.TclError:
                                pass

                # Optimized scroll region update
                self.root.after_idle(self._update_scroll_region_optimized)

            # Check text overflow with error protection
            try:
                self.check_text_overflow()
            except Exception as e:
                logging.error(f"Error checking text overflow from configure: {e}")

        except Exception as e:
            logging.error(f"Error in perform canvas resize: {e}")

    def _update_scroll_region_optimized(self) -> None:
        """Optimized scroll region update"""
        try:
            if not self.components.canvas or not self.components.canvas.winfo_exists():
                return

            bbox = self.components.canvas.bbox("all")
            if bbox:
                # Reduced padding for smoother scrolling
                height_with_padding = bbox[3] * 1.02  # Only 2% padding
                self.components.canvas.configure(
                    scrollregion=(0, 0, bbox[2], height_with_padding)
                )

        except Exception as e:
            logging.error(f"Error updating scroll region: {e}")

    def on_canvas_configure(self, event: Union[tk.Event, Dict[str, int]]) -> None:
        """Legacy canvas configure method (fallback)"""
        try:
            # คำนวณความกว้างที่เหมาะสม - ใช้ 95% ของพื้นที่
            available_width = (
                event.width - 20 if isinstance(event, tk.Event) else event["width"]
            )
            safe_width = int(available_width * 0.95)

            if (
                hasattr(self.components, "text_container")
                and self.components.text_container
            ):
                # อัพเดตความกว้างของข้อความ
                self.components.canvas.itemconfig(
                    self.components.text_container, width=safe_width
                )

                # อัพเดตความกว้างของ outline
                if (
                    hasattr(self.components, "outline_container")
                    and self.components.outline_container
                ):
                    for outline in self.components.outline_container:
                        if outline:
                            try:
                                if self.components.canvas.type(outline) == "text":
                                    self.components.canvas.itemconfig(outline, width=safe_width)
                            except tk.TclError:
                                pass

                # อัพเดต scroll region ให้มีพื้นที่เหลือน้อยลง
                self.components.canvas.update_idletasks()
                bbox = self.components.canvas.bbox("all")
                if bbox:
                    # ลดพื้นที่เพิ่มเติมจาก 10% เป็น 2%
                    height_with_padding = bbox[3] * 1.02  # ใช้แค่ 2%
                    self.components.canvas.configure(
                        scrollregion=(0, 0, bbox[2], height_with_padding)
                    )

            # ใช้ try-except เพื่อป้องกันข้อผิดพลาดจาก check_text_overflow
            try:
                self.check_text_overflow()
            except Exception as e:
                logging.error(f"Error checking text overflow from configure: {e}")

        except Exception as e:
            logging.error(f"Canvas configure error: {e}")

    def on_mousewheel(self, event: tk.Event) -> None:
        """
        จัดการการเลื่อนด้วยล้อเมาส์
        Args:
            event: Mouse wheel event
        """
        # ปรับการเลื่อนให้เร็วขึ้น โดยเพิ่มจำนวนหน่วยที่เลื่อนต่อการหมุนล้อเมาส์
        scroll_speed = 2  # เพิ่มความเร็วเป็น 2 เท่า (เดิมเป็น 1)
        self.components.canvas.yview_scroll(
            -1 * (event.delta // 120) * scroll_speed, "units"
        )

        # ตรวจสอบว่าเลื่อนสุดหรือยัง
        # โดยดึงตำแหน่งปัจจุบันของ scrollbar
        scroll_pos = self.components.canvas.yview()

        # เพิ่มการตรวจสอบว่า bbox เป็น None หรือไม่ก่อนเข้าถึง
        bbox = self.components.canvas.bbox("all")

        # ถ้าเลื่อนลงสุดแล้ว (scroll_pos[1] >= 0.98) ให้ซ่อนลูกศรทันที
        if scroll_pos[1] >= 0.98:
            self.hide_overflow_arrow()
        # ถ้ายังไม่ถึงล่างสุดและมีเนื้อหาเกิน แสดงลูกศร
        elif bbox is not None and bbox[3] > self.components.canvas.winfo_height():
            self.show_overflow_arrow()

    def on_click(self, event: tk.Event) -> None:
        """
        Handle mouse click event
        Args:
            event: Mouse click event
        """
        if self._is_click_on_resize_handle(event):
            return
        if self.state.is_locked and not self._is_click_on_button(event):
            if self.lock_mode == 2:  # Lock with visible bg
                self.show_full_text()
            return
        self._start_move(event)
        if not self.state.is_locked:
            self.show_full_text()

    def _is_click_on_button(self, event: tk.Event) -> bool:
        """
        Check if click was on a button
        Args:
            event: Mouse click event
        Returns:
            bool: True if click was on a button
        """
        for button in self.components.buttons.values():
            if button.winfo_containing(event.x_root, event.y_root) == button:
                return True
        return False

    def _is_click_on_scrollbar(self, event: tk.Event) -> bool:
        """
        Check if click was on scrollbar
        Args:
            event: Mouse click event
        Returns:
            bool: True if click was on scrollbar
        """
        if not hasattr(self.components, 'scrollbar') or not self.components.scrollbar:
            return False
        try:
            widget = self.components.scrollbar.winfo_containing(event.x_root, event.y_root)
            return widget == self.components.scrollbar
        except Exception:
            return False

    def _is_click_on_resize_handle(self, event: tk.Event) -> bool:
        """Check if click was on resize handle"""
        if not hasattr(self, 'resize_handle') or not self.resize_handle:
            return False
        try:
            widget = self.resize_handle.winfo_containing(event.x_root, event.y_root)
            return widget == self.resize_handle
        except Exception:
            return False

    def _start_move(self, event: tk.Event) -> None:
        """
        Initialize window movement
        Args:
            event: Mouse click event
        """
        if not self.state.is_locked:
            self.x = event.x
            self.y = event.y

    def on_drag(self, event: tk.Event) -> None:
        """
        Handle window dragging
        Args:
            event: Mouse drag event
        """
        if not self.state.is_locked and not getattr(self, 'is_resizing', False):
            self._do_move(event)

    def stop_move(self, event: Optional[tk.Event] = None) -> None:
        """
        Stop window movement
        Args:
            event: Optional mouse release event
        """
        self.x = None
        self.y = None

    def _do_move(self, event: tk.Event) -> None:
        """
        Perform window movement
        Args:
            event: Mouse drag event
        """
        if not self.state.is_locked and self.x is not None and self.y is not None:
            deltax = event.x - self.x
            deltay = event.y - self.y
            x = self.root.winfo_x() + deltax
            y = self.root.winfo_y() + deltay
            self.root.geometry(f"+{x}+{y}")

    def on_hover_enter(self, event: Optional[tk.Event] = None) -> None:
        """
        Handle mouse hover enter event
        Args:
            event: Optional mouse enter event
        """
        pass  # All hover handling removed as per UI simplification

    @staticmethod
    def _calculate_content_dimensions(
        text: str, font: tuple, max_width: int
    ) -> Tuple[int, int]:
        """
        Calculate required dimensions for text content
        Args:
            text: Text content
            font: Font configuration tuple
            max_width: Maximum available width
        Returns:
            Tuple[int, int]: Calculated width and height
        """
        temp_label = tk.Label(text=text, font=font)
        temp_label.update_idletasks()

        raw_width = temp_label.winfo_reqwidth()
        raw_height = temp_label.winfo_reqheight()

        if raw_width > max_width:
            # Calculate wrapped height
            lines = math.ceil(raw_width / max_width)
            height = raw_height * lines
            width = max_width
        else:
            width = raw_width
            height = raw_height

        temp_label.destroy()
        return width, height

    def cleanup(self) -> None:
        """Cleanup resources before closing"""
        try:
            # Cancel any pending typewriter effects
            if hasattr(self, "type_writer_timer") and self.type_writer_timer:
                self.root.after_cancel(self.type_writer_timer)
                self.type_writer_timer = None

            # ยกเลิก fade timer ด้วย
            if hasattr(self, "state") and self.state.fade_timer_id:
                self.root.after_cancel(self.state.fade_timer_id)
                self.state.fade_timer_id = None

            # ยกเลิกการเป็น observer
            if hasattr(self, "font_settings") and self.font_settings:
                self.font_settings.remove_observer(self)

            # Clear canvas items
            if (
                hasattr(self, "components")
                and hasattr(self.components, "canvas")
                and self.components.canvas
            ):
                self.components.canvas.delete("all")

            # Reset state
            if hasattr(self, "state"):
                self.state = UIState()

            logging.info("TranslatedUI cleanup completed")

        except Exception as e:
            logging.error(f"Error during cleanup: {e}")

    def _setup_character_name_binding(self):
        """Setup binding for character name clicks"""
        self.components.canvas.tag_bind("name", "<Button-1>", self._on_name_click)
        logging.info("Character name click binding setup")

    def _on_name_click(self, event):
        """
        จัดการเมื่อมีการคลิกที่ชื่อตัวละคร
        - สร้าง click effect
        - ส่งต่อไปยัง character handler

        Args:
            event: tkinter event object ที่มีข้อมูลตำแหน่งที่คลิก
        """
        try:
            self.logging_manager.log_info("🔍 [NAME CLICK] Character name click detected!")

            # ค้นหา item ที่ถูกคลิก
            clicked_item = self.components.canvas.find_closest(
                self.components.canvas.canvasx(event.x),
                self.components.canvas.canvasy(event.y),
            )[0]

            # เก็บสีเดิมไว้
            original_color = self.components.canvas.itemcget(clicked_item, "fill")
            original_text = self.components.canvas.itemcget(clicked_item, "text")

            self.logging_manager.log_info(f"🔍 [NAME CLICK] Clicked text: '{original_text}'")

            # สร้าง click effect
            def flash_effect():
                # เปลี่ยนเป็นสีแดงสว่าง (เช็คว่าเป็น text item ก่อน)
                item_type = self.components.canvas.type(clicked_item)
                if item_type == "text":
                    self.components.canvas.itemconfig(clicked_item, fill="#FF4444")

                # คืนค่าสีเดิมหลังจาก delay
                def restore_color():
                    item_type = self.components.canvas.type(clicked_item)
                    if item_type == "text":
                        self.components.canvas.itemconfig(
                            clicked_item, fill=original_color
                        )

                self.root.after(150, restore_color)

            # ทำ flash effect และส่งต่อไปยัง handler
            flash_effect()
            self.root.after(50, lambda: self._handle_character_click(original_text))

        except Exception as e:
            self.logging_manager.log_error(f"Error in name click effect: {e}")

    def _handle_character_click(self, character_name):
        """
        จัดการเมื่อมีการคลิกที่ชื่อตัวละคร
        - เปิด NPC Manager
        - ค้นหาและจัดการตัวละครตามสถานะในฐานข้อมูล
        """
        try:
            self.logging_manager.log_info(f"🔍 [CHARACTER CLICK] Handling click for: '{character_name}'")

            if not self.main_app:
                self.logging_manager.log_warning(
                    "Main application reference not provided to Translated UI"
                )
                return

            self.root.update_idletasks()

            # เรียกใช้ callback เพื่อเปิด NPC Manager
            if self.toggle_npc_manager_callback and callable(
                self.toggle_npc_manager_callback
            ):
                self.logging_manager.log_info("🔍 [CHARACTER CLICK] Calling toggle_npc_manager_callback")

                # เรียกฟังก์ชันจาก MBB.py เพื่อเปิด NPC Manager
                self.toggle_npc_manager_callback()

                # หลังจากเปิดแล้ว ให้ส่งชื่อตัวละครไปให้ NPC Manager จัดการ
                if (
                    hasattr(self.main_app, "npc_manager")
                    and self.main_app.npc_manager
                ):
                    self.logging_manager.log_info("🔍 [CHARACTER CLICK] NPC Manager found, scheduling search")
                    # ใช้ after เพื่อให้แน่ใจว่าหน้าต่าง NPC Manager สร้างเสร็จแล้ว
                    self.root.after(
                        200, lambda: self._call_npc_manager_search(character_name)
                    )
                else:
                    self.logging_manager.log_error("🔍 [CHARACTER CLICK] NPC Manager not found!")
                    messagebox.showwarning(
                        "Warning",
                        "Could not communicate with NPC Manager after opening.",
                    )
            else:
                self.logging_manager.log_error("🔍 [CHARACTER CLICK] toggle_npc_manager_callback not available!")
                messagebox.showerror("Error", "NPC Manager function is not available.")

        except Exception as e:
            error_msg = f"Error handling character click: {e}"
            self.logging_manager.log_error(error_msg)
            try:
                messagebox.showerror("Error", error_msg)
            except Exception:
                pass

    def _call_npc_manager_search(self, character_name):
        """
        เรียกใช้ฟังก์ชันค้นหาตัวละครที่ถูกต้องใน NPC Manager

        Args:
            character_name (str): ชื่อตัวละครที่จะค้นหา
        """
        try:
            npc_manager = self.main_app.npc_manager

            # ลบช่องว่างส่วนเกินและอักขระพิเศษ
            clean_name = character_name.strip()

            # ตรวจสอบว่าเป็นชื่อที่ verified หรือไม่ (ไม่มีเครื่องหมาย ?)
            is_verified = "?" not in clean_name

            # ลบเครื่องหมาย ? ออกถ้ามี
            clean_name = clean_name.replace("?", "").strip()

            self.logging_manager.log_info(
                f"Calling NPC Manager to handle character: '{clean_name}' (verified: {is_verified})"
            )

            # เรียกใช้ find_and_display_character แทน search_character_and_focus
            # เพราะ find_and_display_character ถูกแก้ไขให้ทำงานตามที่ต้องการแล้ว
            if hasattr(npc_manager, "find_and_display_character"):
                npc_manager.find_and_display_character(clean_name, is_verified)
            else:
                # Fallback ถ้าไม่มีฟังก์ชันที่แก้ไขใหม่
                self.logging_manager.log_warning(
                    "find_and_display_character not found, falling back to default behavior"
                )

        except Exception as e:
            self.logging_manager.log_error(f"Error calling NPC Manager search: {e}")
            import traceback

            self.logging_manager.log_error(traceback.format_exc())

    def _setup_character_name_binding(self):
        """
        ตั้งค่า event binding สำหรับการโต้ตอบกับชื่อตัวละคร
        - รองรับ hover effect ด้วย mouse enter/leave
        - รองรับการคลิกที่ชื่อ
        """
        # เพิ่ม binding สำหรับ hover effect
        self.components.canvas.tag_bind("name", "<Enter>", self._on_name_hover_enter)
        self.components.canvas.tag_bind("name", "<Leave>", self._on_name_hover_leave)
        self.components.canvas.tag_bind("name", "<Button-1>", self._on_name_click)
        logging.info("Character name interaction bindings setup")

    def _on_name_hover_enter(self, event):
        """
        จัดการเมื่อ mouse hover เข้าบริเวณชื่อตัวละคร
        Parameters:
            event: Event object ที่มีข้อมูลพิกัดของเมาส์
        """
        try:
            # 1. เปลี่ยน cursor เป็นรูปมือ
            self.components.canvas.configure(cursor="hand2")

            # 2. ค้นหา item ที่ถูก hover
            current_x = self.components.canvas.canvasx(event.x)
            current_y = self.components.canvas.canvasy(event.y)
            items = self.components.canvas.find_overlapping(
                current_x - 5, current_y - 5, current_x + 5, current_y + 5
            )

            # 3. ค้นหา item ที่มี tag 'name'
            name_item = None
            for item in items:
                if "name" in self.components.canvas.gettags(item):
                    name_item = item
                    break

            if name_item:
                # 4. เก็บสีปัจจุบันไว้ใน tag
                current_color = self.components.canvas.itemcget(name_item, "fill")
                tag_name = f"original_color:{current_color}"

                # ลบ tag เก่าออกก่อน (ถ้ามี)
                for tag in self.components.canvas.gettags(name_item):
                    if tag.startswith("original_color:"):
                        self.components.canvas.dtag(name_item, tag)

                # เพิ่ม tag ใหม่
                self.components.canvas.addtag_withtag(tag_name, name_item)

                # 5. เปลี่ยนเป็นสีขาว (เช็คว่าเป็น text item ก่อน)
                item_type = self.components.canvas.type(name_item)
                if item_type == "text":
                    self.components.canvas.itemconfig(name_item, fill="white")

        except Exception as e:
            self.logging_manager.log_error(f"Error in hover enter effect: {e}")

    def _on_name_hover_leave(self, event):
        """
        จัดการเมื่อ mouse ออกจากบริเวณชื่อตัวละคร
        Parameters:
            event: Event object ที่มีข้อมูลพิกัดของเมาส์
        """
        try:
            # 1. คืนค่า cursor กลับเป็นปกติ
            self.components.canvas.configure(cursor="")

            # 2. ค้นหา item ที่ถูก hover ออก
            current_x = self.components.canvas.canvasx(event.x)
            current_y = self.components.canvas.canvasy(event.y)
            items = self.components.canvas.find_overlapping(
                current_x - 5, current_y - 5, current_x + 5, current_y + 5
            )

            # 3. ค้นหา item ที่มี tag 'name'
            for item in items:
                if "name" in self.components.canvas.gettags(item):
                    # 4. ค้นหาสีเดิมจาก tag
                    original_color = None
                    for tag in self.components.canvas.gettags(item):
                        if tag.startswith("original_color:"):
                            original_color = tag.split(":")[1]
                            self.components.canvas.dtag(item, tag)
                            break

                    # 5. ถ้าพบสีเดิม ให้ใช้สีนั้น ถ้าไม่พบให้ใช้สีตามประเภท (เช็คว่าเป็น text item ก่อน)
                    item_type = self.components.canvas.type(item)
                    if item_type == "text":
                        if original_color:
                            self.components.canvas.itemconfig(item, fill=original_color)
                        else:
                            # ตรวจสอบว่าเป็นชื่อลึกลับหรือไม่
                            text = self.components.canvas.itemcget(item, "text")
                            name_color = "#a855f7" if "?" in text else "#38bdf8"
                            self.components.canvas.itemconfig(item, fill=name_color)
                    break

        except Exception as e:
            self.logging_manager.log_error(f"Error in hover leave effect: {e}")

    def highlight_special_names(self, text, names_set):
        """No-op — name highlighting now handled by create_rich_text_with_outlines().
        Brackets 『』 removed per v4 style rules."""
        return text

    def apply_highlights_to_text(self):
        """
        ยกเลิกการใช้งานฟังก์ชันนี้ เนื่องจากไม่ต้องการไฮไลท์ข้อความด้วยสีเหลือง
        ระบบจะใช้เพียงเครื่องหมาย 『』 ในการแสดงชื่อเฉพาะโดยไม่มีการเปลี่ยนสี
        """
        # ไม่ทำอะไร - ระบบจะใช้เพียงเครื่องหมาย 『』 ในข้อความโดยไม่มีการเปลี่ยนสี
        pass

    def start_fade_timer(self):
        """
        เริ่มนับเวลาถอยหลัง 10 วินาทีเพื่อเริ่ม fade out effect
        """
        # ยกเลิก timer เดิมถ้ามี
        if self.state.fade_timer_id:
            self.root.after_cancel(self.state.fade_timer_id)
            self.state.fade_timer_id = None

        # บันทึกเวลาปัจจุบันเป็นเวลาล่าสุดที่มีการอัพเดตข้อความ
        self.state.last_activity_time = time.time()

        # รีเซ็ตสถานะการทำ fade out ถ้ากำลังทำอยู่
        if self.state.is_fading:
            self.state.is_fading = False

            # คืนค่าความโปร่งใสของ TUI ที่ผู้ใช้ตั้งไว้
            try:
                self.restore_user_transparency()
            except Exception as e:
                logging.error(f"Error restoring TUI transparency during reset: {e}")

            # รีเซ็ตสีของข้อความและชื่อกลับเป็นสีเดิม
            if self.components.text_container:
                self.components.canvas.itemconfig(
                    self.components.text_container, fill="white"
                )

            # รีเซ็ตสีของเงาเป็นสีดำ (ข้าม shadow images)
            for outline in self.components.outline_container:
                item_type = self.components.canvas.type(outline)
                if item_type == "text":
                    self.components.canvas.itemconfig(outline, fill="#000000")

            # รีเซ็ตสีของชื่อตัวละคร
            for name_item in self.components.canvas.find_withtag("name"):
                text = self.components.canvas.itemcget(name_item, "text")
                name_color = "#a855f7" if "?" in text else "#38bdf8"
                # เช็คว่าเป็น text item ก่อนอัพเดตสี (ข้าม shadow images)
                item_type = self.components.canvas.type(name_item)
                if item_type == "text":
                    self.components.canvas.itemconfig(name_item, fill=name_color)
                    
                    # 🔍 DEBUG: Add character name click debugging
                    print(f"🔍 DEBUG: Found name item {name_item} with text: '{text}' (type: {item_type})")
                    
                    # 🔍 DEBUG: Check if click binding exists
                    bindings = self.components.canvas.tag_bind(name_item, "<Button-1>")
                    print(f"🔍 DEBUG: Name item {name_item} click bindings: {bindings}")
                    
                    # 🔍 DEBUG: Add/update character name click binding
                    try:
                        self.components.canvas.tag_bind(name_item, "<Button-1>", 
                            lambda event, character_name=text: self._debug_character_click(event, character_name))
                        print(f"🔍 DEBUG: Added click binding for character: '{text}'")
                    except Exception as e:
                        print(f"❌ DEBUG ERROR: Failed to bind character click for '{text}': {e}")

        # ตั้ง timer ใหม่เพื่อเริ่ม fade out หลังจาก 10 วินาที (เฉพาะเมื่อเปิดใช้งาน)
        if self.state.fadeout_enabled:
            self.state.fade_timer_id = self.root.after(10000, self.check_and_start_fade)
        # logging.info(f"⏰ [FADE DEBUG] Fade timer set, enabled: {self.state.fadeout_enabled}, auto_hide: {self.state.auto_hide_after_fade}")

    def reset_fade_timer_for_user_activity(self, activity_name="user_activity"):
        """
        Reset fade timer เมื่อผู้ใช้มีกิจกรรม (เช่น Previous Dialog)
        รักษาความสอดคล้องกับระบบ fade-out ที่มีอยู่

        Args:
            activity_name (str): ชื่อกิจกรรมที่ทำให้ reset timer
        """
        try:
            logging.info(f"🔄 [TIMER RESET] User activity detected: {activity_name}")

            # 1. Cancel existing fade timer
            if self.state.fade_timer_id:
                self.root.after_cancel(self.state.fade_timer_id)
                self.state.fade_timer_id = None
                logging.info("⏹️ [TIMER RESET] Cancelled existing fade timer")

            # 2. Stop any ongoing fade process
            if self.state.is_fading:
                self.state.is_fading = False
                logging.info("🛑 [TIMER RESET] Stopped ongoing fade process")

                # Restore UI transparency
                try:
                    self.restore_user_transparency()
                    logging.info("💫 [TIMER RESET] Restored user transparency")
                except Exception as e:
                    logging.error(f"Error restoring transparency: {e}")

            # 3. Update last activity time to current time
            self.state.last_activity_time = time.time()

            # 4. Reset just_faded_out state
            if hasattr(self.state, "just_faded_out"):
                self.state.just_faded_out = False

            # 5. Start new 10-second timer (only if fadeout is enabled)
            if self.state.fadeout_enabled:
                self.state.fade_timer_id = self.root.after(10000, self.check_and_start_fade)
                logging.info("⏰ [TIMER RESET] Started new 10-second fade timer")

            logging.info(f"✅ [TIMER RESET] Complete reset for {activity_name}")

        except Exception as e:
            logging.error(f"❌ [TIMER RESET] Error in reset_fade_timer_for_user_activity: {e}")

    def _display_text_direct(self, text):
        """
        แสดงข้อความโดยตรงโดยไม่ reset fade timer
        ใช้สำหรับ Previous Dialog หรือกิจกรรมที่ต้องการควบคุม timer เอง

        Args:
            text (str): ข้อความที่ต้องการแสดง
        """
        try:
            logging.info(f"📄 [DIRECT DISPLAY] Displaying text: {text[:50]}...")

            # Clear canvas
            self.components.canvas.delete("all")
            self.components.outline_container = []

            # *** สำคัญ: ไม่เรียก update_text() เพื่อหลีกเลี่ยง timer reset ***
            # แทนที่จะใช้ logic การแสดงผลโดยตรง

            # Check if it's cutscene dialog (using existing logic)
            if "『" in text and "』" in text:
                logging.info("📄 [DIRECT DISPLAY] Detected cutscene format, using cutscene display")
                # Use cutscene display logic but without timer reset
                self._display_cutscene_text_direct(text)
            else:
                logging.info("📄 [DIRECT DISPLAY] Regular text format, using normal display")
                # Use normal text display logic but without timer reset
                self._display_regular_text_direct(text)

            # Force UI update
            self.root.update_idletasks()

            logging.info("✅ [DIRECT DISPLAY] Text displayed successfully")

        except Exception as e:
            logging.error(f"❌ [DIRECT DISPLAY] Error: {e}")

    def _display_regular_text_direct(self, text):
        """แสดงข้อความธรรมดาโดยตรง (ไม่ reset timer)"""
        try:
            # Use existing text rendering logic from _original_update_text
            # but without timer manipulation

            # Get fonts
            font_info = self.font_manager.get_current_font_info()
            small_font = (font_info["name"], max(12, int(font_info["size"] * 0.7)))
            dialogue_font = (font_info["name"], font_info["size"])

            # Calculate available width
            available_width = self.root.winfo_width() - 40

            # Handle text overflow and rendering
            self.components.outline_container = []

            # Render text to canvas (simplified version)
            self.components.canvas.create_text(
                20, 20,
                text=text,
                font=dialogue_font,
                fill="white",
                anchor="nw",
                width=available_width
            )

        except Exception as e:
            logging.error(f"❌ [DIRECT DISPLAY] Error in regular text display: {e}")

    def _display_cutscene_text_direct(self, text):
        """แสดงข้อความ cutscene โดยตรง (ไม่ reset timer)"""
        try:
            # Simplified cutscene display without timer manipulation
            # Extract speaker and content
            if "：" in text:
                parts = text.split("：", 1)
                speaker = parts[0].strip()
                content = parts[1].strip() if len(parts) > 1 else ""
            else:
                speaker = "Unknown"
                content = text

            # Get fonts
            font_info = self.font_manager.get_current_font_info()
            speaker_font = (font_info["name"], max(14, int(font_info["size"] * 0.8)))
            content_font = (font_info["name"], font_info["size"])

            # Display speaker
            if speaker:
                self.components.canvas.create_text(
                    20, 10,
                    text=speaker,
                    font=speaker_font,
                    fill="#FFD700",  # Gold color for speaker
                    anchor="nw"
                )

            # Display content
            if content:
                self.components.canvas.create_text(
                    20, 40,
                    text=content,
                    font=content_font,
                    fill="white",
                    anchor="nw",
                    width=self.root.winfo_width() - 40
                )

        except Exception as e:
            logging.error(f"❌ [DIRECT DISPLAY] Error in cutscene text display: {e}")

    def check_and_start_fade(self):
        """
        ตรวจสอบว่าควรเริ่ม fade out หรือไม่
        """
        # logging.info(f"🔍 [FADE DEBUG] check_and_start_fade called, fadeout_enabled: {self.state.fadeout_enabled}")

        # *** SAFETY CHECK: Don't fade if window is hidden ***
        if self.state.is_window_hidden or not self.root.winfo_viewable():
            self.state.fade_timer_id = None
            return

        # ถ้าปิดระบบ fade out ไว้ ให้หยุดการทำงานโดยสิ้นเชิง
        if not self.state.fadeout_enabled:
            self.state.fade_timer_id = None  # ยกเลิก timer แทนการ reschedule
            return

        # ตรวจสอบว่าผ่านไป 10 วินาทีหรือยัง นับจากการอัพเดตข้อความล่าสุด
        current_time = time.time()

        # เพิ่มการตรวจสอบว่ามีข้อความให้ fade หรือไม่
        has_content = False

        # ตรวจสอบว่ามีข้อความในส่วนข้อความหลักหรือไม่
        if self.components.text_container:
            text = self.components.canvas.itemcget(
                self.components.text_container, "text"
            )
            if text and text.strip():
                has_content = True

        # ตรวจสอบว่ามีข้อความในส่วนชื่อตัวละครหรือไม่
        for name_item in self.components.canvas.find_withtag("name"):
            text = self.components.canvas.itemcget(name_item, "text")
            if text and text.strip():
                has_content = True
                break

        if (
            current_time - self.state.last_activity_time >= 10
            and not self.state.is_fading
            and has_content  # เพิ่มเงื่อนไขนี้
        ):
            # เริ่ม fade out
            self.state.is_fading = True
            self.fade_out_text()
        else:
            # ยังไม่ครบเวลา หรือไม่มีข้อความให้ fade ตั้ง timer ใหม่ (เฉพาะเมื่อเปิดใช้งาน)
            if self.state.fadeout_enabled:
                self.state.fade_timer_id = self.root.after(1000, self.check_and_start_fade)

    def fade_out_text(self, alpha=1.0, step=0.1):  # เพิ่มขนาด step จาก 0.05 เป็น 0.1
        """
        ทำให้ข้อความและชื่อตัวละครค่อยๆ หายไปแบบ dissolve effect

        Args:
            alpha: ค่าความโปร่งใสปัจจุบัน (1.0 = มองเห็นเต็มที่, 0.0 = มองไม่เห็น)
            step: ขนาดการลดความโปร่งใสในแต่ละขั้นตอน
        """
        try:
            # *** SAFETY CHECK: Stop if window is hidden (e.g. by WASD) ***
            if self.state.is_window_hidden or not self.root.winfo_viewable():
                self.state.is_fading = False
                self.state.fade_timer_id = None
                # 🎯 CONSISTENCY FIX: Also restore transparency when stopped by WASD
                self.restore_user_transparency()
                logging.info(f"🔧 [TRANSPARENCY FIX] Restored user transparency after WASD hide")
                return

            # ถ้ามีการอัพเดตข้อความใหม่ระหว่างการ fade out ให้ยกเลิกการ fade
            current_time = time.time()
            if current_time - self.state.last_activity_time < 10:
                self.state.is_fading = False
                # 🎯 EDGE CASE FIX: Reset transparency to user setting when new message arrives during fade
                self.restore_user_transparency()
                logging.info(f"🔧 [TRANSPARENCY FIX] Restored user transparency during fade out")
                return

            if alpha <= 0:
                # เมื่อหายไปหมดแล้ว ให้ลบองค์ประกอบทั้งหมดจาก canvas แทนการล้างข้อความ

                # 1. บันทึกสถานะว่าเพิ่งมีการ fade out สมบูรณ์
                self.state.just_faded_out = True

                # 2. ล้าง canvas ทั้งหมด แทนที่จะเคลียร์แค่ text
                self.components.canvas.delete("all")
                self.components.outline_container = []
                self.components.text_container = None

                # 3. บันทึกสถานะการทำ fade
                self.state.is_fading = False

                # 4. คืนค่าสถานะต่างๆ เกี่ยวกับข้อความ
                self.dialogue_text = ""
                self.state.full_text = ""

                # 5. Phase 3: TUI fade เสร็จแล้วเมื่อ text fade เสร็จ
                if self.state.auto_hide_after_fade:
                    self.execute_tui_hide()  # ซ่อน TUI ทันที (fade เสร็จแล้วใน loop)

                return

            # ลดความโปร่งใสทีละน้อย
            new_alpha = max(0, alpha - step)

            # คำนวณสีตามค่า alpha
            # ค่า RGB ยังคงเดิม แต่ความเข้มจะลดลงตาม alpha
            r, g, b = 255, 255, 255  # สีข้อความเดิมคือสีขาว
            adjusted_r = int(r * new_alpha)
            adjusted_g = int(g * new_alpha)
            adjusted_b = int(b * new_alpha)
            text_color = f"#{adjusted_r:02x}{adjusted_g:02x}{adjusted_b:02x}"

            # 1. อัพเดตสีของข้อความหลัก
            if self.components.text_container:
                self.components.canvas.itemconfig(
                    self.components.text_container, fill=text_color
                )

            # 2. อัพเดตสีของเงาข้อความหลัก (ปรับให้จางลงเช่นกัน)
            outline_r, outline_g, outline_b = 0, 0, 0  # สีเงาเดิมคือสีดำ
            adjusted_outline_opacity = max(
                0, new_alpha - 0.2
            )  # เงาหายเร็วกว่าข้อความเล็กน้อย
            adjusted_outline_color = f"#{outline_r:02x}{outline_g:02x}{outline_b:02x}"

            for outline in self.components.outline_container:
                # เช็คว่าเป็น text item ก่อนอัพเดตสี (ข้าม shadow images)
                item_type = self.components.canvas.type(outline)
                if item_type == "text":
                    self.components.canvas.itemconfig(
                        outline, fill=adjusted_outline_color
                    )

            # 3. อัพเดตสีของชื่อตัวละคร
            for name_item in self.components.canvas.find_withtag("name"):
                # ดึงสีเดิมของชื่อตัวละคร เพื่อคงความเป็นสีม่วงหรือสีฟ้า
                original_color = ""
                for tag in self.components.canvas.gettags(name_item):
                    if tag.startswith("original_color:"):
                        original_color = tag.split(":")[1]
                        break

                if not original_color:
                    # ถ้าไม่พบ tag ที่เก็บสีเดิม ใช้การตรวจสอบจากข้อความแทน
                    text = self.components.canvas.itemcget(name_item, "text")
                    original_color = "#a855f7" if "?" in text else "#38bdf8"

                # แปลงสีเดิมเป็น RGB
                try:
                    # แปลงสี hex เป็น RGB
                    orig_r = int(original_color[1:3], 16)
                    orig_g = int(original_color[3:5], 16)
                    orig_b = int(original_color[5:7], 16)

                    # ปรับความโปร่งใสของสีตาม alpha
                    faded_r = int(orig_r * new_alpha)
                    faded_g = int(orig_g * new_alpha)
                    faded_b = int(orig_b * new_alpha)

                    name_color = f"#{faded_r:02x}{faded_g:02x}{faded_b:02x}"
                    # เช็คว่าเป็น text item ก่อนอัพเดตสี (ข้าม shadow images)
                    item_type = self.components.canvas.type(name_item)
                    if item_type == "text":
                        self.components.canvas.itemconfig(name_item, fill=name_color)
                except Exception as e:
                    # ถ้าแปลงสีไม่สำเร็จ ใช้การลดความเข้มแบบเดียวกับข้อความหลัก (เช็คว่าเป็น text item ก่อน)
                    item_type = self.components.canvas.type(name_item)
                    if item_type == "text":
                        self.components.canvas.itemconfig(name_item, fill=text_color)

            # 4. อัพเดตสีของเงาชื่อตัวละคร
            for name_outline in self.components.canvas.find_withtag("name_outline"):
                self.components.canvas.itemconfig(
                    name_outline, fill=adjusted_outline_color
                )

            # 5. ปรับความโปร่งใสของไอคอน confirm
            for confirm_icon in self.components.canvas.find_withtag("confirm_icon"):
                # กำหนดความโปร่งใสของไอคอนตาม alpha
                # เนื่องจาก image ไม่สามารถปรับความโปร่งใสได้โดยตรง จึงต้องใช้การซ่อน/แสดงแทน
                if new_alpha < 0.5:
                    # ซ่อนไอคอนเมื่อความโปร่งใสต่ำกว่า 50%
                    self.components.canvas.itemconfig(confirm_icon, state="hidden")
                else:
                    self.components.canvas.itemconfig(confirm_icon, state="normal")

            # 6. เพิ่ม: อัพเดตสีของข้อความส่วนหัวใน choice dialog (header_text)
            header_gold_color = "#FFD700"  # สีทองเดิมของส่วนหัว
            try:
                # แปลงสีทองเป็น RGB
                header_r = int(header_gold_color[1:3], 16)
                header_g = int(header_gold_color[3:5], 16)
                header_b = int(header_gold_color[5:7], 16)

                # ปรับความโปร่งใสของสีตาม alpha
                faded_header_r = int(header_r * new_alpha)
                faded_header_g = int(header_g * new_alpha)
                faded_header_b = int(header_b * new_alpha)

                header_color = (
                    f"#{faded_header_r:02x}{faded_header_g:02x}{faded_header_b:02x}"
                )

                for header_item in self.components.canvas.find_withtag("header_text"):
                    # เช็คว่าเป็น text item ก่อนอัพเดตสี (ข้าม shadow images)
                    item_type = self.components.canvas.type(header_item)
                    if item_type == "text":
                        self.components.canvas.itemconfig(
                            header_item, fill=header_color
                        )
            except Exception as e:
                # ถ้าแปลงสีไม่สำเร็จ ใช้การลดความเข้มแบบเดียวกับข้อความหลัก
                for header_item in self.components.canvas.find_withtag("header_text"):
                    # เช็คว่าเป็น text item ก่อนอัพเดตสี (ข้าม shadow images)
                    item_type = self.components.canvas.type(header_item)
                    if item_type == "text":
                        self.components.canvas.itemconfig(header_item, fill=text_color)

            # 7. เพิ่ม: อัพเดตสีของเงาส่วนหัวใน choice dialog (header_outline)
            for header_outline in self.components.canvas.find_withtag("header_outline"):
                self.components.canvas.itemconfig(
                    header_outline, fill=adjusted_outline_color
                )

            # 8. TUI DISSOLVE EFFECT: ปรับความโปร่งใสของ TUI window พร้อมกับข้อความ
            if self.state.auto_hide_after_fade:
                self.root.attributes("-alpha", new_alpha)

            # เรียกตัวเองซ้ำด้วย alpha ใหม่
            self.state.fade_timer_id = self.root.after(
                25,
                lambda: self.fade_out_text(
                    new_alpha, step
                ),  # ลดเวลาระหว่างขั้นตอนจาก 50ms เป็น 25ms
            )

        except Exception as e:
            logging.error(f"Error in fade_out_text: {e}")
            self.state.is_fading = False

    def clean_canvas(self) -> None:
        """
        ทำความสะอาด canvas โดยการลบองค์ประกอบทั้งหมดและรีเซ็ตสถานะ
        ใช้เมื่อต้องการล้าง canvas อย่างสมบูรณ์
        """
        try:
            # ลบองค์ประกอบทั้งหมดใน canvas
            if hasattr(self.components, "canvas") and self.components.canvas:
                self.components.canvas.delete("all")

            # รีเซ็ตตัวแปรอ้างอิงองค์ประกอบ
            self.components.outline_container = []
            self.components.text_container = None

            # รีเซ็ตสถานะที่เกี่ยวข้องกับข้อความ
            self.dialogue_text = ""
            self.state.full_text = ""
            self.state.is_fading = False
            self.state.is_typing = False

            # ยกเลิก timer ต่างๆ
            if hasattr(self, "type_writer_timer") and self.type_writer_timer:
                self.root.after_cancel(self.type_writer_timer)
                self.type_writer_timer = None

            if self.state.fade_timer_id:
                self.root.after_cancel(self.state.fade_timer_id)
                self.state.fade_timer_id = None

            # ซ่อนลูกศร overflow
            self.hide_overflow_arrow()

            logging.info("Canvas cleaned successfully")
        except Exception as e:
            logging.error(f"Error in clean_canvas: {e}")

    def toggle_fadeout(self):
        """
        สลับสถานะการเปิด/ปิด fade out และอัปเดตการแสดงผลของปุ่ม
        """
        try:
            # สลับสถานะ
            self.state.fadeout_enabled = not self.state.fadeout_enabled

            # Parent-Child Logic: auto-hide ทำงานไปด้วยกับ fade out
            if self.state.fadeout_enabled:
                # ถ้าเปิด fade out ให้เปิด auto-hide ด้วยอัตโนมัติ
                self.state.auto_hide_after_fade = True
            else:
                # ถ้าปิด fade out ต้องปิด auto-hide ด้วย
                self.state.auto_hide_after_fade = False
                self.cancel_window_hide_timer()

            # อัปเดตความโปร่งใสของปุ่ม fadeout ตามสถานะ
            if "fadeout" in self.components.buttons:
                if self.state.fadeout_enabled:
                    # เมื่อเปิดใช้งาน fadeout ให้แสดงปุ่มแบบปกติ (100% opacity)
                    self.components.buttons["fadeout"].configure(
                        image=self.fadeout_image
                    )
                    # Enhanced feedback with auto-hide status
                    self.show_enhanced_fade_feedback()
                else:
                    # เมื่อปิดใช้งาน fadeout ให้แสดงปุ่มแบบจาง (50% opacity)
                    # สร้างภาพโปร่งใส 50% ชั่วคราว ถ้ายังไม่มี
                    if not hasattr(self, "fadeout_disabled_image"):
                        # สร้างภาพใหม่โดยใช้ PIL ลดความโปร่งใสเหลือ 50%
                        img_path = AssetManager.get_asset_path("fade.png")
                        img = Image.open(img_path)
                        img = img.resize((20, 20))
                        img = img.convert("RGBA")

                        # ลดความโปร่งใสด้วยการผสมกับสีพื้นหลัง
                        datas = img.getdata()
                        newData = []
                        for item in datas:
                            # ปรับ alpha channel ให้เหลือ 50%
                            newData.append((item[0], item[1], item[2], item[3] // 2))
                        img.putdata(newData)

                        self.fadeout_disabled_image = ImageTk.PhotoImage(img)

                    # ใช้ภาพที่มีความโปร่งใส 50%
                    self.components.buttons["fadeout"].configure(
                        image=self.fadeout_disabled_image
                    )
                    # *** REVERSED: Fade out DISABLED notification ***
                    self.show_feedback_message(
                        "ปิดการซ่อนข้อความอัตโนมัติ",
                        bg_color="#c62828",  # สีแดงเข้ม (เปลี่ยนเป็นสีแดงสำหรับ disabled)
                        font_size=12,
                    )

            # *** REVERSED BEHAVIOR: Handle timer based on new state ***
            if not self.state.fadeout_enabled and self.state.fade_timer_id:
                # Fade out is now DISABLED - cancel timer
                self.root.after_cancel(self.state.fade_timer_id)
                self.state.fade_timer_id = None
                self.state.is_fading = False

                # คืนค่าความโปร่งใสของ TUI ที่ผู้ใช้ตั้งไว้จาก color picker
                try:
                    self.restore_user_transparency()
                except Exception as e:
                    logging.error(f"Error restoring TUI transparency: {e}")

                # Start checking timer (but won't actually fade)
                self.state.fade_timer_id = self.root.after(
                    1000, self.check_and_start_fade
                )

            # *** REVERSED: If fade out is ENABLED, start fade timer ***
            elif self.state.fadeout_enabled:
                self.start_fade_timer()

            logging.info(
                f"*** REVERSED: Fade out toggled: {'ENABLED (will fade)' if self.state.fadeout_enabled else 'DISABLED (no fade)'}"
            )

        except Exception as e:
            logging.error(f"Error in toggle_fadeout: {e}")

    def show_enhanced_fade_feedback(self):
        """แสดง feedback สำหรับ fade out + auto-hide ที่ทำงานไปด้วยกัน"""
        try:
            if self.state.fadeout_enabled:
                # auto-hide ทำงานไปด้วยกับ fade out เสมอ
                message = "จะซ่อน TUI + ข้อความใน 10 วิ"
                color = "#1565c0"  # Blue for enabled
            else:
                message = "ไม่ซ่อนอัตโนมัติ"
                color = "#d32f2f"  # Red for disabled

            self.show_feedback_message(message, bg_color=color, font_size=12)
        except Exception as e:
            logging.error(f"Error in show_enhanced_fade_feedback: {e}")

    def cancel_window_hide_timer(self):
        """ยกเลิก timer สำหรับซ่อน TUI"""
        try:
            if self.state.window_hide_timer_id:
                self.root.after_cancel(self.state.window_hide_timer_id)
                self.state.window_hide_timer_id = None
                logging.info("🚫 Window hide timer cancelled")
        except Exception as e:
            logging.error(f"Error cancelling window hide timer: {e}")

    def schedule_tui_hide(self, delay_ms=2000):
        """จัดตารางการซ่อน TUI หลังจาก text fade เสร็จ"""
        try:
            # ยกเลิก timer เก่าถ้ามี
            self.cancel_window_hide_timer()

            # ตั้ง timer ใหม่
            self.state.window_hide_timer_id = self.root.after(
                delay_ms, self.execute_tui_hide
            )

            logging.info(f"🕒 Scheduled TUI hide in {delay_ms}ms")
        except Exception as e:
            logging.error(f"Error scheduling TUI hide: {e}")

    def execute_tui_hide(self):
        """ซ่อน TUI window"""
        try:
            self.clear_displayed_text()  # ล้างข้อความก่อนซ่อน
            self.root.withdraw()  # ซ่อนหน้าต่าง
            self.state.is_window_hidden = True
            self.state.window_hide_timer_id = None

            logging.info("🙈 TUI hidden after text fade")

        except Exception as e:
            logging.error(f"Error hiding TUI: {e}")

    def clear_displayed_text(self):
        """ล้างข้อความที่แสดงใน canvas"""
        try:
            self.components.canvas.delete("all")
            self.components.outline_container = []
            self.components.text_container = None
            self.state.full_text = ""

            # Log only once to prevent flooding
            if not self._text_cleared:
                logging.info("🧹 Cleared displayed text from TUI")
                self._text_cleared = True
        except Exception as e:
            logging.error(f"Error clearing displayed text: {e}")

    def show_tui_on_new_translation(self):
        """แสดง TUI เมื่อมีการแปลใหม่"""
        try:
            if self.state.is_window_hidden:
                self.root.deiconify()  # แสดงหน้าต่าง
                self.state.is_window_hidden = False

            # คืนค่าความโปร่งใสของ TUI ทุกครั้ง (fix: opacity ผิดหลัง fade)
            try:
                self.restore_user_transparency()
            except Exception as e:
                logging.error(f"Error restoring TUI transparency on show: {e}")
        except Exception as e:
            logging.error(f"Error showing TUI: {e}")

    def force_show_tui(self):
        """Force show TUI - for manual toggle (F9/TUI button)"""
        try:
            logging.info(f"🔧 [MANUAL SHOW] force_show_tui called, is_window_hidden: {self.state.is_window_hidden}")

            # Always show, regardless of state
            self.root.deiconify()
            self.root.lift()

            # Reset auto-hide state
            self.state.is_window_hidden = False

            # Cancel any pending hide timers
            if self.state.window_hide_timer_id:
                self.root.after_cancel(self.state.window_hide_timer_id)
                self.state.window_hide_timer_id = None

            # Reset fade state
            if self.state.is_fading:
                self.state.is_fading = False

            # Restore user transparency
            try:
                self.restore_user_transparency()
            except Exception as e:
                logging.error(f"Error restoring TUI transparency on manual show: {e}")

            logging.info("✅ [MANUAL SHOW] TUI force shown via manual toggle")

        except Exception as e:
            logging.error(f"Error force showing TUI: {e}")

    def show_previous_dialog(self):
        """
        เรียกใช้ force translate callback และแสดง visual feedback
        """
        try:
            # แสดงข้อความ feedback เมื่อกดปุ่ม force
            self.show_feedback_message("Force Translation!")

            # เรียกใช้ callback
            if callable(self.previous_dialog_callback):
                self.previous_dialog_callback()

            # Log การใช้งาน
            if hasattr(self, "logging_manager") and self.logging_manager:
                self.logging_manager.log_info("Force translation triggered by button")
        except Exception as e:
            logging.error(f"Error in previous dialog: {e}")

    def _on_force_button_hover_enter(self, event: tk.Event) -> None:
        """
        จัดการเมื่อ mouse hover เข้าบริเวณปุ่ม force
        - แสดง visual feedback ทันที
        - เริ่ม timer หน่วงเวลาก่อนสั่ง force translate (ถ้า hover-to-execute เปิดอยู่)
        Args:
            event: Mouse enter event
        """
        try:
            force_button = self.components.buttons.get("force")
            if not force_button or not force_button.winfo_exists():
                return

            # --- Visual Feedback (ทำเสมอเมื่อ hover) ---
            if not hasattr(force_button, "_original_bg_for_hover_f"):
                force_button._original_bg_for_hover_f = force_button.cget("bg")

            force_button.configure(relief="sunken")
            try:
                current_button_bg = force_button.cget("bg")
                highlight_color = self.lighten_color(current_button_bg, factor=0.25)
                force_button.configure(bg=highlight_color)
            except Exception:
                pass
            # --- End Visual Feedback ---

            if self.force_hover_active:
                # ถ้า hover-to-execute เปิดอยู่ ให้เริ่ม timer
                # ยกเลิก timer เก่า (ถ้ามี) เผื่อกรณีเมาส์เข้าๆ ออกๆ เร็วมาก
                if self.force_hover_trigger_timer is not None:
                    self.root.after_cancel(self.force_hover_trigger_timer)
                    self.force_hover_trigger_timer = None

                # ตั้ง timer ใหม่ (เช่น 250ms)
                HOVER_FORCE_DELAY = 250  # มิลลิวินาที
                self.force_hover_trigger_timer = self.root.after(
                    HOVER_FORCE_DELAY, self._trigger_delayed_hover_force
                )
            else:
                # ถ้า hover-to-execute ปิดอยู่ อาจแสดง tooltip หรือไม่ทำอะไร
                pass

        except Exception as e:
            logging.error(f"Error in force button hover enter: {e}")

    def _on_force_button_hover_leave(self, event: tk.Event) -> None:
        """
        จัดการเมื่อ mouse ออกจากบริเวณปุ่ม force
        - คืนค่าสถานะปุ่มกลับเป็นปกติ
        Args:
            event: Mouse leave event
        """
        try:
            force_button = self.components.buttons.get("force")
            if not force_button or not force_button.winfo_exists():
                return

            force_button.configure(relief="flat")  # คืนสภาพปุ่ม

            # คืนค่าสีพื้นหลังเดิมที่เก็บไว้ตอน hover enter
            if hasattr(force_button, "_original_bg_for_hover_f"):
                force_button.configure(bg=force_button._original_bg_for_hover_f)
                try:
                    delattr(force_button, "_original_bg_for_hover_f")  # ลบ attribute ทิ้ง
                except AttributeError:
                    pass  # ถ้าไม่มีก็ไม่เป็นไร
            else:
                # Fallback: ถ้าไม่มีสีเดิมเก็บไว้ ให้ตั้งค่าตามสีพื้นหลัง UI ปัจจุบัน
                # ซึ่งควรจะถูกจัดการโดย _apply_background_color_and_alpha
                # การเรียก _apply_background_color_and_alpha ทั้งหมดอาจจะหนักไป
                # ให้ดึงค่าสีที่ควรจะเป็นจาก settings/appearance_manager
                current_ui_bg = self.settings.get(
                    "bg_color", appearance_manager.bg_color
                )
                if self.lock_mode != 1:  # ถ้าไม่ได้อยู่ในโหมดโปร่งใสเต็มที่
                    force_button.configure(bg=current_ui_bg)
                # ถ้าอยู่ในโหมด lock_mode == 1 (transparent background), ปุ่มจะไม่โปร่งใสตามไปด้วย
                # แต่สีพื้นหลังของปุ่มควรจะยังคงเป็น current_ui_bg (สีที่ใช้ทำ transparent)
                # ซึ่ง _apply_background_color_and_alpha ได้ตั้งไว้แล้ว

        except Exception as e:
            logging.error(f"Error in force button hover leave: {e}")

    def lighten_color(self, color: str, factor: float = 0.2) -> str:
        """
        ทำให้สีสว่างขึ้นตาม factor ที่กำหนด
        Args:
            color: สีใน hex format (#RRGGBB)
            factor: ค่าปรับความสว่าง (0.0-1.0)
        Returns:
            str: สีใหม่ใน hex format
        """
        try:
            # แปลงสี hex เป็น RGB
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)

            # ทำให้แต่ละ channel สว่างขึ้น
            r = min(255, r + int((255 - r) * factor))
            g = min(255, g + int((255 - g) * factor))
            b = min(255, b + int((255 - b) * factor))

            # แปลงกลับเป็น hex format
            return f"#{r:02x}{g:02x}{b:02x}"
        except Exception as e:
            logging.error(f"Error lightening color: {e}")
            return color  # คืนค่าสีเดิมถ้าเกิดข้อผิดพลาด

    def display_cutscene_text(self, display_data):
        """แสดงข้อความ cutscene พร้อมจัดการสีและสัญลักษณ์

        Args:
            display_data (dict): {
                'type': 'cutscene',
                'speaker': str,
                'translation': str,
                'speaker_info': {
                    'found': bool,
                    'source': str,  # 'npc_database' | 'temp_cache' | 'new_speaker'
                    'display_color': str  # 'white' | 'blue'
                }
            }
        """
        try:
            logging.info(f"Displaying cutscene text: {display_data}")

            # ดึงข้อมูลจาก display_data
            speaker = display_data.get("speaker", "")
            translation = display_data.get("translation", "")
            speaker_info = display_data.get("speaker_info", {})

            # สร้างข้อความที่จะแสดง
            if speaker_info.get("found", False):
                # ชื่อที่มีในระบบ - แสดงเครื่องหมาย ✓
                display_text = f"✓ {speaker}: {translation}"
            else:
                # ชื่อใหม่ - แสดงแบบธรรมดา (จะแสดงเป็นสีฟ้า)
                display_text = f"{speaker}: {translation}"

            # รีเซ็ตสถานะการทำ fade out
            if self.state.is_fading:
                self.state.is_fading = False

            # ยกเลิก timer fade out ถ้ามี
            if self.state.fade_timer_id:
                self.root.after_cancel(self.state.fade_timer_id)
                self.state.fade_timer_id = None

            # บันทึกเวลาปัจจุบันเป็นเวลาล่าสุดที่มีการอัพเดตข้อความ
            self.state.last_activity_time = time.time()

            # รีเซ็ตสถานะ just_faded_out ถ้ามี
            if hasattr(self.state, "just_faded_out"):
                self.state.just_faded_out = False

            # ล้าง canvas เพื่อเตรียมเนื้อหาใหม่
            self.components.canvas.delete("all")
            self.components.outline_container = []
            self.components.text_container = None

            # Base configuration
            outline_offset = 1
            outline_color = "#000000"
            outline_positions = [
                (-1, -1),
                (-1, 0),
                (-1, 1),
                (0, -1),
                (0, 1),
                (1, -1),
                (1, 0),
                (1, 1),
            ]

            # เริ่มการแสดงผลที่ด้านบนของ canvas
            self.components.canvas.yview_moveto(0)

            # Get font sizes
            current_font_size = self.settings.get("font_size", 24)
            small_font_size = int(current_font_size * 0.8)

            # Create font configurations
            dialogue_font = (self.settings.get("font"), current_font_size)
            small_font = (self.settings.get("font"), small_font_size)

            self.state.full_text = display_text
            available_width = self.components.canvas.winfo_width() - 40

            # สำหรับ cutscene แสดงแบบเรียบง่าย
            # แยกชื่อผู้พูดและข้อความ
            if ": " in display_text:
                parts = display_text.split(": ", 1)
                speaker_part = parts[0]
                content_part = parts[1] if len(parts) > 1 else ""
            else:
                speaker_part = speaker
                content_part = translation

            # กำหนดสีของชื่อผู้พูด
            speaker_color = "#38bdf8"  # สีฟ้าสำหรับชื่อใหม่
            if speaker_info.get("found", False):
                speaker_color = "#38bdf8"  # ใช้สีฟ้าเหมือนกันแต่จะมี checkmark

            # คำนวณตำแหน่งเริ่มต้น
            start_y = 10

            # สร้างเงาสำหรับชื่อผู้พูดด้วย Advanced Blur Shadow System
            speaker_shadow = self.shadow_engine.create_shadow_on_canvas(
                self.components.canvas,
                text=speaker_part,
                x=10,
                y=start_y,
                font_info=small_font,
                anchor="nw",
                tags=("speaker_shadow",),
            )
            if speaker_shadow:
                self.components.outline_container.append(speaker_shadow)

            # สร้างข้อความชื่อผู้พูด
            name_text = self.components.canvas.create_text(
                10,
                start_y,
                anchor="nw",
                font=small_font,
                fill=speaker_color,
                text=speaker_part,
                tags=("name", "cutscene_speaker"),
            )

            # เพิ่ม confirm icon ถ้าชื่อมีในระบบ
            if speaker_info.get("found", False) and hasattr(self, "confirm_icon"):
                name_bbox = self.components.canvas.bbox(name_text)
                if name_bbox:
                    icon_x = name_bbox[2] + 8
                    icon_y = start_y + ((name_bbox[3] - name_bbox[1]) // 2)

                    self.components.canvas.create_image(
                        icon_x,
                        icon_y,
                        image=self.confirm_icon,
                        anchor="w",
                        tags=("confirm_icon",),
                    )

            # คำนวณตำแหน่งของข้อความบทสนทนา
            name_bbox = self.components.canvas.bbox(name_text)
            if name_bbox:
                dialogue_y = name_bbox[3] + (small_font[1] * 0.3)
            else:
                dialogue_y = start_y + small_font[1] + 5

            # กำหนดความกว้างของข้อความ
            thai_text_width = int(available_width * 0.95)

            # รีเซ็ต outline_container เพื่อเตรียมสร้างเงาใหม่สำหรับข้อความ
            # (เก็บเงาของชื่อที่มีอยู่แล้ว)

            # สร้างเงาสำหรับข้อความบทสนทนา
            for i in range(2):
                offset = (3 - i) * outline_offset // 2
                for dx, dy in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:  # มุม
                    outline = self.components.canvas.create_text(
                        10 + dx * offset,
                        dialogue_y + dy * offset,
                        anchor="nw",
                        font=dialogue_font,
                        fill="#000000",
                        width=thai_text_width,
                        text="",
                        tags=("dialogue_outline",),
                    )
                    self.components.outline_container.append(outline)

            # สร้างเงาชั้นกลางสำหรับข้อความ
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                outline = self.components.canvas.create_text(
                    10 + dx * outline_offset,
                    dialogue_y + dy * outline_offset,
                    anchor="nw",
                    font=dialogue_font,
                    fill=outline_color,
                    width=thai_text_width,
                    text="",
                    tags=("dialogue_outline",),
                )
                self.components.outline_container.append(outline)

            # สร้างข้อความหลัก
            self.components.text_container = self.components.canvas.create_text(
                10,
                dialogue_y,
                anchor="nw",
                font=dialogue_font,
                fill="white",
                width=thai_text_width,
                text="",
                tags=("main_text",),
            )

            # เริ่มแสดงข้อความแบบ typewriter effect
            self.state.is_typing = True
            self.state.typing_timer = None
            self._start_cutscene_typing_effect(content_part, 0)

            # เริ่ม fade timer ถ้าเปิดใช้งาน
            if self.state.fadeout_enabled:
                self.start_fade_timer()

            logging.info(f"Cutscene text display completed for speaker: {speaker}")

        except Exception as e:
            logging.error(f"Error in display_cutscene_text: {e}")
            import traceback

            logging.error(traceback.format_exc())

    def optimize_typing_animation(self) -> None:
        """Coordinate typing animation with resize events"""
        try:
            # Check if resize is in progress
            if (
                hasattr(self, "resize_throttler")
                and self.resize_throttler.pending_resize
            ):
                # Pause animation during resize
                if self.state.typing_timer:
                    self.root.after_cancel(self.state.typing_timer)
                    self.state.typing_timer = None

                # Resume after resize completes
                self.root.after(50, self._resume_typing_animation)
                return

            # Normal animation processing
            self._continue_typing_animation()

        except Exception as e:
            logging.error(f"Error optimizing typing animation: {e}")

    def _resume_typing_animation(self) -> None:
        """Resume typing animation after resize"""
        try:
            if (
                hasattr(self, "resize_throttler")
                and self.resize_throttler.pending_resize
            ):
                # Still resizing, wait more
                self.root.after(25, self._resume_typing_animation)
                return

            # Safe to resume animation
            if self.state.is_typing and self.state.full_text:
                self._continue_typing_animation()

        except Exception as e:
            logging.error(f"Error resuming typing animation: {e}")

    def _continue_typing_animation(self) -> None:
        """Continue typing animation with current state"""
        try:
            if not self.state.is_typing:
                return

            # Continue from where we left off
            if self.components.text_container:
                current_text = self.components.canvas.itemcget(
                    self.components.text_container, "text"
                )
                remaining_text = self.state.full_text[len(current_text) :]

                if remaining_text:
                    # Add next character
                    next_char = remaining_text[0]
                    new_text = current_text + next_char

                    # Update text without triggering full update
                    self.components.canvas.itemconfig(
                        self.components.text_container, text=new_text
                    )

                    # Schedule next character
                    typing_speed = 50  # Default speed
                    if self.font_settings and hasattr(
                        self.font_settings, "typing_speed"
                    ):
                        typing_speed = self.font_settings.typing_speed
                    elif hasattr(self.settings, "get"):
                        typing_speed = self.settings.get("typing_speed", 50)

                    self.state.typing_timer = self.root.after(
                        typing_speed, self._continue_typing_animation
                    )
                else:
                    # Animation complete
                    self.state.is_typing = False
                    self.state.typing_timer = None

        except Exception as e:
            logging.error(f"Error continuing typing animation: {e}")
            self.state.is_typing = False

    def _start_cutscene_typing_effect(self, text, char_index):
        """*** OPTIMIZED TYPING ANIMATION ***
        เริ่มแสดงข้อความแบบ typewriter effect สำหรับ cutscene

        Args:
            text: ข้อความที่จะแสดง
            char_index: ตำแหน่งตัวอักษรปัจจุบัน
        """
        try:
            # *** OPTIMIZATION: Check for resize in progress ***
            if (
                hasattr(self, "resize_throttler")
                and self.resize_throttler.pending_resize
            ):
                # Delay typing during resize for smoother experience
                self.root.after(
                    25, lambda: self._start_cutscene_typing_effect(text, char_index)
                )
                return

            if char_index < len(text):
                # แสดงข้อความที่เพิ่มขึ้นทีละตัวอักษร
                current_text = text[: char_index + 1]

                # อัพเดตข้อความหลัก
                if self.components.text_container:
                    self.components.canvas.itemconfig(
                        self.components.text_container, text=current_text
                    )

                # อัพเดตเงา (ข้าม shadow images)
                for outline in self.components.outline_container:
                    if "dialogue_outline" in self.components.canvas.gettags(outline):
                        item_type = self.components.canvas.type(outline)
                        if item_type == "text":
                            self.components.canvas.itemconfig(
                                outline, text=current_text
                            )

                # กำหนดความเร็วในการพิมพ์
                typing_speed = self.settings.get("typing_speed", 50)  # milliseconds

                # ตั้งเวลาสำหรับตัวอักษรต่อไป
                self.state.typing_timer = self.root.after(
                    typing_speed,
                    lambda: self._start_cutscene_typing_effect(text, char_index + 1),
                )
            else:
                # พิมพ์เสร็จแล้ว
                self.state.is_typing = False
                self.state.typing_timer = None
                logging.info("Cutscene typing effect completed")

        except Exception as e:
            logging.error(f"Error in _start_cutscene_typing_effect: {e}")
            self.state.is_typing = False
            self.state.typing_timer = None

    def create_rich_text_on_canvas(self, x: int, y: int, text: str, base_font_tuple,
                                 fill: str = "white", width: int = None, anchor: str = "nw",
                                 tags: tuple = None) -> list:
        """
        Create rich text on canvas supporting *italic* formatting

        Args:
            x, y: Starting position
            text: Text with possible *italic* markers
            base_font_tuple: Base font tuple like ("Anuphan", 20)
            fill: Text color
            width: Maximum width for text wrapping
            anchor: Text anchor
            tags: Canvas tags

        Returns:
            List of text object IDs created on canvas
        """
        text_objects = []

        try:
            # Parse text into segments
            segments = self.rich_text_formatter.parse_rich_text(text)

            if not segments:
                return text_objects

            # Track current position
            current_x = x
            line_height = int(base_font_tuple[1] * 1.4)  # Font size * 1.4 for proper line spacing (standard ratio)

            # For each segment, create text object with appropriate font
            for i, segment in enumerate(segments):
                segment_text = segment['text']
                font_style = segment['font_style']

                # Get appropriate font
                font_tuple = self.rich_text_formatter.get_font_tuple(base_font_tuple, font_style)

                # Create text object
                text_id = self.components.canvas.create_text(
                    current_x,
                    y,
                    text=segment_text,
                    font=font_tuple,
                    fill=fill,
                    anchor=anchor,
                    width=width,
                    tags=tags
                )

                text_objects.append(text_id)

                # Calculate width of this segment for next position
                # Get text bbox to calculate width
                bbox = self.components.canvas.bbox(text_id)
                if bbox:
                    segment_width = bbox[2] - bbox[0]
                    current_x += segment_width

            logging.info(f"Rich text rendered: {len(segments)} segments, {len(text_objects)} objects")

        except Exception as e:
            logging.error(f"Error in create_rich_text_on_canvas: {e}")
            # Fallback: create single text object with base font
            text_id = self.components.canvas.create_text(
                x, y, text=text, font=base_font_tuple, fill=fill,
                anchor=anchor, width=width, tags=tags
            )
            text_objects.append(text_id)

        return text_objects

    def create_rich_text_with_outlines(self, x: int, y: int, text: str, base_font_tuple,
                                     fill: str = "white", outline_color: str = "#000000",
                                     outline_offset: int = 1, width: int = None,
                                     anchor: str = "nw", tags: tuple = None,
                                     names: list = None) -> dict:
        """
        Create rich text with outline shadows supporting *italic*, **highlight**, and name coloring

        Returns:
            dict with 'main' and 'outlines' keys containing lists of text object IDs
        """
        result = {'main': [], 'outlines': []}

        try:
            logging.info(f"🔍 CREATE_RICH_TEXT: Starting with text = '{text}'")
            logging.info(f"🔍 CREATE_RICH_TEXT: Base font = {base_font_tuple}")

            # Parse text into segments (with name detection if names provided)
            segments = self.rich_text_formatter.parse_rich_text_with_names(text, names)
            logging.info(f"🔍 CREATE_RICH_TEXT: Parsed {len(segments)} segments")

            if not segments:
                return result

            # Create outline positions (8-directional)
            outline_positions = [(-1, -1), (-1, 0), (-1, 1), (0, -1),
                               (0, 1), (1, -1), (1, 0), (1, 1)]

            # Track current position for all segments
            segment_positions = []
            current_x = x

            # 🔧 FIXED: Add manual line wrapping for Rich Text - proper spacing
            line_height = int(base_font_tuple[1] * 1.4)  # Font size * 1.4 for proper line spacing (standard line height ratio)
            current_y = y
            max_width = width if width else 500  # Default max width if not specified

            # First pass: calculate positions with line wrapping
            segments_to_process = segments.copy()  # Create copy to avoid modifying during iteration
            i = 0
            while i < len(segments_to_process):
                segment = segments_to_process[i]
                segment_text = segment['text']
                font_style = segment['font_style']
                logging.info(f"🔍 SEGMENT {i+1}: text='{segment_text}', style='{font_style}'")
                font_tuple = self.rich_text_formatter.get_font_tuple(base_font_tuple, font_style)
                # Names in cutscene/battle → bold font
                if font_style == 'name' and self._get_text_color() != "white":
                    font_tuple = (base_font_tuple[0], base_font_tuple[1], "bold")
                logging.info(f"🔍 SEGMENT {i+1}: font_tuple={font_tuple}")

                # Split long segments into words and process word by word
                words = segment_text.split()

                # Process each word in the segment
                for word_idx, word in enumerate(words):
                    # Add space after word except for last word
                    word_to_measure = word + " " if word_idx < len(words) - 1 else word

                    # Measure word width
                    temp_text = self.components.canvas.create_text(
                        0, 0, text=word_to_measure, font=font_tuple
                    )
                    bbox = self.components.canvas.bbox(temp_text)
                    word_width = bbox[2] - bbox[0] if bbox else 0
                    self.components.canvas.delete(temp_text)

                    # Check if word fits on current line
                    if current_x + word_width > x + max_width and current_x > x:
                        # Move to next line
                        current_x = x
                        current_y += line_height
                        logging.info(f"🔍 WRAP: Moving to next line at y={current_y}")

                    # Add word position
                    segment_positions.append({
                        'x': current_x,
                        'y': current_y,
                        'text': word_to_measure,
                        'font_tuple': font_tuple,
                        'font_style': font_style,
                        'width': word_width
                    })

                    current_x += word_width

                i += 1  # Move to next segment

            # Second pass: create outlines for all segments
            for segment_pos in segment_positions:
                for dx, dy in outline_positions:
                    outline_id = self.components.canvas.create_text(
                        segment_pos['x'] + dx * outline_offset,
                        segment_pos['y'] + dy * outline_offset,  # 🔧 FIXED: Use segment Y position
                        text=segment_pos['text'],
                        font=segment_pos['font_tuple'],
                        fill=outline_color,
                        anchor=anchor,
                        width=None,  # 🔧 FIXED: Use None for Rich Text outlines
                        tags=tags
                    )
                    result['outlines'].append(outline_id)

            # Third pass: create main text for all segments
            for segment_pos in segment_positions:
                # Determine text color based on font style and mode
                style = segment_pos['font_style']
                if style == 'bold':
                    text_color = "#FFB366"  # Light orange highlight word
                elif style == 'name':
                    # Names: cyan in dialogue, mono-color in cutscene/battle
                    mode_color = self._get_text_color()
                    if mode_color == "white":
                        text_color = "#38bdf8"  # Cyan for dialogue mode
                    else:
                        text_color = fill  # Yellow/orange mono-color for cutscene/battle
                else:
                    text_color = fill  # Default color for normal and italic text

                main_id = self.components.canvas.create_text(
                    segment_pos['x'],
                    segment_pos['y'],  # 🔧 FIXED: Use segment Y position
                    text=segment_pos['text'],
                    font=segment_pos['font_tuple'],
                    fill=text_color,
                    anchor=anchor,
                    width=None,  # 🔧 FIXED: Use None for Rich Text segments to prevent individual wrapping
                    tags=tags
                )
                result['main'].append(main_id)

            logging.info(f"Rich text with outlines: {len(segments)} segments, "
                        f"{len(result['main'])} main, {len(result['outlines'])} outlines")

        except Exception as e:
            logging.error(f"Error in create_rich_text_with_outlines: {e}")
            # Fallback: create single text object with base font
            main_id = self.components.canvas.create_text(
                x, y, text=text, font=base_font_tuple, fill=fill,
                anchor=anchor, width=width, tags=tags
            )
            result['main'].append(main_id)

        return result

    def _update_rich_text_dialogue(self, dialogue_text: str, base_font_tuple, dialogue_y: int, available_width: int):
        """
        Update dialogue text with Rich Text support for *italic* formatting

        Args:
            dialogue_text: Text to display (may contain *italic* markers)
            base_font_tuple: Base font configuration
            dialogue_y: Y position for text
            available_width: Maximum width for text wrapping
        """
        try:
            logging.info(f"🔍 UPDATE_RICH_DIALOGUE: Starting with text='{dialogue_text}'")
            logging.info(f"🔍 UPDATE_RICH_DIALOGUE: base_font_tuple={base_font_tuple}")
            logging.info(f"🔍 UPDATE_RICH_DIALOGUE: dialogue_y={dialogue_y}, width={available_width}")
            # Clear any existing rich text objects if we're tracking them
            if hasattr(self, '_rich_text_objects'):
                for obj_id in self._rich_text_objects.get('main', []):
                    try:
                        self.components.canvas.delete(obj_id)
                    except:
                        pass
                for obj_id in self._rich_text_objects.get('outlines', []):
                    try:
                        self.components.canvas.delete(obj_id)
                    except:
                        pass

            # Create rich text with outlines and store references
            logging.info(f"🔍 UPDATE_RICH_DIALOGUE: About to call create_rich_text_with_outlines")
            self._rich_text_objects = self.create_rich_text_with_outlines(
                x=10,
                y=dialogue_y,
                text=dialogue_text,
                base_font_tuple=base_font_tuple,
                fill=self._get_text_color(),
                outline_color="#000000",
                outline_offset=1,
                width=available_width,
                anchor="nw",
                tags=("text", "rich_text_dialogue"),
                names=getattr(self, 'names', None)
            )

            # Store current dialogue text for future reference
            self.dialogue_text = dialogue_text

            # 🔧 FIXED: Add Rich Text outlines to outline_container for proper system integration
            # This ensures Rich Text shadows work correctly with fade effects and other systems
            if self._rich_text_objects.get('outlines'):
                self.components.outline_container.extend(self._rich_text_objects['outlines'])

            logging.info(f"Rich text dialogue updated: {len(self._rich_text_objects.get('main', []))} main objects, "
                        f"{len(self._rich_text_objects.get('outlines', []))} outline objects")

        except Exception as e:
            logging.error(f"Error updating rich text dialogue: {e}")
            # Fallback: use simple text without rich formatting
            if hasattr(self.components, 'text_container'):
                try:
                    self.components.canvas.itemconfig(
                        self.components.text_container,
                        text=dialogue_text,
                        font=base_font_tuple
                    )
                except:
                    pass

    def display_speaker_name(self, speaker_name: str, font_tuple):
        """
        Display character/speaker name with proper styling and shadows

        Args:
            speaker_name: Name of the speaker to display
            font_tuple: Font configuration for the speaker name
        """
        try:
            logging.info(f"🎭 DISPLAY_SPEAKER_NAME: Displaying speaker '{speaker_name}' with font {font_tuple}")

            # Create name shadows (8-point system) - same as existing implementation
            outline_offset = 1
            outline_color = "#000000"
            outline_positions = [
                (-1, -1),
                (-1, 0),
                (-1, 1),
                (0, -1),
                (0, 1),
                (1, -1),
                (1, 0),
                (1, 1),
            ]

            # Speaker color: battle/cutscene = mono-color, dialogue = cyan/purple
            # All speakers use normal weight (no bold) for compatibility
            mode_color = self._get_text_color()
            if mode_color != "white":
                # Battle/Cutscene: mono-color
                name_color = mode_color
                speaker_font = font_tuple
            elif "?" in speaker_name:
                name_color = "#a855f7"
                speaker_font = font_tuple
            else:
                name_color = "#38bdf8"
                speaker_font = font_tuple

            # Create outlines/shadows for the speaker name
            for dx, dy in outline_positions:
                outline = self.components.canvas.create_text(
                    10 + dx * outline_offset,
                    10 + dy * outline_offset,
                    anchor="nw",
                    font=speaker_font,
                    fill=outline_color,
                    text=speaker_name,
                    tags=("name_outline",),
                )
                self.components.outline_container.append(outline)

            speaker_text_id = self.components.canvas.create_text(
                10,
                10,
                anchor="nw",
                font=speaker_font,
                fill=name_color,
                text=speaker_name,
                tags=("name",),
            )

            logging.info(f"✅ DISPLAY_SPEAKER_NAME: Speaker name displayed successfully with text_id={speaker_text_id}")

        except Exception as e:
            logging.error(f"❌ DISPLAY_SPEAKER_NAME: Error displaying speaker name '{speaker_name}': {e}")

    # *** ENHANCED TUI AUTO HIDE ICONS SYSTEM ***
    def setup_enhanced_auto_hide_system(self):
        """Setup enhanced auto hide system with smart event-driven detection"""
        try:
            # Initial setup
            self.setup_auto_hide_bindings()
            self.cache_ui_widgets()

            # Setup smart event-driven monitoring
            self.setup_smart_geometry_tracking()

            # Start only basic hover monitor (low frequency)
            self.start_hover_monitor()

            logging.info("Enhanced auto-hide system initialized successfully")
        except Exception as e:
            logging.error(f"Error setting up enhanced auto-hide system: {e}")

    def setup_smart_geometry_tracking(self):
        """Setup smart geometry tracking using Configure events"""
        try:
            if self.root and self.root.winfo_exists():
                # Bind to Configure event for efficient geometry tracking
                self.root.bind("<Configure>", self.on_ui_configure_event, add=True)

                # Initialize current geometry
                self.last_ui_position = (self.root.winfo_x(), self.root.winfo_y())
                self.last_ui_size = (self.root.winfo_width(), self.root.winfo_height())
                self.last_ui_geometry = self.root.geometry()

                logging.info("Smart geometry tracking setup completed")

        except Exception as e:
            logging.error(f"Error setting up smart geometry tracking: {e}")

    def on_ui_configure_event(self, event=None):
        """Handle UI Configure events (move/resize) efficiently"""
        try:
            # Only handle events for the main window
            if event and event.widget != self.root:
                return

            if not self.auto_hide_enabled or not self.root.winfo_exists():
                return

            # Get current geometry
            current_x = self.root.winfo_x()
            current_y = self.root.winfo_y()
            current_width = self.root.winfo_width()
            current_height = self.root.winfo_height()

            # Check what changed
            position_changed = (
                abs(current_x - self.last_ui_position[0]) > self.position_change_threshold or
                abs(current_y - self.last_ui_position[1]) > self.position_change_threshold
            )

            size_changed = (
                abs(current_width - self.last_ui_size[0]) > self.size_change_threshold or
                abs(current_height - self.last_ui_size[1]) > self.size_change_threshold
            )

            # Handle changes with smart debouncing
            if position_changed:
                self.handle_position_change(current_x, current_y)

            if size_changed:
                self.handle_size_change(current_width, current_height)

            # Update tracking
            self.last_ui_position = (current_x, current_y)
            self.last_ui_size = (current_width, current_height)
            self.last_ui_geometry = self.root.geometry()

        except Exception as e:
            logging.error(f"Error in configure event handler: {e}")

    def handle_position_change(self, new_x, new_y):
        """Handle position change with smart debouncing"""
        try:
            if not self.is_moving:
                self.is_moving = True
                logging.info(f"UI movement detected: {new_x},{new_y}")

            # Cancel previous end timer
            if self.move_end_timer:
                self.root.after_cancel(self.move_end_timer)

            # Set new end timer
            self.move_end_timer = self.root.after(300, self.on_smart_move_end)

            # Immediate hover area update during move
            self.check_mouse_position_immediate()

        except Exception as e:
            logging.error(f"Error handling position change: {e}")

    def handle_size_change(self, new_width, new_height):
        """Handle size change with smart debouncing"""
        try:
            if not self.is_resizing:
                self.is_resizing = True
                logging.info(f"UI resize detected: {new_width}x{new_height}")

            # Cancel previous end timer
            if self.resize_end_timer:
                self.root.after_cancel(self.resize_end_timer)

            # Set new end timer
            self.resize_end_timer = self.root.after(300, self.on_smart_resize_end)

            # Immediate hover area update during resize
            self.check_mouse_position_immediate()

        except Exception as e:
            logging.error(f"Error handling size change: {e}")

    def on_smart_move_end(self):
        """Called when movement ends (smart version)"""
        try:
            if self.root.winfo_exists():
                final_x = self.root.winfo_x()
                final_y = self.root.winfo_y()
                logging.info(f"UI movement completed: Final position {final_x},{final_y}")

                self.is_moving = False
                self.move_end_timer = None

                # 💾 Save position for current mode
                self._save_current_position_to_settings()

                # Full refresh only when movement stops
                self.refresh_auto_hide_bindings()
                self.check_mouse_position_immediate()

        except Exception as e:
            logging.error(f"Error in smart move end: {e}")

    def on_smart_resize_end(self):
        """Called when resizing ends (smart version)"""
        try:
            if self.root.winfo_exists():
                final_width = self.root.winfo_width()
                final_height = self.root.winfo_height()
                final_x = self.root.winfo_x()
                final_y = self.root.winfo_y()
                logging.info(f"UI resize completed: Final size {final_width}x{final_height} at {final_x},{final_y}")

                self.is_resizing = False
                self.resize_end_timer = None

                # Full refresh only when resizing stops
                self.refresh_auto_hide_bindings()
                self.check_mouse_position_immediate()

        except Exception as e:
            logging.error(f"Error in smart resize end: {e}")

    def setup_auto_hide_bindings(self):
        """Setup mouse hover detection สำหรับ auto hide icons"""
        try:
            # Clear existing bindings first
            self.clear_auto_hide_bindings()

            # Get all UI widgets to bind
            widgets_to_bind = self.get_all_ui_widgets()

            # Bind events to all widgets
            for widget in widgets_to_bind:
                if widget and widget.winfo_exists():
                    widget.bind("<Enter>", self.on_tui_enter, add=True)
                    widget.bind("<Leave>", self.on_tui_leave, add=True)
                    # Also bind motion for more precise tracking
                    widget.bind("<Motion>", self.on_mouse_motion, add=True)

            logging.info(f"Auto-hide bindings setup for {len(widgets_to_bind)} widgets")
        except Exception as e:
            logging.error(f"Error setting up auto-hide bindings: {e}")

    def clear_auto_hide_bindings(self):
        """Clear existing auto-hide bindings"""
        try:
            widgets_to_clear = self.ui_widgets_cache.copy()
            for widget in widgets_to_clear:
                if widget and widget.winfo_exists():
                    widget.unbind("<Enter>")
                    widget.unbind("<Leave>")
                    widget.unbind("<Motion>")
        except Exception as e:
            logging.error(f"Error clearing auto-hide bindings: {e}")

    def get_all_ui_widgets(self):
        """Get all UI widgets that should have hover detection"""
        widgets = []

        try:
            # Root window
            if self.root and self.root.winfo_exists():
                widgets.append(self.root)

            # Canvas (main content area)
            if hasattr(self.components, 'canvas') and self.components.canvas:
                widgets.append(self.components.canvas)

            # Control area
            if hasattr(self.components, 'control_area') and self.components.control_area:
                widgets.append(self.components.control_area)

            # Resize handle
            if hasattr(self, 'resize_handle') and self.resize_handle:
                widgets.append(self.resize_handle)

            # All buttons (even if hidden)
            for button_name in ["close", "lock", "color", "fadeout"]:
                button = self.components.buttons.get(button_name)
                if button and button.winfo_exists():
                    widgets.append(button)

            # Get all child widgets recursively
            def get_children(widget):
                children = []
                try:
                    for child in widget.winfo_children():
                        children.append(child)
                        children.extend(get_children(child))
                except:
                    pass
                return children

            # Add all children of main containers
            if hasattr(self.components, 'canvas') and self.components.canvas:
                widgets.extend(get_children(self.components.canvas))

            if hasattr(self.components, 'control_area') and self.components.control_area:
                widgets.extend(get_children(self.components.control_area))

        except Exception as e:
            logging.error(f"Error getting UI widgets: {e}")

        return list(set(widgets))  # Remove duplicates

    def cache_ui_widgets(self):
        """Cache current UI widgets for binding management"""
        self.ui_widgets_cache = self.get_all_ui_widgets()


    def check_mouse_position_immediate(self):
        """Immediately check mouse position against current UI bounds"""
        try:
            if not self.root.winfo_exists():
                return

            mouse_x = self.root.winfo_pointerx()
            mouse_y = self.root.winfo_pointery()
            root_x = self.root.winfo_rootx()
            root_y = self.root.winfo_rooty()
            root_width = self.root.winfo_width()
            root_height = self.root.winfo_height()

            # Check if mouse is inside UI bounds
            mouse_inside = (
                root_x <= mouse_x <= root_x + root_width and
                root_y <= mouse_y <= root_y + root_height
            )

            # Update hover state if needed
            if mouse_inside != self.mouse_inside_ui:
                self.mouse_inside_ui = mouse_inside

                if mouse_inside:
                    self.on_tui_enter_direct()
                else:
                    self.on_tui_leave_direct()

        except Exception:
            pass  # Ignore mouse position errors

    def start_hover_monitor(self):
        """Start smart hover monitoring (low frequency backup for missed events)"""
        def monitor():
            try:
                if not self.auto_hide_enabled or not self.root.winfo_exists():
                    return

                # Only do backup checking if not actively moving/resizing
                if not self.is_moving and not self.is_resizing:
                    self.check_mouse_position_immediate()

                # Low frequency - this is just a backup for missed events
                if self.auto_hide_enabled:
                    self.hover_monitor_timer = self.root.after(200, monitor)

            except Exception as e:
                logging.error(f"Error in hover monitor: {e}")

        monitor()

    def refresh_auto_hide_bindings(self):
        """Refresh auto-hide bindings when UI changes"""
        try:
            # Cache new widgets
            old_cache = self.ui_widgets_cache.copy()
            self.cache_ui_widgets()

            # Only refresh if widgets actually changed
            if set(old_cache) != set(self.ui_widgets_cache):
                self.setup_auto_hide_bindings()
                logging.info("Auto-hide bindings refreshed due to UI changes")

        except Exception as e:
            logging.error(f"Error refreshing auto-hide bindings: {e}")

    def on_tui_enter(self, event=None):
        """Handle mouse entering TUI area (event-based)"""
        self.on_tui_enter_direct()

    def on_tui_leave(self, event=None):
        """Handle mouse leaving TUI area (event-based)"""
        self.on_tui_leave_direct()

    def on_mouse_motion(self, event=None):
        """Handle mouse motion for enhanced tracking"""
        if not self.auto_hide_enabled:
            return

        # Update that mouse is actively moving inside UI
        self.mouse_inside_ui = True
        self.on_tui_enter_direct()

    def on_tui_enter_direct(self):
        """Direct method for handling hover enter (called by monitors)"""
        if not self.auto_hide_enabled:
            return

        # ป้องกันการเรียกซ้ำ - ถ้า hover อยู่แล้วไม่ต้องทำอะไร
        if self.hover_active and self.icons_visible:
            return

        logging.info("AUTO-HIDE: Mouse entered TUI area - showing icons instantly")
        self.hover_active = True

        # Cancel any ongoing fade out immediately
        if self.fade_out_timer:
            self.root.after_cancel(self.fade_out_timer)
            self.fade_out_timer = None

        # Cancel ongoing animation immediately
        if self.fade_animation_id:
            self.root.after_cancel(self.fade_animation_id)
            self.fade_animation_id = None

        # แสดงไอคอนทันที (ไม่ใช้ fade_icons_in เพื่อหลีกเลี่ยงการกระพริบ)
        if not self.icons_visible:
            self.set_icons_alpha(1.0)
            self.icons_visible = True
            self.current_alpha = 1.0
            logging.info("AUTO-HIDE: Icons shown instantly")

    def on_tui_leave_direct(self):
        """Direct method for handling hover leave (called by monitors)"""
        if not self.auto_hide_enabled:
            return

        # ป้องกันการเรียกซ้ำ - ถ้าไม่ hover อยู่แล้วไม่ต้องทำอะไร
        if not self.hover_active and not self.icons_visible:
            return

        logging.info("AUTO-HIDE: Mouse left TUI area - hiding icons")
        self.hover_active = False

        # Start fade out immediately เฉพาะเมื่อไอคอนแสดงอยู่
        if self.icons_visible:
            self.fade_icons_out()

    def fade_icons_in(self, duration=None):
        """แสดงไอคอนทันที 100% ไม่มี animation"""
        if not self.auto_hide_enabled or self.icons_visible:
            return

        logging.info("AUTO-HIDE: Showing icons instantly (100% opacity)")

        # แสดงไอคอนทันที 100% opacity ไม่มี animation เลย
        self.set_icons_alpha(1.0)
        self.icons_visible = True
        self.current_alpha = 1.0

        # ยกเลิก animation ทั้งหมด
        if self.fade_animation_id:
            self.root.after_cancel(self.fade_animation_id)
            self.fade_animation_id = None

    def fade_icons_out(self, duration=None):
        """Fade out icons ตาม duration ที่กำหนด"""
        if not self.auto_hide_enabled or not self.icons_visible:
            return

        # Get duration from settings if not provided
        if duration is None:
            duration = self.settings.get("tui_auto_hide_icons", {}).get("fade_out_duration", 1000)

        start_time = time.time()
        start_alpha = self.current_alpha

        def animate():
            if self.hover_active:  # Check if mouse re-entered
                return

            elapsed = (time.time() - start_time) * 1000  # ms
            progress = min(elapsed / duration, 1.0)

            # Ease-in-out function
            alpha = start_alpha * (1.0 - self.ease_in_out(progress))
            self.current_alpha = alpha

            # Apply alpha to all icons
            self.set_icons_alpha(alpha)

            if progress < 1.0 and not self.hover_active:
                self.fade_animation_id = self.root.after(16, animate)  # 60fps
            else:
                self.icons_visible = False
                self.fade_animation_id = None

        animate()

    def ease_in_out(self, t):
        """Ease-in-out animation curve"""
        return t * t * (3.0 - 2.0 * t)

    def set_icons_alpha(self, alpha_value):
        """ตั้งค่า transparency ของไอคอนทั้งหมด"""
        try:
            # Apply alpha simulation to all icon buttons
            for button_name in ["close", "lock", "color", "fadeout"]:
                button = self.components.buttons.get(button_name)
                if button and button.winfo_exists():
                    if alpha_value < 0.1:  # Hidden state
                        # Hide buttons by removing from pack layout
                        button.pack_forget()
                    else:
                        # Show buttons by restoring pack layout
                        # Check if button is not currently visible
                        if not button.winfo_viewable() or not button.winfo_ismapped():
                            # Different pady for close button vs others
                            pady_value = (5, 5) if button_name == "close" else 5
                            button.pack(side=tk.TOP, pady=pady_value)

            # Apply alpha to resize handle
            if hasattr(self, 'resize_handle') and self.resize_handle and self.resize_handle.winfo_exists():
                if alpha_value < 0.1:
                    # Hide resize handle by removing from place layout
                    self.resize_handle.place_forget()
                else:
                    # Show resize handle by restoring place layout
                    if not self.resize_handle.winfo_viewable() or not self.resize_handle.winfo_ismapped():
                        self.resize_handle.place(relx=1, rely=1, anchor="se")

        except Exception as e:
            logging.error(f"Error setting icons alpha: {e}")


if __name__ == "__main__":
    root = tk.Tk()
    settings = Settings()

    # หลังจากลบ DummyLoggingManager แล้ว ควรสร้างตัวแปร dummy แทน
    dummy_logging_manager = None  # ก่อนหน้านี้เป็น DummyLoggingManager()

    # Test setup with dummy callbacks
    app = Translated_UI(
        root=root,
        toggle_translation=lambda: None,
        stop_translation=lambda: None,
        previous_dialog_callback=lambda: None,
        toggle_main_ui=lambda: None,
        toggle_ui=lambda: None,
        settings=settings,
        switch_area=lambda x: None,
        logging_manager=dummy_logging_manager,
    )

    root.mainloop()
