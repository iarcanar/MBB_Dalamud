"""
Translated Logs Module - Enhanced Chat-style Translation History Display

Version: 2.1.0
Author: MBB_PROJECT Team
Last Updated: 2025-07-18

Features:
- Smart Cache System for message replacement
- Position Lock System with instant toggle
- Font Management with real-time updates
- Flat design UI with minimal colors
- Performance optimized scrolling and animations
- Custom scrollbar and hover effects
"""

import tkinter as tk
from tkinter import BooleanVar
import logging
from asset_manager import AssetManager
import time
import hashlib
from appearance import appearance_manager

# เพิ่ม import สำหรับการจัดการ monitor position
try:
    import win32api
    import win32con

    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False
    print("Warning: win32api not available, using fallback positioning for Logs UI")

logging.basicConfig(level=logging.ERROR)

# --- Design System Constants ---
# Fallback font สำหรับ UI elements ใน translated_logs (ตัวอักษรใน bubble โหลดจาก settings)
FONT_FAMILY = "Anuphan"
SINGLE_BUBBLE_COLOR = "#1C1C1C"

# Window size defaults
DEFAULT_LOG_WIDTH = 300
DEFAULT_LOG_HEIGHT = 800
FALLBACK_LOG_GEOMETRY = "240x600+1480+100"

# Transparency alpha values per mode
ALPHA_MAP = {
    "A": 0.95,   # normal
    "B": 0.70,   # transparent
    "C": 0.50,   # super transparent
    "D": 1.00,   # opaque
}
TRANSPARENCY_MODES = list(ALPHA_MAP.keys())

# Message cache max size
MAX_CACHE_SIZE = 200


class LightweightChatBubble(tk.Frame):
    """
    Lightweight Chat Bubble widget using tk.Frame and tk.Label for optimal performance
    """

    def __init__(
        self,
        parent,
        speaker,
        message,
        speaker_color,
        bubble_color,
        font_size,
        max_width,
        font_family=FONT_FAMILY,
    ):
        super().__init__(parent, bg=bubble_color)

        self.speaker_label = None
        self.message_label = None
        self._last_wrap_width = max_width - 24  # Track wrapping state

        # Create labels for speaker and message
        if speaker:
            self.speaker_label = tk.Label(
                self,
                text=speaker,
                font=(font_family, font_size, "bold"),
                fg=speaker_color,
                bg=bubble_color,
                justify="left",
                anchor="w",
            )
            self.speaker_label.pack(fill="x", expand=True, padx=12, pady=(8, 0))

        self.message_label = tk.Label(
            self,
            text=message,
            font=(font_family, font_size),
            fg="#FFFFFF",
            bg=bubble_color,
            justify="left",
            wraplength=max_width - 24,
            anchor="w",
        )
        message_pady = (4, 10) if speaker else (8, 10)
        self.message_label.pack(fill="x", expand=True, padx=12, pady=message_pady)

        self.bind("<Configure>", self._on_resize)

    def _on_resize(self, event):
        """Update wraplength when bubble size changes"""
        new_width = event.width - 24  # -24 for left/right padding
        if new_width > 0:
            self.message_label.config(wraplength=new_width)
            self._last_wrap_width = new_width

    def update_font_size(self, new_size, font_family=None):
        """Update font size and family for all labels"""
        if font_family is None:
            font_family = FONT_FAMILY

        if self.speaker_label:
            self.speaker_label.config(font=(font_family, new_size, "bold"))
        self.message_label.config(font=(font_family, new_size))

    def check_wrap_changed(self):
        """Check if text wrapping changed significantly (for repack decision)"""
        current_width = self.winfo_width() - 24
        if current_width <= 0:
            return False
        # Consider repack needed if width changed by more than 20%
        return abs(current_width - self._last_wrap_width) > (
            self._last_wrap_width * 0.2
        )


class Translated_Logs:
    """Main class for enhanced chat-style translation logs with smart animations and font management"""

    def __init__(self, root, settings, on_close_callback=None, main_app=None):
        self.root = root
        self.settings = settings
        self.on_close_callback = on_close_callback
        self.main_app = main_app  # เพิ่ม reference ของ main app

        # เพิ่มตัวแปรสำหรับสถานะ lock - โหลดจาก settings
        self.is_position_locked = settings.get("logs_position_locked", False)
        self.locked_geometry = settings.get("logs_locked_geometry", None)
        self._last_save_time = 0  # เพิ่มสำหรับ throttling
        self._session_opened = False  # ใช้ track ว่าเปิดใน session นี้หรือยัง

        # Main state variables
        self.is_visible = False
        self.is_ui_locked = False
        self._is_first_show = True

        # Transparency settings — ค่า alpha อยู่ใน ALPHA_MAP constant
        self.current_mode = "A"

        # Bubble and font settings
        self.bubble_list = []

        # Animation state
        self._scroll_animation_id = None

        # Reverse mode
        self.reverse_mode = BooleanVar(
            value=self.settings.get("logs_reverse_mode", False)
        )

        # Smart Message Cache System
        self.message_cache = (
            {}
        )  # {message_hash: {'text': str, 'speaker': str, 'timestamp': float, 'bubble_index': int}}
        self.last_message_hash = None
        self.enable_smart_replacement = True

        # Font — โหลดจาก settings โดยตรง (ไม่ผ่าน FontManager)
        self.current_font_family = self.settings.get("font", FONT_FAMILY)
        logs_ui = self.settings.get("logs_ui") or {}
        self.current_font_size = int(logs_ui.get("font_size", 16))

        # Initialize UI components
        self.setup_ui()
        self.load_settings()
        self.root.withdraw()
        # ยกเลิก rounded corners สำหรับ flat design
        # self.root.after(100, self.apply_rounded_corners_to_ui)

        logging.info("✅ Modern Chat Logs initialized with Smart Cache System!")
        logging.info(f"Initial geometry: {self.root.geometry()}")
        logging.info(
            f"Smart Replacement: {'เปิด' if self.enable_smart_replacement else 'ปิด'}"
        )
        logging.info(
            f"Font: {self.current_font_family}, Size: {self.current_font_size}"
        )
        logging.info(f"_is_first_show: {self._is_first_show}")

    def update_font_settings(self, font_name: str, font_size: int):
        """Public API — เรียกจาก MBB.apply_font_with_target() เมื่อ target=logs หรือ both"""
        self.current_font_family = font_name
        self.current_font_size = font_size
        self._update_all_fonts(font_name)
        self._update_font_display()
        # บันทึกลง logs_ui เพื่อให้ persist ข้ามการ restart
        self.settings.set_logs_settings(font_family=font_name, font_size=font_size)
        logging.info(f"🔤 TranslatedLogs font updated: {font_name} {font_size}pt")

    def hide_window(self):
        # บันทึกตำแหน่งสุดท้ายก่อนซ่อน (ถ้าอยู่ในสถานะ lock)
        if self.is_position_locked:
            self.locked_geometry = self.root.geometry()
            self.save_locked_position()
            print(
                f"Lock mode: Saved final position before hiding: {self.locked_geometry}"
            )
        else:
            # UNLOCK mode: รีเซ็ทการบันทึกตำแหน่งเพื่อให้แสดงที่ริมขวาสุดเสมอ
            logging.info("UNLOCK mode: clearing position data")
            self.settings.clear_logs_position_cache()
            self._is_first_show = True  # บังคับให้ใช้ logic การแสดงใหม่

        self.root.withdraw()
        self.is_visible = False

        # Call callback to notify main UI
        if self.on_close_callback:
            try:
                self.on_close_callback()
                logging.info("Called on_close_callback to notify main UI.")
            except Exception as e:
                logging.error(f"Error executing on_close_callback: {e}")

    def setup_ui(self):
        """Create main UI with chat interface - flat design"""
        self.root.title("Conversation History")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)

        self.content_frame = tk.Frame(
            self.root, bg=appearance_manager.bg_color, bd=0, highlightthickness=0
        )
        self.content_frame.pack(fill=tk.BOTH, expand=True)

        # Setup UI components in order
        # หมายเหตุ: bottom_controls ต้องเรียกหลัง chat_area เพื่อให้ z-order สูงกว่า
        # (ใน Tkinter widget ที่สร้างทีหลัง = อยู่บนสุด, place() จึงมองเห็นได้)
        self.setup_header()
        self.setup_chat_area()
        self.setup_bottom_controls()

        self.setup_resize_handle()
        self.setup_bindings()

    def setup_header(self):
        """Create header with font size controls"""
        header_frame = tk.Frame(
            self.content_frame, bg=appearance_manager.bg_color, height=35
        )
        header_frame.pack(side=tk.TOP, fill=tk.X, pady=(0, 5))
        header_frame.pack_propagate(False)

        # pack RIGHT ก่อน LEFT เพื่อให้ controls_frame ได้พื้นที่เสมอ
        controls_frame = tk.Frame(header_frame, bg=appearance_manager.bg_color)
        controls_frame.pack(side=tk.RIGHT, padx=8)

        self.title_label = tk.Label(
            header_frame,
            text="💬 บทสนทนา",
            font=(FONT_FAMILY, 10, "bold"),
            fg="#38bdf8",
            bg=appearance_manager.bg_color,
        )
        self.title_label.pack(side=tk.LEFT, padx=(8, 4), pady=8)

        hide_btn = tk.Button(
            controls_frame,
            text="✕",
            command=self.hide_window,
            font=("Tahoma", 10, "bold"),
            fg="#ff6b6b",
            bg=appearance_manager.bg_color,
            bd=0,
            padx=6,
            pady=2,
            cursor="hand2",
            highlightthickness=0,
            activebackground="#ff6b6b",
            activeforeground="white",
        )
        hide_btn.pack(side=tk.RIGHT, padx=(8, 0))

        def on_hide_enter(e):
            hide_btn.configure(bg="#ff6b6b", fg="white")

        def on_hide_leave(e):
            hide_btn.configure(bg=appearance_manager.bg_color, fg="#ff6b6b")

        hide_btn.bind("<Enter>", on_hide_enter)
        hide_btn.bind("<Leave>", on_hide_leave)

        font_frame = tk.Frame(controls_frame, bg=appearance_manager.bg_color)
        font_frame.pack(side=tk.LEFT, padx=(0, 5))

        font_minus_btn = tk.Button(
            font_frame,
            text="−",
            command=self._decrease_font_size,
            font=(FONT_FAMILY, 14, "bold"),
            fg=appearance_manager.fg_color,
            bg=appearance_manager.bg_color,
            bd=0,
            padx=6,
            pady=0,
            cursor="hand2",
            width=2,
            highlightthickness=0,
            activebackground=appearance_manager.darken_color(
                appearance_manager.bg_color, 0.3
            ),
            activeforeground="#B0B0B0",
        )
        font_minus_btn.pack(side=tk.LEFT, padx=(0, 1))
        self._add_hover_effect(font_minus_btn)

        self.font_size_label = tk.Label(
            font_frame,
            text=str(self.current_font_size),
            font=(FONT_FAMILY, 9),
            fg=appearance_manager.get_theme_color("text_dim", "#888888"),
            bg=appearance_manager.bg_color,
            width=3,
        )
        self.font_size_label.pack(side=tk.LEFT, padx=1)

        font_plus_btn = tk.Button(
            font_frame,
            text="+",
            command=self._increase_font_size,
            font=(FONT_FAMILY, 12, "bold"),
            fg=appearance_manager.fg_color,
            bg=appearance_manager.bg_color,
            bd=0,
            padx=6,
            pady=0,
            cursor="hand2",
            width=2,
            highlightthickness=0,
            activebackground=appearance_manager.darken_color(
                appearance_manager.bg_color, 0.3
            ),
            activeforeground="#B0B0B0",
        )
        font_plus_btn.pack(side=tk.LEFT, padx=(1, 0))
        self._add_hover_effect(font_plus_btn)

        self._bind_drag_to_widget(header_frame)
        self._bind_drag_to_widget(self.title_label)
        self._bind_drag_to_widget(font_frame)
        self._bind_drag_to_widget(self.font_size_label)

    def _add_hover_effect(self, button):
        """Add hover effect to button"""

        def on_enter(e):
            button.configure(
                bg=appearance_manager.darken_color(appearance_manager.bg_color, 0.3),
                fg="#B0B0B0",
            )

        def on_leave(e):
            button.configure(
                bg=appearance_manager.bg_color, fg=appearance_manager.fg_color
            )

        button.bind("<Enter>", on_enter)
        button.bind("<Leave>", on_leave)

    def _increase_font_size(self):
        """Increase font size by 1pt (max 28pt)"""
        if self.current_font_size < 28:
            self.current_font_size += 1
            self._update_all_fonts()
            self._update_font_display()
            self._sync_font_to_settings()

    def _decrease_font_size(self):
        """Decrease font size by 1pt (min 10pt)"""
        if self.current_font_size > 10:
            self.current_font_size -= 1
            self._update_all_fonts()
            self._update_font_display()
            self._sync_font_to_settings()

    def _sync_font_to_settings(self):
        """Persist logs font to settings and sync FontPanel if open."""
        self.settings.set_logs_settings(
            font_family=self.current_font_family,
            font_size=self.current_font_size,
        )
        # Sync FontPanel ถ้าเปิดอยู่และ target=logs
        try:
            sp = getattr(self.main_app, "settings_ui", None) if self.main_app else None
            fp = getattr(sp, "_font_panel", None) if sp else None
            if fp and fp.isVisible() and fp._target_mode == "logs":
                fp._size_value = self.current_font_size
                fp._size_label.setText(str(self.current_font_size))
                fp._update_preview()
        except Exception:
            pass

    def _update_all_fonts(self, font_family_override=None):
        """Update fonts smartly - only repack if wrapping changed significantly"""
        try:
            # ใช้ font family ที่กำหนด หรือใช้ current font family
            font_family = font_family_override or self.current_font_family

            logging.info(f"🔄 _update_all_fonts called with: {font_family_override}")
            logging.info(f"📝 Using font family: {font_family}")
            logging.info(f"📊 Total bubbles to update: {len(self.bubble_list)}")

            # Update font size for all bubbles
            for i, bubble in enumerate(self.bubble_list):
                bubble.update_font_size(self.current_font_size, font_family)
                if i < 3:  # Log first 3 bubbles
                    logging.info(f"   Updated bubble {i+1} with font: {font_family}")

            # Check if any bubble wrapping changed significantly
            needs_repack = False
            for bubble in self.bubble_list:
                if bubble.check_wrap_changed():
                    needs_repack = True
                    break

            if needs_repack:
                logging.info(
                    "Font change caused significant layout change - repacking bubbles"
                )
                self.root.after(20, self._repack_bubbles)
            else:
                logging.info("Font updated without layout changes - no repack needed")

        except Exception as e:
            logging.error(f"Error updating fonts: {e}")
            import traceback

            traceback.print_exc()

    def _update_font_display(self):
        """Update font size display"""
        if hasattr(self, "font_size_label"):
            self.font_size_label.config(text=str(self.current_font_size))

    def _bind_drag_to_widget(self, widget):
        """Add drag binding to widget"""
        widget.bind("<Button-1>", self.start_move)
        widget.bind("<B1-Motion>", self.do_move)
        widget.bind("<ButtonRelease-1>", self.stop_move)

    def setup_chat_area(self):
        """สร้างพื้นที่ chat พร้อม custom scrollbar และ mouse wheel - flat design"""
        chat_frame = tk.Frame(self.content_frame, bg=appearance_manager.bg_color)
        chat_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(
            chat_frame, bg=appearance_manager.bg_color, highlightthickness=0, bd=0
        )
        self.setup_custom_scrollbar(chat_frame)
        self.scrollable_frame = tk.Frame(self.canvas, bg=appearance_manager.bg_color)
        self.canvas.configure(yscrollcommand=self.scrollbar_update)

        self.scrollbar_canvas.pack(side="right", fill="y", padx=(2, 0))
        self.canvas.pack(side="left", fill="both", expand=True)

        self.canvas_frame_id = self.canvas.create_window(
            0, 0, window=self.scrollable_frame, anchor="nw"
        )

        self.scrollable_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        self.setup_mouse_wheel_support()

        self._bind_drag_to_widget(chat_frame)
        self._bind_drag_to_widget(self.canvas)
        self._bind_drag_to_widget(self.scrollable_frame)

    def setup_mouse_wheel_support(self):
        """เพิ่ม mouse wheel support ให้ครบถ้วน"""
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.scrollable_frame.bind("<MouseWheel>", self._on_mousewheel)
        self.scrollbar_canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.content_frame.bind("<MouseWheel>", self._on_mousewheel)

        def propagate_wheel(event):
            self._on_mousewheel(event)

        self.root.bind("<MouseWheel>", propagate_wheel)

    def setup_custom_scrollbar(self, parent):
        """สร้าง custom scrollbar สีเทาเข้มแบบโค้งมน"""
        scrollbar_width = 8
        self.scrollbar_canvas = tk.Canvas(
            parent,
            width=scrollbar_width,
            height=100,
            bg=appearance_manager.bg_color,
            highlightthickness=0,
            bd=0,
        )

        thumb_color = "#555555"
        self.scrollbar_thumb = self.scrollbar_canvas.create_rectangle(
            1, 0, scrollbar_width - 1, 50, fill=thumb_color, outline="", tags=("thumb",)
        )

        self.scrollbar_canvas.bind("<Button-1>", self._on_scrollbar_click)
        self.scrollbar_canvas.bind("<B1-Motion>", self._on_scrollbar_drag)

        def on_scroll_enter(e):
            self.scrollbar_canvas.itemconfig(self.scrollbar_thumb, fill="#777777")

        def on_scroll_leave(e):
            self.scrollbar_canvas.itemconfig(self.scrollbar_thumb, fill=thumb_color)

        self.scrollbar_canvas.bind("<Enter>", on_scroll_enter)
        self.scrollbar_canvas.bind("<Leave>", on_scroll_leave)

    def scrollbar_update(self, start, end):
        """อัพเดท custom scrollbar"""
        try:
            start, end = float(start), float(end)
            canvas_height = self.scrollbar_canvas.winfo_height()
            thumb_height = max(20, canvas_height * (end - start))
            y_position = start * canvas_height
            self.scrollbar_canvas.coords(
                self.scrollbar_thumb, 1, y_position, 7, y_position + thumb_height
            )
            self.scrollbar_canvas.itemconfig(
                self.scrollbar_thumb,
                state="normal" if not (start <= 0.01 and end >= 0.99) else "hidden",
            )
        except Exception as e:
            logging.error(f"Error updating scrollbar: {e}")

    def _on_scrollbar_click(self, event):
        """จัดการการคลิก scrollbar"""
        try:
            self.canvas.yview_moveto(event.y / self.scrollbar_canvas.winfo_height())
        except Exception as e:
            logging.error(f"Error in scrollbar click: {e}")

    def _on_scrollbar_drag(self, event):
        """จัดการการลาก scrollbar"""
        try:
            self.canvas.yview_moveto(
                max(0, min(1, event.y / self.scrollbar_canvas.winfo_height()))
            )
        except Exception as e:
            logging.error(f"Error in scrollbar drag: {e}")

    def setup_bottom_controls(self):
        """สร้าง controls ด้านล่างพร้อมไอคอน — ซ่อนเริ่มต้น, แสดงเมื่อ hover"""
        bottom_frame = tk.Frame(
            self.content_frame, bg=appearance_manager.bg_color, height=30
        )
        # ไม่ pack/place เริ่มต้น — ใช้ place_forget/place ผ่าน hover events
        bottom_frame.pack_propagate(False)
        self._bottom_frame = bottom_frame
        self._controls_visible = False

        left_frame = tk.Frame(bottom_frame, bg=appearance_manager.bg_color)
        left_frame.pack(side=tk.LEFT, padx=5)

        self.setup_lock_button(left_frame)  # เพิ่มปุ่ม lock ก่อน
        self.setup_transparency_button(left_frame)
        self.setup_reverse_button(left_frame)
        self.setup_smart_button(left_frame)  # เพิ่มปุ่ม smart replacement
        self.setup_font_button(left_frame)  # เพิ่มปุ่ม font manager

        self._bind_drag_to_widget(bottom_frame)
        self._bind_drag_to_widget(left_frame)

    def setup_lock_button(self, parent):
        """สร้างปุ่ม lock/unlock ตำแหน่ง พร้อมไอคอน"""
        try:
            # โหลดไฟล์ไอคอน
            self.unlock_icon = AssetManager.load_icon("unlock.png", (16, 16))
            self.lock_icon = AssetManager.load_icon("lock.png", (16, 16))

            # สร้างปุ่ม (เริ่มต้นเป็น unlock)
            if self.unlock_icon:
                lock_btn = tk.Button(
                    parent,
                    image=self.unlock_icon,
                    command=self.toggle_position_lock,
                    bg=appearance_manager.bg_color,
                    bd=0,
                    padx=4,
                    cursor="hand2",
                    highlightthickness=0,
                )
            else:
                # Fallback เป็นข้อความ
                lock_btn = tk.Button(
                    parent,
                    text="🔓",
                    command=self.toggle_position_lock,
                    font=("Arial", 11),
                    fg="#888888",
                    bg=appearance_manager.bg_color,
                    bd=0,
                    padx=4,
                    cursor="hand2",
                    highlightthickness=0,
                )

            lock_btn.pack(side=tk.LEFT, padx=2)
            self.lock_button = lock_btn
            self._add_hover_effect(lock_btn)

            # Update button state ตาม settings ที่โหลดมา
            self._update_lock_button_state()

        except Exception as e:
            logging.error(f"Error setting up lock button: {e}")
            # Fallback button
            lock_btn = tk.Button(
                parent,
                text="🔓",
                command=self.toggle_position_lock,
                font=("Arial", 11),
                fg="#888888",
                bg=appearance_manager.bg_color,
                bd=0,
                padx=4,
                cursor="hand2",
            )
            lock_btn.pack(side=tk.LEFT, padx=2)
            self.lock_button = lock_btn

            # Update button state สำหรับ fallback button ด้วย
            self._update_lock_button_state()

    def _update_lock_button_state(self):
        """Update lock button appearance ตามสถานะปัจจุบัน"""
        try:
            if not hasattr(self, 'lock_button'):
                return

            if self.is_position_locked:
                # Locked state
                if hasattr(self, "lock_icon") and self.lock_icon:
                    self.lock_button.config(image=self.lock_icon)
                else:
                    self.lock_button.config(text="🔒", fg="#FF6B6B")

            else:
                # Unlocked state
                if hasattr(self, "unlock_icon") and self.unlock_icon:
                    self.lock_button.config(image=self.unlock_icon)
                else:
                    self.lock_button.config(text="🔓", fg="#888888")

        except Exception as e:
            logging.error(f"Error updating lock button state: {e}")

    def toggle_position_lock(self):
        """Toggle การ lock/unlock ตำแหน่ง Log UI - ปรับปรุงให้ปลอดภัย"""
        try:
            self.is_position_locked = not self.is_position_locked

            if self.is_position_locked:
                # Lock: บันทึกตำแหน่งปัจจุบันทันที
                current_geometry = self.root.geometry()
                self.locked_geometry = current_geometry

                # บันทึกลง settings ทันที
                self.settings.set_logs_settings(
                    width=self.root.winfo_width(),
                    height=self.root.winfo_height(),
                    x=self.root.winfo_x(),
                    y=self.root.winfo_y(),
                )
                self.settings.set("logs_position_locked", True)
                self.settings.set("logs_locked_geometry", current_geometry)

                logging.info(f"Lock: position saved {current_geometry}")

            else:
                # Unlock: เคลียร์ flag เท่านั้น ไม่ปรับตำแหน่งทันที
                self.locked_geometry = None
                self.settings.set("logs_position_locked", False)
                self.settings.set("logs_locked_geometry", "")  # เคลียร์
                self.settings.clear_logs_position_cache()  # เคลียร์ cache หลัก

                logging.info("Position unlocked")

                # ไม่เรียก _apply_smart_positioning() ทันที เพื่อป้องกัน UI หาย
                # smart positioning จะทำงานในรอบถัดไปที่เปิด UI

            # Update UI appearance
            self._update_lock_button_state()

        except Exception as e:
            logging.error(f"Error toggling position lock: {e}")

    def setup_reverse_button(self, parent):
        """สร้างปุ่ม reverse พร้อมไอคอน swap.png"""
        try:
            self.swap_icon = AssetManager.load_icon("swap.png", (16, 16))
            if self.swap_icon:
                reverse_btn = tk.Button(
                    parent,
                    image=self.swap_icon,
                    command=self.toggle_reverse_mode,
                    bg=appearance_manager.bg_color,
                    bd=0,
                    padx=4,
                    cursor="hand2",
                    highlightthickness=0,
                )
            else:
                reverse_btn = tk.Button(
                    parent,
                    text="↕",
                    command=self.toggle_reverse_mode,
                    font=("Arial", 11),
                    fg=self._get_reverse_color(),
                    bg=appearance_manager.bg_color,
                    bd=0,
                    padx=4,
                    cursor="hand2",
                    highlightthickness=0,
                )
            reverse_btn.pack(side=tk.LEFT, padx=2)
            self.reverse_button = reverse_btn
            self._add_hover_effect(reverse_btn)
        except Exception as e:
            logging.error(f"Error setting up reverse button: {e}")
            reverse_btn = tk.Button(
                parent,
                text="↕",
                command=self.toggle_reverse_mode,
                font=("Arial", 11),
                fg=self._get_reverse_color(),
                bg=appearance_manager.bg_color,
                bd=0,
                padx=4,
                cursor="hand2",
            )
            reverse_btn.pack(side=tk.LEFT, padx=2)
            self.reverse_button = reverse_btn

    def setup_smart_button(self, parent):
        """สร้างปุ่ม toggle smart replacement mode - minimal flat design"""
        try:
            # เริ่มต้นด้วยสถานะปัจจุบัน
            smart_btn = tk.Button(
                parent,
                text=self._get_smart_icon(),
                command=self.toggle_smart_replacement,
                font=("Arial", 10, "bold"),
                fg=self._get_smart_color_flat(),
                bg=appearance_manager.bg_color,
                bd=1,
                padx=6,
                pady=2,
                cursor="hand2",
                highlightthickness=0,
                relief="solid",
                highlightcolor="#666666",
                highlightbackground="#666666",
            )
            smart_btn.pack(side=tk.LEFT, padx=2)
            self.smart_button = smart_btn
            self._add_hover_effect(smart_btn)
        except Exception as e:
            logging.error(f"Error setting up smart button: {e}")
            # Fallback button
            smart_btn = tk.Button(
                parent,
                text="S",
                command=self.toggle_smart_replacement,
                font=("Tahoma", 10),
                fg=self._get_smart_color_flat(),
                bg=appearance_manager.bg_color,
                bd=1,
                padx=4,
                cursor="hand2",
                relief="solid",
            )
            smart_btn.pack(side=tk.LEFT, padx=2)
            self.smart_button = smart_btn

    def _get_smart_icon(self):
        """ส่งคืนไอคอนตามสถานะ smart mode"""
        return "ON" if self.enable_smart_replacement else "OFF"

    def _get_smart_color_flat(self):
        """ส่งคืนสีข้อความปุ่ม smart ตามสถานะ - flat design"""
        return "#FFFFFF" if self.enable_smart_replacement else "#888888"

    def setup_font_button(self, parent):
        """สร้างปุ่ม font manager - minimal flat design"""
        try:
            # ใช้ข้อความ "Font" แทนตัว F
            _dim = appearance_manager.get_theme_color("text_dim", "#888888")
            _border = appearance_manager.get_theme_color("border", "#444444")
            font_btn = tk.Button(
                parent,
                text="Font",
                command=self.open_font_manager,
                font=(FONT_FAMILY, 9, "bold"),
                fg=_dim,
                bg=appearance_manager.bg_color,
                bd=1,
                padx=4,
                pady=2,
                cursor="hand2",
                highlightthickness=0,
                relief="solid",
                highlightcolor=_border,
                highlightbackground=_border,
            )
            font_btn.pack(side=tk.LEFT, padx=2)
            self.font_button = font_btn
            self._add_hover_effect(font_btn)
        except Exception as e:
            logging.error(f"Error setting up font button: {e}")
            # Fallback button
            font_btn = tk.Button(
                parent,
                text="Font",
                command=self.open_font_manager,
                font=("Tahoma", 9),
                fg=appearance_manager.get_theme_color("text_dim", "#888888"),
                bg=appearance_manager.bg_color,
                bd=1,
                padx=3,
                cursor="hand2",
                relief="solid",
            )
            font_btn.pack(side=tk.LEFT, padx=2)
            self.font_button = font_btn

    def open_font_manager(self):
        """เปิด FontPanel (PyQt6) ข้างๆ Logs UI"""
        try:
            if not self.main_app:
                logging.warning("open_font_manager: no main_app reference")
                return

            sp = getattr(self.main_app, "settings_ui", None)
            if not sp:
                return

            # pre-set target mode เป็น logs เสมอเมื่อเปิดจาก Logs UI
            self.settings.set("font_target_mode", "logs")

            # เปิด FontPanel (ไม่ใช้ _toggle_font — ป้องกันกรณี panel เปิดอยู่แล้วถูกปิด)
            if hasattr(sp, "_ensure_font_panel"):
                sp._ensure_font_panel()
            fp = getattr(sp, "_font_panel", None)
            if fp:
                fp.reload_target()
                if not fp.isVisible():
                    fp.show()
                fp.raise_()
                fp.activateWindow()
                self._position_font_panel_near_logs(fp)

        except Exception as e:
            logging.error(f"Error opening font manager: {e}")

    def _position_font_panel_near_logs(self, font_panel):
        """วาง FontPanel ข้าง Logs UI — ตรวจจับว่าควรอยู่ซ้ายหรือขวา"""
        try:
            logs_x = self.root.winfo_x()
            logs_y = self.root.winfo_y()
            logs_w = self.root.winfo_width()
            fp_w = font_panel.width() or font_panel.sizeHint().width() or 260
            screen_w = self.root.winfo_screenwidth()
            gap = 8

            # ถ้า logs อยู่ฝั่งขวา → แสดง font panel ทางซ้าย
            if logs_x + logs_w // 2 > screen_w // 2:
                x = logs_x - fp_w - gap
            else:
                x = logs_x + logs_w + gap

            # clamp ไม่ให้ออกนอกจอ
            x = max(0, min(x, screen_w - fp_w))
            font_panel.move(x, logs_y)
        except Exception:
            pass

    def setup_transparency_button(self, parent):
        """สร้างปุ่ม transparency พร้อมไอคอน trans.png"""
        try:
            self.trans_icon = AssetManager.load_icon("trans.png", (16, 16))
            if self.trans_icon:
                trans_btn = tk.Button(
                    parent,
                    image=self.trans_icon,
                    command=self.toggle_transparency,
                    bg=appearance_manager.bg_color,
                    bd=0,
                    padx=4,
                    cursor="hand2",
                    highlightthickness=0,
                )
            else:
                trans_btn = tk.Button(
                    parent,
                    text="👁",
                    command=self.toggle_transparency,
                    font=("Segoe UI Symbol", 12),
                    fg=appearance_manager.fg_color,
                    bg=appearance_manager.bg_color,
                    bd=0,
                    padx=4,
                    cursor="hand2",
                    highlightthickness=0,
                )
            trans_btn.pack(side=tk.LEFT, padx=2)
            self.trans_button = trans_btn
            self._add_hover_effect(trans_btn)
        except Exception as e:
            logging.error(f"Error setting up transparency button: {e}")
            trans_btn = tk.Button(
                parent,
                text="T",
                command=self.toggle_transparency,
                font=("Tahoma", 10),
                fg=appearance_manager.fg_color,
                bg=appearance_manager.bg_color,
                bd=0,
                padx=4,
                cursor="hand2",
            )
            trans_btn.pack(side=tk.LEFT, padx=2)

    def setup_resize_handle(self):
        """สร้าง resize handle — ซ่อนเริ่มต้น, แสดงเมื่อ hover ตรงตำแหน่ง"""
        bg = appearance_manager.bg_color
        try:
            self.resize_icon = AssetManager.load_icon("resize.png", (16, 16))

            # สร้าง blank icon สำหรับซ่อน (16×16 transparent)
            self._resize_blank_icon = None
            try:
                from PIL import Image, ImageTk
                _blank = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
                self._resize_blank_icon = ImageTk.PhotoImage(_blank)
            except Exception:
                pass

            if self.resize_icon:
                self.resize_handle = tk.Label(
                    self.content_frame,
                    image=self._resize_blank_icon or self.resize_icon,
                    bg=bg,
                    cursor="arrow",
                )
            else:
                self.resize_handle = tk.Label(
                    self.content_frame,
                    text="⋮⋮",
                    font=("Arial", 8),
                    fg=bg,  # ซ่อน — fg = bg เริ่มต้น
                    bg=bg,
                    cursor="arrow",
                )
            self.resize_handle.place(relx=1.0, rely=1.0, anchor="se", x=-1, y=-1)
            self.resize_handle.bind("<Double-1>", lambda e: self.toggle_lock_ui())
            self.resize_handle.bind("<Button-1>", self.start_resize)
            self.resize_handle.bind("<B1-Motion>", self.do_resize)
            self.resize_handle.bind("<ButtonRelease-1>", self.stop_resize)

            # แสดง/ซ่อนเมื่อ hover ตรงตำแหน่ง icon
            def _show_handle(e):
                if self.resize_icon and self._resize_blank_icon:
                    self.resize_handle.config(image=self.resize_icon, cursor="sizing")
                else:
                    self.resize_handle.config(
                        fg=appearance_manager.darken_color(
                            appearance_manager.fg_color, 0.6
                        ),
                        cursor="sizing",
                    )

            def _hide_handle(e):
                if self.resize_icon and self._resize_blank_icon:
                    self.resize_handle.config(
                        image=self._resize_blank_icon, cursor="arrow"
                    )
                else:
                    self.resize_handle.config(fg=bg, cursor="arrow")

            self.resize_handle.bind("<Enter>", _show_handle)
            self.resize_handle.bind("<Leave>", _hide_handle)
        except Exception as e:
            logging.error(f"Error setting up resize handle: {e}")

    def setup_bindings(self):
        """Setup event bindings สำหรับการลากหน้าต่าง และการ resize"""
        self._bind_drag_to_widget(self.content_frame)

        # เพิ่ม Configure event handler สำหรับการ track ขนาดหน้าต่าง
        self.root.bind("<Configure>", self._on_window_configure)
        logging.info("✅ Enhanced drag bindings setup complete!")

        # Hover polling — แสดง/ซ่อน bottom controls ตาม mouse position
        self.root.after(200, self._start_hover_check)

    def _is_mouse_over_window(self) -> bool:
        """ตรวจสอบว่า mouse อยู่บน window หรือไม่"""
        try:
            px = self.root.winfo_pointerx()
            py = self.root.winfo_pointery()
            widget_at = self.root.winfo_containing(px, py)
            if not widget_at:
                return False
            return widget_at.winfo_toplevel() == self.root
        except Exception:
            return False

    def _start_hover_check(self):
        """Poll 120ms — แสดง/ซ่อน bottom bar ด้วย place/place_forget"""
        try:
            if not self.root.winfo_exists():
                return
            hovering = self._is_mouse_over_window()
            if hovering != self._controls_visible:
                self._controls_visible = hovering
                if hovering:
                    self._bottom_frame.place(
                        relx=0, rely=1.0, anchor="sw", relwidth=1.0, height=30
                    )
                else:
                    self._bottom_frame.place_forget()
        except Exception:
            pass
        finally:
            try:
                self.root.after(120, self._start_hover_check)
            except Exception:
                pass

    def _get_reverse_color(self):
        return "#00BFFF" if self.reverse_mode.get() else appearance_manager.fg_color

    def _on_window_configure(self, event):
        """จัดการการเปลี่ยนขนาดหน้าต่าง - บันทึกขนาดใหม่เมื่อ lock"""
        try:
            # ตรวจสอบว่าเป็น event ของ root window (ไม่ใช่ child widgets)
            if event.widget != self.root:
                return

            # บันทึกขนาดและตำแหน่งใหม่เมื่ออยู่ในสถานะ lock
            if self.is_position_locked:
                current_time = time.time()

                # Throttle การบันทึก (ไม่บันทึกบ่อยเกินไป)
                if current_time - self._last_save_time > 0.5:
                    current_geometry = self.root.geometry()
                    self.locked_geometry = current_geometry

                    # บันทึกลง settings
                    self.settings.set_logs_settings(
                        width=self.root.winfo_width(),
                        height=self.root.winfo_height(),
                        x=self.root.winfo_x(),
                        y=self.root.winfo_y(),
                    )
                    self.settings.set("logs_locked_geometry", current_geometry)

                    self._last_save_time = current_time
                    logging.debug(f"Lock: size saved {current_geometry}")

        except Exception as e:
            logging.error(f"Error in window configure handler: {e}")

    def _on_frame_configure(self, event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event=None):
        canvas_width = self.canvas.winfo_width()
        self.canvas.itemconfig(self.canvas_frame_id, width=canvas_width)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _generate_message_hash(self, text, speaker=None):
        """สร้าง hash สำหรับข้อความเพื่อใช้เป็น cache key"""
        # ใช้ text + speaker + timestamp (ปัดเศษ 10 วินาที) เป็น key
        timestamp_rounded = int(time.time() // 10) * 10
        hash_source = f"{text.strip()}_{speaker or ''}_{timestamp_rounded}"
        return hashlib.md5(hash_source.encode()).hexdigest()[:12]

    def _is_likely_retranslation(self, new_text, cached_text):
        """ตรวจสอบว่าเป็นการแปลซ้ำหรือไม่"""
        if not cached_text or not new_text:
            return False

        # ลบ speaker prefix ออกเพื่อเปรียบเทียบเฉพาะข้อความ
        new_content = new_text.split(": ", 1)[-1] if ": " in new_text else new_text
        cached_content = (
            cached_text.split(": ", 1)[-1] if ": " in cached_text else cached_text
        )

        # Debug log
        logging.info(
            f"🔍 Comparing: NEW='{new_content[:50]}...' vs CACHED='{cached_content[:50]}...'"
        )

        # ถ้าความยาวใกล้เคียงกัน และมีคำร่วมกัน = น่าจะเป็นการแปลซ้ำ
        len_ratio = min(len(new_content), len(cached_content)) / max(
            len(new_content), len(cached_content)
        )
        logging.info(f"🔍 Length ratio: {len_ratio:.2f}")

        if len_ratio > 0.3:  # ลดจาก 0.4 เป็น 0.3 เพื่อให้หลวมกว่า
            # ตรวจสอบคำที่ซ้ำกัน
            words_new = set(new_content.lower().split())
            words_cached = set(cached_content.lower().split())
            if len(words_new) > 0 and len(words_cached) > 0:
                common_ratio = len(words_new & words_cached) / max(
                    len(words_new), len(words_cached)
                )
                logging.info(f"🔍 Common words ratio: {common_ratio:.2f}")
                result = common_ratio > 0.2  # ลดจาก 0.25 เป็น 0.2 เพื่อให้หลวมกว่า
                logging.info(f"🔍 Is retranslation: {result}")
                return result

        logging.info(f"🔍 Is retranslation: False (length ratio too low)")
        return False

    def _replace_last_message(self, new_text, is_lore_text=False):
        """แทนที่ข้อความล่าสุดด้วยการแปลใหม่"""
        if not self.bubble_list:
            logging.warning("🔄 Cannot replace: no bubbles in list")
            return False

        try:
            logging.info(f"🔄 Replacing last message with: '{new_text[:50]}...'")

            # ลบ bubble ล่าสุด
            last_bubble = self.bubble_list[-1]
            last_bubble.destroy()
            self.bubble_list.pop()

            # เพิ่มข้อความใหม่
            self._add_new_message_bubble(new_text)

            # แสดง replacement indicator
            self._show_replacement_indicator()

            logging.info(f"✅ Successfully replaced last message")
            return True

        except Exception as e:
            logging.error(f"Error replacing message: {e}")
            return False

    def _add_new_message_bubble(self, text, is_lore_text=False):
        """เพิ่ม bubble ใหม่สำหรับข้อความ"""
        # Parse message content
        speaker, message, speaker_color = self._parse_message(text)
        bubble_color = self._get_bubble_color(speaker)
        max_bubble_width = self.scrollable_frame.winfo_width() - 20

        # Create new bubble
        bubble = LightweightChatBubble(
            self.scrollable_frame,
            speaker,
            message,
            speaker_color,
            bubble_color,
            self.current_font_size,
            max_bubble_width,
            self.current_font_family,
        )

        # Add to list
        self.bubble_list.append(bubble)

        # Pack new bubble
        self._pack_new_bubble(bubble)

        # Manage bubble limit
        self._limit_bubbles()

        # Smooth scroll to latest
        self.root.after(50, self._smooth_scroll_to_latest)

        # Update status
        self._update_status()

    def _show_replacement_indicator(self):
        """No-op — status label ถูกลบออกแล้ว"""
        pass

    # === CORE MESSAGE HANDLING - Enhanced with Smart Cache ===

    def add_message(self, text, is_force_retranslation=False, is_lore_text=False):
        """เพิ่มข้อความใหม่ด้วย Smart Cache System ⭐"""
        if not text or not text.strip():
            return
        try:
            # Debug log
            logging.info(
                f"🔄 add_message called: force={is_force_retranslation}, smart_enabled={self.enable_smart_replacement}"
            )

            # ตรวจสอบว่าเป็นการแปลซ้ำหรือไม่
            if (
                self.enable_smart_replacement
                and is_force_retranslation
                and self.last_message_hash
                and self.last_message_hash in self.message_cache
            ):

                cached_data = self.message_cache[self.last_message_hash]

                # ถ้าเป็นการแปลซ้ำของข้อความล่าสุด
                if self._is_likely_retranslation(text, cached_data["text"]):
                    logging.info(f"🔄 Detected retranslation, replacing last message")
                    if self._replace_last_message(text, is_lore_text=is_lore_text):
                        # อัปเดต cache ด้วยข้อความใหม่
                        self.message_cache[self.last_message_hash]["text"] = text
                        self.message_cache[self.last_message_hash][
                            "timestamp"
                        ] = time.time()
                        return
                else:
                    logging.info(
                        f"🔄 Force translate but not similar enough, adding new message"
                    )

            # ถ้าไม่ใช่ retranslation ให้เพิ่มข้อความใหม่
            self._add_new_message_with_cache(text, is_lore_text=is_lore_text)

        except Exception as e:
            logging.error(f"Error in smart add_message: {e}")
            # Fallback: ใช้วิธีเดิม
            self._add_message_fallback(text)

    def _add_new_message_with_cache(self, text, is_lore_text=False):
        """เพิ่มข้อความใหม่พร้อมบันทึกลง cache"""
        # สร้าง hash สำหรับข้อความ
        speaker, message, speaker_color = self._parse_message(text)
        message_hash = self._generate_message_hash(text, speaker)

        # เพิ่ม bubble
        self._add_new_message_bubble(text)

        # บันทึกลง cache
        self.message_cache[message_hash] = {
            "text": text,
            "speaker": speaker,
            "timestamp": time.time(),
            "bubble_index": len(self.bubble_list) - 1,
        }
        self.last_message_hash = message_hash

        logging.info(
            f"✅ Added message with cache - total: {len(self.bubble_list)} bubbles"
        )

    def _add_message_fallback(self, text):
        """วิธีเดิม - ใช้เมื่อระบบใหม่มีปัญหา"""
        # Parse message content
        speaker, message, speaker_color = self._parse_message(text)
        bubble_color = self._get_bubble_color(speaker)
        max_bubble_width = self.scrollable_frame.winfo_width() - 20

        # Create new bubble
        bubble = LightweightChatBubble(
            self.scrollable_frame,
            speaker,
            message,
            speaker_color,
            bubble_color,
            self.current_font_size,
            max_bubble_width,
            self.current_font_family,
        )

        # Add to list
        self.bubble_list.append(bubble)

        # Pack new bubble intelligently (without repacking others)
        self._pack_new_bubble(bubble)

        # Manage bubble limit
        self._limit_bubbles()

        # Smooth scroll to latest with animation
        self.root.after(50, self._smooth_scroll_to_latest)

        # Update status
        self._update_status()

        logging.info(
            f"✅ Added message (fallback) - total: {len(self.bubble_list)} bubbles"
        )

    def _pack_new_bubble(self, bubble):
        """Pack new bubble intelligently based on current mode - key improvement! 🚀"""
        # Calculate dynamic spacing based on font size
        dynamic_pady = max(5, int(self.current_font_size * 0.8))
        pack_options = {"fill": tk.X, "pady": (0, dynamic_pady), "padx": (8, 8)}

        if self.reverse_mode.get():
            # Reverse mode: pack at the top
            if len(self.bubble_list) > 1:
                # Pack before the previous last bubble (which is now second-to-last)
                previous_bubble = self.bubble_list[-2]
                bubble.pack(before=previous_bubble, **pack_options)
            else:
                # First bubble - pack normally
                bubble.pack(**pack_options)
        else:
            # Normal mode: pack at the bottom (default)
            bubble.pack(**pack_options)

        logging.info(
            f"Packed new bubble in {'reverse' if self.reverse_mode.get() else 'normal'} mode"
        )

    def _smooth_scroll_to_latest(self):
        """Smooth animated scroll to latest message ✨"""
        # Cancel any existing animation
        if self._scroll_animation_id:
            self.root.after_cancel(self._scroll_animation_id)
            self._scroll_animation_id = None

        # Update canvas first
        self.canvas.update_idletasks()

        # Determine target position
        target_y = 1.0 if not self.reverse_mode.get() else 0.0

        # Get current position
        current_view = self.canvas.yview()
        current_y = current_view[1] if not self.reverse_mode.get() else current_view[0]

        # Skip animation if already at target
        if abs(current_y - target_y) < 0.01:
            return

        # Calculate smooth animation steps
        steps = 8
        step_size = (target_y - current_y) / steps

        def animate_scroll(step=0):
            if step < steps:
                new_y = current_y + (step_size * (step + 1))

                # Apply smooth easing curve
                progress = (step + 1) / steps
                eased_progress = 1 - (1 - progress) ** 3  # ease-out cubic
                final_y = current_y + (target_y - current_y) * eased_progress

                if not self.reverse_mode.get():
                    self.canvas.yview_moveto(final_y - 0.1)
                else:
                    self.canvas.yview_moveto(final_y)

                # Schedule next animation frame
                self._scroll_animation_id = self.root.after(
                    25, lambda: animate_scroll(step + 1)
                )
            else:
                # Final position - ensure we're exactly at target
                self.canvas.yview_moveto(
                    target_y if self.reverse_mode.get() else target_y - 0.1
                )
                self._scroll_animation_id = None

        # Start animation
        animate_scroll()

    def _parse_message(self, text, is_lore_text=False):
        """แยกแยะข้อความและกำหนดสีของ Speaker"""

        # --- [ โค้ดที่แก้ไขใหม่ ] ---
        # ถ้าได้รับสัญญาณว่าเป็น Lore Text ให้จัดการเป็นกรณีพิเศษทันที
        if is_lore_text:
            speaker = "Lore"
            message = text.strip()
            speaker_color = "#a0a0a0"  # สีเทาอ่อนสำหรับ Lore
            return speaker, message, speaker_color
        # --- [ จบส่วนที่แก้ไข ] ---

        # ถ้าไม่ใช่ Lore Text ให้ใช้ Logic เดิมในการแยกชื่อ
        speaker, message, speaker_color = None, text.strip(), "#38bdf8"
        if "???" in text.split(":", 1)[0]:
            parts = text.split(":", 1)
            speaker, message, speaker_color = (
                parts[0].strip(),
                parts[1].strip() if len(parts) > 1 else "",
                "#a855f7",
            )
        elif "คุณจะพูดว่าอย่างไร?" in text or "What will you say?" in text:
            parts = (
                text.split("คุณจะพูดว่าอย่างไร?", 1)
                if "คุณจะพูดว่าอย่างไร?" in text
                else text.split("What will you say?", 1)
            )
            speaker, message, speaker_color = (
                "คุณจะพูดว่าอย่างไร?",
                parts[1].strip() if len(parts) > 1 else "",
                "#FFD700",
            )
        elif ": " in text:
            try:
                speaker_part, message_part = text.split(": ", 1)
                # เพิ่มเงื่อนไขป้องกันการเข้าใจผิดว่าข้อความยาวๆ เป็นชื่อคน
                if len(speaker_part) < 35 and " - " not in speaker_part:
                    speaker, message = speaker_part.strip(), message_part.strip()
            except ValueError:
                pass

        return speaker, message, speaker_color

    def _get_bubble_color(self, speaker):
        """กำหนดสี bubble เป็นสีเดียวกันทั้งหมด"""
        return SINGLE_BUBBLE_COLOR

    def _limit_bubbles(self):
        """จำกัดจำนวน bubbles และ cache อย่างชาญฉลาด"""
        max_bubbles = 100
        if len(self.bubble_list) > max_bubbles:
            bubbles_to_remove = len(self.bubble_list) - max_bubbles
            for old_bubble in self.bubble_list[:bubbles_to_remove]:
                old_bubble.destroy()
            self.bubble_list = self.bubble_list[bubbles_to_remove:]
            logging.info(f"Cleaned up {bubbles_to_remove} old bubbles")

        # evict oldest cache entries เมื่อเกิน MAX_CACHE_SIZE
        if len(self.message_cache) > MAX_CACHE_SIZE:
            sorted_keys = sorted(
                self.message_cache, key=lambda k: self.message_cache[k]["timestamp"]
            )
            for k in sorted_keys[: len(self.message_cache) - MAX_CACHE_SIZE]:
                del self.message_cache[k]

    def _update_status(self):
        """No-op — status label ถูกลบออกแล้ว"""
        pass

    def toggle_reverse_mode(self):
        """สลับ reverse mode - ใช้ full repack เนื่องจากเปลี่ยนลำดับการแสดงผล"""
        self.reverse_mode.set(not self.reverse_mode.get())
        self.settings.set("logs_reverse_mode", self.reverse_mode.get())

        # Update button color if it's text-based
        if hasattr(self.reverse_button, "cget") and self.reverse_button.cget("text"):
            self.reverse_button.config(fg=self._get_reverse_color())

        # Full repack required for mode change
        logging.info(
            f"Toggle reverse mode to: {self.reverse_mode.get()} - performing full repack"
        )
        self._repack_bubbles()

    def _repack_bubbles(self):
        """Full repack - ใช้เฉพาะเมื่อจำเป็น (toggle mode, font wrapping change)"""
        if not self.bubble_list:
            return

        logging.info("Performing full repack of all bubbles")

        # Remove all bubbles from layout
        for bubble in self.bubble_list:
            bubble.pack_forget()

        # Calculate dynamic spacing based on current font size
        dynamic_pady = max(5, int(self.current_font_size * 0.8))
        pack_options = {"fill": tk.X, "pady": (0, dynamic_pady), "padx": (8, 8)}

        # Pack in correct order based on mode
        bubbles_to_pack = (
            reversed(self.bubble_list) if self.reverse_mode.get() else self.bubble_list
        )
        for bubble in bubbles_to_pack:
            bubble.pack(**pack_options)

        # Smooth scroll to appropriate position after repack
        self.root.after(100, self._smooth_scroll_to_latest)

    def toggle_transparency(self):
        """สลับความโปร่งใส 4 ระดับ"""
        next_mode = {"A": "B", "B": "C", "C": "D", "D": "A"}
        self.current_mode = next_mode[self.current_mode]
        alpha = ALPHA_MAP[self.current_mode]
        try:
            if self.is_visible:
                self.root.attributes("-alpha", alpha)
                logging.info(
                    f"Changed transparency to mode {self.current_mode} (alpha: {alpha})"
                )
        except Exception as e:
            logging.error(f"Error setting transparency: {e}")

    # === WINDOW MANAGEMENT ===

    def position_at_right_edge(self, monitor_info):
        """จัดตำแหน่ง LOG UI ที่ริมขวาสุดของจอ สำหรับสถานะ unlock
        
        Args:
            monitor_info (dict): ข้อมูลจอภาพปัจจุบันของ MBB
        """
        try:
            # ข้อมูลจอภาพ
            monitor_width = monitor_info["width"]
            monitor_height = monitor_info["height"]
            monitor_left = monitor_info["left"]
            monitor_top = monitor_info["top"]
            
            window_width = DEFAULT_LOG_WIDTH
            window_height = DEFAULT_LOG_HEIGHT

            # จำกัดขนาดตามหน้าจอ
            max_width = min(window_width, monitor_width - 80)
            max_height = min(window_height, monitor_height - 100)
            
            # ตำแหน่งริมขวาสุด เว้นจากขอบ 100px ตามที่กำหนด
            pos_x = monitor_left + monitor_width - max_width - 100
            pos_y = monitor_top + 100  # เว้นจากขอบบน 100px
            
            geometry = f"{max_width}x{max_height}+{pos_x}+{pos_y}"
            print(f"UNLOCK mode: Positioning LOG UI at right edge: {geometry}")
            
            self.root.geometry(geometry)
            self.root.update_idletasks()
            
        except Exception as e:
            logging.error(f"Error in position_at_right_edge: {e}")
            # Fallback to default positioning
            self.root.geometry(FALLBACK_LOG_GEOMETRY)

    def check_screen_size_and_adjust(self, mbb_side="left", monitor_info=None):
        """ปรับขนาดและตำแหน่งหน้าต่างแบบฉลาด - แสดงที่ขอบจอของอีกฝั่ง

        Args:
            mbb_side (str): ตำแหน่งของ MBB window ('left' หรือ 'right')
            monitor_info (dict): ข้อมูลจอภาพปัจจุบันของ MBB
        """
        try:
            # เมื่อมี mbb_side parameter = บังคับใช้ smart positioning
            use_smart_positioning = mbb_side and mbb_side in ["left", "right"]

            if not use_smart_positioning:
                # ตรวจสอบว่ามี geometry ที่บันทึกไว้แล้วหรือไม่ (logic เดิม)
                current_geometry = self.root.geometry()
                if current_geometry and current_geometry != "1x1+0+0":
                    logging.info(f"Using existing geometry: {current_geometry}")
                    return

            # ใช้ logic แบบฉลาด (ใหม่) หรือ fallback (เดิม)
            self.root.update_idletasks()

            # ดึงข้อมูลจอภาพ
            if monitor_info and use_smart_positioning:
                # ใช้ข้อมูลจอภาพที่ส่งมาจาก MBB
                monitor_left = monitor_info["left"]
                monitor_right = monitor_info["right"]
                monitor_top = monitor_info["top"]
                monitor_bottom = monitor_info["bottom"]
                monitor_width = monitor_info["width"]
                monitor_height = monitor_info["height"]

                print(f"Log UI: Using MBB monitor info: {monitor_info}")
            else:
                # Fallback ใช้หน้าจอหลัก
                try:
                    if HAS_WIN32:
                        # ใช้หน้าจอหลักสำหรับการคำนวณ
                        screen_width = self.root.winfo_screenwidth()
                        screen_height = self.root.winfo_screenheight()
                        monitor_left = 0
                        monitor_right = screen_width
                        monitor_top = 0
                        monitor_bottom = screen_height
                        monitor_width = screen_width
                        monitor_height = screen_height

                        print(
                            f"Log UI: Using fallback screen dimensions: {screen_width}x{screen_height}"
                        )
                    else:
                        # Fallback ไม่มี win32api
                        screen_width = self.root.winfo_screenwidth()
                        screen_height = self.root.winfo_screenheight()
                        monitor_left = 0
                        monitor_right = screen_width
                        monitor_top = 0
                        monitor_bottom = screen_height
                        monitor_width = screen_width
                        monitor_height = screen_height

                except Exception as e:
                    print(f"Failed to get monitor info for Log UI: {e}")
                    # Fallback ใช้หน้าจอหลัก
                    screen_width = self.root.winfo_screenwidth()
                    screen_height = self.root.winfo_screenheight()
                    monitor_left = 0
                    monitor_right = screen_width
                    monitor_top = 0
                    monitor_bottom = screen_height
                    monitor_width = screen_width
                    monitor_height = screen_height

            # คำนวณขนาดหน้าต่าง Log
            if use_smart_positioning:
                window_width = DEFAULT_LOG_WIDTH
                window_height = DEFAULT_LOG_HEIGHT

                # คำนวณตำแหน่ง Y เว้นจากขอบบน 100px
                y = monitor_top + 100

                # คำนวณตำแหน่ง X - เว้นจากขอบขวา 100px เสมอ
                gap = 100  # ระยะห่างจากขอบขวา

                # แสดงที่ขอบขวาสุดเสมอ ไม่ว่า MBB จะอยู่ที่ไหน
                x = monitor_right - window_width - gap

                # ตรวจสอบขอบเขตจอ
                x = max(monitor_left, min(x, monitor_right - window_width))
                y = max(monitor_top, min(y, monitor_bottom - window_height))

                print(
                    f"Log UI positioned at: {x}, {y} (size: {window_width}x{window_height}, MBB side: {mbb_side})"
                )
            else:
                # Fallback positioning (logic เดิม)
                window_height = max(300, int(monitor_height * 0.9))
                window_width = 400
                x = monitor_left
                y = max(monitor_top, (monitor_height - window_height) // 2)

                logging.info(f"Log UI fallback positioning: {x}, {y}")

            default_geometry = f"{window_width}x{window_height}+{x}+{y}"
            self.root.geometry(default_geometry)

            logging.info(f"Applied geometry for Log UI: {default_geometry}")

        except Exception as e:
            logging.error(f"Error adjusting Log window: {e}")
            # Fallback geometry
            self.root.geometry("400x600+0+200")

    def show_window(self, mbb_side="left", monitor_info=None):
        """แสดงหน้าต่าง พร้อมตรวจสอบและกำหนดขนาดที่ถูกต้องในครั้งแรก

        Args:
            mbb_side (str): ตำแหน่งของ MBB window ('left' หรือ 'right')
            monitor_info (dict): ข้อมูลจอภาพปัจจุบันของ MBB
        """
        # ลำดับความสำคัญ: Lock (ถ้ามี) > Default Position > Smart Positioning
        
        # Debug: แสดงสถานะทั้งหมดก่อนตัดสินใจ
        logging.info(f"\n=== SHOW_WINDOW DEBUG TRACE ===")
        logging.info(f"mbb_side: {mbb_side}")
        logging.info(f"monitor_info: {monitor_info}")
        logging.info(f"self.is_position_locked: {self.is_position_locked}")
        logging.info(f"self.locked_geometry: {getattr(self, 'locked_geometry', 'NOT_SET')}")
        logging.info(f"self._session_opened: {self._session_opened}")
        logging.info(f"Current geometry: {self.root.geometry()}")
        
        # ตรวจสอบเงื่อนไข 1: Lock mode (ใช้ตำแหน่งที่บันทึกไว้)
        condition1 = self.is_position_locked and self.locked_geometry and self.locked_geometry.strip()
        logging.info(f"Condition 1 (Lock mode): {condition1}")

        # ตรวจสอบเงื่อนไข 2: First open in session และไม่มี lock - ใช้ค่าเริ่มต้น
        condition2 = not self._session_opened and not self.is_position_locked
        logging.info(f"Condition 2 (First open in session + No lock): {condition2}")
        
        logging.info(f"=== DECISION PATH ===")

        if condition1:
            # ความสำคัญสูงสุด: ใช้ตำแหน่งและขนาดที่ล็อกไว้ (persistent across sessions)
            logging.info(f"✓ Taking Priority 1: Using LOCKED position: {self.locked_geometry}")

            # โหลดขนาดที่บันทึกไว้จาก settings
            try:
                saved_width = self.settings.get("logs_ui", {}).get("width", 300)
                saved_height = self.settings.get("logs_ui", {}).get("height", 800)
                saved_x = self.settings.get("logs_ui", {}).get("x", 0)
                saved_y = self.settings.get("logs_ui", {}).get("y", 0)

                # สร้าง geometry string ที่รวมขนาดและตำแหน่งที่บันทึกไว้
                complete_geometry = f"{saved_width}x{saved_height}+{saved_x}+{saved_y}"
                logging.info(f"✓ Using complete locked geometry (size+position): {complete_geometry}")
                self.root.geometry(complete_geometry)

                # อัพเดท locked_geometry ให้ตรงกับขนาดจริง
                self.locked_geometry = complete_geometry

            except Exception as e:
                logging.error(f"Error loading locked size: {e}, using fallback")
                self.root.geometry(self.locked_geometry)

            self._session_opened = True  # ป้องกัน smart positioning ทำงานซ้ำ

        elif condition2:
            # Priority 2: เปิดครั้งแรกใน session และไม่ได้ lock - ใช้ค่าเริ่มต้น
            logging.info(f"✓ Taking Priority 2: First open in session - using default position")
            
            default_width = DEFAULT_LOG_WIDTH
            default_height = DEFAULT_LOG_HEIGHT
            
            if monitor_info:
                # คำนวณตำแหน่งขวาสุดของจอ - 200px
                monitor_width = monitor_info.get("width", 1920)
                monitor_height = monitor_info.get("height", 1080)
                monitor_left = monitor_info.get("left", 0)
                monitor_top = monitor_info.get("top", 0)
                
                # ตำแหน่งขวาสุด - 100px
                pos_x = monitor_left + monitor_width - default_width - 100
                pos_y = monitor_top + 100  # เว้นจากขอบบน 100px
                
                geometry = f"{default_width}x{default_height}+{pos_x}+{pos_y}"
                logging.info(f"Setting default geometry: {geometry}")
                self.root.geometry(geometry)
            else:
                # Fallback ถ้าไม่มี monitor info (1920-300-100=1520)
                self.root.geometry(f"{default_width}x{default_height}+1520+100")
            
            # Set session opened ONLY if no lock (lock mode จะไม่เปลี่ยน session state)
            if not self.is_position_locked:
                self._session_opened = True
            
        elif mbb_side and mbb_side in ["left", "right"] and monitor_info:
            # Priority 3: Smart positioning (ถ้าเปิดอีกครั้งในsession เดียวกัน)
            logging.info(f"✓ Taking Priority 3: Using smart positioning for Log UI (MBB side: {mbb_side})")
            self.check_screen_size_and_adjust(mbb_side, monitor_info)

        else:
            # Fallback: ใช้ตำแหน่งปัจจุบันหรือ default
            logging.info("✓ Taking Priority 4: Fallback logic")
            current_geometry = self.root.geometry()
            if not current_geometry or current_geometry in ["1x1+0+0", "200x200+0+0"]:
                self.root.geometry(FALLBACK_LOG_GEOMETRY)
        
        logging.info(f"=== END DEBUG TRACE ===\n")

        self.root.deiconify()
        self.root.update_idletasks()

        # ตั้งค่า resize handle
        if hasattr(self, "resize_handle"):
            self.resize_handle.place(relx=1.0, rely=1.0, anchor="se", x=-1, y=-1)
            if not hasattr(self, "is_ui_locked"):
                self.is_ui_locked = False
            cursor_type = "sizing" if self.is_ui_locked else "arrow"
            self.resize_handle.config(cursor=cursor_type)

        # ไม่ต้อง apply rounded corners สำหรับ flat design
        # self.root.after(50, self.apply_rounded_corners_to_ui)

        self.root.lift()
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", ALPHA_MAP.get(self.current_mode, ALPHA_MAP["A"]))
        self.is_visible = True

        self._smooth_scroll_to_latest()

    def show(self, mbb_side="left", monitor_info=None):
        self.show_window(mbb_side, monitor_info)

    def hide(self):
        self.hide_window()

    # === DRAG & RESIZE FUNCTIONALITY ===

    def start_move(self, event):
        if not self._is_control_click(event):
            self.drag_start_x = event.x_root - self.root.winfo_x()
            self.drag_start_y = event.y_root - self.root.winfo_y()

    def do_move(self, event):
        if hasattr(self, "drag_start_x"):
            x = event.x_root - self.drag_start_x
            y = event.y_root - self.drag_start_y
            self.root.geometry(f"+{x}+{y}")

            # ถ้าอยู่ในสถานะ lock ให้บันทึกตำแหน่งทันที
            if self.is_position_locked:
                self.locked_geometry = self.root.geometry()

    def stop_move(self, event):
        if hasattr(self, "drag_start_x"):
            delattr(self, "drag_start_x")
        if hasattr(self, "drag_start_y"):
            delattr(self, "drag_start_y")

        # ถ้าอยู่ในสถานะ lock ให้บันทึกตำแหน่งสุดท้ายลง settings
        if self.is_position_locked:
            self.locked_geometry = self.root.geometry()
            self.save_locked_position()
            logging.info(f"Lock mode: saved {self.locked_geometry}")

    def save_locked_position(self):
        """บันทึกตำแหน่งที่ล็อกลง settings.json"""
        try:
            if self.is_position_locked and self.root.winfo_exists():
                self.settings.set_logs_settings(
                    width=self.root.winfo_width(),
                    height=self.root.winfo_height(),
                    x=self.root.winfo_x(),
                    y=self.root.winfo_y(),
                )
                self.settings.set("logs_locked_geometry", self.root.geometry())
                logging.debug(f"Lock: saved {self.root.geometry()}")
        except Exception as e:
            logging.error(f"Error saving locked position: {e}")

    def _is_control_click(self, event):
        try:
            return isinstance(
                event.widget.winfo_containing(event.x_root, event.y_root), tk.Button
            )
        except (AttributeError, tk.TclError):
            return False

    def start_resize(self, event):
        """เริ่มการปรับขนาดหน้าต่างด้วย Enhanced Ghost Frame 🚀"""
        if not self.is_ui_locked:
            self.toggle_lock_ui()
            return

        # Store initial state
        self.resize_start_x = event.x_root
        self.resize_start_y = event.y_root
        self.resize_start_width = self.root.winfo_width()
        self.resize_start_height = self.root.winfo_height()
        self.resize_last_update = 0  # Throttling timestamp

        # Create enhanced ghost frame
        self.ghost_frame = tk.Toplevel(self.root)
        self.ghost_frame.overrideredirect(True)
        self.ghost_frame.attributes("-alpha", 0.35)  # ลด alpha เพื่อประสิทธิภาพ
        self.ghost_frame.attributes("-topmost", True)

        # ใช้สีเทาเข้มเหมือน UI พร้อม border ที่เห็นชัด
        ghost_bg = appearance_manager.darken_color(appearance_manager.bg_color, 0.2)
        self.ghost_frame.configure(bg=ghost_bg, cursor="sizing")

        # สร้าง border frame ภายใน เพื่อให้เห็นขอบเขตชัด
        self.ghost_border = tk.Frame(
            self.ghost_frame,
            bg=appearance_manager.fg_color,
            bd=0,
            highlightthickness=2,
            highlightcolor="#60A5FA",  # สีฟ้าอ่อนสำหรับ border
            highlightbackground="#60A5FA",
        )
        self.ghost_border.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        # ตั้งค่าตำแหน่งเริ่มต้น
        self.ghost_frame.geometry(self.root.geometry())
        logging.info("🎯 Enhanced ghost frame created for smooth resize")

    def do_resize(self, event):
        """ปรับขนาด Ghost Frame ด้วย throttling เพื่อประสิทธิภาพสูงสุด ⚡"""
        if not (self.is_ui_locked and hasattr(self, "ghost_frame")):
            return

        # Throttling: อัพเดทเฉพาะทุก 16ms (60fps max) เพื่อประสิทธิภาพ
        current_time = time.time() * 1000  # milliseconds
        if (
            hasattr(self, "resize_last_update")
            and (current_time - self.resize_last_update) < 16
        ):
            return
        self.resize_last_update = current_time

        # คำนวณขนาดใหม่ด้วย smooth constraints
        dx = event.x_root - self.resize_start_x
        dy = event.y_root - self.resize_start_y

        # กำหนดขนาดขั้นต่ำ/สูงสุดที่สมเหตุสมผล
        min_width, min_height = 300, 200
        max_width = self.root.winfo_screenwidth() - 50
        max_height = self.root.winfo_screenheight() - 100

        new_w = max(min_width, min(max_width, self.resize_start_width + dx))
        new_h = max(min_height, min(max_height, self.resize_start_height + dy))

        # อัพเดทขนาดแบบ smooth (rounded เพื่อลด jitter)
        smooth_w = int(round(new_w / 5) * 5)  # Round to nearest 5px for smoothness
        smooth_h = int(round(new_h / 5) * 5)

        try:
            self.ghost_frame.geometry(
                f"{smooth_w}x{smooth_h}+{self.root.winfo_x()}+{self.root.winfo_y()}"
            )

            # อัพเดทสี border ตามขนาด (สีเขียวเมื่อขยาย, ส้มเมื่อลด)
            if hasattr(self, "ghost_border"):
                if (
                    smooth_w >= self.resize_start_width
                    and smooth_h >= self.resize_start_height
                ):
                    # ขยาย - สีเขียวอ่อน
                    self.ghost_border.configure(
                        highlightcolor="#10B981", highlightbackground="#10B981"
                    )
                elif (
                    smooth_w <= self.resize_start_width
                    and smooth_h <= self.resize_start_height
                ):
                    # ลด - สีส้มอ่อน
                    self.ghost_border.configure(
                        highlightcolor="#F59E0B", highlightbackground="#F59E0B"
                    )
                else:
                    # ปกติ - สีฟ้าอ่อน
                    self.ghost_border.configure(
                        highlightcolor="#60A5FA", highlightbackground="#60A5FA"
                    )

        except tk.TclError:
            # หาก ghost frame ถูกทำลายแล้ว ให้หยุดการทำงาน
            pass

    def stop_resize(self, event):
        """หยุดการปรับขนาดด้วย fade-out animation และ cleanup ที่สมบูรณ์ ✨"""
        if not hasattr(self, "ghost_frame"):
            return

        # เก็บขนาดสุดท้ายก่อน cleanup
        try:
            final_width = self.ghost_frame.winfo_width()
            final_height = self.ghost_frame.winfo_height()

            # Smooth fade-out animation สำหรับ ghost frame
            def fade_out_ghost(alpha=0.35):
                try:
                    if alpha > 0.05 and hasattr(self, "ghost_frame"):
                        self.ghost_frame.attributes("-alpha", alpha)
                        self.root.after(20, lambda: fade_out_ghost(alpha - 0.07))
                    else:
                        # จบ animation - ทำลาย ghost frame
                        if hasattr(self, "ghost_frame"):
                            self.ghost_frame.destroy()
                            delattr(self, "ghost_frame")
                        if hasattr(self, "ghost_border"):
                            delattr(self, "ghost_border")
                except tk.TclError:
                    # Ghost frame ถูกทำลายแล้ว
                    pass

            # เริ่ม fade-out animation
            fade_out_ghost()

            # ใช้ขนาดใหม่กับหน้าต่างจริง
            self.root.geometry(f"{final_width}x{final_height}")

            # บันทึกการตั้งค่าและ refresh UI
            self.save_settings()
            # ไม่ต้อง apply rounded corners สำหรับ flat design
            # self.root.after(80, self.apply_rounded_corners_to_ui)
            self.root.after(120, self._repack_bubbles)

            logging.info(
                f"✅ Resize completed: {final_width}x{final_height} with flat design"
            )

        except Exception as e:
            logging.error(f"Error in stop_resize: {e}")
            # Fallback cleanup
            if hasattr(self, "ghost_frame"):
                try:
                    self.ghost_frame.destroy()
                    delattr(self, "ghost_frame")
                except (AttributeError, tk.TclError):
                    pass

        # Cleanup resize state variables
        for attr in [
            "resize_start_x",
            "resize_start_y",
            "resize_start_width",
            "resize_start_height",
            "resize_last_update",
            "ghost_border",
        ]:
            if hasattr(self, attr):
                delattr(self, attr)

    def toggle_lock_ui(self):
        self.is_ui_locked = not self.is_ui_locked
        self.resize_handle.config(cursor="sizing" if self.is_ui_locked else "arrow")

    # === SETTINGS MANAGEMENT ===

    def load_settings(self):
        try:
            logs_settings = self.settings.get_logs_settings()
            if logs_settings:
                # โหลด reverse mode
                self.reverse_mode.set(self.settings.get("logs_reverse_mode", False))

                # โหลด font size และ font family
                font_size = logs_settings.get("font_size")
                if font_size and 10 <= font_size <= 28:
                    self.current_font_size = font_size
                    self._update_font_display()

                font_family = logs_settings.get("font_family")
                if font_family:
                    self.current_font_family = font_family

                # โหลด transparency mode
                mode = logs_settings.get("transparency_mode")
                if mode in TRANSPARENCY_MODES:
                    self.current_mode = mode

                # ไม่โหลด geometry จาก settings เมื่อเปิดโปรแกรมใหม่
                # เพื่อให้ใช้ค่าเริ่มต้น 240x600 และตำแหน่งขวาสุด
                # geometry จะถูกบันทึกเฉพาะใน session เมื่อ lock เท่านั้น
                
                # Reset to first show state
                self._is_first_show = True
                self._session_opened = False
                
                logging.info("Starting with default settings (unlock mode)")

            # ไม่โหลดสถานะ lock เมื่อเปิดโปรแกรมใหม่ - เริ่มต้นด้วย unlock เสมอ
            # สถานะ lock จะถูกเก็บเฉพาะใน session ปัจจุบัน
            self.is_position_locked = False
            self.locked_geometry = None
            
            # อัปเดตไอคอนปุ่ม unlock
            if hasattr(self, "lock_button"):
                if hasattr(self, "unlock_icon") and self.unlock_icon:
                    self.lock_button.config(image=self.unlock_icon)
                else:
                    self.lock_button.config(text="🔓", fg="#888888")
            logging.info("Initial state: UNLOCKED (always start unlocked)")

        except Exception as e:
            logging.error(f"Error loading settings: {e}")

    def save_settings(self):
        try:
            if self.root.winfo_exists():
                width = self.root.winfo_width()
                height = self.root.winfo_height()
                x = self.root.winfo_x()
                y = self.root.winfo_y()

                # ใช้ฟังก์ชัน set_logs_settings ที่รองรับพารามิเตอร์เพิ่มเติมแล้ว
                self.settings.set_logs_settings(
                    width=width,
                    height=height,
                    x=x,
                    y=y,
                    font_size=self.current_font_size,
                    font_family=self.current_font_family,
                    transparency_mode=self.current_mode,
                    logs_reverse_mode=self.reverse_mode.get(),
                )

                # บันทึกสถานะ lock แยกต่างหาก
                self.settings.set("logs_position_locked", self.is_position_locked)
                if self.is_position_locked:
                    # อัปเดตตำแหน่งล็อกเป็นปัจจุบัน
                    self.locked_geometry = self.root.geometry()
                    self.settings.set("logs_locked_geometry", self.locked_geometry)
                    logging.debug(f"Lock: auto-saved {self.locked_geometry}")

                logging.info(
                    f"Saved logs settings: {width}x{height}+{x}+{y}, font:{self.current_font_size}, mode:{self.current_mode}, locked:{self.is_position_locked}"
                )
        except Exception as e:
            logging.error(f"Error saving settings: {e}")

    # === UTILITY METHODS ===

    def clear_logs(self):
        """Clear all messages with animation cleanup and reset cache"""
        # Cancel any ongoing scroll animation
        if self._scroll_animation_id:
            self.root.after_cancel(self._scroll_animation_id)
            self._scroll_animation_id = None

        for bubble in self.bubble_list:
            bubble.destroy()
        self.bubble_list.clear()

        # Clear smart cache
        self.message_cache.clear()
        self.last_message_hash = None

        self._update_status()
        logging.info("Cleared all log messages and cache")

    def toggle_smart_replacement(self):
        """เปิด/ปิดการแทนที่อัจฉริยะ"""
        self.enable_smart_replacement = not self.enable_smart_replacement
        status = "เปิด" if self.enable_smart_replacement else "ปิด"
        logging.info(f"Smart Replacement: {status}")

        # อัปเดตปุ่ม smart ให้แสดงสถานะใหม่ - flat design
        if hasattr(self, "smart_button"):
            self.smart_button.config(
                text=self._get_smart_icon(),
                fg=self._get_smart_color_flat(),
                bg=appearance_manager.bg_color,
            )

        logging.info(f"Smart replacement: {status}")

    def get_cache_stats(self):
        """ดูสถิติ cache ปัจจุบัน"""
        return {
            "total_cached": len(self.message_cache),
            "total_bubbles": len(self.bubble_list),
            "last_message": self.last_message_hash is not None,
            "smart_mode": self.enable_smart_replacement,
        }

    def add_message_from_translation(self, text, is_force_retranslation=False):
        """เมธอดสำหรับเรียกจาก MBB.py - รองรับการระบุว่าเป็นการแปลใหม่หรือไม่"""
        self.add_message(text, is_force_retranslation=is_force_retranslation)

    def cleanup(self):
        """Cleanup resources before closing with enhanced ghost frame cleanup"""
        try:
            # Cancel animations
            if self._scroll_animation_id:
                self.root.after_cancel(self._scroll_animation_id)
                self._scroll_animation_id = None

            # Enhanced ghost frame cleanup
            self.emergency_cleanup_ghost()

            self.save_settings()
            self.clear_logs()
            logging.info(
                "✅ Translated logs cleanup completed with enhanced ghost cleanup"
            )
        except Exception as e:
            logging.error(f"Error in cleanup: {e}")

    # === ENHANCED RESIZE SYSTEM DEBUG ===

    def _is_ghost_frame_active(self):
        """ตรวจสอบว่า ghost frame กำลังทำงานอยู่หรือไม่"""
        return hasattr(self, "ghost_frame") and self.ghost_frame.winfo_exists()

    def emergency_cleanup_ghost(self):
        """ทำความสะอาด ghost frame ในกรณีฉุกเฉิน"""
        try:
            if hasattr(self, "ghost_frame"):
                self.ghost_frame.destroy()
                delattr(self, "ghost_frame")
            if hasattr(self, "ghost_border"):
                delattr(self, "ghost_border")

            # Cleanup all resize variables
            for attr in [
                "resize_start_x",
                "resize_start_y",
                "resize_start_width",
                "resize_start_height",
                "resize_last_update",
            ]:
                if hasattr(self, attr):
                    delattr(self, attr)

            logging.info("🧹 Emergency ghost frame cleanup completed")
        except Exception as e:
            logging.error(f"Error in emergency cleanup: {e}")
