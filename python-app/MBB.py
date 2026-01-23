__version__ = "1.5.28"  # MBB Dalamud Bridge - Test Hook buttons, TUI position fixes

from enum import Enum
import json
from pydoc import text
import random
import subprocess
import sys
import os
import atexit
import psutil
import tempfile

# ตั้งค่า encoding สำหรับ Windows console เพื่อรองรับภาษาไทย
if sys.platform == "win32":
    try:
        # ตั้งค่า console code page เป็น UTF-8
        from ctypes import windll as console_windll

        console_windll.kernel32.SetConsoleCP(65001)
        console_windll.kernel32.SetConsoleOutputCP(65001)
        # ตั้งค่า stdout encoding
        import io

        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")
    except:
        pass
import tkinter as tk
from tkinter import (
    ttk,
    messagebox,
    Checkbutton,
    BooleanVar,
)  # เพิ่ม Checkbutton, BooleanVar
from tkinter import Label  # เพิ่ม import Label
import math  # เพิ่ม import math
from PIL import ImageGrab, ImageEnhance, Image, ImageTk, ImageDraw, ImageFilter
import win32gui
import win32con
from ctypes import windll, wintypes
import ctypes
# OCR removed - project is 100% text hook now
import time
import threading
import difflib
import logging
import traceback
from datetime import datetime
from text_corrector import TextCorrector
import translated_ui
from text_corrector import DialogueType
from control_ui import Control_UI
from translator_gemini import TranslatorGemini
from settings import Settings, SettingsUI
from advance_ui import AdvanceUI
from mini_ui import MiniUI
from loggings import LoggingManager
# DISABLED - Rainbow progress bar causes tkinter errors
from translator_factory import TranslatorFactory
import keyboard
import re
from appearance import appearance_manager
import importlib.util
import warnings
import webbrowser
from translated_logs import Translated_Logs
from font_manager import FontSettings, initialize_font_manager
from asset_manager import AssetManager
from dalamud_bridge import DalamudBridge
from dalamud_immediate_handler import create_dalamud_immediate_handler

# UI Components for redesigned architecture
from button_factory import ButtonFactory
from ui_components import HeaderBar, ControlPanel, BottomBar

# --- TranslationPolicy removed ---

# Tesseract OCR removed - using EasyOCR only

warnings.filterwarnings("ignore", category=UserWarning)

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Import npc_manager silently
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
npc_manager_path = os.path.join(current_dir, "npc_manager_card.py")  # เปลี่ยนเป็นไฟล์ใหม่

try:
    spec = importlib.util.spec_from_file_location("npc_manager_card", npc_manager_path)
    npc_manager_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(npc_manager_module)
    NPCManagerCard = getattr(npc_manager_module, "NPCManagerCard", None)
except Exception as e:
    NPCManagerCard = None


def create_rounded_rectangle(self, x1, y1, x2, y2, radius=25, **kwargs):
    """วาดสี่เหลี่ยมมุมโค้งบน Canvas ด้วย Arc segments สำหรับขอบที่สม่ำเสมอ

    Args:
        x1, y1: พิกัดมุมบนซ้าย
        x2, y2: พิกัดมุมล่างขวา
        radius: รัศมีมุมโค้ง
        **kwargs: พารามิเตอร์อื่นๆ เช่น fill, outline, width

    Returns:
        list: รายการ IDs ของส่วนประกอบทั้งหมด [fill_rect, top_arc, right_arc, bottom_arc, left_arc, edges...]
    """
    # ปรับค่ารัศมีหากขนาดของสี่เหลี่ยมเล็กเกินไป
    width, height = x2 - x1, y2 - y1
    radius = min(radius, width // 2, height // 2)

    # แยก kwargs สำหรับ fill และ outline
    fill = kwargs.get('fill', '')
    outline = kwargs.get('outline', '')
    outline_width = kwargs.get('width', 1)

    items = []

    # 1. วาดพื้นหลัง (fill) - สี่เหลี่ยมด้านในโดยไม่มีขอบ
    if fill:
        # วาดสี่เหลี่ยมกลาง (ไม่รวมมุม)
        center_rect = self.create_rectangle(
            x1 + radius, y1, x2 - radius, y2,
            fill=fill, outline=''
        )
        items.append(center_rect)

        # วาดสี่เหลี่ยมซ้าย-ขวา
        left_rect = self.create_rectangle(
            x1, y1 + radius, x1 + radius, y2 - radius,
            fill=fill, outline=''
        )
        items.append(left_rect)

        right_rect = self.create_rectangle(
            x2 - radius, y1 + radius, x2, y2 - radius,
            fill=fill, outline=''
        )
        items.append(right_rect)

        # วาด fill สำหรับมุมโค้งด้วย arc
        # Top-left
        items.append(self.create_arc(
            x1, y1, x1 + radius * 2, y1 + radius * 2,
            start=90, extent=90, fill=fill, outline=''
        ))
        # Top-right
        items.append(self.create_arc(
            x2 - radius * 2, y1, x2, y1 + radius * 2,
            start=0, extent=90, fill=fill, outline=''
        ))
        # Bottom-right
        items.append(self.create_arc(
            x2 - radius * 2, y2 - radius * 2, x2, y2,
            start=270, extent=90, fill=fill, outline=''
        ))
        # Bottom-left
        items.append(self.create_arc(
            x1, y2 - radius * 2, x1 + radius * 2, y2,
            start=180, extent=90, fill=fill, outline=''
        ))

    # 2. วาดขอบ (outline) - ใช้ arc และ line สำหรับขอบที่สม่ำเสมอ
    if outline:
        # วาดขอบมุมโค้งด้วย arc (style='arc' = เฉพาะเส้นโค้ง)
        # Top-left corner
        items.append(self.create_arc(
            x1, y1, x1 + radius * 2, y1 + radius * 2,
            start=90, extent=90, outline=outline, width=outline_width, style='arc'
        ))
        # Top-right corner
        items.append(self.create_arc(
            x2 - radius * 2, y1, x2, y1 + radius * 2,
            start=0, extent=90, outline=outline, width=outline_width, style='arc'
        ))
        # Bottom-right corner
        items.append(self.create_arc(
            x2 - radius * 2, y2 - radius * 2, x2, y2,
            start=270, extent=90, outline=outline, width=outline_width, style='arc'
        ))
        # Bottom-left corner
        items.append(self.create_arc(
            x1, y2 - radius * 2, x1 + radius * 2, y2,
            start=180, extent=90, outline=outline, width=outline_width, style='arc'
        ))

        # วาดขอบตรง (edges)
        # Top edge
        items.append(self.create_line(
            x1 + radius, y1, x2 - radius, y1,
            fill=outline, width=outline_width
        ))
        # Right edge
        items.append(self.create_line(
            x2, y1 + radius, x2, y2 - radius,
            fill=outline, width=outline_width
        ))
        # Bottom edge
        items.append(self.create_line(
            x2 - radius, y2, x1 + radius, y2,
            fill=outline, width=outline_width
        ))
        # Left edge
        items.append(self.create_line(
            x1, y2 - radius, x1, y1 + radius,
            fill=outline, width=outline_width
        ))

    # Return first item ID for backward compatibility
    return items[0] if items else None


# เพิ่มเมธอดให้กับ tk.Canvas
tk.Canvas.create_rounded_rectangle = create_rounded_rectangle


class ButtonStateManager:
    """จัดการสถานะปุ่ม TUI/LOG/MINI อย่างเป็นระบบ พร้อม immediate feedback และ background verification"""

    def __init__(self, appearance_manager, parent_app):
        self.appearance_manager = appearance_manager
        self.parent_app = parent_app
        self.button_states = {
            "tui": {
                "active": False,
                "button_ref": None,
                "window_ref": None,
                "pending": False,
            },
            "log": {
                "active": False,
                "button_ref": None,
                "window_ref": None,
                "pending": False,
            },
            "mini": {
                "active": False,
                "button_ref": None,
                "window_ref": None,
                "pending": False,
            },
        }
        self.state_colors = {
            "normal": None,
            "hover": None,
            "hover_light": None,  # สำหรับ hover เมื่อปุ่มเปิดอยู่
            "toggle_on": None,
            "toggle_off": None,
            "pending": None,  # สีสำหรับสถานะรอการตรวจสอบ
        }
        self.verification_thread = None
        self.verification_delay = 0.1  # ดีเลย์สำหรับการตรวจสอบพื้นหลัง (100ms)
        self.update_theme_colors()

    def update_theme_colors(self):
        """อัปเดตสีตามธีมปัจจุบัน"""
        self.state_colors["normal"] = self.appearance_manager.get_theme_color(
            "button_bg", "#262637"
        )
        self.state_colors["hover"] = self.appearance_manager.get_accent_color()
        self.state_colors["toggle_on"] = self.appearance_manager.get_accent_color()
        self.state_colors["toggle_off"] = self.state_colors["normal"]

        # สร้างสี hover อ่อนสำหรับเมื่อปุ่มเปิดอยู่
        accent_color = self.appearance_manager.get_accent_color()
        self.state_colors["hover_light"] = self.lighten_color(accent_color, 1.2)

        # สี pending - ใช้สี accent แต่อ่อนกว่าเล็กน้อย (สำหรับ immediate feedback)
        self.state_colors["pending"] = self.lighten_color(accent_color, 1.1)

    def lighten_color(self, hex_color, factor=1.2):
        """ทำให้สีอ่อนลง"""
        try:
            # แปลง hex เป็น RGB
            hex_color = hex_color.lstrip("#")
            rgb = tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))

            # ทำให้อ่อนลง
            rgb_light = tuple(min(255, int(c * factor)) for c in rgb)

            # แปลงกลับเป็น hex
            return "#{:02x}{:02x}{:02x}".format(*rgb_light)
        except:
            # ถ้าเกิดข้อผิดพลาด ให้ใช้สีเดิม
            return hex_color

    def register_button(self, button_key, button_ref, window_ref=None):
        """ลงทะเบียนปุ่มและหน้าต่าง"""
        if button_key in self.button_states:
            self.button_states[button_key]["button_ref"] = button_ref
            if window_ref:
                self.button_states[button_key]["window_ref"] = window_ref

    def set_window_ref(self, button_key, window_ref):
        """ตั้งค่า window reference (สำหรับกรณีที่สร้างหลังจากปุ่ม)"""
        if button_key in self.button_states:
            self.button_states[button_key]["window_ref"] = window_ref

    def is_window_active(self, button_key):
        """ตรวจสอบว่าหน้าต่างเปิดอยู่หรือไม่"""
        try:
            if button_key == "tui":
                return self._detect_tui_window_state()
            elif button_key == "log":
                return self._detect_log_window_state()
            elif button_key == "mini":
                return self._detect_mini_ui_state()
            return False
        except Exception:
            return False

    def _detect_tui_window_state(self):
        """ตรวจสอบสถานะ TUI window"""
        try:
            return (
                hasattr(self.parent_app, "translated_ui_window")
                and self.parent_app.translated_ui_window.winfo_exists()
                and self.parent_app.translated_ui_window.state() != "withdrawn"
            )
        except (tk.TclError, AttributeError):
            return False

    def _detect_log_window_state(self):
        """ตรวจสอบสถานะ LOG window"""
        try:
            return (
                hasattr(self.parent_app, "translated_logs_instance")
                and self.parent_app.translated_logs_instance is not None
                and hasattr(self.parent_app.translated_logs_instance, "root")
                and self.parent_app.translated_logs_instance.root.winfo_exists()
                and self.parent_app.translated_logs_instance.root.state() != "withdrawn"
            )
        except (tk.TclError, AttributeError):
            return False

    # NOTE: _detect_control_window_state removed - CON button and control UI no longer exist
    # def _detect_control_window_state(self):
    #     """ตรวจสอบสถานะ Control window"""
    #     ... (commented out)

    def _detect_mini_ui_state(self):
        """ตรวจสอบสถานะ Mini UI"""
        try:
            return (
                hasattr(self.parent_app, "mini_ui")
                and self.parent_app.mini_ui
                and hasattr(self.parent_app.mini_ui, "mini_ui")
                and self.parent_app.mini_ui.mini_ui.winfo_exists()
                and self.parent_app.mini_ui.mini_ui.state() != "withdrawn"
            )
        except (tk.TclError, AttributeError):
            return False

    def update_button_visual(self, button_key, visual_state, custom_color=None):
        """อัปเดตการแสดงผลปุ่ม"""
        try:
            button = self.button_states[button_key]["button_ref"]
            if not button:
                logging.warning(f"Button {button_key} reference is None")
                return

            if not button.winfo_exists():
                logging.warning(f"Button {button_key} widget no longer exists")
                return

            # เลือกสี
            if custom_color:
                color = custom_color
            else:
                color = self.state_colors.get(visual_state, self.state_colors["normal"])

            # เลือกสีตัวอักษรตามสถานะ
            if visual_state == "toggle_on":
                # เมื่อ active: ใช้สีดำให้เห็นชัดบน background สว่าง (cyan)
                # ความโปร่งแสงลดลง = ทำให้ทึบขึ้น = ใช้สีดำ
                fg_color = "#000000"
            elif visual_state in ["hover", "hover_light"]:
                # เมื่อ hover: ใช้สีเทาเข้มให้เห็นชัดแต่ไม่ดำสนิท
                fg_color = "#1a1a1a"
            else:
                # เมื่อ normal: ใช้สี text_dim
                fg_color = self.appearance_manager.get_theme_color("text_dim", "#b2b2b2")

            # อัปเดตปุ่ม
            if hasattr(button, "update_button"):
                # Canvas button
                button.update_button(bg=color, fg=fg_color)
            else:
                # Regular button
                button.config(bg=color, fg=fg_color)

        except Exception as e:
            logging.error(f"Error updating button visual for {button_key}: {e}")

    def set_button_state(self, button_key, active_state):
        """ตั้งค่าสถานะปุ่มและอัปเดตการแสดงผล"""
        if button_key in self.button_states:
            self.button_states[button_key]["active"] = active_state
            visual_state = "toggle_on" if active_state else "toggle_off"
            self.update_button_visual(button_key, visual_state)

    def handle_hover_enter(self, button_key):
        """จัดการ hover enter event"""
        current_state = self.button_states[button_key]["active"]
        if current_state:
            # ถ้าปุ่มเปิดอยู่ ให้ใช้สีอ่อนกว่า
            self.update_button_visual(button_key, "hover_light")
        else:
            # ถ้าปุ่มปิดอยู่ ให้ใช้สี hover ปกติ
            self.update_button_visual(button_key, "hover")

    def handle_hover_leave(self, button_key):
        """จัดการ hover leave event"""
        current_state = self.button_states[button_key]["active"]
        visual_state = "toggle_on" if current_state else "toggle_off"
        self.update_button_visual(button_key, visual_state)

    def toggle_button_immediate(self, button_key):
        """Toggle ปุ่มพร้อม immediate visual feedback (ประหยัดทรัพยากร)

        1. แสดง highlight ทันที
        2. ตรวจสอบสถานะจริงด้วย root.after() แทน thread
        """
        if button_key not in self.button_states:
            return

        # 1. แสดง visual feedback ทันที
        current_state = self.button_states[button_key]["active"]
        new_expected_state = not current_state

        # อัปเดตสถานะทันทีเพื่อ UI responsiveness
        self.button_states[button_key]["active"] = new_expected_state
        immediate_color = (
            self.state_colors["toggle_on"]
            if new_expected_state
            else self.state_colors["normal"]
        )

        self.update_button_visual(button_key, None, custom_color=immediate_color)

        # บันทึกเวลาที่ toggle เพื่อประหยัดทรัพยากรในการ sync
        import time

        self._last_toggle_time = time.time()

        # 2. ตรวจสอบสถานะจริงหลัง 150ms (ประหยัดทรัพยากรกว่า thread)
        def verify_state():
            try:
                actual_state = self.is_window_active(button_key)
                # ถ้าสถานะจริงต่างจากที่ตั้งไว้ ให้แก้ไข
                if actual_state != self.button_states[button_key]["active"]:
                    self.button_states[button_key]["active"] = actual_state
                    final_color = (
                        self.state_colors["toggle_on"]
                        if actual_state
                        else self.state_colors["normal"]
                    )
                    self.update_button_visual(
                        button_key, None, custom_color=final_color
                    )

            except Exception as e:
                logging.warning(f"Error verifying button state for {button_key}: {e}")

        # ใช้ root.after แทน thread (ประหยัดทรัพยากร)
        self.parent_app.root.after(150, verify_state)

    def sync_all_states(self):
        """ซิงค์สถานะปุ่มทั้งหมดกับสถานะหน้าต่างจริง"""
        for button_key in self.button_states.keys():
            # ข้ามถ้ากำลัง pending
            if self.button_states[button_key].get("pending", False):
                continue

            actual_state = self.is_window_active(button_key)
            stored_state = self.button_states[button_key]["active"]

            if actual_state != stored_state:
                self.set_button_state(button_key, actual_state)

    def sync_all_states_async(self):
        """ซิงค์สถานะแบบ lightweight โดยไม่ใช้ thread (ประหยัดทรัพยากร)"""

        def sync_one_button(button_index=0):
            try:
                button_keys = list(self.button_states.keys())
                if button_index >= len(button_keys):
                    return  # เสร็จแล้ว

                button_key = button_keys[button_index]

                # ข้ามการตรวจสอบหากมี recent activity
                if hasattr(self, "_last_toggle_time") and hasattr(
                    self, "_last_toggle_time"
                ):
                    import time

                    if time.time() - getattr(self, "_last_toggle_time", 0) < 1:
                        # ข้ามการตรวจสอบใน 1 วินาทีแรกหลัง toggle
                        self.parent_app.root.after(
                            10, lambda: sync_one_button(button_index + 1)
                        )
                        return

                actual_state = self.is_window_active(button_key)
                stored_state = self.button_states[button_key]["active"]

                if actual_state != stored_state:
                    self.set_button_state(button_key, actual_state)

                # ตรวจสอบปุ่มถัดไปใน 10ms
                self.parent_app.root.after(
                    10, lambda: sync_one_button(button_index + 1)
                )

            except Exception as e:
                logging.warning(f"Error in lightweight sync: {e}")

        # เริ่มตรวจสอบปุ่มแรก
        sync_one_button(0)


class MagicBabelApp:
    def __init__(self, root):
        # Show version info immediately
        print(f"=== MagicBabel System Started v{__version__} ===")

        # 1. การตั้งค่าพื้นฐาน (เหมือนเดิม)
        self.root = root
        self.root.withdraw()
        self.root.attributes("-topmost", True)
        self.translation_event = threading.Event()
        self.ocr_cache = {}
        self.ocr_speed = "normal"
        self.cache_timeout = 1.0
        self.cpu_limit = 80
        self.cpu_check_interval = 1.0
        self.last_cpu_check = time.time()
        self.ocr_interval = 0.3
        self.last_ocr_time = time.time()
        self.same_text_count = 0
        self.last_signatures = {}

        # --- ส่วน Splash Screen (เหมือนเดิม) ---
        def show_splash():
            splash = tk.Toplevel(root)
            splash.overrideredirect(True)
            splash.attributes("-topmost", True)
            try:
                image = Image.open("assets/MBBvisual.png")
                image = image.convert("RGBA")
                SPLASH_WIDTH = 1280
                SPLASH_HEIGHT = 720
                original_ratio = image.width / image.height
                new_ratio = SPLASH_WIDTH / SPLASH_HEIGHT
                if new_ratio > original_ratio:
                    new_width = int(SPLASH_HEIGHT * original_ratio)
                    new_height = SPLASH_HEIGHT
                else:
                    new_width = SPLASH_WIDTH
                    new_height = int(SPLASH_WIDTH / original_ratio)
                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(image)
                screen_width = splash.winfo_screenwidth()
                screen_height = splash.winfo_screenheight()
                x = (screen_width - new_width) // 2
                y = (screen_height - new_height) // 2
                splash.geometry(f"{new_width}x{new_height}+{x}+{y}")
                splash.attributes("-transparentcolor", "black")
                splash.configure(bg="black")
                logo = tk.Label(splash, image=photo, bg="black", bd=0)
                logo.photo = photo
                logo.pack(fill="both", expand=True)
                for i in range(0, 20):
                    alpha = i / 20.0
                    splash.attributes("-alpha", alpha)
                    splash.update()
                    time.sleep(0.02)
                return splash, photo
            except Exception as e:
                print(f"Error loading splash screen: {e}")
                if splash.winfo_exists():
                    splash.destroy()
                return None, None

        self.splash, self.splash_photo = show_splash()
        # --- จบส่วน Splash Screen ---

        # เพิ่มตัวแปรล็อคการเคลื่อนย้าย UI
        self._processing_intensive_task = False

        # เพิ่มตัวแปรสำหรับ tooltip
        self.tooltip_window = None
        self.tooltip_label = None

        # *** เพิ่มตัวแปรสำหรับจัดการ Temporary Area Display ***
        self._last_preset_switch_display_time = 0.0  # เวลาล่าสุดที่แสดง Area ชั่วคราว
        self._min_preset_display_interval = (
            1.8  # วินาที - เวลาน้อยสุดก่อนแสดง Animation อีกครั้ง
        )
        self._active_temp_area_widgets = (
            {}
        )  # Dict เก็บ widget ของ Area ชั่วคราวที่กำลังแสดง {area: {'window': Toplevel, 'label': Label, 'fade_job': after_id}}

        # 5. Initialize core components
        self.settings = Settings()
        # *** เพิ่ม: ตัวแปรสำหรับ Checkbutton ของ Guide ***
        self.show_guide_var = BooleanVar()
        self.show_guide_var.set(
            self.settings.get("show_starter_guide", False)
        )  # โหลดค่าจาก settings - เปลี่ยนเป็น False เพื่อไม่แสดงอัตโนมัติ

        # NOTE: bottom_button_states dict removed - using ButtonStateManager exclusively now

        self.logging_manager = LoggingManager(self.settings)
        self.cpu_limit = self.settings.get("cpu_limit", 80)
        try:
            import psutil

            self.has_psutil = True
            self.logging_manager.log_info("psutil available - CPU monitoring enabled")
        except ImportError:
            self.has_psutil = False
            self.logging_manager.log_warning(
                "psutil not available - CPU monitoring disabled"
            )

        # Initialize CPU Monitor
        try:
            from simple_monitor import SimpleCPUMonitor

            self.cpu_monitor = SimpleCPUMonitor(self.settings)
            print("CPU performance monitor initialized")
        except ImportError:
            self.cpu_monitor = None
            self.logging_manager.log_warning("SimpleCPUMonitor not available")
        self.font_manager = initialize_font_manager(None, self.settings)
        appearance_manager.settings = (
            self.settings
        )  # ส่ง settings ให้ appearance_manager ก่อน

        # สร้าง text_corrector และโหลดข้อมูล NPC ทันที (เพิ่มส่วนนี้)
        self.text_corrector = TextCorrector()
        try:
            self.text_corrector.reload_data()
            self.logging_manager.log_info(
                f"Loaded {len(self.text_corrector.names) if hasattr(self.text_corrector, 'names') else 0} character names"
            )
        except Exception as e:
            self.logging_manager.log_error(
                f"Error initializing TextCorrector early: {e}"
            )

        # 7. Initialize Dalamud Bridge
        self.dalamud_bridge = DalamudBridge()
        self.dalamud_mode = True  # HARDCODE: MBB Dalamud Bridge ALWAYS uses Text Hook
        self.dalamud_text_queue = []

        # Dalamud handler will be initialized in setup_translator_and_ocr() after translator creation

        # 8. Initialize variables (เพื่อให้ self.current_area พร้อมใช้งาน)
        self.hotkeys = {}
        self.init_variables()
        self.load_shortcuts()
        self.load_icons()

        # 8. Initialize window positions (เหมือนเดิม)
        self.last_main_ui_pos = None
        self.last_mini_ui_pos = None
        self.last_translated_ui_pos = None

        # *** ลำดับใหม่: สร้าง UI Components ทั้งหมดก่อน ***
        # 9. Create UI components
        self.mini_ui = MiniUI(self.root, self.show_main_ui_from_mini)
        self.mini_ui.set_toggle_translation_callback(self.toggle_translation)
        self.blink_interval = 500
        self.mini_ui.blink_interval = self.blink_interval

        # *** โหลด themes ก่อนสร้าง UI และ ButtonStateManager เพื่อให้สีถูกต้อง ***
        # ต้องโหลด themes ก่อนเรียก get_accent_color() ใน create_main_ui()
        self.logging_manager.log_info("โหลดข้อมูลธีมก่อนสร้าง UI...")
        appearance_manager.load_custom_themes(self.settings)

        # ตั้งค่าธีมทันทีเพื่อให้ UI ใช้สีที่ถูกต้อง
        saved_theme = self.settings.get("theme", "Theme1")
        if saved_theme in self.settings.get("custom_themes", {}):
            appearance_manager.set_theme(saved_theme)
            self.logging_manager.log_info(f"ใช้ธีม: {saved_theme}")
        else:
            appearance_manager.set_theme("Theme1")
            self.logging_manager.log_info("ใช้ธีมเริ่มต้น: Theme1")

        # สร้าง ButtonStateManager หลังโหลด themes เพื่อให้มีสีที่ถูกต้อง
        self.button_state_manager = ButtonStateManager(appearance_manager, self)

        # สร้าง ButtonFactory สำหรับ UI component creation
        self.button_factory = ButtonFactory(appearance_manager)

        self.create_main_ui()  # สร้าง UI components
        self.create_translated_ui()
        self.create_translated_logs()
        self.create_settings_ui()

        # *** แก้ไขจุดนี้: ตอนสร้าง Control_UI ให้ส่ง callback ใหม่ไปด้วย ***
        control_root = tk.Toplevel(self.root)
        control_root.protocol("WM_DELETE_WINDOW", lambda: self.on_control_close())
        self.control_ui = Control_UI(
            control_root,
            self.show_previous_dialog,
            self.switch_area,
            self.settings,
            parent_callback=self.handle_control_ui_event,  # Add parent callback for event handling
            trigger_temporary_area_display_callback=self.trigger_temporary_area_display,  # ส่งเมธอดนี้เป็น callback
            on_close_callback=self.on_control_close,
        )
        if hasattr(self.control_ui, "set_cpu_limit_callback"):
            self.control_ui.set_cpu_limit_callback(self.set_cpu_limit)
            self.logging_manager.log_info(
                "CPU limit callback registered with Control UI."
            )
        else:
            self.logging_manager.log_warning(
                "Control UI does not have set_cpu_limit_callback method."
            )
        control_root.withdraw()
        # *** จบส่วนสร้าง UI Components ***

        # --- ลำดับใหม่: ตั้งค่า Theme และ Callback ---
        # ตั้งค่า Callback ก่อนเรียกใช้ Theme ครั้งแรก
        appearance_manager.set_theme_change_callback(self._apply_theme_update)
        self.logging_manager.log_info("Theme change callback registered.")

        # Apply style เริ่มต้น (อาจตั้งค่า bg ให้ root)
        self.custom_font = appearance_manager.apply_style(self.root)

        # 6. Theme ถูกโหลดแล้วก่อนสร้าง UI - ย้ายไปบรรทัด 594
        # ตั้งค่า callback หลังจาก UI พร้อมแล้ว
        self.logging_manager.log_info("ตั้งค่า theme callback...")

        # บันทึกสีธีมปัจจุบัน (เหมือนเดิม)
        current_theme = appearance_manager.get_current_theme()
        accent_color = appearance_manager.get_accent_color()
        self.logging_manager.log_info(
            f"กำลังใช้ธีม: {current_theme}, สีหลัก: {accent_color}"
        )
        # --- จบส่วนตั้งค่า Theme ---

        # แสดงข้อมูลเริ่มต้น (Text Hook Mode)
        model = self.settings.get_displayed_model()
        self.logging_manager.log_info(f"=== MagicBabel System Started v{__version__} ===")
        self.logging_manager.log_info(f"Model: {model}")
        self.logging_manager.log_info(f"Mode: Text Hook (Dalamud)")
        self.logging_manager.log_info("===============================")
        # self.text_corrector = TextCorrector() # ย้ายไปสร้างก่อนหน้านี้แล้ว

        # 10. Sync ค่าเริ่มต้นของพื้นที่และ Preset (ตอนนี้ UI พร้อมแล้ว)
        self.sync_initial_areas()

        # ไม่จำเป็นต้องเรียก _apply_theme_update หรือ update_area_button_highlights อีก
        # เพราะการเรียก set_theme() ได้ trigger callback ไปแล้ว และ sync_initial_areas ได้ update UI ย่อยแล้ว

        # 11. Initialize translation system (เหมือนเดิม)
        self.init_translation_and_bridge()
        self.bind_events()
        self.apply_saved_settings()

        # 12. Initialize NPC manager (เหมือนเดิม)
        self.npc_manager = None

        # 13. Translation Policy removed

        current_dir = os.path.dirname(os.path.abspath(__file__))
        npc_manager_path = os.path.join(current_dir, "npc_manager_card.py")
        try:
            spec = importlib.util.spec_from_file_location(
                "npc_manager_card", npc_manager_path
            )
            if spec and spec.loader:
                npc_manager_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(npc_manager_module)
                create_npc_manager = getattr(
                    npc_manager_module, "create_npc_manager_card", None
                )
                if NPCManagerCard is None:
                    self.logging_manager.log_warning(
                        "Function 'create_npc_manager_card' not found in npc_manager_card.py"
                    )
            else:
                create_npc_manager = None
                self.logging_manager.log_warning(
                    f"Could not load spec for npc_manager_card.py at {npc_manager_path}"
                )
        except FileNotFoundError:
            create_npc_manager = None
            self.logging_manager.log_warning(
                f"npc_manager_card.py not found at {npc_manager_path}"
            )
        except Exception as e:
            create_npc_manager = None
            self.logging_manager.log_error(f"Error loading npc_manager_card: {e}")

        # 13. จัดการการแสดง splash screen และ main window (เหมือนเดิม)
        def finish_startup():
            try:
                self.root.after(2000, lambda: self._complete_startup())
            except Exception as e:
                self.logging_manager.log_error(f"Error in finish_startup: {e}")
                if self.root and self.root.winfo_exists():
                    self.root.deiconify()

        startup_thread = threading.Thread(target=finish_startup, daemon=True)
        startup_thread.start()

    def _complete_startup(self):
        """แยกฟังก์ชันสำหรับจัดการส่วนสุดท้ายของการเริ่มต้นโปรแกรม"""
        try:
            # ปิด splash screen ด้วย fade effect
            if hasattr(self, "splash") and self.splash and self.splash.winfo_exists():
                try:
                    for i in range(10, -1, -1):
                        alpha = i / 10
                        self.splash.attributes("-alpha", alpha)
                        self.splash.update()
                        time.sleep(0.02)  # ลดเวลา delay
                    self.splash.destroy()
                except Exception as e:
                    self.logging_manager.log_error(f"Error closing splash: {e}")
                    if self.splash.winfo_exists():
                        self.splash.destroy()

            # แสดง main window และตั้งค่าให้ไม่มีขอบ
            self.root.deiconify()
            self.root.overrideredirect(True)  # สำคัญ: ต้องตั้งค่าหลังจาก deiconify
            self.root.update()  # บังคับให้ window อัพเดท
            self.logging_manager.log_info("MagicBabel application started and ready")

            # 🔧 FORCE STATUS UPDATE: Schedule update after startup completes
            self.root.after(2000, self._delayed_status_update)

            # หยุด rainbow animation ตอนเริ่มต้นโปรแกรม (ไม่ควรแสดงตอนยังไม่แปล)

            # เพิ่มการโหลดข้อมูล NPC
            self.reload_npc_data()
            self.logging_manager.log_info("Reloaded NPC data during startup")

            # Starter guide auto-show disabled - removed to prevent unwanted website opening

            # เริ่มระบบ monitoring สำหรับ button states
            self.start_window_state_monitor()

            # 🚀 AUTO-START: ตรวจสอบและเริ่ม auto-start translation
            self.setup_auto_start()

            # 🔥 WARMUP: Schedule translation warmup injection
            # IMPORTANT: Schedule AFTER auto-start delay to ensure translation is active
            auto_start_delay = self.settings.get('auto_start_delay', 3) * 1000  # milliseconds
            warmup_additional_delay = int(self.settings.get('warmup_delay', 0.8) * 1000)
            total_warmup_delay = auto_start_delay + warmup_additional_delay

            self.logging_manager.log_info(f"🔥 [WARMUP] Scheduling warmup {total_warmup_delay}ms after ready state")
            self.root.after(total_warmup_delay, self._inject_warmup_message)

        except Exception as e:
            self.logging_manager.log_error(f"Error in _complete_startup: {e}")
            # กรณีเกิดข้อผิดพลาด ให้แสดง main window

    def _inject_warmup_message(self):
        """
        Inject warmup message to pre-initialize Gemini API
        Reduces first translation delay from 500-2000ms to 200-500ms

        IMPORTANT: Only warmup if translation is active (after auto-start or manual start)
        """
        try:
            # Check if warmup enabled
            if not self.settings.get('enable_translation_warmup', True):
                self.logging_manager.log_info("🔥 [WARMUP] Warmup disabled")
                return

            # CRITICAL: Only warmup if translation is already active
            # This ensures warmup happens AFTER auto-start (not before)
            if not self.is_translating:
                self.logging_manager.log_info("🔥 [WARMUP] Skipped - translation not active yet (will warmup after START)")
                return

            # Validate dependencies
            if not hasattr(self, 'dalamud_handler') or not self.dalamud_handler:
                self.logging_manager.log_warning("🔥 [WARMUP] Skipped - handler not ready")
                return

            self.logging_manager.log_info("🔥 [WARMUP] Starting translation warmup...")
            start_time = time.time()

            # Create warmup message with current timestamp
            # IMPORTANT: Use current time to pass timestamp filter
            warmup_message = {
                "Type": "battle",
                "Speaker": "System",
                "Message": "⚔️ MagicBabel Battle Chat Ready!",
                "Timestamp": int(time.time() * 1000),
                "ChatType": 68  # Battle Chat mode - test ChatType 68
            }

            # Inject through handler
            self.dalamud_handler.process_message(warmup_message)

            duration = time.time() - start_time
            self.logging_manager.log_info(f"🔥 [WARMUP] Injection completed in {duration:.2f}s")

        except Exception as e:
            self.logging_manager.log_error(f"Warmup injection error: {e}")

    def start_window_state_monitor(self):
        """เริ่มระบบ monitoring สถานะหน้าต่างอย่างต่อเนื่อง"""
        self.check_window_states()
        # ตั้งเวลาให้ตรวจสอบทุก 5 วินาที (ประหยัดทรัพยากร)
        self.root.after(5000, self.start_window_state_monitor)

    def check_window_states(self):
        """ตรวจสอบสถานะหน้าต่างทั้งหมดและอัปเดตปุ่มตามสถานะจริง"""
        try:
            if hasattr(self, "button_state_manager"):
                # ใช้ async version เพื่อไม่ block UI
                self.button_state_manager.sync_all_states_async()
        except Exception as e:
            self.logging_manager.log_warning(f"Error checking window states: {e}")
            self.root.deiconify()
            self.root.overrideredirect(True)

    def _clear_active_temp_areas(self):
        """ทำลายหน้าต่างและยกเลิก animation ของ temporary areas ที่กำลังแสดงผลอยู่"""
        # logging.debug(f"Clearing active temporary areas: {list(self._active_temp_area_widgets.keys())}")
        for area, widgets in list(self._active_temp_area_widgets.items()):
            if widgets:
                fade_job = widgets.get("fade_job")
                window = widgets.get("window")

                # ยกเลิก after job ถ้ามี
                if fade_job:
                    try:
                        self.root.after_cancel(fade_job)
                        # logging.debug(f"Cancelled fade job for area {area}")
                    except ValueError:  # อาจจะถูก cancel ไปแล้ว
                        pass
                    except Exception as e:
                        logging.warning(
                            f"Error cancelling fade job for area {area}: {e}"
                        )

                # ทำลายหน้าต่างถ้ายังอยู่
                if window and window.winfo_exists():
                    try:
                        window.destroy()
                        # logging.debug(f"Destroyed temporary window for area {area}")
                    except tk.TclError:  # อาจจะถูกทำลายไปแล้ว
                        pass
                    except Exception as e:
                        logging.warning(
                            f"Error destroying temporary window for area {area}: {e}"
                        )

        # เคลียร์ dictionary
        self._active_temp_area_widgets.clear()
        # logging.debug("Active temporary areas cleared.")

    def trigger_temporary_area_display(self, area_string):
        """Callback ที่ถูกเรียกโดย Control_UI เพื่อแสดงพื้นที่ของ Preset ปัจจุบันชั่วคราว"""
        try:
            # 1. ตรวจสอบว่าฟังก์ชัน Show Area แบบ manual กำลังทำงานอยู่หรือไม่
            if self.is_area_shown:
                logging.info(
                    "Manual 'Show Area' is active, skipping temporary display."
                )
                # อาจจะพิจารณาอัพเดท label บนพื้นที่ manual แทน ถ้าต้องการ
                return

            # 2. ตรวจสอบการสลับ Preset อย่างรวดเร็ว
            current_time = time.time()
            time_since_last = current_time - self._last_preset_switch_display_time
            # logging.debug(f"Time since last temp display: {time_since_last:.2f}s")

            # 3. ล้าง Area ชั่วคราวที่อาจค้างอยู่ก่อนแสดงผลใหม่
            self._clear_active_temp_areas()

            # 4. แยกพื้นที่จาก string
            areas_to_display = sorted(
                [a for a in area_string.split("+") if a in ["A", "B", "C"]]
            )
            if not areas_to_display:
                logging.warning(f"No valid areas in area_string: '{area_string}'")
                return

            # 5. ตัดสินใจว่าจะแสดงผลแบบไหน
            if time_since_last < self._min_preset_display_interval:
                # --- สลับเร็วกว่ากำหนด: แสดงแบบเร็ว ไม่มี Animation ---
                logging.info(
                    f"Rapid preset switch detected (interval {time_since_last:.2f}s < {self._min_preset_display_interval:.2f}s). Showing quick area display."
                )
                self._show_quick_area(areas_to_display, duration=1000)  # แสดง 1 วินาที
            else:
                # --- สลับปกติ: แสดงแบบ Animation ---
                logging.info(
                    f"Showing animated area display for areas: {areas_to_display}"
                )
                self._show_animated_area(
                    areas_to_display, duration=1800, fade_duration=300
                )  # แสดง 1.8 วินาที, fade 0.3 วิ

            # 6. อัพเดทเวลาล่าสุดที่แสดงผล
            self._last_preset_switch_display_time = current_time

        except Exception as e:
            self.logging_manager.log_error(
                f"Error in trigger_temporary_area_display: {e}"
            )
            import traceback

            traceback.print_exc()

    def _show_animated_area(self, areas_to_display, duration=1800, fade_duration=300):
        """แสดงพื้นที่ที่ระบุพร้อม Animation Fade-in/Fade-out และ Label"""
        try:
            logging.info(
                f"--- Starting _show_animated_area for: {areas_to_display} ---"
            )  # Log เริ่มต้น
            base_alpha = 0.6  # ความโปร่งใสสูงสุดตอนแสดงผล
            steps = 10  # จำนวนขั้นในการ fade
            interval = (
                fade_duration // steps if steps > 0 else fade_duration
            )  # เวลาระหว่างแต่ละ step (ms)
            if interval <= 0:
                interval = 10  # ป้องกัน interval เป็น 0 หรือลบ

            # *** เพิ่ม: ล้างข้อมูลเก่าก่อนเริ่มสร้างใหม่ (ย้ายมาจาก trigger) ***
            self._clear_active_temp_areas()

            created_windows = 0  # ตัวนับจำนวน window ที่สร้างสำเร็จ

            for area in areas_to_display:
                logging.debug(f"Processing area: {area}")
                translate_area = self.settings.get_translate_area(area)

                # *** เพิ่ม Log ตรวจสอบข้อมูลพิกัด ***
                if not translate_area:
                    logging.warning(
                        f"No coordinates found for area '{area}' in settings."
                    )
                    continue
                logging.debug(f"Coordinates for area '{area}': {translate_area}")

                # คำนวณพิกัดและขนาด
                scale_x, scale_y = self.get_screen_scale()
                start_x_coord = translate_area.get("start_x", 0)
                start_y_coord = translate_area.get("start_y", 0)
                end_x_coord = translate_area.get("end_x", 0)
                end_y_coord = translate_area.get("end_y", 0)

                x = int(start_x_coord * scale_x)
                y = int(start_y_coord * scale_y)
                width = int((end_x_coord - start_x_coord) * scale_x)
                height = int((end_y_coord - start_y_coord) * scale_y)

                # *** เพิ่ม Log ตรวจสอบขนาด ***
                logging.debug(
                    f"Calculated geometry for area '{area}': w={width}, h={height}, x={x}, y={y}"
                )

                # ป้องกันขนาดเล็กหรือติดลบ
                if width <= 1 or height <= 1:
                    logging.warning(
                        f"Area '{area}' size is invalid ({width}x{height}), skipping display."
                    )
                    continue

                # สร้างหน้าต่าง Toplevel
                try:
                    window = tk.Toplevel(self.root)
                    window.overrideredirect(True)
                    window.attributes("-topmost", True)
                    window.geometry(f"{width}x{height}+{x}+{y}")
                    window.config(bg="black")  # สีที่จะทำให้โปร่งใส
                    window.attributes("-transparentcolor", "black")

                    # สร้างกรอบสีแดงบางๆ ภายใน Canvas
                    canvas = tk.Canvas(
                        window, bg="black", highlightthickness=0
                    )  # Canvas ใช้ bg สีโปร่งใส
                    canvas.pack(fill=tk.BOTH, expand=True)
                    canvas.create_rectangle(
                        1, 1, width - 1, height - 1, outline="red", width=2
                    )  # วาดกรอบ

                    # ตั้งค่า Alpha เริ่มต้นเป็น 0 (มองไม่เห็น)
                    window.attributes("-alpha", 0.0)

                    # สร้าง Label ตัวอักษร (A, B, C) บน Canvas
                    label_font = ("Nasalization Rg", 18, "bold")
                    label_widget = tk.Label(
                        canvas, text=area, fg="white", bg="red", font=label_font, padx=4
                    )
                    canvas.create_window(
                        5, 2, window=label_widget, anchor="nw"
                    )  # ตำแหน่งมุมบนซ้าย

                    logging.debug(f"Window and label created for area '{area}'.")
                    created_windows += 1

                    # เก็บ widget ไว้ใน dictionary (สำคัญ: ต้องทำก่อนเริ่ม animation)
                    self._active_temp_area_widgets[area] = {
                        "window": window,
                        "label": label_widget,
                        "fade_job": None,
                    }

                    # --- Fade In Animation ---
                    # ใช้ nested function เพื่อให้แน่ใจว่า lambda จับค่า window และ area ที่ถูกต้อง ณ เวลาสร้าง
                    def create_fade_in_lambda(target_area, target_window, step_num):
                        def step_action():
                            # ตรวจสอบก่อนทำงานในแต่ละ step
                            if target_area not in self._active_temp_area_widgets:
                                return
                            active_widgets = self._active_temp_area_widgets[target_area]
                            win = active_widgets.get("window")
                            if (
                                not win
                                or not win.winfo_exists()
                                or win != target_window
                            ):  # ตรวจสอบว่าเป็น window เดิมหรือไม่
                                if target_area in self._active_temp_area_widgets:
                                    del self._active_temp_area_widgets[target_area]
                                return

                            current_alpha = (step_num / steps) * base_alpha
                            try:
                                win.attributes("-alpha", current_alpha)
                            except tk.TclError:
                                if target_area in self._active_temp_area_widgets:
                                    del self._active_temp_area_widgets[target_area]
                                return

                            if step_num < steps:
                                next_step_lambda = create_fade_in_lambda(
                                    target_area, target_window, step_num + 1
                                )
                                job_id = self.root.after(interval, next_step_lambda)
                                if target_area in self._active_temp_area_widgets:
                                    self._active_temp_area_widgets[target_area][
                                        "fade_job"
                                    ] = job_id
                            else:
                                # เมื่อ Fade In เสร็จ ตั้งเวลาสำหรับ Fade Out
                                fade_out_delay = duration - fade_duration
                                if fade_out_delay < 0:
                                    fade_out_delay = 100
                                # สร้าง lambda สำหรับ fade out โดยเฉพาะ
                                fade_out_lambda = (
                                    lambda: self._fade_out_and_destroy_temp_area(
                                        target_area, base_alpha, steps, interval
                                    )
                                )
                                job_id = self.root.after(
                                    fade_out_delay, fade_out_lambda
                                )
                                if target_area in self._active_temp_area_widgets:
                                    self._active_temp_area_widgets[target_area][
                                        "fade_job"
                                    ] = job_id

                        return step_action

                    # เริ่ม Fade In สำหรับ window ปัจจุบัน
                    initial_fade_in_lambda = create_fade_in_lambda(area, window, 1)
                    self.root.after(
                        10, initial_fade_in_lambda
                    )  # หน่วงเล็กน้อยก่อนเริ่ม fade แรก

                except Exception as create_error:
                    logging.error(
                        f"Error creating window/widgets for area '{area}': {create_error}"
                    )
                    # พยายามทำลาย window ที่อาจสร้างไปแล้วบางส่วน
                    if "window" in locals() and window.winfo_exists():
                        try:
                            window.destroy()
                        except:
                            pass
                    continue  # ไปยัง area ถัดไป

            logging.info(
                f"--- Finished _show_animated_area, created {created_windows} windows ---"
            )

        except Exception as e:
            self.logging_manager.log_error(f"Error in _show_animated_area: {e}")
            self._clear_active_temp_areas()  # เคลียร์ทั้งหมดถ้ามีปัญหา

    def _fade_out_and_destroy_temp_area(self, area, start_alpha, steps, interval):
        """จัดการ Animation Fade-out และทำลายหน้าต่างชั่วคราว"""
        if area not in self._active_temp_area_widgets:
            return  # ไม่มี area นี้แล้ว

        widgets = self._active_temp_area_widgets[area]
        window = widgets.get("window")
        if not window or not window.winfo_exists():
            if area in self._active_temp_area_widgets:
                del self._active_temp_area_widgets[area]
            return

        # --- Fade Out Animation ---
        def fade_out_step(current_step):
            # ตรวจสอบก่อนทำงานในแต่ละ step
            if area not in self._active_temp_area_widgets:
                return
            local_widgets = self._active_temp_area_widgets[area]
            local_window = local_widgets.get("window")
            if not local_window or not local_window.winfo_exists():
                if area in self._active_temp_area_widgets:
                    del self._active_temp_area_widgets[area]
                return  # หยุดถ้า window ถูกลบไปแล้ว

            current_alpha = (current_step / steps) * start_alpha
            try:
                local_window.attributes("-alpha", current_alpha)
            except tk.TclError:  # Window อาจถูกทำลายไปแล้ว
                if area in self._active_temp_area_widgets:
                    del self._active_temp_area_widgets[area]
                return

            if current_step > 0:
                job_id = self.root.after(
                    interval, lambda s=current_step - 1: fade_out_step(s)
                )
                # ตรวจสอบอีกครั้งก่อน assign job_id
                if area in self._active_temp_area_widgets:
                    self._active_temp_area_widgets[area]["fade_job"] = job_id
            else:
                # เมื่อ Fade Out เสร็จ ทำลายหน้าต่างและลบออกจาก dict
                try:
                    if local_window.winfo_exists():
                        local_window.destroy()
                except:
                    pass  # ป้องกัน error ถ้า window หายไปแล้ว
                finally:
                    if area in self._active_temp_area_widgets:
                        del self._active_temp_area_widgets[area]
                    # logging.debug(f"Fade out complete, temporary area {area} destroyed.")

        # เริ่ม Fade Out (เริ่มจาก step เต็ม)
        fade_out_step(steps)

    def _show_quick_area(self, areas_to_display, duration=1000):
        """แสดงพื้นที่อย่างรวดเร็วโดยไม่มี Animation หรือ Label"""
        try:
            logging.info(f"--- Starting _show_quick_area for: {areas_to_display} ---")
            quick_alpha = 0.5  # ความโปร่งใสของกรอบแบบเร็ว

            # *** เพิ่ม: ล้างข้อมูลเก่าก่อนเริ่มสร้างใหม่ (ย้ายมาจาก trigger) ***
            self._clear_active_temp_areas()

            created_windows = 0

            for area in areas_to_display:
                logging.debug(f"Processing quick area: {area}")
                translate_area = self.settings.get_translate_area(area)

                if not translate_area:
                    logging.warning(
                        f"No coordinates found for area '{area}' in settings (quick)."
                    )
                    continue
                logging.debug(f"Coordinates for quick area '{area}': {translate_area}")

                # คำนวณพิกัดและขนาด
                scale_x, scale_y = self.get_screen_scale()
                start_x_coord = translate_area.get("start_x", 0)
                start_y_coord = translate_area.get("start_y", 0)
                end_x_coord = translate_area.get("end_x", 0)
                end_y_coord = translate_area.get("end_y", 0)

                x = int(start_x_coord * scale_x)
                y = int(start_y_coord * scale_y)
                width = int((end_x_coord - start_x_coord) * scale_x)
                height = int((end_y_coord - start_y_coord) * scale_y)

                logging.debug(
                    f"Calculated quick geometry for area '{area}': w={width}, h={height}, x={x}, y={y}"
                )

                # ป้องกันขนาดเล็กหรือติดลบ
                if width <= 1 or height <= 1:
                    logging.warning(
                        f"Area '{area}' size is invalid ({width}x{height}), skipping quick display."
                    )
                    continue

                # สร้างหน้าต่าง Toplevel
                try:
                    window = tk.Toplevel(self.root)
                    window.overrideredirect(True)
                    window.attributes("-topmost", True)
                    window.geometry(f"{width}x{height}+{x}+{y}")
                    window.config(bg="black")
                    window.attributes("-transparentcolor", "black")
                    canvas = tk.Canvas(window, bg="black", highlightthickness=0)
                    canvas.pack(fill=tk.BOTH, expand=True)
                    canvas.create_rectangle(
                        1, 1, width - 1, height - 1, outline="red", width=2
                    )  # วาดกรอบ

                    window.attributes(
                        "-alpha", quick_alpha
                    )  # แสดงผลทันทีด้วย alpha ที่กำหนด
                    created_windows += 1

                    # เก็บ widget (เฉพาะ window) และตั้งเวลาทำลาย
                    self._active_temp_area_widgets[area] = {
                        "window": window,
                        "label": None,
                        "fade_job": None,
                    }
                    destroy_lambda = lambda a=area: self._destroy_temp_area(a)
                    job_id = self.root.after(duration, destroy_lambda)
                    # ตรวจสอบก่อน assign job_id
                    if area in self._active_temp_area_widgets:
                        self._active_temp_area_widgets[area]["fade_job"] = job_id

                except Exception as create_error:
                    logging.error(
                        f"Error creating quick window for area '{area}': {create_error}"
                    )
                    if "window" in locals() and window.winfo_exists():
                        try:
                            window.destroy()
                        except:
                            pass
                    continue  # ไปยัง area ถัดไป

            logging.info(
                f"--- Finished _show_quick_area, created {created_windows} windows ---"
            )

        except Exception as e:
            self.logging_manager.log_error(f"Error in _show_quick_area: {e}")
            self._clear_active_temp_areas()  # เคลียร์ทั้งหมดถ้ามีปัญหา

    def _destroy_temp_area(self, area):
        """ทำลายหน้าต่างของ temporary area ที่ระบุ"""
        if area in self._active_temp_area_widgets:
            widgets = self._active_temp_area_widgets[area]
            window = widgets.get("window")
            if window and window.winfo_exists():
                try:
                    window.destroy()
                except:
                    pass  # ป้องกัน error ถ้า window หายไปแล้ว
            # ใช้ pop เพื่อลบและคืนค่า ถ้าต้องการ log เพิ่มเติม
            self._active_temp_area_widgets.pop(area, None)
            # logging.debug(f"Quick temporary area {area} destroyed.")

    # ============================================================================
    # Callback Handler for Control UI Events
    # ============================================================================
    def handle_control_ui_event(self, event_name, value):
        """
        จัดการ Event ที่ส่งมาจาก Control UI (เช่น การเปลี่ยนโหมด Click Translate)

        Args:
            event_name (str): ชื่อของ event ที่เกิดขึ้น (เช่น "click_translate_mode_changed")
            value: ค่าที่เกี่ยวข้องกับ event (เช่น True/False สำหรับ click_translate)
        """
        if event_name == "click_translate_mode_changed":
            # ตรวจสอบว่า translation_event ถูกสร้างหรือยัง
            # ควรจะถูกสร้างใน init_variables หรือ init_ocr_and_translation
            if not hasattr(self, "translation_event") or not isinstance(
                self.translation_event, threading.Event
            ):
                logging.error("Translation event not initialized or invalid type.")
                # อาจจะแจ้งเตือนผู้ใช้หรือพยายามสร้างใหม่ แต่ตอนนี้แค่ log error
                return

            logging.info(f"Received click_translate_mode_changed event: {value}")

            # อัพเดทสถานะ UI ทันที
            if value:
                self._update_status_line(
                    "🖱️ 1-Click Mode: ON (Use FORCE button or right-click to translate)"
                )
            else:
                self._update_status_line("")  # No default status message

            # จัดการการทำงานของลูปแปลภาษา
            if value:
                # ถ้า Click Translate เปิด: ให้ลูปหยุดรอ (โดยการ clear event)
                # การ clear จะทำให้ wait() ในลูป block จนกว่าจะมีการ set()
                self.translation_event.clear()
                logging.debug(
                    "Translation event cleared (Click Translate ON). Loop will wait."
                )
            else:
                # ถ้า Click Translate ปิด: ปลุกให้ลูปทำงานต่อ (โดยการ set event)
                # การ set จะทำให้ wait() ในลูปที่กำลัง block อยู่หลุดออกมาทำงานต่อ
                self.translation_event.set()
                logging.debug(
                    "Translation event set (Click Translate OFF). Loop will resume."
                )

            # หมายเหตุ: เราไม่จำเป็นต้องเปลี่ยนค่า self.is_translating ที่นี่
            # เพราะการ Start/Stop การแปลโดยรวมยังคงควบคุมด้วยปุ่ม Start/Stop หลัก
            # Click Translate เป็นเพียงการควบคุมว่าจะให้ลูปทำงาน *อัตโนมัติ* หรือไม่
            # เมื่อ is_translating เป็น False ลูปจะไม่ทำงานอยู่แล้ว ไม่ว่า Click Translate จะเป็นอะไรก็ตาม

    def toggle_theme(self):
        """เปิดหน้าต่างจัดการธีม"""
        # ตรวจสอบว่ามีหน้าต่างจัดการธีมเปิดอยู่หรือไม่
        if (
            hasattr(self, "theme_manager_window")
            and self.theme_manager_window.winfo_exists()
        ):
            # ถ้ามีหน้าต่างเปิดอยู่แล้ว ให้ปิด
            self.theme_manager_window.destroy()
            # ไม่จำเป็นต้องจัดการสีปุ่ม theme ที่นี่ เพราะ _apply_theme_update จะจัดการเมื่อธีมเปลี่ยน
            return

        # สร้างหน้าต่างใหม่
        self.theme_manager_window = tk.Toplevel(self.root)
        self.theme_manager_window.title("Theme Manager")
        self.theme_manager_window.overrideredirect(True)

        # กำหนดสีพื้นหลัง (ดึงจาก appearance_manager)
        self.theme_manager_window.configure(bg=appearance_manager.bg_color)

        # สร้าง UI จัดการธีม
        theme_ui = appearance_manager.create_theme_manager_ui(
            self.theme_manager_window, self.settings
        )
        theme_ui.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # ตำแหน่งหน้าต่าง (ด้านขวาของหน้าต่างหลัก)
        x = self.root.winfo_x() + self.root.winfo_width() + 10
        y = self.root.winfo_y()
        self.theme_manager_window.geometry(f"+{x}+{y}")

        # *** Callback ถูกตั้งค่าถาวรใน __init__ แล้ว ไม่ต้องตั้งค่าที่นี่ ***
        # appearance_manager.set_theme_change_callback(self._apply_theme_update)

        # ผูก events สำหรับการเคลื่อนย้ายหน้าต่าง
        self.theme_manager_window.bind("<Button-1>", self.start_move_theme_window)
        self.theme_manager_window.bind("<B1-Motion>", self.do_move_theme_window)

        # จัดการเมื่อปิดหน้าต่าง (อาจจะไม่จำเป็น ถ้า callback จัดการถูกต้อง)
        self.theme_manager_window.protocol("WM_DELETE_WINDOW", self.close_theme_manager)

        # รอให้หน้าต่างแสดงผลเสร็จ แล้วทำให้ขอบโค้งมน
        self.theme_manager_window.update_idletasks()
        self.apply_rounded_corners_to_theme_window()  # เมธอดนี้อาจจะต้องปรับปรุงให้ใช้ Windows API หรือวิธีอื่นที่เหมาะสม

        # บันทึกธีมปัจจุบันเพิ่มเติมเพื่อความมั่นใจ (อาจจะไม่จำเป็น)
        # current_theme = appearance_manager.get_current_theme()
        # self.settings.set("theme", current_theme)
        # self.settings.save_settings()

        # บันทึกลอก
        self.logging_manager.log_info("เปิดหน้าต่างจัดการธีม")

    def restart_control_ui(self):
        """รีสตาร์ท Control UI เพื่อใช้ธีมใหม่"""
        try:
            # ตรวจสอบว่ามี control_ui หรือไม่
            if not hasattr(self, "control_ui") or not self.control_ui:
                self.logging_manager.log_info(
                    "Control UI not found, nothing to restart"
                )
                return False

            # เก็บข้อมูลสถานะปัจจุบันไว้
            current_areas = self.current_area
            current_preset = (
                self.control_ui.current_preset
                if hasattr(self.control_ui, "current_preset")
                else 1
            )
            was_visible = False
            control_ui_pos = None

            # ตรวจสอบตำแหน่งและสถานะการแสดงผลปัจจุบัน
            if hasattr(self.control_ui, "root") and self.control_ui.root.winfo_exists():
                was_visible = self.control_ui.root.state() != "withdrawn"
                # เก็บตำแหน่งปัจจุบัน
                if was_visible:
                    control_ui_pos = (
                        self.control_ui.root.winfo_x(),
                        self.control_ui.root.winfo_y(),
                    )
                # ปิดหน้าต่างเดิม
                self.control_ui.root.destroy()

            # บันทึกข้อมูลเกี่ยวกับการรีสตาร์ท
            self.logging_manager.log_info("Restarting Control UI with current theme")
            self.logging_manager.log_info(
                f"Current areas: {current_areas}, Preset: {current_preset}"
            )

            # สร้าง Control UI ใหม่
            control_root = tk.Toplevel(self.root)
            control_root.protocol("WM_DELETE_WINDOW", lambda: self.on_control_close())
            self.control_ui = Control_UI(
                control_root,
                self.show_previous_dialog,
                self.switch_area,
                self.settings,
                parent_callback=self.handle_control_ui_event,  # Add parent callback for event handling
                on_close_callback=self.on_control_close,
            )

            # เพิ่มบรรทัดนี้เพื่อตั้งค่า callback สำหรับ CPU limit
            self.control_ui.set_cpu_limit_callback(self)

            # คืนค่าสถานะเดิม
            areas = (
                current_areas.split("+")
                if isinstance(current_areas, str)
                else current_areas
            )
            for area in ["A", "B", "C"]:
                self.control_ui.area_states[area] = area in areas

            # คืนค่า preset
            self.control_ui.current_preset = current_preset
            self.control_ui.update_preset_display()
            self.control_ui.update_button_highlights()

            # เพิ่ม callback สำหรับปรับความเร็ว OCR
            self.control_ui.speed_callback = self.set_ocr_speed

            # คืนค่าตำแหน่งหน้าต่าง (ถ้ามี)
            if control_ui_pos and control_root.winfo_exists():
                control_root.geometry(f"+{control_ui_pos[0]}+{control_ui_pos[1]}")

            # เปิดหน้าต่างหากเดิมเปิดอยู่
            if was_visible:
                self.control_ui.show_window()
                # CON button removed - no UI update needed
            else:
                control_root.withdraw()

            self.logging_manager.log_info("Control UI restarted successfully")
            return True

        except Exception as e:
            self.logging_manager.log_error(f"Error restarting Control UI: {e}")
            # ถ้าเกิดข้อผิดพลาดให้พยายามสร้าง Control UI ใหม่แบบพื้นฐาน
            try:
                if not hasattr(self, "control_ui") or not self.control_ui:
                    control_root = tk.Toplevel(self.root)
                    control_root.protocol(
                        "WM_DELETE_WINDOW", lambda: self.on_control_close()
                    )
                    self.control_ui = Control_UI(
                        control_root,
                        self.show_previous_dialog,
                        self.switch_area,
                        self.settings,
                        parent_callback=self.handle_control_ui_event,  # Add parent callback for event handling
                        on_close_callback=self.on_control_close,
                    )
                    control_root.withdraw()
            except:
                pass
            return False

    def start_move_theme_window(self, event):
        """เริ่มต้นการเคลื่อนย้ายหน้าต่าง Theme Manager"""
        self.theme_x = event.x
        self.theme_y = event.y

    def do_move_theme_window(self, event):
        """เคลื่อนย้ายหน้าต่าง Theme Manager"""
        if hasattr(self, "theme_x") and hasattr(self, "theme_y"):
            deltax = event.x - self.theme_x
            deltay = event.y - self.theme_y
            x = self.theme_manager_window.winfo_x() + deltax
            y = self.theme_manager_window.winfo_y() + deltay
            self.theme_manager_window.geometry(f"+{x}+{y}")

    def close_theme_manager(self):
        """ปิดหน้าต่าง Theme Manager และรีเซ็ต callback"""
        if (
            hasattr(self, "theme_manager_window")
            and self.theme_manager_window.winfo_exists()
        ):
            self.theme_manager_window.destroy()
        appearance_manager.set_theme_change_callback(None)

    def apply_rounded_corners_to_theme_window(self):
        """ปรับให้หน้าต่าง Theme Manager ไม่มีขอบวินโดว์ (ไม่ต้องมีขอบโค้ง)"""
        try:
            # รอให้หน้าต่างแสดงผลเสร็จ
            self.theme_manager_window.update_idletasks()

            # ใช้เพียง overrideredirect แทนการใช้ Windows API
            self.theme_manager_window.overrideredirect(True)

        except Exception as e:
            self.logging_manager.log_error(f"Error applying window style: {e}")

    def _apply_theme_update(self):
        """
        Apply the current theme to all relevant UI components.
        Handles both modern (Canvas) and standard (tk.Button) widgets now.
        """
        try:
            log_func = getattr(self.logging_manager, "log_info", print)
            print("DEBUG: _apply_theme_update called")
            log_func("Applying theme update across all components...")

            # --- ดึงค่าสีหลัก ---
            theme_accent = appearance_manager.get_accent_color()
            theme_highlight = appearance_manager.get_highlight_color()
            theme_secondary = appearance_manager.get_theme_color("secondary")
            theme_button_bg = appearance_manager.get_theme_color("button_bg", "#262637")
            theme_bg_color = appearance_manager.bg_color
            theme_text = appearance_manager.get_theme_color("text", "#ffffff")
            theme_text_dim = appearance_manager.get_theme_color("text_dim", "#b2b2b2")
            theme_error = appearance_manager.get_theme_color("error", "#e74c3c")
            bottom_button_inactive_bg = theme_button_bg
            bottom_button_active_state_bg = "#404040"
            bottom_bg = "#141414"  # สีพื้นหลังส่วนล่าง

            # --- 1. อัพเดท Widget ที่ MBB.py เป็นเจ้าของโดยตรง ---
            # ... (โค้ดอัพเดท main_frame, header_frame, content_frame, ปุ่ม Modern, Status, Swap Button เหมือนเดิม) ...
            if hasattr(self, "main_frame") and self.main_frame.winfo_exists():
                self.main_frame.configure(bg=theme_bg_color)
                # ... (โค้ดอัพเดท Header widgets) ...
                header_frame, content_frame = None, None
                for i, child in enumerate(self.main_frame.winfo_children()):
                    if isinstance(child, tk.Frame) and child.winfo_exists():
                        if i == 0:
                            header_frame = child
                            header_frame.configure(bg=theme_bg_color)
                        elif i == 1:
                            content_frame = child
                            content_frame.configure(bg=theme_bg_color)
                # NOTE: Header widgets (logo, version, pin, theme, close buttons) are now handled by HeaderBar.update_theme()
                # if header_frame:
                #     for widget in header_frame.winfo_children():
                #         ... (commented out - delegated to HeaderBar)
                if content_frame:
                    for child in content_frame.winfo_children():
                        if isinstance(child, tk.Frame) and child.winfo_exists():
                            child.configure(bg=theme_bg_color)
                    # OCR Area Selection removed - area buttons deleted from buttons_to_update list (15 lines)
                    buttons_to_update = [  # Canvas only
                        (
                            getattr(self, "start_stop_button", None),
                            theme_accent,
                            appearance_manager.get_theme_color("accent_light"),
                        ),
                        (
                            getattr(self, "settings_button", None),
                            theme_button_bg,
                            theme_accent,
                        ),
                        (
                            getattr(self, "npc_manager_button", None),
                            theme_button_bg,
                            theme_accent,
                        ),
                    ]
                    for button, base_color, hover_color in buttons_to_update:
                        if (
                            button
                            and isinstance(button, tk.Canvas)
                            and hasattr(button, "button_bg")
                            and button.winfo_exists()
                        ):
                            try:
                                button.configure(bg=theme_bg_color)
                                is_selected = getattr(button, "selected", False)
                                is_hovering = getattr(button, "_is_hovering", False)
                                if button == getattr(self, "start_stop_button", None):
                                    button.original_bg = (
                                        theme_secondary if is_selected else theme_accent
                                    )
                                # OCR Area Selection removed - area button color handling deleted
                                else:
                                    button.original_bg = (
                                        "#404060" if is_selected else theme_button_bg
                                    )
                                button.hover_bg = hover_color
                                current_display_color = (
                                    button.hover_bg
                                    if is_hovering
                                    else button.original_bg
                                )
                                # OCR Area Selection removed - area button color check deleted
                                if is_selected and button == getattr(
                                    self, "start_stop_button", None
                                ):
                                    current_display_color = theme_secondary
                                button.itemconfig(
                                    button.button_bg, fill=current_display_color
                                )
                                if hasattr(button, "button_text"):
                                    text_color = theme_text
                                    if is_selected and button in [
                                        getattr(self, "settings_button", None),
                                        # show_area_button reference removed
                                        getattr(self, "npc_manager_button", None),
                                        getattr(self, "start_stop_button", None),
                                    ]:
                                        text_color = theme_highlight
                                    button.itemconfig(
                                        button.button_text, fill=text_color
                                    )
                            except tk.TclError:
                                logging.warning(
                                    f"TclError updating modern button: {button}"
                                )
                    status_frame_widget = None
                    if (
                        hasattr(self, "status_label")
                        and self.status_label.winfo_exists()
                    ):
                        self.status_label.configure(
                            fg=theme_secondary, bg=theme_bg_color
                        )
                        if isinstance(self.status_label.master, tk.Frame):
                            status_frame_widget = self.status_label.master
                            status_frame_widget.configure(bg=theme_bg_color)
                        #     bg_color=theme_bg_color,
                        #     fg_color=appearance_manager.get_theme_color("secondary"),
                        #     canvas_bg="#1a1a1a",
                        # )
                    # NOTE: swap_data_button is now handled by ControlPanel.update_theme()
                    # if (
                    #     hasattr(self, "swap_data_button")
                    #     and self.swap_data_button.winfo_exists()
                    # ):
                    #     ... (commented out - delegated to ControlPanel)

            # อัพเดท Info Label และ Frame ด้านล่าง
            if hasattr(self, "info_label") and self.info_label.winfo_exists():
                self.update_info_label_with_model_color()
                if isinstance(self.info_label.master, tk.Frame):
                    self.info_label.master.configure(bg=bottom_bg)
            if (
                hasattr(self, "bottom_container")
                and self.bottom_container.winfo_exists()
            ):
                self.bottom_container.configure(bg=bottom_bg)
                for child in self.bottom_container.winfo_children():
                    if isinstance(child, tk.Frame) and child.winfo_exists():
                        child.configure(bg=bottom_bg)
                    # *** เพิ่ม: อัพเดทสี Label คำอธิบาย ***
                    elif isinstance(child, tk.Label) and child == getattr(
                        self, "bottom_button_description_label", None
                    ):
                        child.configure(bg=bottom_bg, fg=theme_text_dim)

            # NOTE: bottom_settings_button is now handled by BottomBar.update_theme()
            # --- อัพเดทปุ่ม Settings ---
            # if (
            #     hasattr(self, "bottom_settings_button")
            #     and self.bottom_settings_button
            #     and self.bottom_settings_button.winfo_exists()
            # ):
            #     ... (commented out - delegated to BottomBar)

            # --- อัปเดต ButtonStateManager colors ---
            if hasattr(self, "button_state_manager"):
                self.button_state_manager.update_theme_colors()
                # Re-apply current states with new colors
                for button_key in ["tui", "log"]:  # NOTE: mini and con removed
                    current_state = self.button_state_manager.button_states[button_key][
                        "active"
                    ]
                    visual_state = "toggle_on" if current_state else "toggle_off"
                    self.button_state_manager.update_button_visual(
                        button_key, visual_state
                    )

            # NOTE: Bottom buttons (tui, log, mini, npc_manager, settings) are now handled by BottomBar.update_theme()
            # --- อัพเดทปุ่มล่าง (tk.Button) และ Re-bind Hover ---
            # bottom_buttons_map = {...}
            # ... (commented out - delegated to BottomBar)

            # OCR Area Selection removed - update_area_button_highlights call deleted (19 lines)

            # --- 2. เรียก update_theme ของ Component ย่อย ---
            # Update new UI components
            if hasattr(self, "header_bar") and self.header_bar:
                try:
                    self.header_bar.update_theme()
                    log_func("HeaderBar theme updated.")
                except Exception as e:
                    logging.error(f"Error updating HeaderBar theme: {e}")

            if hasattr(self, "control_panel") and self.control_panel:
                try:
                    self.control_panel.update_theme()
                    log_func("ControlPanel theme updated.")
                except Exception as e:
                    logging.error(f"Error updating ControlPanel theme: {e}")

            if hasattr(self, "bottom_bar") and self.bottom_bar:
                try:
                    self.bottom_bar.update_theme()
                    log_func("BottomBar theme updated.")
                except Exception as e:
                    logging.error(f"Error updating BottomBar theme: {e}")

            # Update other UI components
            if (
                hasattr(self, "mini_ui")
                and self.mini_ui
                and self.mini_ui.mini_ui
                and self.mini_ui.mini_ui.winfo_exists()
            ):
                try:
                    self.mini_ui.update_theme(theme_accent, theme_highlight)
                    log_func("MiniUI theme updated.")
                except Exception as e:
                    logging.error(f"Error updating MiniUI theme: {e}")
            if (
                hasattr(self, "control_ui")
                and self.control_ui
                and self.control_ui.root
                and self.control_ui.root.winfo_exists()
            ):
                try:
                    print("DEBUG: Calling control_ui.update_theme()")
                    self.control_ui.update_theme()
                    log_func("ControlUI theme updated.")
                    print("DEBUG: control_ui.update_theme() completed")
                except Exception as e:
                    logging.error(f"Error updating ControlUI theme: {e}")
                    print(f"DEBUG: Error calling control_ui.update_theme(): {e}")
            if (
                hasattr(self, "settings_ui")
                and self.settings_ui.settings_visible
                and self.settings_ui.settings_window
                and self.settings_ui.settings_window.winfo_exists()
            ):
                try:
                    if hasattr(self.settings_ui, "update_theme"):
                        self.settings_ui.update_theme()
                    else:
                        self.settings_ui.settings_window.configure(bg=theme_bg_color)
                        logging.warning("SettingsUI missing update_theme")
                except Exception as e:
                    logging.error(f"Error updating SettingsUI theme: {e}")

            log_func("Theme update applied successfully.")

        except Exception as e:
            print(
                f"CRITICAL Error applying theme update: {e}"
            )  # ใช้ print ถ้า logging ไม่พร้อม
            if hasattr(self, "logging_manager"):
                self.logging_manager.log_error(f"Error applying theme update: {e}")
            import traceback

            traceback.print_exc()

    def update_mini_ui_theme(self, accent_color, highlight_color):
        """อัพเดทธีมสำหรับ Mini UI"""
        if not hasattr(self, "mini_ui") or not self.mini_ui:
            return

        # อัพเดทสีปุ่มใน mini_ui
        try:
            if hasattr(self.mini_ui, "mini_ui") and self.mini_ui.mini_ui:
                # ค้นหาปุ่มที่มีข้อความ "⇄"
                for child in self.mini_ui.mini_ui.winfo_children():
                    if isinstance(child, tk.Frame):
                        for widget in child.winfo_children():
                            if (
                                isinstance(widget, tk.Button)
                                and widget.cget("text") == "⇄"
                            ):
                                widget.configure(fg=highlight_color)
                                break

                # อัพเดทปุ่ม Start/Stop
                if hasattr(self.mini_ui, "start_button"):
                    # ปรับสีตามสถานะการแปล
                    if self.mini_ui.is_translating:
                        pass  # คงสถานะเดิม
                    else:
                        # ใช้สีตามธีมปัจจุบัน
                        accent_light = appearance_manager.themes[
                            appearance_manager.current_theme
                        ]["accent_light"]
                        self.mini_ui.start_button.configure(
                            activebackground=accent_color
                        )

                        # อัพเดทเหตุการณ์ hover
                        self.mini_ui.start_button.bind(
                            "<Enter>",
                            lambda e: self.mini_ui.start_button.config(bg="#666666"),
                        )
                        self.mini_ui.start_button.bind(
                            "<Leave>",
                            lambda e: self.mini_ui.start_button.config(
                                bg=appearance_manager.bg_color
                            ),
                        )
        except Exception as e:
            logging.error(f"Error updating mini UI theme: {e}")

    def create_modern_button(
        self,
        parent,
        text,
        command,
        width=95,
        height=30,
        fg="#ffffff",
        bg=None,
        hover_bg=None,
        font=("Nasalization Rg", 10),
    ):
        """สร้างปุ่มโมเดิร์นสำหรับ Control UI - CYBERPUNK STYLE"""
        # กำหนดค่าสีเริ่มต้นจากธีมปัจจุบันถ้าไม่ได้ระบุมา
        if bg is None:
            bg = appearance_manager.get_theme_color("button_bg", "#1a1a2e")  # Dark background
        if hover_bg is None:
            hover_bg = appearance_manager.get_theme_color("button_bg", "#1a1a2e")  # Keep dark on hover

        # Get border color
        border_color = appearance_manager.get_accent_color()  # Cyan or magenta

        # บันทึกสีที่ใช้สำหรับดีบัก
        self.logging_manager.log_info(
            f"Creating CYBERPUNK button '{text}' with bg={bg}, border={border_color}"
        )

        # สร้าง canvas สำหรับวาดปุ่ม
        canvas = tk.Canvas(
            parent,
            width=width,
            height=height,
            bg=appearance_manager.bg_color,
            highlightthickness=0,
            bd=0,
        )

        # วาดรูปทรงปุ่ม - SIMPLE RECTANGLE (ไม่มีมุมโค้ง) + DARK BACKGROUND + BRIGHT BORDER
        button_bg = canvas.create_rectangle(
            2, 2, width-2, height-2,
            fill=bg,  # Dark background
            outline=border_color,  # Bright cyan/magenta border
            width=2
        )

        # สร้างข้อความบนปุ่ม - BRIGHT TEXT
        button_text = canvas.create_text(
            width // 2, height // 2, text=text,
            fill=border_color,  # Match border color for consistency
            font=font
        )

        # ผูกคำสั่งเมื่อคลิก
        canvas.bind("<Button-1>", lambda event: command())

        # เพิ่ม tag สำหรับระบุสถานะ hover
        canvas._is_hovering = False

        # วาด CYBER CORNER ACCENTS - ปรับตำแหน่งเพื่อไม่ให้ทับกับขอบหลัก
        corner_size = 10
        accent_offset = 4  # ระยะห่างจากขอบ
        accent_items = []

        # Top-left corner
        accent_items.append(canvas.create_line(
            accent_offset, accent_offset,
            accent_offset + corner_size, accent_offset,
            fill=border_color, width=2, capstyle=tk.PROJECTING
        ))
        accent_items.append(canvas.create_line(
            accent_offset, accent_offset,
            accent_offset, accent_offset + corner_size,
            fill=border_color, width=2, capstyle=tk.PROJECTING
        ))

        # Top-right corner
        accent_items.append(canvas.create_line(
            width - accent_offset, accent_offset,
            width - accent_offset - corner_size, accent_offset,
            fill=border_color, width=2, capstyle=tk.PROJECTING
        ))
        accent_items.append(canvas.create_line(
            width - accent_offset, accent_offset,
            width - accent_offset, accent_offset + corner_size,
            fill=border_color, width=2, capstyle=tk.PROJECTING
        ))

        # Bottom-left corner
        accent_items.append(canvas.create_line(
            accent_offset, height - accent_offset,
            accent_offset + corner_size, height - accent_offset,
            fill=border_color, width=2, capstyle=tk.PROJECTING
        ))
        accent_items.append(canvas.create_line(
            accent_offset, height - accent_offset,
            accent_offset, height - accent_offset - corner_size,
            fill=border_color, width=2, capstyle=tk.PROJECTING
        ))

        # Bottom-right corner
        accent_items.append(canvas.create_line(
            width - accent_offset, height - accent_offset,
            width - accent_offset - corner_size, height - accent_offset,
            fill=border_color, width=2, capstyle=tk.PROJECTING
        ))
        accent_items.append(canvas.create_line(
            width - accent_offset, height - accent_offset,
            width - accent_offset, height - accent_offset - corner_size,
            fill=border_color, width=2, capstyle=tk.PROJECTING
        ))

        # สร้าง hover effect - GLOW EFFECT (ใช้สีเดียวกัน ไม่เปลี่ยน width)
        def on_enter(event):
            if hasattr(canvas, "selected") and canvas.selected:
                return

            # เก็บสถานะว่ากำลัง hover
            canvas._is_hovering = True

            # CYBERPUNK GLOW: เพิ่มความสว่างของขอบและข้อความ
            glow_color = appearance_manager.get_theme_color("accent_light", "#4cfefe")

            # เปลี่ยนสีขอบและข้อความเป็นสีสว่างขึ้น (ไม่เปลี่ยน width)
            canvas.itemconfig(button_bg, outline=glow_color)
            canvas.itemconfig(button_text, fill=glow_color)

            # เปลี่ยนสี cyber accents (ไม่เปลี่ยน width)
            for item in accent_items:
                canvas.itemconfig(item, fill=glow_color)

        def on_leave(event):
            # ยกเลิกสถานะ hover
            canvas._is_hovering = False

            if not hasattr(canvas, "selected") or not canvas.selected:
                # คืนสีเดิม (ไม่เปลี่ยน width)
                canvas.itemconfig(button_bg, outline=border_color)
                canvas.itemconfig(button_text, fill=border_color)

                # คืนสี cyber accents (ไม่เปลี่ยน width)
                for item in accent_items:
                    canvas.itemconfig(item, fill=border_color)

        canvas.bind("<Enter>", on_enter)
        canvas.bind("<Leave>", on_leave)

        # เพิ่ม metadata สำหรับการใช้งานภายหลัง
        canvas.selected = False
        canvas.original_bg = bg
        canvas.hover_bg = hover_bg
        canvas.button_bg = button_bg
        canvas.button_text = button_text
        canvas.border_color = border_color
        canvas.accent_items = accent_items  # Store cyber accent references

        # สร้างฟังก์ชันที่ใช้ itemconfig แทน config - CYBERPUNK VERSION
        def update_button(text=None, fg=None, bg=None, border=None):
            try:
                if text is not None and canvas.winfo_exists():
                    canvas.itemconfig(button_text, text=text)
                if fg is not None and canvas.winfo_exists():
                    # Update text color
                    canvas.itemconfig(button_text, fill=fg)
                if bg is not None and canvas.winfo_exists():
                    # ถ้าไม่ได้อยู่ในสถานะ hover ให้อัพเดตพื้นหลัง
                    if not canvas._is_hovering:
                        canvas.itemconfig(button_bg, fill=bg)
                    # อัพเดทสีเดิมเสมอ
                    canvas.original_bg = bg
                if border is not None and canvas.winfo_exists():
                    # Update border color
                    if not canvas._is_hovering:
                        canvas.itemconfig(button_bg, outline=border)
                        canvas.itemconfig(button_text, fill=border)
                        # Update cyber accents
                        for item in canvas.accent_items:
                            canvas.itemconfig(item, fill=border)
                    canvas.border_color = border
            except Exception as e:
                print(f"Error in button update: {e}")

        canvas.update_button = update_button
        return canvas

    def create_breathing_effect(self):
        """สร้าง breathing effect แบบสมูทสำหรับไฟแสดงสถานะ"""

        # คลาสสำหรับจัดการ breathing effect
        class BreathingEffect:
            def __init__(self, label, interval=30, min_alpha=0.3, max_alpha=1.0):
                self.label = label
                self.interval = interval
                self.min_alpha = min_alpha
                self.max_alpha = max_alpha
                self.current_alpha = min_alpha
                self.step = 0.05
                self.direction = 1  # 1 = เพิ่มค่า, -1 = ลดค่า
                self.active = False
                self.after_id = None  # เพิ่มตัวแปรเก็บ ID ของ after callback

                # ใช้รูปภาพเดิม
                self.original_image = Image.open("assets/red_icon.png").resize((20, 20))

                # สร้างภาพไว้ใช้งาน
                self.create_images()

            def create_images(self):
                """สร้างภาพสำหรับแสดงผล breathing effect"""
                # สร้างภาพวงกลมสีแดงที่มีความโปร่งใสต่างๆ จากรูปภาพเดิม
                self.images = {}
                self.current_image = None

                for alpha in range(30, 101, 5):  # 0.3 ถึง 1.0 ในขั้นที่ 0.05
                    alpha_val = alpha / 100

                    # คัดลอกภาพต้นฉบับ
                    img = self.original_image.copy().convert("RGBA")

                    # ปรับค่า alpha ของภาพ
                    data = img.getdata()
                    new_data = []
                    for item in data:
                        # ถ้าเป็นพิกเซลที่มีสี (ไม่ใช่พื้นที่โปร่งใส)
                        if item[3] > 0:
                            # คงค่าสี RGB เดิม แต่ปรับค่า alpha
                            new_data.append(
                                (item[0], item[1], item[2], int(255 * alpha_val))
                            )
                        else:
                            new_data.append(item)  # คงค่าพิกเซลที่โปร่งใสเดิมไว้

                    img.putdata(new_data)

                    # เก็บภาพไว้ใน dict
                    self.images[alpha_val] = ImageTk.PhotoImage(img)

                # กำหนดภาพเริ่มต้น
                self.current_image = self.images[self.min_alpha]
                self.label.config(image=self.current_image)

            def start(self):
                """เริ่ม breathing effect"""
                self.active = True
                self.breathe()

            def stop(self):
                """หยุด breathing effect อย่างสมบูรณ์"""
                self.active = False
                # ยกเลิกการตั้งเวลา callback ถ้ามี
                if self.after_id is not None:
                    self.label.after_cancel(self.after_id)
                    self.after_id = None
                # รีเซ็ตไปที่ภาพเริ่มต้น
                self.label.config(image=self.black_icon)

            def breathe(self):
                """สร้าง breathing effect แบบต่อเนื่อง"""
                if not self.active:
                    return

                # คำนวณค่า alpha ใหม่
                self.current_alpha += self.step * self.direction

                # เช็คขอบเขตและเปลี่ยนทิศทาง
                if self.current_alpha >= self.max_alpha:
                    self.current_alpha = self.max_alpha
                    self.direction = -1
                elif self.current_alpha <= self.min_alpha:
                    self.current_alpha = self.min_alpha
                    self.direction = 1

                # หาค่า alpha ที่ใกล้เคียงที่สุดที่มีในแคช
                closest_alpha = min(
                    self.images.keys(), key=lambda x: abs(x - self.current_alpha)
                )

                # อัพเดทรูปภาพ
                self.label.config(image=self.images[closest_alpha])

                # เรียกตัวเองอีกครั้งหลังจากพักตามเวลาที่กำหนด
                if self.active:  # ตรวจสอบอีกครั้งก่อนตั้งเวลาเรียกตัวเอง
                    self.after_id = self.label.after(self.interval, self.breathe)

        # Rainbow progress bar replaces breathing effect
        # No longer need breathing effect as we use rainbow animation
        return None

    def on_settings_close(self):
        """เรียกเมื่อหน้าต่าง Settings ถูกปิด"""
        # Settings button uses icon - no text update needed
        self.update_button_highlight(self.settings_button, False)

    def on_npc_manager_close(self):
        """เรียกเมื่อหน้าต่าง NPC Manager ถูกปิด"""
        self.update_button_highlight(self.npc_manager_button, False)

    def on_translated_ui_close(self):
        """เรียกเมื่อหน้าต่าง Translated UI ถูกปิด"""
        if hasattr(self, "button_state_manager"):
            self.button_state_manager.set_button_state("tui", False)

    def on_translated_logs_close(self):
        """เรียกเมื่อหน้าต่าง Translated Logs ถูกปิด"""
        if hasattr(self, "button_state_manager"):
            self.button_state_manager.set_button_state("log", False)

    def on_control_close(self):
        """เรียกเมื่อหน้าต่าง Control UI ถูกปิด"""
        # CON button removed - no UI update needed
        pass

    def on_mini_ui_close(self):
        """เรียกเมื่อหน้าต่าง Mini UI ถูกปิด"""
        # อัพเดตสถานะหรือแสดง main UI ถ้าจำเป็น
        self.root.deiconify()

    def init_mini_ui(self):
        self.mini_ui = MiniUI(self.root, self.show_main_ui_from_mini)
        self.mini_ui.set_toggle_translation_callback(self.toggle_translation)
        self.mini_ui.blink_interval = self.blink_interval

    def create_translated_logs(self):
        try:
            logging.info("Creating translated logs window...")

            # สร้าง window
            self.translated_logs_window = tk.Toplevel(self.root)

            # เพิ่ม protocol handler
            self.translated_logs_window.protocol(
                "WM_DELETE_WINDOW", lambda: self.on_translated_logs_close()
            )

            # สร้างและเก็บ instance
            self.translated_logs_instance = Translated_Logs(
                self.translated_logs_window, self.settings
            )

            # *** อัปเดต reference เพื่อให้ MBB.py ใช้ window ที่ถูกต้อง ***
            self.translated_logs_window = self.translated_logs_instance.root

            # ไม่ต้อง withdraw() ที่นี่ เพราะ Translated_Logs จะเริ่มในสถานะซ่อนเองแล้ว
            self.logging_manager.log_info("Translated logs created successfully")

        except Exception as e:
            self.logging_manager.log_error(f"Error creating translated logs: {e}")
            logging.exception("Detailed error in create_translated_logs:")
            # *** เพิ่มบรรทัดนี้: กำหนดค่าเป็น None หากเกิดข้อผิดพลาด ***
            self.translated_logs_instance = None

    def load_shortcuts(self):
        self.toggle_ui_shortcut = self.settings.get_shortcut("toggle_ui", "alt+h")
        self.start_stop_shortcut = self.settings.get_shortcut(
            "start_stop_translate", "f9"
        )

    def handle_error(self, error_message):
        self.logging_manager.log_error(f"Error: {error_message}")

    def load_icons(self):
        self.blink_icon = ImageTk.PhotoImage(
            Image.open("assets/red_icon.png").resize((20, 20))
        )
        self.black_icon = ImageTk.PhotoImage(
            Image.open("assets/black_icon.png").resize((20, 20))
        )
        self.pin_icon = ImageTk.PhotoImage(
            Image.open("assets/pin.png").resize((20, 20))
        )
        self.unpin_icon = ImageTk.PhotoImage(
            Image.open("assets/unpin.png").resize((20, 20))
        )

    def create_main_ui(self):
        # ปรับขนาดหน้าต่างหลัก (เพิ่มความสูง)
        self.root.geometry(
            "300x330"
        )  # ลดความสูงทีละนิด (เอาปุ่ม Guide ออกแล้ว)
        self.root.overrideredirect(True)

        # เพิ่ม rounded corners ให้ UI หลัก
        self.root.after(
            100, lambda: self.apply_rounded_corners(self.root, 16)
        )  # เรียกหลังจาก UI โหลดเสร็จ - เพิ่มความโค้ง 2 เท่า

        current_bg_color = appearance_manager.bg_color

        # Main frame
        self.main_frame = tk.Frame(
            self.root, bg=current_bg_color, padx=10, pady=10, bd=0, highlightthickness=0
        )
        self.main_frame.pack(expand=True, fill=tk.BOTH)

        # === REDESIGNED: HeaderBar Component ===
        self.header_bar = HeaderBar(
            self.main_frame,
            self.button_factory,
            appearance_manager,
            {
                'toggle_topmost': self.toggle_topmost,
                'toggle_theme': self.toggle_theme,
                'exit_program': self.exit_program,
            }
        )
        self.header_bar.set_version(__version__)
        # Update pin state based on current topmost setting
        self.header_bar.update_pin_state(self.root.attributes("-topmost"))
        # === End HeaderBar ===

        # === REDESIGNED: ControlPanel Component ===
        # Swap Data removed - game name detection deleted
        # initial_game_name = self._get_current_npc_game_name()

        self.control_panel = ControlPanel(
            self.main_frame,
            self.button_factory,
            appearance_manager,
            {
                'toggle_translation': self.toggle_translation,
                # Swap Data removed - 'swap_npc_data' callback deleted
                # OCR Area Selection removed - 'start_selection_a/b/c' callbacks deleted
            }
        )
        # Load and display game info from NPC.json
        try:
            from Manager import get_game_info_from_json
            npc_json_path = os.path.join(os.getcwd(), "NPC.json")
            game_info = get_game_info_from_json(npc_json_path)
            if game_info and "name" in game_info:
                self.control_panel.set_swap_text(game_info["name"])
            else:
                self.control_panel.set_swap_text("Unknown")
        except Exception as e:
            print(f"Failed to load game info: {e}")
            self.control_panel.set_swap_text("Error")

        # Create content_frame reference for backward compatibility
        self.content_frame = self.control_panel.frame
        # === End ControlPanel ===

        # === REDESIGNED: BottomBar Component ===
        self.bottom_bar = BottomBar(
            self.root,
            self.button_factory,
            appearance_manager,
            self.button_state_manager,
            {
                'toggle_tui': self.toggle_translated_ui,
                'toggle_log': self.toggle_translated_logs,
                'toggle_mini': self.toggle_mini_ui,
                'toggle_npc_manager': self.toggle_npc_manager,
                'toggle_settings': self.toggle_settings,
            }
        )
        # Set initial info text
        self.bottom_bar.set_info(self.get_current_settings_info())

        # Create backward compatibility references
        self.bottom_container = self.bottom_bar.frame
        self.tui_button = self.bottom_bar.btn_tui
        self.log_button = self.bottom_bar.btn_log
        self.mini_button = self.bottom_bar.btn_mini
        self.npc_manager_button = self.bottom_bar.btn_npc_manager
        self.bottom_npc_manager_button = self.bottom_bar.btn_npc_manager
        self.settings_button = self.bottom_bar.btn_settings
        self.bottom_settings_button = self.bottom_bar.btn_settings
        self.info_label = self.bottom_bar.lbl_info
        self.bottom_button_description_label = self.bottom_bar.lbl_description
        # === End BottomBar ===

        # OCR Area Selection removed - area button references deleted
        # Create backward compatibility references for Control Panel widgets
        self.status_label = self.control_panel.lbl_status
        self.start_stop_button = self.control_panel.btn_start_stop
        self.swap_data_button = self.control_panel.btn_swap  # Swap button (UI only)

        # Update info label with model color
        self.update_info_label_with_model_color()  # เรียกเพื่อให้สีถูกต้อง

        # Guide button removed - no longer needed

        # === Tooltips for UI Components ===
        # OCR Area Selection removed - area button tooltips deleted (4 lines)

        # Control panel tooltips
        self.create_tooltip(self.start_stop_button, "<เริ่ม-หยุด> แปล")
        self.create_tooltip(self.control_panel.lbl_swap, "ฐานข้อมูลเกมปัจจุบัน")
        # Swap button disabled - no tooltip needed

        # Header bar tooltips (using new component references)
        self.create_tooltip(self.header_bar.btn_pin, "ปักหมุด")
        self.update_pin_tooltip(self.root.attributes("-topmost"))
        self.create_tooltip(self.header_bar.btn_theme, "เลือกสีในแบบของคุณ")
        self.create_tooltip(self.header_bar.btn_close, "close")

        # Bottom bar tooltips
        # NOTE: TUI, LOG, MINI buttons use lbl_description for hover text (not standard tooltips)
        # เพื่อแสดงคำอธิบายแบบพิเศษบน UI แทนกล่อง tooltip ปกติ
        self.create_tooltip(self.npc_manager_button, "จัดการข้อมูลตัวละคร")
        self.create_tooltip(self.settings_button, "ตั้งค่าโปรแกรม")

        # Hover effects และ state management ถูกจัดการโดย BottomBar component แล้ว
        # ไม่ต้อง setup hover effects ที่นี่

    # OCR Area Selection removed - update_area_button_highlights() method deleted (9 lines)

    def apply_rounded_corners(self, widget, radius):
        """ใส่ขอบโค้งมนให้ widget"""
        try:
            # รอให้ widget วาดเสร็จ
            widget.update()

            # ดึง HWND
            hwnd = widget.winfo_id()
            if hwnd == 0:
                return

            # ดึงขนาด
            width = widget.winfo_width()
            height = widget.winfo_height()

            if width <= 0 or height <= 0:
                return

            # สร้าง region โค้งมน
            from ctypes import windll

            region = windll.gdi32.CreateRoundRectRgn(
                0, 0, width, height, radius, radius
            )
            if region:
                windll.user32.SetWindowRgn(hwnd, region, True)
        except:
            pass

    def create_tooltip(self, widget, text):
        """สร้าง tooltip แบบลอยเหนือ UI ไม่มีพื้นหลัง แสดงทันที

        Args:
            widget: Widget ที่ต้องการเพิ่ม tooltip
            text: ข้อความที่จะแสดงใน tooltip (ภาษาไทย)
        """
        # Swap Data removed - swap_data_button check deleted (3 lines)

        # --- โค้ดเดิมสำหรับ Widget อื่นๆ ---
        widget._tooltip_text = text

        def show_tooltip(event):
            # เรียกใช้เมธอดภายในตัวใหม่
            self._show_tooltip_internal(widget, widget._tooltip_text)
            return None  # ไม่หยุด event propagation

        def hide_tooltip(event):
            # เรียกใช้เมธอดภายในตัวใหม่
            self._hide_tooltip_internal()
            return None  # ไม่หยุด event propagation

        # ผูก event เข้ากับ widget โดยใช้ add="+"
        widget.bind("<Enter>", show_tooltip, add="+")
        widget.bind("<Leave>", hide_tooltip, add="+")

        # เพิ่มการจัดการเมื่อ widget ถูกทำลาย
        def on_destroy(event):
            # ตรวจสอบว่า widget ที่ถูก destroy คือ widget ที่ tooltip กำลังแสดงให้หรือไม่
            # (การตรวจสอบนี้อาจจะไม่จำเป็นมากนัก แต่ใส่เผื่อไว้)
            # เราจะจัดการการซ่อน tooltip หลักๆ ผ่าน <Leave>
            pass

        widget.bind("<Destroy>", on_destroy, add="+")

    def _show_tooltip_internal(self, widget, text):
        """สร้างและแสดง Tooltip สำหรับ Widget ที่ระบุ"""
        # ซ่อน tooltip เก่าก่อน (ถ้ามี)
        if (
            hasattr(self, "tooltip_window")
            and self.tooltip_window
            and self.tooltip_window.winfo_exists()
        ):
            try:
                self.tooltip_window.destroy()
            except tk.TclError:  # อาจถูกทำลายไปแล้ว
                pass
            self.tooltip_window = None

        # สร้าง tooltip window ใหม่
        self.tooltip_window = tk.Toplevel(self.root)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.attributes("-topmost", True)

        # ใช้สีพื้นหลังจาก theme (เหมือน control_ui.py)
        try:
            bg_color = appearance_manager.get_theme_colors()["bg"]
            border_color = appearance_manager.get_theme_colors()["accent"]
        except:
            bg_color = "#1a1a1a"
            border_color = "#6c5ce7"

        # สร้าง Frame หลักพร้อมขอบสี (เหมือน control_ui.py)
        frame = tk.Frame(self.tooltip_window, bg=border_color, padx=1, pady=1)
        frame.pack()

        # สร้าง Frame ภายในสำหรับเนื้อหา (เหมือน control_ui.py)
        inner_frame = tk.Frame(frame, bg=bg_color, padx=8, pady=6)
        inner_frame.pack()

        # สร้าง Label สำหรับแสดงข้อความ (เหมือน control_ui.py)
        self.tooltip_label = tk.Label(
            inner_frame,
            text=text,
            fg="white",
            bg=bg_color,
            font=("IBM Plex Sans Thai Medium", 10),
            justify=tk.LEFT,
        )
        self.tooltip_label.pack()

        # คำนวณตำแหน่งที่จะแสดง tooltip - เหมือน control_ui.py
        self.tooltip_window.update_idletasks()  # จำเป็นต้องเรียกเพื่อให้ได้ขนาดที่ถูกต้อง
        tooltip_width = self.tooltip_window.winfo_width()
        tooltip_height = self.tooltip_window.winfo_height()

        # คำนวณตำแหน่งกึ่งกลาง - เหมือน control_ui.py
        x = widget.winfo_rootx() + (widget.winfo_width() // 2) - (tooltip_width // 2)
        y = widget.winfo_rooty() - tooltip_height - 10  # 10px เหนือ widget

        # กำหนดตำแหน่ง - เหมือน control_ui.py
        try:
            self.tooltip_window.wm_geometry(f"+{x}+{y}")
        except tk.TclError:  # Handle กรณี window ถูกทำลายระหว่าง update
            self.tooltip_window = None

    def _hide_tooltip_internal(self):
        """ซ่อนและทำลาย Tooltip ที่กำลังแสดงอยู่"""
        if (
            hasattr(self, "tooltip_window")
            and self.tooltip_window
            and self.tooltip_window.winfo_exists()
        ):
            try:
                self.tooltip_window.destroy()
            except tk.TclError:
                pass  # อาจถูกทำลายไปแล้ว
            self.tooltip_window = None

    def setup_button_events(self):
        """Setup hover effects for UI control buttons ให้ครอบคลุมทุกจุดบนปุ่ม"""
        # ตรวจสอบว่าปุ่มถูกสร้างแล้วหรือไม่
        required_buttons = ["tui_button", "log_button", "mini_button"]  # NOTE: con_button removed
        for btn_name in required_buttons:
            if not hasattr(self, btn_name):
                self.logging_manager.log_info(
                    f"Button {btn_name} not initialized yet, skipping setup"
                )
                return  # ยังไม่มีปุ่มครบ ข้ามการตั้งค่า

        # สีเมื่อ hover จากธีมปัจจุบัน
        hover_bg = appearance_manager.get_accent_color()
        normal_bg = appearance_manager.bg_color
        active_bg = "#404040"  # สีเมื่อปุ่มถูกเลือก

        for button in [
            self.tui_button,
            self.log_button,
            self.mini_button,
        ]:
            # ตรวจสอบว่าเป็นปุ่มแบบใหม่หรือเก่า
            if hasattr(button, "button_bg") and hasattr(button, "itemconfig"):
                # กรณีปุ่มแบบใหม่ (Canvas)
                # เก็บค่าเดิมไว้
                button._original_bg = button.itemcget(button.button_bg, "fill")
                button._hover_bg = hover_bg

                # ล้าง bindings เดิม (ถ้ามี) เพื่อป้องกันการทำงานซ้ำซ้อน
                button.unbind("<Enter>")
                button.unbind("<Leave>")
                button.unbind("<Motion>")

                # สร้าง hover effect ที่ชัดเจนกว่าเดิม
                def on_canvas_enter(event, btn=button):
                    if hasattr(btn, "selected") and btn.selected:
                        return
                    # ใช้สี hover ที่เข้มขึ้น
                    btn.itemconfig(btn.button_bg, fill=btn._hover_bg)
                    # เปลี่ยน cursor เป็นรูปมือ
                    btn.config(cursor="hand2")
                    # เก็บสถานะ hover
                    btn._is_hovering = True

                def on_canvas_leave(event, btn=button):
                    if hasattr(btn, "selected") and btn.selected:
                        return
                    # กลับไปใช้สีเดิม
                    btn.itemconfig(btn.button_bg, fill=btn._original_bg)
                    # กลับไปใช้ cursor ปกติ
                    btn.config(cursor="")
                    # ยกเลิกสถานะ hover
                    btn._is_hovering = False

                # ผูก event handlers ใหม่
                button.bind("<Enter>", on_canvas_enter, add="+")
                button.bind("<Leave>", on_canvas_leave, add="+")

                # สำหรับ Canvas ต้อง bind ทั้ง widget และ items ภายใน
                for item_id in button.find_all():
                    button.tag_bind(item_id, "<Enter>", on_canvas_enter, add="+")
                    button.tag_bind(item_id, "<Leave>", on_canvas_leave, add="+")

            else:
                # กรณีปุ่มแบบเก่า (Button)
                # ล้าง bindings เดิม (ถ้ามี) เพื่อป้องกันการทำงานซ้ำซ้อน
                button.unbind("<Enter>")
                button.unbind("<Leave>")
                button.unbind("<Motion>")

                # เก็บสีเดิมไว้
                button._original_bg = button.cget("bg")

                def on_button_enter(event, btn=button):
                    current_bg = btn.cget("bg")
                    if current_bg == normal_bg:
                        btn.config(bg=hover_bg, cursor="hand2")
                    elif current_bg != active_bg:  # ถ้าไม่ใช่สีเมื่อถูกเลือก
                        btn.config(bg="#595959", cursor="hand2")

                def on_button_leave(event, btn=button):
                    current_bg = btn.cget("bg")
                    if current_bg == hover_bg:
                        btn.config(bg=btn._original_bg, cursor="")
                    elif current_bg != active_bg:  # ถ้าไม่ใช่สีเมื่อถูกเลือก
                        btn.config(bg=btn._original_bg, cursor="")

                def on_button_motion(event, btn=button):
                    # เรียกใช้ enter เพื่อแน่ใจว่ามีการตอบสนอง
                    on_button_enter(event, btn)

                # ผูก event handlers
                button.bind("<Enter>", on_button_enter, add="+")
                button.bind("<Leave>", on_button_leave, add="+")
                button.bind("<Motion>", on_button_motion, add="+")

        # บันทึก log
        self.logging_manager.log_info("Enhanced button hover effects setup completed")

    def enlarge_button_hitbox(self, button, padding=5):
        """เพิ่มพื้นที่การตรวจจับเมาส์สำหรับปุ่มให้ใหญ่กว่าขนาดที่มองเห็น

        Args:
            button: ปุ่มที่ต้องการเพิ่มพื้นที่การตรวจจับ
            padding: จำนวนพิกเซลที่จะเพิ่มรอบๆ ปุ่ม (default: 5px)
        """
        if not button.winfo_exists():
            return

        # สร้าง transparent frame ที่ใหญ่กว่าปุ่ม
        if not hasattr(button, "_hitbox_frame"):
            hitbox = tk.Frame(button.master, bg="")
            hitbox.place(
                in_=button,
                x=-padding,
                y=-padding,
                width=button.winfo_width() + 2 * padding,
                height=button.winfo_height() + 2 * padding,
            )
            button._hitbox_frame = hitbox

            # ส่งต่อ events จาก hitbox ไปยังปุ่ม
            def forward_event(event, event_name):
                # สร้าง event ใหม่และส่งไปยังปุ่ม
                new_event = type("Event", (), {})()
                new_event.x = event.x - padding  # ปรับตำแหน่ง x
                new_event.y = event.y - padding  # ปรับตำแหน่ง y
                new_event.x_root = event.x_root
                new_event.y_root = event.y_root
                button.event_generate(event_name)
                return "break"  # หยุดการแพร่กระจาย event

            # ผูก events
            hitbox.bind("<Enter>", lambda e: forward_event(e, "<Enter>"), add="+")
            hitbox.bind("<Leave>", lambda e: forward_event(e, "<Leave>"), add="+")
            hitbox.bind("<Motion>", lambda e: forward_event(e, "<Motion>"), add="+")
            hitbox.bind("<Button-1>", lambda e: forward_event(e, "<Button-1>"), add="+")

            # ตรวจสอบการลบปุ่ม
            def on_button_destroy(event):
                if (
                    hasattr(button, "_hitbox_frame")
                    and button._hitbox_frame.winfo_exists()
                ):
                    button._hitbox_frame.destroy()

            button.bind("<Destroy>", on_button_destroy, add="+")

    def toggle_translated_ui(self):
        """Toggle Translated UI visibility without affecting translation state"""
        # แสดง immediate feedback ผ่าง button_state_manager
        if hasattr(self, "button_state_manager"):
            self.button_state_manager.toggle_button_immediate("tui")

        # ทำ toggle จริง
        if self.translated_ui_window.winfo_exists():
            # Check window state
            window_withdrawn = self.translated_ui_window.state() == "withdrawn"

            # *** FIX: Use self.translated_ui (TranslatedUI instance) instead of self.translated_ui_window ***
            auto_hidden = False
            if hasattr(self, 'translated_ui') and hasattr(self.translated_ui, 'state'):
                auto_hidden = self.translated_ui.state.is_window_hidden
                print(f"🔧 [TOGGLE DEBUG] auto_hidden from translated_ui: {auto_hidden}")

            print(f"🔧 [TOGGLE DEBUG] window_withdrawn: {window_withdrawn}, auto_hidden: {auto_hidden}")

            if window_withdrawn or auto_hidden:
                # *** FIX: Call force_show_tui on the correct instance ***
                if hasattr(self, 'translated_ui') and hasattr(self.translated_ui, 'force_show_tui'):
                    print(f"🔧 [TOGGLE DEBUG] Calling force_show_tui on translated_ui instance")
                    self.translated_ui.force_show_tui()
                else:
                    # Fallback for older versions
                    print(f"🔧 [TOGGLE DEBUG] Using fallback deiconify")
                    self.translated_ui_window.deiconify()
                    self.translated_ui_window.lift()
                    if hasattr(self, 'translated_ui') and hasattr(self.translated_ui, 'state'):
                        self.translated_ui.state.is_window_hidden = False
            else:
                print(f"🔧 [TOGGLE DEBUG] Withdrawing window")
                self.translated_ui_window.withdraw()
                self.on_translated_ui_close()  # เรียก callback
        else:
            # กรณีหน้าต่างถูกทำลายไปแล้ว ให้สร้างใหม่
            print(f"🔧 [TOGGLE DEBUG] Creating new translated_ui")
            self.create_translated_ui()
            self.translated_ui_window.deiconify()

    def on_translated_ui_close(self):
        """เรียกเมื่อหน้าต่าง Translated UI ถูกปิด"""
        self.logging_manager.log_info(
            "Translated UI window was closed, updating main UI button and hiding Mini UI."
        )
        # อัปเดตสถานะและแจ้ง ButtonStateManager
        # NOTE: Using ButtonStateManager only - bottom_button_states removed

        # แจ้ง ButtonStateManager ให้อัปเดตสีปุ่ม TUI ให้กลับเป็นสถานะ off
        if hasattr(self, "button_state_manager"):
            self.button_state_manager.button_states["tui"]["active"] = False
            self.button_state_manager.update_button_visual("tui", "toggle_off")

        # UI INDEPENDENCE: ไม่ซ่อน Mini UI เมื่อปิด TUI
        # Mini UI และ Main UI เป็นเพียงหน้ากาก - การซ่อน TUI ไม่ควรส่งผลต่อ Mini UI
        # self.logging_manager.log_info("TUI closed - Mini UI remains visible (UI independence)")

        # 🔄 UNIFIED SYNC: ใช้ฟังก์ชัน unified sync หลังจาก toggle เสร็จ
        current_visibility = self._is_tui_visible()
        self._sync_tui_button_state(current_visibility, "F9/TUI toggle")

        # *** TUI INDEPENDENCE ***
        # F9 ควบคุมเฉพาะ TUI การแปลแยกจากกัน
        # การกดปุ่ม TUI จะไม่หยุดการแปล (TUI independence)
        if hasattr(self, "is_translating") and self.is_translating:
            # TUI ถูกปิดโดยผู้ใช้ - การแปลยังคงทำงานต่อ
            self.logging_manager.log_info(
                "TUI closed independently - translation continues."
            )

    def get_mbb_position_info(self):
        """ตรวจจับตำแหน่งและข้อมูลจอภาพสำหรับ smart positioning ของ LOG UI"""
        try:
            # ดึงข้อมูลหน้าต่าง main
            main_x = self.root.winfo_x()
            main_y = self.root.winfo_y()
            main_width = self.root.winfo_width()
            main_height = self.root.winfo_height()

            # ดึงข้อมูลจอภาพ
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()

            # คำนวณจุดกลางของหน้าต่าง main
            main_center_x = main_x + (main_width // 2)
            screen_center_x = screen_width // 2

            # กำหนด side ตามตำแหน่งของหน้าต่าง main
            if main_center_x < screen_center_x:
                mbb_side = "left"  # หน้าต่าง main อยู่ซีกซ้าย
            else:
                mbb_side = "right"  # หน้าต่าง main อยู่ซีกขวา

            # สร้างข้อมูลจอภาพสำหรับ translated_logs
            monitor_info = {
                "left": 0,
                "right": screen_width,
                "top": 0,
                "bottom": screen_height,
                "width": screen_width,
                "height": screen_height,
            }

            print(
                f"MBB Position Info: side='{mbb_side}', main_pos=({main_x}, {main_y}), screen={screen_width}x{screen_height}"
            )

            return mbb_side, monitor_info

        except Exception as e:
            print(f"Error getting MBB position info: {e}")
            # Fallback values
            return "left", {
                "left": 0,
                "right": 1920,
                "top": 0,
                "bottom": 1080,
                "width": 1920,
                "height": 1080,
            }

    def toggle_translated_logs(self):
        """Toggle Translated Logs visibility independently"""
        logging.info("Attempting to toggle translated logs")

        # แสดง immediate feedback ผ่าน button_state_manager
        if hasattr(self, "button_state_manager"):
            self.button_state_manager.toggle_button_immediate("log")

        # 1. ตรวจสอบว่า instance ถูกสร้างสำเร็จหรือไม่ (ทั้ง hasattr และ ไม่ใช่ None)
        if (
            not hasattr(self, "translated_logs_instance")
            or self.translated_logs_instance is None
        ):
            logging.error(
                "translated_logs_instance is missing or was not created successfully."
            )
            # ลองสร้างใหม่ดูก่อน
            logging.info("Attempting to recreate translated_logs_instance...")
            self.create_translated_logs()
            # ตรวจสอบอีกครั้งหลังพยายามสร้างใหม่
            if (
                not hasattr(self, "translated_logs_instance")
                or self.translated_logs_instance is None
            ):
                logging.error("Failed to create/recreate translated_logs_instance.")
                messagebox.showwarning(
                    "Logs ไม่พร้อมใช้งาน", "ไม่สามารถเปิด/ปิดหน้าต่างประวัติการแปลได้"
                )
                # อาจจะปรับสีปุ่มกลับ ถ้าจำเป็น
                if hasattr(self, "button_state_manager"):
                    try:
                        # Use ButtonStateManager to reset button state
                        self.button_state_manager.set_button_state("log", False)
                    except Exception as btn_err:
                        logging.warning(f"Could not reset log button state: {btn_err}")
                return  # ออกจากฟังก์ชันถ้าสร้างไม่สำเร็จ

        # --- ถ้ามาถึงตรงนี้ แสดงว่า self.translated_logs_instance มีค่าและไม่ใช่ None ---

        # 2. ตรวจสอบหน้าต่าง (ต้องมี self.translated_logs_window ด้วย)

        # Debug: ตรวจสอบสถานะ window
        has_window_attr = hasattr(self, "translated_logs_window")
        window_exists = False
        if has_window_attr:
            try:
                window_exists = self.translated_logs_window.winfo_exists()
            except Exception as e:
                logging.error(f"Error checking window existence: {e}")
                window_exists = False

        if not has_window_attr or not window_exists:
            # กรณีหน้าต่างถูกทำลายไปแล้ว แต่ instance อาจจะยังอยู่ (หรือเพิ่งสร้างใหม่ด้านบน)
            logging.info(
                "Translated logs window doesn't exist or was destroyed, attempting to show/recreate..."
            )
            # Instance ควรจะมีอยู่แล้วจากการตรวจสอบด้านบน
            # เราแค่ต้องแน่ใจว่าหน้าต่างแสดงผลและตั้งค่า visibility ถูกต้อง
            try:
                # แสดงหน้าต่าง (Translated_Logs จะจัดการสร้าง/แสดง window ให้ถ้าจำเป็น)
                # show_window ใน translated_logs ควรจะ deiconify ถ้ามี window อยู่แล้ว
                # เตรียมข้อมูลสำหรับ smart positioning
                mbb_side, monitor_info = self.get_mbb_position_info()
                self.translated_logs_instance.show_window(mbb_side, monitor_info)
                # ตรวจสอบอีกครั้งว่า show_window ทำงานสำเร็จหรือไม่
                if (
                    self.translated_logs_window.winfo_exists()
                    and self.translated_logs_window.state() != "withdrawn"
                ):
                    self.translated_logs_instance.is_visible = (
                        True  # ตั้งค่า is_visible หลังแสดงหน้าต่าง
                    )
                    # ButtonStateManager จัดการสีให้แล้ว ไม่ต้อง hardcode
                    # NOTE: Using ButtonStateManager only - bottom_button_states removed
                else:
                    # ถ้า show_window ไม่สำเร็จ (อาจเกิด error ภายใน Translated_Logs)
                    logging.error(
                        "Failed to show the translated logs window after attempting."
                    )
                    messagebox.showerror("ข้อผิดพลาด", "ไม่สามารถแสดงหน้าต่างประวัติการแปลได้")
                    # รีเซ็ตปุ่มถ้าจำเป็น
                    if hasattr(self, "button_state_manager"):
                        self.button_state_manager.set_button_state("log", False)

            except Exception as show_err:
                logging.error(
                    f"Error trying to show translated logs window: {show_err}"
                )
                messagebox.showerror(
                    "ข้อผิดพลาด", f"เกิดปัญหาในการแสดงหน้าต่าง Logs: {show_err}"
                )
                # รีเซ็ตปุ่มถ้าจำเป็น
                if hasattr(self, "button_state_manager"):
                    self.button_state_manager.set_button_state("log", False)

        # 3. กรณีหน้าต่างมีอยู่แล้ว: สลับการแสดงผล
        elif self.translated_logs_window.winfo_exists():
            if self.translated_logs_window.state() == "withdrawn":
                # แสดงหน้าต่าง - ใช้ show_window เพื่อให้ logic positioning ทำงาน
                mbb_side, monitor_info = self.get_mbb_position_info()
                self.translated_logs_instance.show_window(mbb_side, monitor_info)
                self.translated_logs_instance.is_visible = True  # ตั้งค่า is_visible
                # ButtonStateManager จัดการสีให้แล้ว ไม่ต้อง hardcode
                # NOTE: Using ButtonStateManager only - bottom_button_states removed
            else:
                # ซ่อนหน้าต่าง
                self.translated_logs_window.withdraw()
                self.translated_logs_instance.is_visible = False  # ตั้งค่า is_visible
                self.on_translated_logs_close()  # เรียก callback ซึ่งควรจะเปลี่ยนสีปุ่มกลับ

    def toggle_control(self):
        """Toggle the control UI window visibility and sync its state."""
        # แสดง immediate feedback ผ่าน button_state_manager
        if hasattr(self, "button_state_manager"):
            self.button_state_manager.toggle_button_immediate("con")

        try:
            # ตรวจสอบว่า control_ui instance และ หน้าต่างของมันมีอยู่หรือไม่
            if (
                hasattr(self, "control_ui")
                and self.control_ui
                and hasattr(self.control_ui, "root")
                and self.control_ui.root.winfo_exists()
            ):
                # ถ้ามีอยู่แล้ว และกำลังซ่อนอยู่
                if self.control_ui.root.state() == "withdrawn":
                    # *** สั่งให้ Control UI อัพเดทการแสดงผลตาม state ปัจจุบันของ MBB ก่อนแสดง ***
                    current_preset_num = self.settings.get("current_preset", 1)
                    self.control_ui.update_display(
                        self.current_area, current_preset_num
                    )
                    logging.info(
                        f"Syncing Control UI before showing: areas='{self.current_area}', preset={current_preset_num}"
                    )

                    # กำหนดให้ control_ui มีการอ้างอิงถึง root window ของ main UI
                    if (
                        hasattr(self.control_ui, "parent_root")
                        and self.control_ui.parent_root != self.root
                    ):
                        self.control_ui.parent_root = self.root

                    # ลบค่าตำแหน่งที่บันทึกไว้เพื่อบังคับให้คำนวณตำแหน่งใหม่ตามที่ต้องการ
                    self.control_ui.ui_cache["position_x"] = None
                    self.control_ui.ui_cache["position_y"] = None

                    # แสดงหน้าต่าง Control UI
                    self.control_ui.show_window()  # เมธอดนี้จะเรียก position_right_of_main_ui ให้เอง

                    # CON button removed - no state management needed

                # ถ้ามีอยู่แล้ว และกำลังแสดงอยู่
                else:
                    # ซ่อนหน้าต่าง Control UI
                    self.control_ui.close_window()  # เมธอดนี้อาจจะจัดการ withdraw

                    # CON button removed - no state management needed

            # ถ้ายังไม่มี control_ui instance หรือหน้าต่างถูกทำลายไปแล้ว
            else:
                logging.info("Creating new Control UI instance.")
                control_root = tk.Toplevel(self.root)
                control_root.protocol(
                    "WM_DELETE_WINDOW", lambda: self.on_control_close()
                )

                # สร้าง instance ใหม่
                self.control_ui = Control_UI(
                    control_root,
                    self.show_previous_dialog,
                    self.switch_area,
                    self.settings,
                    parent_callback=self.handle_control_ui_event,  # Add parent callback for event handling
                    on_close_callback=self.on_control_close,
                )

                # กำหนดให้ control_ui มีการอ้างอิงถึง root window ของ main UI
                self.control_ui.parent_root = self.root

                # ลงทะเบียน callback สำหรับ CPU limit
                if hasattr(self.control_ui, "set_cpu_limit_callback"):
                    self.control_ui.set_cpu_limit_callback(self.set_cpu_limit)
                    logging.info("CPU limit callback registered with new Control UI.")
                else:
                    logging.warning(
                        "Newly created Control UI does not have set_cpu_limit_callback method."
                    )

                # *** สั่งให้ Control UI อัพเดทการแสดงผลตาม state ปัจจุบันของ MBB ทันทีหลังสร้าง ***
                current_preset_num = self.settings.get("current_preset", 1)
                self.control_ui.update_display(self.current_area, current_preset_num)
                logging.info(
                    f"Syncing new Control UI after creation: areas='{self.current_area}', preset={current_preset_num}"
                )

                # แสดงหน้าต่าง Control UI ที่สร้างใหม่
                self.control_ui.show_window()

                # NOTE: CON button removed - no state management needed

        except Exception as e:
            self.logging_manager.log_error(f"Error in toggle_control: {e}")
            import traceback

            traceback.print_exc()
            # อาจจะแสดง messagebox แจ้งผู้ใช้
            messagebox.showerror("Error", f"Could not toggle Control Panel: {e}")

    # OCR removed - method deleted
    # def set_ocr_speed(self, speed_mode):
    #     """OCR removed - project is 100% text hook"""
    #     pass

    def add_message(self, text):
        if hasattr(self, "translated_logs_instance"):
            self.translated_logs_instance.add_message(text)

    def get_current_settings_info(self):
        """รับข้อมูล Model ปัจจุบัน"""
        model = self.settings.get_displayed_model()  # ใช้ displayed_model แทน model ID
        return f"MODEL: {model}"

    def _delayed_status_update(self):
        """Delayed status update after startup completion"""
        try:
            self.logging_manager.log_info("🚀 Forcing initial status update (delayed)...")
            self.update_info_label_with_model_color()

            # Start Dalamud status timer if in Dalamud mode (independent of translation loop)
            if self.dalamud_mode:
                self._start_dalamud_status_timer()
        except Exception as e:
            self.logging_manager.log_error(f"Delayed status update error: {e}")

    def setup_auto_start(self):
        """ตั้งค่าและเริ่ม auto-start translation หากเปิดใช้งาน"""
        try:
            if self.should_auto_start():
                delay = self.settings.get('auto_start_delay', 3)
                self.logging_manager.log_info(f"🚀 Auto-start scheduled in {delay} seconds...")

                # เก็บ flag ว่า auto-start กำลังรอ
                self.auto_start_pending = True
                self.auto_start_timer_id = None

                # แสดงข้อความ countdown
                self.show_auto_start_countdown(delay)

                # กำหนดเวลา auto-start
                self.auto_start_timer_id = self.root.after(delay * 1000, self.execute_auto_start)
            else:
                self.logging_manager.log_info("Auto-start disabled or conditions not met")
        except Exception as e:
            self.logging_manager.log_error(f"Error in setup_auto_start: {e}")

    def should_auto_start(self):
        """ตรวจสอบว่าควร auto-start หรือไม่"""
        try:
            # ตรวจสอบว่าระบบพร้อมใช้งาน
            if self.is_translating or self.is_resizing:
                return False

            # ตรวจสอบ setting auto-start ทั่วไป
            auto_start_enabled = self.settings.get('auto_start_translation', False)

            # ตรวจสอบ setting auto-start สำหรับ Dalamud mode
            dalamud_auto = self.settings.get('dalamud_auto_start', True)

            # กรณี Dalamud mode: ใช้ dalamud_auto_start setting
            if self.dalamud_mode and dalamud_auto:
                self.logging_manager.log_info("Auto-start enabled: Dalamud mode with dalamud_auto_start=True")
                return True

            # กรณีทั่วไป: ใช้ auto_start_translation setting
            if auto_start_enabled:
                self.logging_manager.log_info("Auto-start enabled: general auto_start_translation=True")
                return True

            return False
        except Exception as e:
            self.logging_manager.log_error(f"Error checking auto-start conditions: {e}")
            return False

    def show_auto_start_countdown(self, delay):
        """แสดง countdown ของ auto-start"""
        try:
            self.auto_start_countdown = delay
            self.update_auto_start_status()
            self.countdown_timer()
        except Exception as e:
            self.logging_manager.log_error(f"Error in show_auto_start_countdown: {e}")

    def countdown_timer(self):
        """Timer สำหรับ countdown"""
        try:
            # 🔒 MEMORY LEAK FIX: เพิ่มการตรวจสอบป้องกัน memory leak
            if not hasattr(self, 'auto_start_pending') or not self.auto_start_pending:
                self.logging_manager.log_info("Countdown timer stopped - auto_start_pending=False")
                return

            if not hasattr(self, 'auto_start_countdown') or self.auto_start_countdown <= 0:
                self.clear_auto_start_status()
                return

            if self.auto_start_countdown > 0:
                self.update_auto_start_status()
                self.auto_start_countdown -= 1
                # 🔒 SAFETY: จำกัด max iterations ป้องกัน infinite loop
                if self.auto_start_countdown >= 0:
                    self.root.after(1000, self.countdown_timer)
                else:
                    self.clear_auto_start_status()
            else:
                self.clear_auto_start_status()

        except Exception as e:
            self.logging_manager.log_error(f"Error in countdown_timer: {e}")
            # 🔒 SAFETY: clear status on error เพื่อหยุด timer
            self.clear_auto_start_status()

    def update_auto_start_status(self):
        """อัพเดทสถานะ auto-start บน status line"""
        try:
            if hasattr(self, 'auto_start_countdown') and self.auto_start_countdown > 0:
                status_text = f"🚀 Auto-start in {self.auto_start_countdown}s (Press ESC to cancel)"
                self.logging_manager.log_info(status_text)
        except Exception as e:
            self.logging_manager.log_error(f"Error updating auto-start status: {e}")

    def clear_auto_start_status(self):
        """ล้างสถานะ auto-start"""
        try:
            if hasattr(self, 'auto_start_pending'):
                self.auto_start_pending = False
            self.logging_manager.log_info("Auto-start countdown cleared")
        except Exception as e:
            self.logging_manager.log_error(f"Error clearing auto-start status: {e}")

    def cancel_auto_start(self):
        """ยกเลิก auto-start"""
        try:
            if hasattr(self, 'auto_start_pending') and self.auto_start_pending:
                # ยกเลิก timer
                if hasattr(self, 'auto_start_timer_id') and self.auto_start_timer_id:
                    self.root.after_cancel(self.auto_start_timer_id)

                # ล้าง flags
                self.auto_start_pending = False
                self.clear_auto_start_status()
                self.logging_manager.log_info("🚫 Auto-start cancelled by user")
                return True
            return False
        except Exception as e:
            self.logging_manager.log_error(f"Error cancelling auto-start: {e}")
            return False

    def execute_auto_start(self):
        """เริ่ม translation อัตโนมัติ"""
        try:
            # 🔒 SAFETY: ตรวจสอบว่า application ยังทำงานอยู่
            if not hasattr(self, 'root') or not self.root.winfo_exists():
                self.logging_manager.log_info("🚫 Auto-start cancelled - application closing")
                return

            # ตรวจสอบว่ายังควร auto-start อยู่หรือไม่
            if not hasattr(self, 'auto_start_pending') or not self.auto_start_pending:
                return

            # ตรวจสอบสถานะระบบอีกรอบ
            if self.is_translating or self.is_resizing:
                self.logging_manager.log_info("🚫 Auto-start cancelled - system busy")
                self.clear_auto_start_status()
                return

            # 🔒 SAFETY: ตรวจสอบ translator พร้อมใช้งาน
            if not hasattr(self, 'translator') or not self.translator:
                self.logging_manager.log_info("🚫 Auto-start cancelled - translator not ready")
                self.clear_auto_start_status()
                return

            # เริ่ม translation
            self.logging_manager.log_info("🚀 Executing auto-start translation...")
            self.clear_auto_start_status()

            # เรียก toggle_translation() เหมือนกดปุ่ม START
            self.toggle_translation()

        except Exception as e:
            self.logging_manager.log_error(f"Error in execute_auto_start: {e}")
            self.clear_auto_start_status()

    def on_escape_key(self, event):
        """จัดการเมื่อกดปุ่ม ESC - ยกเลิก auto-start หาก active"""
        try:
            if self.cancel_auto_start():
                # ถ้ายกเลิก auto-start สำเร็จ ไม่ต้องทำอะไรเพิ่ม
                return
        except Exception as e:
            self.logging_manager.log_error(f"Error handling ESC key: {e}")

    def _start_dalamud_status_timer(self):
        """Start independent status update timer for Dalamud mode"""
        if not hasattr(self, '_dalamud_status_timer_active'):
            self._dalamud_status_timer_active = True
            self.logging_manager.log_info("🚀 Starting Dalamud status update timer...")
            self._schedule_dalamud_status_update()

    def _schedule_dalamud_status_update(self):
        """Schedule periodic status updates for Dalamud mode"""
        if not getattr(self, '_dalamud_status_timer_active', False):
            return

        try:
            # Update status display
            self.logging_manager.log_info("🔄 [INDEPENDENT] Updating Dalamud status display...")
            self.update_info_label_with_model_color()
        except Exception as e:
            self.logging_manager.log_error(f"Independent status update error: {e}")

        # Schedule next update in 2 seconds
        if getattr(self, '_dalamud_status_timer_active', False):
            self.root.after(2000, self._schedule_dalamud_status_update)

    def _stop_dalamud_status_timer(self):
        """Stop the independent status update timer"""
        if hasattr(self, '_dalamud_status_timer_active'):
            self._dalamud_status_timer_active = False
            self.logging_manager.log_info("🛑 Stopping Dalamud status update timer...")

    def update_info_label_with_model_color(self):
        """อัพเดทข้อความบน info_label ให้แสดงชื่อโมเดลแบบโดดเด่น"""
        if not hasattr(self, "info_label"):
            return

        # รับข้อมูลโมเดลปัจจุบัน
        model = self.settings.get_displayed_model().lower()

        # CYBERPUNK: กำหนดสีสำหรับ Gemini model
        if "gemini" in model:
            text_color = "#FF00FF"  # CYBERPUNK: Magenta (theme secondary color)
            model_icon = "⬤"
        else:
            text_color = "#B0B0B0"  # CYBERPUNK: Theme text_dim
            model_icon = "•"  # สัญลักษณ์เริ่มต้น

        # เตรียมข้อความแบบมีสัญลักษณ์ - แบบ 2 บรรทัด
        model_text = model.upper()

        # เพิ่มสถานะ Dalamud Bridge ถ้าเปิดใช้งาน
        if self.dalamud_mode:
            # 🔧 IMPROVED STATUS DETECTION: Check multiple conditions for accurate status
            is_bridge_connected = (hasattr(self, 'dalamud_bridge') and self.dalamud_bridge and self.dalamud_bridge.is_connected)
            is_translating = (hasattr(self, 'dalamud_immediate_handler') and self.dalamud_immediate_handler and self.dalamud_immediate_handler.is_translating)

            # Check if we've received any messages recently (indicates working connection)
            has_recent_messages = False
            if hasattr(self, 'dalamud_bridge') and self.dalamud_bridge:
                stats = self.dalamud_bridge.stats
                if stats.get('last_message_time') and stats.get('messages_received', 0) > 0:
                    import time
                    time_since_last = time.time() - stats['last_message_time']
                    has_recent_messages = time_since_last < 60  # Within last 60 seconds

            # 🔧 CHECK FOR ACTIVE TRANSLATION: Priority check for _translating_in_progress
            if hasattr(self, '_translating_in_progress') and self._translating_in_progress:
                # 🚀 Currently translating a message - CYBERPUNK: Bright Cyan
                bridge_status = " [DALAMUD:TRANSLATING]"
                text_color = "#00FFFF"  # CYBERPUNK: Bright Cyan (theme accent) - สว่างสุดเมื่อกำลังแปล
                if hasattr(self, 'logging_manager'):
                    self.logging_manager.log_info("🚀 Status: DALAMUD:TRANSLATING (actively translating)")

                # TUI AUTO-SHOW TRIGGER: เมื่อพบข้อความ text hook
                self._trigger_tui_auto_show()
            elif is_bridge_connected and is_translating:
                # ✅ Connected AND actively translating - CYBERPUNK: Dark Cyan
                bridge_status = " [DALAMUD:ON]"
                text_color = "#00B8D4"  # CYBERPUNK: Dark Cyan - เชื่อมต่อและกำลังแปล
                if hasattr(self, 'logging_manager'):
                    self.logging_manager.log_info("✅ Status: DALAMUD:ON (connected & translating)")
            elif is_bridge_connected or has_recent_messages:
                # ✅ Connected but not translating - CYBERPUNK: Dark Cyan
                bridge_status = " [DALAMUD:READY]"
                text_color = "#00B8D4"  # CYBERPUNK: Dark Cyan - พร้อมใช้งาน
                if hasattr(self, 'logging_manager'):
                    self.logging_manager.log_info(f"✅ Status: DALAMUD:READY (connected={is_bridge_connected}, recent_msgs={has_recent_messages})")
            else:
                # ⏳ Not connected or waiting - CYBERPUNK: Gray
                bridge_status = " [DALAMUD:WAIT]"
                text_color = "#808080"  # CYBERPUNK: Gray - รอการเชื่อมต่อ (ไม่ใช้สีแดงอีกต่อไป)
                if hasattr(self, 'logging_manager'):
                    self.logging_manager.log_info("⏳ Status: DALAMUD:WAIT (not connected)")
        else:
            bridge_status = ""

        # แสดงใน 2 บรรทัด: บรรทัดแรก MODEL, บรรทัดที่สอง DALAMUD STATUS
        if self.dalamud_mode and bridge_status:
            display_text = f"{model_icon} MODEL: {model_text}\n{bridge_status.strip()}"
            height = 2
        else:
            display_text = f"{model_icon} MODEL: {model_text}"
            height = 1

        # อัพเดทข้อความและสี
        self.info_label.config(
            text=display_text,
            bg="#141414",
            fg=text_color,
            font=("Consolas", 8, "bold"),
            height=height,
        )

    def _is_tui_visible(self):
        """ตรวจสอบว่า TUI กำลังแสดงอยู่หรือไม่"""
        try:
            if hasattr(self, 'translated_ui') and self.translated_ui:
                return self.translated_ui.root.state() != "withdrawn"
            return False
        except Exception as e:
            if hasattr(self, 'logging_manager'):
                self.logging_manager.log_error(f"Error checking TUI visibility: {e}")
            return False

    def _show_translated_ui_auto(self):
        """แสดง TUI อัตโนมัติ (สำหรับ auto-show trigger)"""
        try:
            if hasattr(self, 'translated_ui') and self.translated_ui:
                self.translated_ui.root.deiconify()
                if hasattr(self, 'logging_manager'):
                    self.logging_manager.log_info("📱 TUI Auto-Show: Displayed TUI successfully")
                return True
        except Exception as e:
            if hasattr(self, 'logging_manager'):
                self.logging_manager.log_error(f"TUI auto-show error: {e}")
        return False

    def _trigger_tui_auto_show(self):
        """TUI AUTO-SHOW: แสดง TUI เมื่อพบข้อความ text hook"""
        try:

            # Check if auto-show is enabled
            if not self.settings.get("enable_tui_auto_show", True):
                return


            # Debounce: ไม่ auto-show หากเพิ่งแสดงไปแล้ว
            import time
            current_time = time.time()
            if hasattr(self, '_last_auto_show_time'):
                if current_time - self._last_auto_show_time < 1.0:  # 1 second cooldown
                    return
            self._last_auto_show_time = current_time

            # Don't auto-show if user recently manually hid TUI
            if hasattr(self, '_user_manual_hide_time'):
                if current_time - self._user_manual_hide_time < 5.0:  # 5 second grace period
                    return

            # Only auto-show if system is in valid state
            if not self.dalamud_mode:
                return
            if not hasattr(self, 'translated_ui'):
                return


            # Only show if not already visible
            is_visible = self._is_tui_visible()

            if not is_visible:
                if self._show_translated_ui_auto():
                    self._sync_tui_button_state(True, "Auto-show trigger")
                    if hasattr(self, 'logging_manager'):
                        self.logging_manager.log_info("📱 TUI AUTO-SHOW: Displayed TUI on text hook detection")

        except Exception as e:
            if hasattr(self, 'logging_manager'):
                self.logging_manager.log_error(f"TUI auto-show trigger error: {e}")

    def toggle_topmost(self):
        # อ่านสถานะปัจจุบัน
        current_state = bool(self.root.attributes("-topmost"))
        # เปลี่ยนสถานะเป็นตรงข้าม
        new_state = not current_state
        # กำหนดสถานะใหม่
        self.root.attributes("-topmost", new_state)

        # อัพเดท HeaderBar pin state
        self.header_bar.update_pin_state(new_state)

        # อัพเดท tooltip ด้วยเมธอดใหม่
        self.update_pin_tooltip(new_state)

        # บันทึกล็อกเพื่อดีบัก
        self.logging_manager.log_info(
            f"Topmost state changed: {current_state} -> {new_state}"
        )
        self.logging_manager.log_info(f"New tooltip: {'unpin' if new_state else 'Pin'}")

    def update_pin_tooltip(self, is_pinned=None):
        """อัพเดท tooltip ของปุ่มปักหมุดตามสถานะปัจจุบัน

        Args:
            is_pinned: สถานะการปักหมุด (True/False) หรือ None เพื่อตรวจสอบสถานะปัจจุบัน
        """
        # ตรวจสอบสถานะปัจจุบันถ้าไม่ได้ระบุ
        if is_pinned is None:
            is_pinned = bool(self.root.attributes("-topmost"))

        # Get pin button from header_bar
        pin_button = self.header_bar.btn_pin

        # ลบ tooltip เดิมถ้ามี
        if hasattr(pin_button, "_tooltip") and pin_button._tooltip:
            try:
                pin_button._tooltip.destroy()
            except Exception:
                pass  # กรณีที่อาจมีข้อผิดพลาดในการทำลาย tooltip
            pin_button._tooltip = None
            pin_button._tooltip_visible = False

        # กำหนดข้อความตามสถานะการปักหมุด
        tooltip_text = "unpin" if is_pinned else "Pin"

        # ล้าง event bindings เดิม
        pin_button.unbind("<Enter>")
        pin_button.unbind("<Leave>")
        pin_button.unbind("<Motion>")

        # สร้าง tooltip ใหม่
        self.create_tooltip(pin_button, tooltip_text)

        # บันทึกสถานะปัจจุบันไว้ใน widget
        pin_button._is_pinned = is_pinned

    def toggle_npc_manager(self, character_name=None):
        """Toggle NPC Manager window

        Args:
            character_name (str, optional): Character name that was clicked (for character click flow)
        """
        # 🐛 DEBUG: Log the character name parameter
        if character_name:
            self.logging_manager.log_info(f"🔍 [TOGGLE CALLED] Character name: '{character_name}'")
        else:
            self.logging_manager.log_info("🔍 [TOGGLE CALLED] No character name (manual toggle)")

        if NPCManagerCard is None:
            messagebox.showwarning("Warning", "NPC Manager is not available.")
            return

        try:
            # 🎯 UI INDEPENDENCE: เปิด NPC Manager โดยไม่หยุดการแปล

            # ซ่อน TUI ทันที
            if hasattr(self, 'translated_ui_window') and self.translated_ui_window.winfo_exists():
                if self.translated_ui_window.state() != "withdrawn":
                    self.translated_ui_window.withdraw()
                    self.logging_manager.log_info("👁️ NPC Manager: ซ่อน TUI อัตโนมัติ")

            # อัพเดตสถานะปุ่ม TUI
            # NOTE: Using ButtonStateManager only - bottom_button_states removed
            if hasattr(self, "button_state_manager"):
                self.button_state_manager.button_states["tui"]["active"] = False
                self.button_state_manager.update_button_visual("tui", "toggle_off")

            # ล็อค UI ระหว่างทำงานหนัก
            self.lock_ui_movement()

            # แสดงไอคอนกำลังโหลด - ปิดเพื่อลบ white window แว้บ
            # self.show_loading_indicator()  # ปิดเพื่อลบ white window

            # กรณีที่ยังไม่มี instance
            if self.npc_manager is None:
                self.npc_manager = NPCManagerCard(
                    self.root,
                    reload_callback=self.reload_npc_data,
                    logging_manager=self.logging_manager,
                    stop_translation_callback=self.stop_translation,
                    parent_app=self,  # ส่ง main app instance
                )
                self.npc_manager.on_close_callback = self.on_npc_manager_close
                self.npc_manager.show_window()
                self.update_button_highlight(self.npc_manager_button, True)
                # ปลดล็อค UI และซ่อนไอคอนกำลังโหลด
                self._finish_npc_manager_loading()
                return

            # กรณีที่ window ถูกทำลายหรือไม่มีอยู่
            if (
                not hasattr(self.npc_manager, "window")
                or not self.npc_manager.window.winfo_exists()
            ):
                self.npc_manager = NPCManagerCard(
                    self.root,
                    reload_callback=self.reload_npc_data,
                    logging_manager=self.logging_manager,
                    stop_translation_callback=self.stop_translation,
                    parent_app=self,  # ส่ง main app instance
                )
                self.npc_manager.on_close_callback = self.on_npc_manager_close
                self.npc_manager.show_window()
                self.update_button_highlight(self.npc_manager_button, True)
                # ปลดล็อค UI และซ่อนไอคอนกำลังโหลด
                self._finish_npc_manager_loading()
                return

            # กรณีที่ window มีอยู่แล้ว
            window_state = self.npc_manager.window.state()
            window_viewable = self.npc_manager.window.winfo_viewable()
            is_visible = (
                window_state != "withdrawn"
                and window_viewable
            )

            # 🐛 DEBUG: Log window state for debugging immediate hiding issue
            self.logging_manager.log_info(f"🔍 [NPC TOGGLE] Window state: '{window_state}', viewable: {window_viewable}, is_visible: {is_visible}")

            # 🐛 FIX: ถ้ามี character_name หมายความว่าเป็น character click flow - ให้แสดง NPC Manager เสมอ
            if character_name:
                self.logging_manager.log_info(f"🔍 [NPC TOGGLE] Character click flow for '{character_name}' - always show NPC Manager")
                self.npc_manager.show_window()
                self.update_button_highlight(self.npc_manager_button, True)
            elif is_visible:
                self.logging_manager.log_info("🔍 [NPC TOGGLE] Manual toggle - Window is visible, hiding it")
                self.npc_manager.window.withdraw()
                self.update_button_highlight(self.npc_manager_button, False)
                if hasattr(self.npc_manager, "search_var"):
                    self.npc_manager.search_var.set("")
            else:
                self.logging_manager.log_info("🔍 [NPC TOGGLE] Manual toggle - Window is not visible, showing it")
                self.npc_manager.show_window()
                self.update_button_highlight(self.npc_manager_button, True)

            # ปลดล็อค UI และซ่อนไอคอนกำลังโหลด
            self._finish_npc_manager_loading()

        except Exception as e:
            error_msg = f"Failed to toggle NPC Manager: {str(e)}"
            self.logging_manager.log_error(error_msg)
            messagebox.showerror("Error", error_msg)
            self.npc_manager = None
            # ปลดล็อค UI และซ่อนไอคอนกำลังโหลดในกรณีเกิดข้อผิดพลาด
            self._finish_npc_manager_loading()

    def _finish_npc_manager_loading(self):
        """จัดการการทำงานหลังเสร็จสิ้นการโหลด NPC Manager"""
        if hasattr(self, "hide_loading_indicator"):
            self.hide_loading_indicator()
        # ปลดล็อค UI การเคลื่อนย้าย
        self.unlock_ui_movement()

    def reload_npc_data(self):
        """Reload NPC data and update related components"""
        self.logging_manager.log_info("Reloading NPC data...")

        if hasattr(self, "translator") and self.translator:
            self.translator.reload_data()
            self.logging_manager.log_info("Translator data reloaded")

        if hasattr(self, "text_corrector") and self.text_corrector:
            self.text_corrector.reload_data()
            # เพิ่มการตรวจสอบว่ามีข้อมูลหลังจาก reload หรือไม่
            if hasattr(self.text_corrector, "names"):
                self.logging_manager.log_info(
                    f"Loaded {len(self.text_corrector.names)} character names from NPC data"
                )
                if len(self.text_corrector.names) == 0:
                    self.logging_manager.log_warning(
                        "No character names found after reload!"
                    )

        if hasattr(self, "translated_ui"):
            if hasattr(self.text_corrector, "names"):
                character_names = self.text_corrector.names
                self.translated_ui.update_character_names(character_names)
                self.logging_manager.log_info(
                    f"Updated Translated_UI with {len(character_names)} character names"
                )

        self.logging_manager.log_info("NPC data reload completed")

    def show_main_ui_from_mini(self):
        self.save_ui_positions()
        self.mini_ui.mini_ui.withdraw()
        self.root.deiconify()
        # NOTE: ไม่ต้องเรียก overrideredirect(True) เพราะ main UI ต้องมี title bar
        self.root.attributes("-topmost", True)
        self.root.lift()
        if self.last_main_ui_pos:
            self.root.geometry(self.last_main_ui_pos)

    def create_translated_ui(self):
        self.translated_ui_window = tk.Toplevel(self.root)

        # *** ปรับปรุงส่วนนี้ทั้งหมด ***

        # 1. เตรียม Callbacks ที่ v9 ต้องการ
        # Callback สำหรับเรียก NPC Manager จาก TUI
        toggle_npc_manager_cb = (
            self.toggle_npc_manager if hasattr(self, "toggle_npc_manager") else None
        )
        # Callback สำหรับเมื่อ TUI ถูกปิด
        on_close_cb = self.on_translated_ui_close

        # 2. เตรียม character_names (เหมือนเดิม แต่ทำให้ปลอดภัยขึ้น)
        character_names = set()
        if hasattr(self, "text_corrector") and hasattr(self.text_corrector, "names"):
            character_names = self.text_corrector.names

        # 3. เตรียม font_settings
        font_settings = None
        if hasattr(self, "font_manager") and hasattr(
            self.font_manager, "font_settings"
        ):
            font_settings = self.font_manager.font_settings

        # 4. สร้าง instance ของ Translated_UI (v9) ด้วยพารามิเตอร์ที่ครบถ้วน
        self.translated_ui = translated_ui.Translated_UI(
            self.translated_ui_window,
            self.toggle_translation,
            self.stop_translation,
            None,  # 🚫 DISABLED: Force translate disabled to prevent duplicate translation
            self.toggle_main_ui,
            self.toggle_ui,
            self.settings,
            self.switch_area,
            self.logging_manager,
            character_names=character_names,
            main_app=self,  # ส่ง self (MagicBabelApp) เข้าไป
            font_settings=font_settings,  # ส่ง font_settings เข้าไป
            toggle_npc_manager_callback=toggle_npc_manager_cb,  # ส่ง callback 1
            on_close_callback=on_close_cb,  # ส่ง callback 2
        )

        # *** PREVIOUS DIALOG: ตั้งค่า callback สำหรับ Previous Dialog System ***
        if hasattr(self.translated_ui, 'previous_dialog_callback'):
            self.translated_ui.previous_dialog_callback = self.show_previous_dialog
            logging.info("📄 [CALLBACK] Previous dialog callback set successfully")
        else:
            logging.warning("📄 [CALLBACK] TranslatedUI does not have previous_dialog_callback attribute")

        # *** TUI POSITIONING: Bottom of screen, centered horizontally, 100px from bottom edge ***
        window_width = self.settings.get("width", 960)
        window_height = self.settings.get("height", 240)
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        # Center horizontally
        x = (screen_width - window_width) // 2
        # Position at bottom with 100px margin from bottom edge
        y = screen_height - window_height - 100

        self.translated_ui_window.geometry(f"+{x}+{y}")
        self.translated_ui_window.withdraw()

    def create_settings_ui(self):
        # ส่ง self เป็น main_app เข้าไปให้ SettingsUI
        self.settings_ui = SettingsUI(
            self.root,
            self.settings,
            self.apply_settings,
            self.update_hotkeys,
            main_app=self,
        )
        # OCR removed - set_ocr_toggle_callback() call deleted
        self.settings_ui.on_close_callback = self.on_settings_close
        self.settings_ui.close_settings()

    def init_translation_and_bridge(self):
        """Initialize Text Hook Translation System (no OCR - pure text hook)"""
        try:
            # OCR removed - MBB Dalamud Bridge uses 100% text hook via Dalamud

            # สร้าง text_corrector
            try:
                self.text_corrector = TextCorrector()
                # เพิ่มบรรทัดนี้เพื่อให้แน่ใจว่ามีการโหลดข้อมูล
                self.text_corrector.reload_data()
                self.logging_manager.log_info("TextCorrector initialized successfully")
            except Exception as e:
                self.logging_manager.log_error(f"Error initializing TextCorrector: {e}")
                raise ValueError(f"Failed to initialize TextCorrector: {e}")

            # ดึงข้อมูลการตั้งค่า model
            api_params = self.settings.get_api_parameters()
            if not api_params or "model" not in api_params:
                self.logging_manager.log_error("No model specified in API parameters")
                raise ValueError("No model specified in API parameters")

            model_name = api_params["model"]
            self.logging_manager.log_info(
                f"Creating translator for model: {model_name}"
            )

            # เก็บข้อมูล translator เดิมถ้ามี
            translator_before = None
            old_class = "None"
            if hasattr(self, "translator") and self.translator is not None:
                translator_before = self.translator
                old_class = translator_before.__class__.__name__
                self.logging_manager.log_info(f"Previous translator: {old_class}")

            # รีเซ็ต translator เป็น None ก่อนสร้างใหม่
            self.translator = None

            try:
                self.translator = TranslatorFactory.create_translator(self.settings)
                if not self.translator:
                    self.logging_manager.log_error(
                        f"TranslatorFactory returned None for model: {model_name}"
                    )
                    raise ValueError(
                        f"Failed to create translator for model: {model_name}"
                    )

                # ตรวจสอบประเภทของ translator ที่ได้
                translator_class = self.translator.__class__.__name__
                self.logging_manager.log_info(
                    f"Successfully created {translator_class} instance: {translator_class}"
                )

                # Log current parameters
                params = self.translator.get_current_parameters()
                self.logging_manager.log_info(f"\nCurrent translator parameters:")
                self.logging_manager.log_info(f"Model: {params.get('model')}")
                self.logging_manager.log_info(f"Max tokens: {params.get('max_tokens')}")
                self.logging_manager.log_info(
                    f"Temperature: {params.get('temperature')}"
                )
                self.logging_manager.log_info(f"Top P: {params.get('top_p', 'N/A')}")

                # บันทึกเพิ่มเติมว่าเป็นการเปลี่ยนแปลงประเภทหรือไม่
                if translator_before:
                    new_class = self.translator.__class__.__name__
                    if old_class != new_class:
                        self.logging_manager.log_info(
                            f"Translator type changed: {old_class} -> {new_class}"
                        )
                    else:
                        self.logging_manager.log_info(
                            f"Translator type unchanged: {new_class}"
                        )

                del translator_before  # คืนหน่วยความจำ

            except Exception as e:
                self.logging_manager.log_error(f"Error creating translator: {e}")
                raise ValueError(f"Failed to create translator: {e}")

            # Initialize Dalamud Bridge for real-time text hook
            try:
                self.dalamud_bridge = DalamudBridge()
                self.dalamud_mode = True  # HARDCODE: MBB Dalamud Bridge ALWAYS uses Text Hook  # Use consistent setting name
                self.last_text_hook_data = None  # For duplicate prevention


                self.logging_manager.log_info("🌉 Dalamud Bridge initialized")

                # 🔧 CREATE DALAMUD HANDLER: Following Guardian Agent analysis
                if self.dalamud_mode and self.translator:
                    try:
                        self.dalamud_handler = create_dalamud_immediate_handler(
                            translator=self.translator,
                            ui_updater=None,  # Will be set in _setup_dalamud_handler
                            main_app=self
                        )
                        self._setup_dalamud_handler()  # Configure dependencies immediately
                        self.logging_manager.log_info("✅ Dalamud handler initialized with filtering")
                    except Exception as e:
                        self.logging_manager.log_error(f"Dalamud handler creation failed: {e}")
                        self.dalamud_mode = False

            except Exception as e:
                self.logging_manager.log_warning(f"Dalamud Bridge initialization failed: {e}")
                self.dalamud_bridge = None
                self.dalamud_mode = False

            return True

        except Exception as e:
            self.logging_manager.log_error(
                f"Error initializing OCR and translation: {e}"
            )
            raise

    # OCR removed - cache methods deleted
    # def get_cached_ocr_result(self, area, image_hash):
    #     """OCR removed - project is 100% text hook"""
    #     pass

    # def cache_ocr_result(self, area, image_hash, result):
    #     """OCR removed - project is 100% text hook"""
    #     pass

    # def toggle_ocr_gpu(self):
    #     """OCR removed - project is 100% text hook"""
    #     pass

    # OCR removed - method deleted
    # def ocr_toggle_callback(self):
    #     """OCR removed - project is 100% text hook"""
    #     pass

    def init_variables(self):
        self.is_translating = False
        self.is_resizing = False
        self.translation_thread = None
        self.last_text = ""
        self.last_translation = ""
        self.last_translation_time = 0
        # force translate variables removed - no longer needed
        # 📝 ORIGINAL TEXT DISPLAY: Current text for status line display
        self.current_original_text = ""  # เก็บข้อความล่าสุดสำหรับแสดงบน status line
        self.original_text_timer = None  # Timer สำหรับซ่อนข้อความหลัง 10 วินาที

        # 📄 PREVIOUS DIALOG SYSTEM: History collection for previous dialog navigation
        self.dialog_history = []              # เก็บประวัติข้อความ (เก็บได้สูงสุด 10 ข้อความ)
        self.max_history = 10                 # จำนวนข้อความสูงสุดใน history
        self.current_history_index = -1       # ตำแหน่งปัจจุบันใน history (-1 = ข้อความล่าสุด)

        # *** REMOVED TEST DATA - ใช้เฉพาะข้อความแปลจริง ***
        # self.add_test_dialog_history()

        self.blinking = False
        self.mini_ui_blinking = False
        self.main_window_pos = None
        self.translated_window_pos = None
        self.mini_ui_pos = None
        self.settings_window_pos = None
        self.show_area_window = None
        self.is_area_shown = False
        self.x = None
        self.y = None
        self.current_area = "A"  # ค่าเริ่มต้น

        # *** เพิ่มตัวแปรใหม่สำหรับ Text Stability Check System ***
        self.unstable_text = ""  # เก็บข้อความล่าสุดที่ยังไม่นิ่ง
        self.stability_counter = 0  # ตัวนับความนิ่งของข้อความ
        self.last_stable_text = ""  # เก็บข้อความล่าสุดที่ "แปลไปแล้ว"
        self.STABILITY_THRESHOLD = 2  # ต้องเจอข้อความนิ่ง 2 ครั้งติดต่อกันถึงจะแปล

    def bind_events(self):
        self.root.bind("<Button-1>", self.start_move)
        self.root.bind("<ButtonRelease-1>", self.stop_move)
        self.root.bind("<B1-Motion>", self.do_move)
        self.root.bind("<Escape>", self.on_escape_key)

        toggle_ui_shortcut = self.settings.get_shortcut("toggle_ui", "alt+h")
        start_stop_shortcut = self.settings.get_shortcut("start_stop_translate", "f9")
        previous_dialog_shortcut = self.settings.get_shortcut(
            "previous_dialog_key", "f10"
        )

        if self.settings.get("enable_ui_toggle"):
            if "toggle_ui" in self.hotkeys:
                keyboard.remove_hotkey(self.hotkeys["toggle_ui"])
            self.hotkeys["toggle_ui"] = keyboard.add_hotkey(
                toggle_ui_shortcut, self.toggle_ui
            )

        if "start_stop_translate" in self.hotkeys:
            keyboard.remove_hotkey(self.hotkeys["start_stop_translate"])
        self.hotkeys["start_stop_translate"] = keyboard.add_hotkey(
            start_stop_shortcut, self.toggle_translated_ui
        )

        # Previous dialog hotkey functionality removed - replaced by right-click system

        if self.settings.get("enable_wasd_auto_hide"):
            try:
                # Use scan codes for reliable key detection across keyboard layouts
                # Scan codes work regardless of language layout
                wasd_scan_codes = {
                    17: "w",  # W key scan code
                    30: "a",  # A key scan code
                    31: "s",  # S key scan code
                    32: "d"   # D key scan code
                }

                bound_keys = []
                failed_keys = []

                for scan_code, description in wasd_scan_codes.items():
                    try:
                        # Remove existing hotkey if present
                        hotkey_name = f"scan_{scan_code}"
                        if hotkey_name in self.hotkeys:
                            keyboard.remove_hotkey(self.hotkeys[hotkey_name])

                        # Bind using scan code for universal keyboard layout support
                        self.hotkeys[hotkey_name] = keyboard.add_hotkey(
                            scan_code, self.hide_and_stop_translation, suppress=False
                        )
                        bound_keys.append(f"{description}(scan:{scan_code})")
                    except Exception as key_error:
                        failed_keys.append(f"{description}(scan:{scan_code}): {key_error}")
                        continue

                if bound_keys:
                    self.logging_manager.log_info(f"✅ WASD keys bound successfully: {', '.join(bound_keys)}")

                if failed_keys:
                    self.logging_manager.log_warning(f"⚠️ Failed to bind some WASD keys: {', '.join(failed_keys)}")
                    if len(failed_keys) == len(wasd_scan_codes):
                        self.logging_manager.log_error("❌ All WASD key binding failed - Administrator privileges may be required")

            except Exception as e:
                self.logging_manager.log_error(f"❌ WASD auto-hide setup failed: {e}")
                self.logging_manager.log_warning("⚠️ WASD auto-hide requires administrator privileges on Windows")

        self.logging_manager.log_info(
            f"Hotkeys bound: Toggle UI: {toggle_ui_shortcut}, Toggle TUI: {start_stop_shortcut}, Previous Dialog: {previous_dialog_shortcut}"
        )

    def update_hotkeys(self):
        self.load_shortcuts()
        self.remove_all_hotkeys()
        self.bind_events()
        self.logging_manager.log_info(
            f"Hotkeys updated: Toggle UI: {self.toggle_ui_shortcut}, Toggle TUI: {self.start_stop_shortcut}"
        )

    def apply_saved_settings(self):
        # ถ้ามี font_manager ให้ใช้ในการอัพเดตฟอนต์
        if (
            hasattr(self, "font_manager")
            and hasattr(self.font_manager, "font_settings")
            and hasattr(self, "translated_ui")
        ):
            # ใช้เมธอดใหม่เพื่ออัพเดตการตั้งค่าฟอนต์
            font_name = self.settings.get("font")
            font_size = self.settings.get("font_size")
            self.update_font_settings(font_name, font_size)

            # ยังคงอัพเดตส่วนอื่นๆ ตามปกติ
            self.translated_ui.update_transparency(self.settings.get("transparency"))
            self.translated_ui_window.geometry(
                f"{self.settings.get('width')}x{self.settings.get('height')}"
            )
        else:
            # โค้ดเดิมถ้ายังไม่มี font_manager
            self.translated_ui.update_transparency(self.settings.get("transparency"))
            self.translated_ui.adjust_font_size(self.settings.get("font_size"))
            self.translated_ui.update_font(self.settings.get("font"))
            self.translated_ui_window.geometry(
                f"{self.settings.get('width')}x{self.settings.get('height')}"
            )

        self.remove_all_hotkeys()
        self.bind_events()

    def remove_all_hotkeys(self):
        for key in list(self.hotkeys.keys()):
            try:
                keyboard.remove_hotkey(self.hotkeys[key])
                del self.hotkeys[key]
            except Exception:
                pass
        self.hotkeys.clear()

    def _remove_wasd_hotkeys(self):
        """Remove only WASD hotkeys when disabling the feature"""
        if hasattr(self, "hotkeys"):
            wasd_keys = ["scan_17", "scan_30", "scan_31", "scan_32"]  # W, A, S, D scan codes
            for key in wasd_keys:
                if key in self.hotkeys:
                    try:
                        keyboard.remove_hotkey(self.hotkeys[key])
                        del self.hotkeys[key]
                        self.logging_manager.log_info(f"🗑️ Removed WASD hotkey: {key}")
                    except Exception as e:
                        self.logging_manager.log_warning(f"⚠️ Failed to remove WASD hotkey {key}: {e}")

    def _register_wasd_hotkeys(self):
        """Register WASD hotkeys when enabling the feature"""
        try:
            wasd_scan_codes = {
                17: "w",  # W key scan code
                30: "a",  # A key scan code
                31: "s",  # S key scan code
                32: "d"   # D key scan code
            }

            bound_keys = []
            failed_keys = []

            for scan_code, description in wasd_scan_codes.items():
                try:
                    hotkey_name = f"scan_{scan_code}"
                    # Remove if already exists
                    if hotkey_name in self.hotkeys:
                        keyboard.remove_hotkey(self.hotkeys[hotkey_name])

                    # Register new hotkey
                    self.hotkeys[hotkey_name] = keyboard.add_hotkey(
                        scan_code, self.hide_and_stop_translation, suppress=False
                    )
                    bound_keys.append(f"{description}(scan:{scan_code})")
                except Exception as key_error:
                    failed_keys.append(f"{description}(scan:{scan_code}): {key_error}")

            if bound_keys:
                self.logging_manager.log_info(f"✅ WASD keys registered: {', '.join(bound_keys)}")
            if failed_keys:
                self.logging_manager.log_warning(f"⚠️ Failed to register WASD keys: {', '.join(failed_keys)}")

        except Exception as e:
            self.logging_manager.log_error(f"❌ WASD hotkey registration failed: {e}")

    def toggle_settings(self):
        if self.settings_ui.settings_visible:
            self.settings_ui.close_settings()
            # Settings button uses icon - no text update needed
            self.update_button_highlight(self.settings_button, False)
        else:
            # เปิด Settings โดยไม่หยุดการแปล
            self.logging_manager.log_info("⚙️ Settings: เปิดหน้าต่างการตั้งค่า (ไม่หยุดการแปล)")

            # ไม่ซ่อน TUI เมื่อเปิด Settings
            # ไม่ปรับสถานะปุ่ม TUI (เก็บสถานะเดิมไว้)

            # Settings button uses icon - text update not needed
            self.update_button_highlight(self.settings_button, True)

            self.settings_ui.open_settings(
                self.root.winfo_x(), self.root.winfo_y(), self.root.winfo_width()
            )
            # Settings button uses icon - text update not needed
            self.update_button_highlight(self.settings_button, True)

    # toggle_edit_area method removed - Edit Area functionality not used in this version

    def apply_settings(self, settings_dict):
        """Apply settings and update UI components"""
        try:
            # อัพเดท translated UI ถ้ามีการเปลี่ยนแปลงที่เกี่ยวข้อง
            if hasattr(self, "translated_ui") and self.translated_ui:
                if "transparency" in settings_dict:
                    self.translated_ui.update_transparency(
                        settings_dict["transparency"]
                    )

                # ใช้ font_manager ถ้ามี ในการอัพเดตการตั้งค่าฟอนต์
                if hasattr(self, "font_manager") and hasattr(
                    self.font_manager, "font_settings"
                ):
                    font_updated = False
                    font_name = None
                    font_size = None

                    if "font" in settings_dict:
                        font_name = settings_dict["font"]
                        font_updated = True

                    if "font_size" in settings_dict:
                        font_size = settings_dict["font_size"]
                        font_updated = True

                    if font_updated:
                        # ใช้เมธอดใหม่เพื่ออัพเดตฟอนต์
                        self.update_font_settings(font_name, font_size)
                else:
                    # ใช้โค้ดเดิมถ้ายังไม่มี font_manager (เพื่อความเข้ากันได้กับเวอร์ชันเก่า)
                    if "font_size" in settings_dict:
                        self.translated_ui.adjust_font_size(settings_dict["font_size"])
                    if "font" in settings_dict:
                        self.translated_ui.update_font(settings_dict["font"])

                # อัพเดทขนาดหน้าต่าง
                if "width" in settings_dict and "height" in settings_dict:
                    width = settings_dict["width"]
                    height = settings_dict["height"]
                    self.translated_ui.root.geometry(f"{width}x{height}")

                    # Force update UI
                    self.translated_ui.force_check_overflow()
                    self.translated_ui.root.update_idletasks()

            # อัพเดทค่า flags
            # Force translate setting removed - replaced by previous dialog system
            if "enable_wasd_auto_hide" in settings_dict:
                old_wasd_state = getattr(self, 'enable_wasd_auto_hide', False)
                self.enable_wasd_auto_hide = settings_dict["enable_wasd_auto_hide"]

                # 🔧 CRITICAL FIX: Re-register hotkeys when WASD setting changes
                if old_wasd_state != self.enable_wasd_auto_hide:
                    self.logging_manager.log_info(f"📌 WASD Auto Hide changed: {old_wasd_state} → {self.enable_wasd_auto_hide}")
                    # Remove all WASD hotkeys first
                    self._remove_wasd_hotkeys()
                    # If enabled, register new hotkeys
                    if self.enable_wasd_auto_hide:
                        self._register_wasd_hotkeys()

            if "enable_ui_toggle" in settings_dict:
                self.enable_ui_toggle = settings_dict["enable_ui_toggle"]

            # อัพเดท Dalamud mode
            if "dalamud_enabled" in settings_dict:
                self.dalamud_mode = True  # HARDCODE: Always use Text Hook in MBB Dalamud Bridge
                self.logging_manager.log_info("Dalamud mode ALWAYS enabled (hardcoded)")

                # ถ้าเปิด Dalamud mode และกำลังแปลอยู่ ให้เริ่ม bridge
                if self.dalamud_mode and self.is_translating:
                    if hasattr(self, 'dalamud_bridge') and not self.dalamud_bridge.is_running:
                        self.dalamud_bridge.start()
                        self.logging_manager.log_info("Started Dalamud Bridge")
                # ถ้าปิด Dalamud mode ให้หยุด bridge
                elif not self.dalamud_mode and hasattr(self, 'dalamud_bridge') and self.dalamud_bridge.is_running:
                    self.dalamud_bridge.stop()
                    self.logging_manager.log_info("Stopped Dalamud Bridge")

            # อัพเดท info label ถ้ามี
            if hasattr(self, "info_label"):
                self.update_info_label_with_model_color()

            logging.info("Settings applied successfully")
            return True

        except Exception as e:
            error_msg = f"Error applying settings: {e}"
            logging.error(error_msg)
            messagebox.showerror("Error", error_msg)
            return False

    def update_font_settings(self, font_name=None, font_size=None):
        """
        อัพเดตการตั้งค่าฟอนต์และแจ้งให้ components ทั้งหมดที่เกี่ยวข้องทราบ

        Args:
            font_name: ชื่อฟอนต์ใหม่ (ถ้ามี)
            font_size: ขนาดฟอนต์ใหม่ (ถ้ามี)
        """
        # ตรวจสอบว่ามี font_manager และ font_settings หรือไม่
        if not hasattr(self, "font_manager") or not hasattr(
            self.font_manager, "font_settings"
        ):
            return

        font_settings = self.font_manager.font_settings

        if font_name is None:
            font_name = font_settings.font_name
        if font_size is None:
            font_size = font_settings.font_size

        # ตรวจสอบ font_target_mode เพื่อกำหนดปลายทาง
        target_mode = self.settings.get("font_target_mode", "both")
        self.logging_manager.log_info(f"🎯 Font target mode: {target_mode}")

        # อัพเดตตาม target mode
        if target_mode == "translated_ui" or target_mode == "both":
            # อัพเดต TranslatedUI
            if hasattr(self, 'translated_ui') and self.translated_ui:
                self.translated_ui.update_font(font_name)
                self.translated_ui.adjust_font_size(font_size)
                self.logging_manager.log_info(f"✅ TranslatedUI font updated: {font_name} size {font_size}")

        if target_mode == "translated_logs" or target_mode == "both":
            # อัพเดต TranslatedLogs
            if hasattr(self, 'translated_logs') and self.translated_logs:
                self.translated_logs.update_font_settings(font_name, font_size)
                self.logging_manager.log_info(f"✅ TranslatedLogs font updated: {font_name} size {font_size}")

        # อัพเดตการตั้งค่าฟอนต์ผ่าน font_settings (สำหรับ observer pattern)
        font_settings.apply_font(font_name, font_size)

        # บันทึกล็อก
        self.logging_manager.log_info(f"🔤 Font applied to {target_mode}: {font_name} size {font_size}")

    def apply_font_with_target(self, font_config):
        """
        ใช้ฟอนต์ตาม target ที่กำหนดจาก Font Manager

        Args:
            font_config: dict containing 'font', 'font_size', and 'target'
        """
        if not isinstance(font_config, dict):
            return

        font_name = font_config.get("font")
        font_size = font_config.get("font_size")
        target_mode = font_config.get("target", "both")

        if not font_name or not font_size:
            return

        self.logging_manager.log_info(f"🎯 Font Manager callback - Target: {target_mode}, Font: {font_name}, Size: {font_size}")

        # อัพเดตตาม target mode ที่ส่งมาจาก Font Manager
        if target_mode == "translated_ui":
            # อัพเดตเฉพาะ TranslatedUI
            if hasattr(self, 'translated_ui') and self.translated_ui:
                self.translated_ui.update_font(font_name)
                self.translated_ui.adjust_font_size(font_size)
                self.logging_manager.log_info(f"✅ TranslatedUI only font updated: {font_name} size {font_size}")

        elif target_mode == "translated_logs":
            # อัพเดตเฉพาะ TranslatedLogs
            if hasattr(self, 'translated_logs') and self.translated_logs:
                self.translated_logs.update_font_settings(font_name, font_size)
                self.logging_manager.log_info(f"✅ TranslatedLogs only font updated: {font_name} size {font_size}")

        else:  # both or any other value
            # อัพเดตทั้งคู่
            if hasattr(self, 'translated_ui') and self.translated_ui:
                self.translated_ui.update_font(font_name)
                self.translated_ui.adjust_font_size(font_size)
                self.logging_manager.log_info(f"✅ TranslatedUI font updated: {font_name} size {font_size}")

            if hasattr(self, 'translated_logs') and self.translated_logs:
                self.translated_logs.update_font_settings(font_name, font_size)
                self.logging_manager.log_info(f"✅ TranslatedLogs font updated: {font_name} size {font_size}")

        # อัพเดตการตั้งค่าใน settings file
        self.settings.set("font", font_name)
        self.settings.set("font_size", font_size)

        # บันทึกล็อก
        self.logging_manager.log_info(f"🔤 Font applied via Font Manager to {target_mode}: {font_name} size {font_size}")

    # OCR removed - reinitialize_ocr() deleted
    # def reinitialize_ocr(self):
    #     """OCR removed - project is 100% text hook"""
    #     pass

    def update_api_settings(self):
        """อัพเดท API settings และสร้าง translator ใหม่ตามประเภท model

        Returns:
            bool: True ถ้าการอัพเดทสำเร็จ, False ถ้าไม่สำเร็จ

        หมายเหตุ: ฟังก์ชันนี้ทำหน้าที่หลักในการรีสตาร์ทระบบการแปลเมื่อมีการเปลี่ยนโมเดล
        """
        try:
            api_params = self.settings.get_api_parameters()
            if not api_params:
                logging.error("No API parameters found in settings")
                return False

            # ตรวจสอบประเภทของ translator ปัจจุบัน - ใช้เฉพาะ Gemini เท่านั้น
            is_gemini = isinstance(self.translator, TranslatorGemini)

            current_translator_type = "gemini" if is_gemini else "unknown"

            # ตรวจสอบประเภทของโมเดลใหม่
            new_model = api_params["model"]
            new_model_type = TranslatorFactory.validate_model_type(new_model)

            logging.info(
                f"Current translator type: {current_translator_type}, class: {self.translator.__class__.__name__}"
            )
            logging.info(f"New model: {new_model}, model type: {new_model_type}")

            # บันทึกการเปลี่ยนแปลงพารามิเตอร์
            self.logging_manager.log_info("\n=== API Parameters Updated ===")
            self.logging_manager.log_info(
                f"Current translator type: {current_translator_type}"
            )
            self.logging_manager.log_info(f"New model type: {new_model_type}")
            self.logging_manager.log_info(
                f"Model: {getattr(self.translator, 'model', 'unknown')} -> {new_model}"
            )
            self.logging_manager.log_info(
                f"Max tokens: {getattr(self.translator, 'max_tokens', 'N/A')} -> {api_params.get('max_tokens', 'N/A')}"
            )
            self.logging_manager.log_info(
                f"Temperature: {getattr(self.translator, 'temperature', 'N/A')} -> {api_params.get('temperature', 'N/A')}"
            )

            # ตรวจสอบว่าต้องสร้าง translator ใหม่หรือไม่ - เฉพาะ Gemini เท่านั้น
            model_changed = (
                new_model_type != "gemini" or current_translator_type != "gemini"
            )

            # ลบส่วนการตรวจสอบการเปลี่ยนแปลงพารามิเตอร์ที่ซ้ำซ้อน
            # และใช้ตัวแปรที่กำหนดไว้แล้ว
            previous_model_type = current_translator_type
            current_model_type = new_model_type

            if model_changed:
                # ยืนยันการรีสตาร์ทอีกรอบ (ครั้งที่ 2)
                confirm = messagebox.askyesno(
                    "ยืนยันการรีสตาร์ทระบบแปล",
                    f"การเปลี่ยนโมเดลจาก {previous_model_type} เป็น {current_model_type} จำเป็นต้องรีสตาร์ทระบบการแปล\n\nต้องการดำเนินการต่อหรือไม่?",
                    icon="warning",
                )

                if not confirm:
                    self.logging_manager.log_info("User cancelled restart process")
                    return False

                self.logging_manager.log_info(
                    f"Model changed from {previous_model_type} to {current_model_type}. Restarting translation system."
                )

                # =======================================
                # ส่วนสำคัญ: เริ่มกระบวนการรีสตาร์ทระบบแปล
                # =======================================

                # แสดงให้ผู้ใช้เห็นว่ากำลังรีสตาร์ทระบบจริงๆ
                # สร้างหน้าต่างแสดงการโหลด
                loading_window = tk.Toplevel(self.root)
                loading_window.title("กำลังรีสตาร์ทระบบแปล...")
                loading_window.geometry("300x120")
                loading_window.resizable(False, False)
                loading_window.configure(background="#141414")
                loading_window.attributes("-topmost", True)

                # จัดวางตำแหน่งให้อยู่กลาง
                if hasattr(self, "root"):
                    x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 150
                    y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 60
                    loading_window.geometry(f"+{x}+{y}")

                # ข้อความ
                message_label = tk.Label(
                    loading_window,
                    text=f"กำลังรีสตาร์ทระบบการแปลเพื่อเปลี่ยนเป็นโมเดล {new_model}...\nโปรดรอสักครู่",
                    bg="#141414",
                    fg="#ffffff",
                    font=("Segoe UI", 10),
                )
                message_label.pack(pady=(20, 10))

                # Progress bar
                progress = ttk.Progressbar(
                    loading_window,
                    orient="horizontal",
                    mode="indeterminate",
                    length=250,
                )
                progress.pack(pady=10)
                progress.start()

                # อัพเดทหน้าต่าง
                loading_window.update()

                # เก็บข้อมูลสถานะการแปลก่อนรีเซ็ต
                is_translating = getattr(self, "is_translating", False)

                # หยุดการแปลถ้ากำลังแปลอยู่
                if is_translating:
                    self.logging_manager.log_info(
                        "Stopping ongoing translation process"
                    )
                    self.stop_translation()

                # ปิดทุกหน้าต่างที่เกี่ยวข้องกับการแปล
                if (
                    hasattr(self, "translated_ui_window")
                    and self.translated_ui_window.winfo_exists()
                ):
                    self.translated_ui_window.withdraw()

                if (
                    hasattr(self, "translated_logs_window")
                    and self.translated_logs_window.winfo_exists()
                ):
                    self.translated_logs_window.withdraw()

                # บังคับให้การประมวลผลทุกส่วนทำงานเสร็จ
                self.root.update_idletasks()
                self.root.update()

                # รอให้กระบวนการทุกอย่างเสร็จสิ้น
                time.sleep(0.5)

                # ล้างข้อมูลเดิมทั้งหมด
                self.logging_manager.log_info(
                    "Clearing all translation-related variables"
                )

                # จัดการกับตัวแปรเดิม
                old_translator = self.translator
                self.translator = None

                # ล้างข้อมูลแคช
                if hasattr(self, "_ocr_cache"):
                    self._ocr_cache.clear()

                # ล้างข้อมูลใน text_corrector
                if hasattr(self, "text_corrector"):
                    self.text_corrector = TextCorrector()

                # อัพเดทความคืบหน้า
                progress["value"] = 30
                loading_window.update()

                # บังคับให้ garbage collector ทำงาน
                import gc

                # ทำลายตัวแปรเดิม
                del old_translator
                # บังคับให้คืนหน่วยความจำ
                gc.collect()

                # อัพเดทความคืบหน้า
                progress["value"] = 60
                loading_window.update()

                # ========================================================
                # ข้อสำคัญ: รีสตาร์ทระบบแปลโดยเรียกใช้ฟังก์ชันเริ่มต้นใหม่
                # init_translation_and_bridge() จะสร้าง translator ใหม่ตามโมเดล
                # ที่กำหนดใน settings ซึ่งถูกอัพเดทแล้วด้วยโมเดลใหม่
                # ========================================================

                self.logging_manager.log_info(
                    "====== RESTARTING TRANSLATION SYSTEM ======"
                )

                # สร้าง translator ใหม่โดยการรีสตาร์ทระบบ
                try:
                    # สร้าง translator ใหม่โดยการรีสตาร์ทระบบ
                    self.init_translation_and_bridge()

                    # ตรวจสอบว่าสร้างสำเร็จหรือไม่
                    if not self.translator:
                        error_message = f"Failed to create translator instance for {current_model_type}"
                        self.logging_manager.log_error(error_message)
                        messagebox.showerror("รีสตาร์ทล้มเหลว", error_message)
                        loading_window.destroy()
                        return False

                    # ตรวจสอบว่าเป็น Gemini translator ที่ถูกต้อง
                    if current_model_type == "gemini" and not isinstance(
                        self.translator, TranslatorGemini
                    ):
                        error_message = f"Expected TranslatorGemini but got {self.translator.__class__.__name__}"
                        self.logging_manager.log_error(error_message)
                        messagebox.showerror("รีสตาร์ทล้มเหลว", error_message)
                        loading_window.destroy()
                        return False
                    elif current_model_type != "gemini":
                        error_message = f"Only Gemini models are supported. Got: {current_model_type}"
                        self.logging_manager.log_error(error_message)
                        messagebox.showerror("รีสตาร์ทล้มเหลว", error_message)
                        loading_window.destroy()
                        return False

                except Exception as e:
                    self.logging_manager.log_error(
                        f"Failed to reinitialize translation system: {e}"
                    )
                    messagebox.showerror(
                        "รีสตาร์ทล้มเหลว", f"ไม่สามารถสร้างระบบแปลใหม่ได้: {e}"
                    )
                    loading_window.destroy()
                    return False

                # ตรวจสอบว่าสร้างสำเร็จหรือไม่
                translator_class_name = self.translator.__class__.__name__
                self.logging_manager.log_info(
                    f"Successfully created new translator: {translator_class_name} with model: {new_model}"
                )

                # ตรวจสอบประเภทของ translator ที่ได้
                self.logging_manager.log_info(
                    f"New translator class: {translator_class_name}"
                )
                self.logging_manager.log_info(
                    f"New translator parameters: {self.translator.get_current_parameters()}"
                )

                # อัพเดทความคืบหน้า
                progress["value"] = 100
                loading_window.update()

                # ปิดหน้าต่างโหลด
                loading_window.destroy()

                # ========================================================
                # ข้อสำคัญ: คืนสถานะของหน้าต่างและการแปลหลังจากรีสตาร์ท
                # ========================================================

                # แสดงหน้าต่างที่ถูกซ่อนไว้
                if (
                    hasattr(self, "translated_ui_window")
                    and self.translated_ui_window.winfo_exists()
                ):
                    if is_translating:
                        self.translated_ui_window.deiconify()

                if (
                    hasattr(self, "translated_logs_window")
                    and self.translated_logs_window.winfo_exists()
                    and self.translated_logs_instance.is_visible
                ):
                    self.translated_logs_window.deiconify()

                # คืนสถานะการแปลถ้าเดิมกำลังแปลอยู่
                if is_translating:
                    self.logging_manager.log_info("Restoring translation state")
                    self.is_translating = True
                    # เริ่มการแปลใหม่
                    self.toggle_translation()

                # แสดงข้อความสำเร็จ
                messagebox.showinfo(
                    "รีสตาร์ทสำเร็จ",
                    f"รีสตาร์ทระบบการแปลและเปลี่ยนโมเดลเป็น {new_model} เรียบร้อยแล้ว",
                )

            else:
                # ถ้าประเภทเดียวกัน อัพเดทพารามิเตอร์ในตัวที่มีอยู่
                try:
                    self.translator.update_parameters(
                        model=api_params["model"],
                        max_tokens=api_params["max_tokens"],
                        temperature=api_params["temperature"],
                        top_p=api_params.get("top_p", 0.9),
                    )
                    self.logging_manager.log_info(
                        f"Updated translator parameters: {api_params}"
                    )
                except Exception as e:
                    self.logging_manager.log_error(
                        f"Failed to update translator parameters: {e}"
                    )
                    messagebox.showerror("Error", f"ไม่สามารถอัพเดทพารามิเตอร์ได้: {e}")
                    return False

            # แสดงการตั้งค่าปัจจุบัน
            try:
                # ใช้ get_all_settings ถ้ามี หรือใช้ __dict__ แทนถ้าไม่มี
                if hasattr(self.settings, "get_all_settings"):
                    current_settings = self.settings.get_all_settings()
                else:
                    # ใช้ self.settings โดยตรงถ้าเป็น dictionary
                    current_settings = (
                        self.settings.settings
                        if hasattr(self.settings, "settings")
                        else {}
                    )

                self.logging_manager.log_info(f"Current Settings: {current_settings}")
                self.logging_manager.log_info("============================\n")
            except Exception as e:
                self.logging_manager.log_error(f"Error getting current settings: {e}")
                # ไม่ return False เพราะไม่ใช่ข้อผิดพลาดสำคัญ

            # อัพเดท info label ด้วยสีตามโมเดล
            if hasattr(self, "info_label"):
                self.update_info_label_with_model_color()

            # อัพเดท screen size display
            if hasattr(self, "get_current_settings_info"):
                info_text = self.get_current_settings_info()
                if hasattr(self, "info_label"):
                    self.info_label.config(text=info_text)

            return True

        except Exception as e:
            error_message = f"Error updating API settings: {e}"
            self.logging_manager.log_error(error_message)
            messagebox.showerror("Error", f"เกิดข้อผิดพลาดในการอัพเดทการตั้งค่า API: {e}")
            return False

    def toggle_show_area(self):
        if self.is_area_shown:
            self.hide_show_area()
            # show_area_button highlight update removed - Edit Area functionality not used
        else:
            self.show_area()
            # show_area_button highlight update removed - Edit Area functionality not used

    def show_area(self):
        """แสดงพื้นที่ที่เลือกทั้งหมดบนหน้าจอ"""
        if not hasattr(self, "settings"):
            logging.error("Settings not initialized")
            return

        try:
            # ลบหน้าต่างเก่า
            if hasattr(self, "show_area_windows"):
                for window in self.show_area_windows.values():
                    if window and window.winfo_exists():
                        window.destroy()

            self.show_area_windows = {}
            active_areas = (
                self.current_area.split("+")
                if isinstance(self.current_area, str)
                else [self.current_area]
            )

            for area in active_areas:
                translate_area = self.settings.get_translate_area(area)
                if not translate_area:
                    continue

                window = tk.Toplevel(self.root)
                window.overrideredirect(True)
                window.attributes("-alpha", 0.4)
                window.attributes("-topmost", True)

                # คำนวณตำแหน่งและขนาด
                scale_x, scale_y = self.get_screen_scale()
                x = int(translate_area["start_x"] * scale_x)
                y = int(translate_area["start_y"] * scale_y)
                width = int(
                    (translate_area["end_x"] - translate_area["start_x"]) * scale_x
                )
                height = int(
                    (translate_area["end_y"] - translate_area["start_y"]) * scale_y
                )

                window.geometry(f"{width}x{height}+{x}+{y}")
                canvas = tk.Canvas(window, bg="red", highlightthickness=0)
                canvas.pack(fill=tk.BOTH, expand=True)
                window.lift()
                self.show_area_windows[area] = window

            # show_area_button update removed - Edit Area functionality not used
            self.is_area_shown = True

        except Exception as e:
            logging.error(f"Error showing areas: {str(e)}")
            messagebox.showerror(
                "Error", "Failed to show selected areas. Check logs for details."
            )
            self.is_area_shown = False

    def sync_initial_areas(self):
        """
        Synchronize the initial area state based on saved settings.
        Sets MBB.current_area and updates relevant UI components.
        """
        try:
            # 1. โหลดหมายเลข preset ล่าสุดจาก settings
            current_preset_num = self.settings.get("current_preset", 1)

            # 2. โหลดข้อมูล preset จาก settings
            preset_data = self.settings.get_preset(current_preset_num)

            initial_area_str = "A+B"  # Default ถ้าหา preset ไม่เจอ
            if preset_data and "areas" in preset_data:
                # ใช้พื้นที่จาก preset ที่โหลดมา
                initial_area_str = preset_data["areas"]
                # กรณีพิเศษ: ทำให้ preset 1 เป็น "A+B" เสมอ (ถ้าข้อมูลไม่ตรง)
                if current_preset_num == 1 and initial_area_str != "A+B":
                    initial_area_str = "A+B"
                    logging.warning("Preset 1 definition corrected to 'A+B'.")
                    # อาจต้องพิจารณาบันทึกการแก้ไขนี้กลับไปที่ settings หรือไม่
                    # self.settings.save_preset(1, "A+B", preset_data.get("coordinates", {}))
            else:
                logging.warning(
                    f"Preset {current_preset_num} data not found or 'areas' key missing. Defaulting to 'A+B'."
                )
                # ถ้า preset ที่บันทึกไว้หาไม่เจอ ให้กลับไปใช้ preset 1
                current_preset_num = 1
                initial_area_str = "A+B"
                self.settings.set(
                    "current_preset", current_preset_num
                )  # บันทึก preset fallback

            # 3. กำหนด State หลักใน MBB.py
            self.current_area = initial_area_str

            # 4. อัพเดทค่าใน settings ให้ตรงกัน
            self.settings.set("current_area", self.current_area)

            # OCR Area Selection removed - update_area_button_highlights call deleted (3 lines)

            # 5. สั่งให้ Control UI อัพเดทการแสดงผล (ถ้ามีอยู่)
            if hasattr(self, "control_ui") and self.control_ui:
                # ตรวจสอบว่า control_ui ยังไม่ถูกทำลาย
                if self.control_ui.root.winfo_exists():
                    # ส่งค่า area string และ preset number ปัจจุบันไปให้อัพเดท
                    self.control_ui.update_display(
                        self.current_area, current_preset_num
                    )
                    logging.info(
                        f"Instructed Control UI to update display: areas='{self.current_area}', preset={current_preset_num}"
                    )
                else:
                    logging.warning(
                        "Control UI root window does not exist during sync_initial_areas."
                    )

            # บันทึก log การ sync
            self.logging_manager.log_info(
                f"Initial areas synced: MBB.current_area set to '{self.current_area}' based on Preset {current_preset_num}"
            )

            # ไม่จำเป็นต้องเรียก update_ui_theme หรือ update_area_button_highlights ซ้ำที่นี่
            # เพราะจะถูกเรียกต่อใน __init__ อยู่แล้ว

        except Exception as e:
            self.logging_manager.log_error(f"Error in sync_initial_areas: {e}")
            # Fallback ในกรณีเกิดข้อผิดพลาดร้ายแรง
            self.current_area = "A+B"
            self.settings.set("current_area", "A+B")
            self.settings.set("current_preset", 1)
            # OCR Area Selection removed - update_area_button_highlights call deleted
            if (
                hasattr(self, "control_ui")
                and self.control_ui
                and self.control_ui.root.winfo_exists()
            ):
                self.control_ui.update_display("A+B", 1)
            import traceback

            traceback.print_exc()

    def update_button_highlight(self, button, is_active):
        """อัพเดทสถานะไฮไลท์ของปุ่ม
        Args:
            button: ปุ่มที่ต้องการอัพเดท
            is_active: สถานะการไฮไลท์ (True/False)
        """
        # ดึงสีไฮไลท์จากธีมปัจจุบัน
        highlight_color = appearance_manager.get_highlight_color()

        # ตรวจสอบว่าเป็นปุ่มแบบใหม่หรือเก่า
        if hasattr(button, "button_bg"):  # ปุ่มแบบใหม่ (Canvas)
            if is_active:
                # ใช้สีรองของธีมสำหรับ start_stop_button เมื่อ active
                if button == getattr(self, "start_stop_button", None):
                    button.itemconfig(button.button_bg, fill=appearance_manager.get_theme_color("secondary"))
                    button.itemconfig(button.button_text, fill="#ffffff")  # ตัวอักษรสีขาว
                else:
                    button.itemconfig(button.button_bg, fill="#404060")
                    button.itemconfig(button.button_text, fill=highlight_color)
                button.selected = True
            else:
                button.itemconfig(button.button_bg, fill=button.original_bg)
                button.itemconfig(button.button_text, fill="#ffffff")
                button.selected = False
        else:  # ปุ่มแบบเดิม (Button)
            if is_active:
                button.configure(fg=highlight_color, bg="#404060")
            else:
                button.configure(fg="white", bg=appearance_manager.bg_color)

    def hide_show_area(self):
        if hasattr(self, "show_area_windows"):
            for window in self.show_area_windows.values():
                if window and window.winfo_exists():
                    window.destroy()
            self.show_area_windows.clear()
        else:
            self.show_area_windows = {}

        if hasattr(self, "show_area_window") and self.show_area_window:
            self.show_area_window.destroy()
            self.show_area_window = None

        # ใช้ update_button แทน config
        # show_area_button update removed - Edit Area functionality not used
        self.is_area_shown = False

    # OCR Area Selection removed - start_selection_a/b/c methods deleted (12 lines)
    # OCR Area Selection removed - Full selection system deleted (~310 lines):
    #   - start_selection() - Main area selection window
    #   - start_drag() - Mouse drag handler
    #   - update_selection() - Selection rectangle update
    #   - finish_selection() - Complete selection and save coordinates
    #   - close_selection() - Close selection window
    #   - cancel_selection() - Cancel selection (ESC key)
        """
        ปรับปรุงคุณภาพของภาพก่อนส่งเข้า OCR

        Args:
            image: PIL.Image object
            area_type: ประเภทของพื้นที่ ('normal', 'choice', 'cutscene')

        Returns:
            PIL.Image: ภาพที่ผ่านการปรับปรุงแล้ว
        """
        try:
            # วิเคราะห์ภาพเบื้องต้น
            img_array = np.array(image.convert("L"))
            brightness = np.mean(img_array)
            contrast = np.std(img_array)

            # แปลงเป็น OpenCV format
            img_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

            # ปรับแต่งตามประเภทพื้นที่
            if area_type == "choice":  # ตัวเลือก
                # เพิ่มความคมชัดสูงสำหรับพื้นที่ตัวเลือก
                clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
                gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
                enhanced = clahe.apply(gray)

                # ใช้ binary threshold เพื่อทำให้ข้อความชัดเจนยิ่งขึ้น
                _, binary = cv2.threshold(enhanced, 127, 255, cv2.THRESH_BINARY)
                processed = Image.fromarray(binary)

            elif area_type == "cutscene":  # คัทซีน
                # ลด noise สำหรับภาพฉากหลัง
                gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
                denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
                processed = Image.fromarray(denoised)

            else:  # ข้อความทั่วไป
                # ปรับค่าตามคุณสมบัติของภาพ
                resize_factor = 1.5  # ค่าเริ่มต้น
                contrast_factor = 1.3  # ค่าเริ่มต้น

                # ปรับ resize factor ตามขนาดภาพ - ภาพเล็กต้องขยายมากกว่า
                image_size = image.width * image.height
                if image_size < 10000:  # ภาพขนาดเล็ก
                    resize_factor = 2.0
                elif image_size > 100000:  # ภาพขนาดใหญ่
                    resize_factor = 1.2

                # ปรับ contrast ตามความสว่างของภาพ
                if brightness < 100:  # ภาพมืด
                    contrast_factor = 1.5
                elif brightness > 200:  # ภาพสว่างมาก
                    contrast_factor = 1.1

                # 1. ขยายภาพตาม factor
                width = int(image.width * resize_factor)
                height = int(image.height * resize_factor)
                resized = image.resize((width, height), Image.Resampling.LANCZOS)

                # 2. ปรับ contrast ตาม factor
                enhancer = ImageEnhance.Contrast(resized)
                enhanced = enhancer.enhance(contrast_factor)

                # 3. แปลงเป็นภาพขาวดำ
                gray = enhanced.convert("L")

                # 4. เพิ่มการปรับความชัดของตัวอักษร
                sharpener = ImageEnhance.Sharpness(gray)
                processed = sharpener.enhance(1.5)

            return processed

        except Exception as e:
            logging.error(f"Error in image preprocessing: {e}")
            # ถ้าเกิดข้อผิดพลาด ให้ใช้ภาพต้นฉบับ
            return image

    def check_cpu_usage(self):
        """ตรวจสอบและปรับการทำงานตามการใช้ CPU

        Returns:
            float: เปอร์เซ็นต์การใช้งาน CPU ปัจจุบัน
        """
        try:
            import psutil

            current_time = time.time()

            # ตรวจสอบเป็นระยะเพื่อไม่ให้ตรวจสอบบ่อยเกินไป
            if not hasattr(self, "last_cpu_check") or not hasattr(
                self, "cpu_check_interval"
            ):
                self.last_cpu_check = 0
                self.cpu_check_interval = 1.0  # ตรวจสอบทุก 1 วินาที

            if current_time - self.last_cpu_check < self.cpu_check_interval:
                return -1  # ยังไม่ถึงเวลาตรวจสอบ

            self.last_cpu_check = current_time

            # วัดการใช้ CPU ปัจจุบัน
            current_cpu = psutil.cpu_percent(interval=0.1)

            # ตรวจสอบว่ามีการตั้งค่า CPU limit หรือไม่
            cpu_limit = self.settings.get("cpu_limit", 80)  # ค่าเริ่มต้น 80%

            # ปรับความเร็ว OCR ตามการใช้ CPU
            if current_cpu > cpu_limit:
                # ถ้า CPU สูงเกิน ลดความเร็ว OCR
                if self.ocr_speed == "high":
                    self.set_ocr_speed("normal")
                    self.logging_manager.log_info(
                        f"CPU usage {current_cpu}% exceeds limit {cpu_limit}%. Reducing OCR speed."
                    )

                # ถ้ายังสูงอยู่ เพิ่ม OCR interval
                if hasattr(self, "ocr_interval"):
                    self.ocr_interval = min(1.0, self.ocr_interval * 1.2)
            elif current_cpu < cpu_limit * 0.8:  # ถ้าต่ำกว่า 80% ของลิมิต
                # อาจพิจารณาเพิ่มความเร็ว แต่ไม่เกินที่ผู้ใช้ตั้งค่าไว้
                if hasattr(self, "ocr_interval") and self.ocr_interval > 0.3:
                    self.ocr_interval = max(0.3, self.ocr_interval * 0.9)  # ลดลงอย่างช้าๆ

            return current_cpu

        except ImportError:
            # ถ้าไม่มี psutil
            self.logging_manager.log_warning(
                "psutil module not available. CPU monitoring disabled."
            )
            return -1
        except Exception as e:
            self.logging_manager.log_error(f"Error in check_cpu_usage: {e}")
            return -1

    def set_cpu_limit(self, limit):
        """ตั้งค่าลิมิต CPU

        Args:
            limit (int): เปอร์เซ็นต์ลิมิต CPU (0-100)
        """
        # ตรวจสอบค่าที่รับเข้ามา
        if not 0 <= limit <= 100:
            limit = 80  # ค่าเริ่มต้น

        self.cpu_limit = limit
        self.settings.set("cpu_limit", limit)
        self.settings.save_settings()
        self.logging_manager.log_info(f"CPU limit set to {limit}%")

        # ปรับโหมด OCR ตามลิมิต
        if limit <= 50:
            self.set_ocr_speed("normal")  # ใช้โหมดปกติเมื่อลิมิตต่ำ
        elif limit >= 80:
            # ถ้าลิมิตสูง อาจใช้โหมด high ได้ถ้าเคยตั้งไว้แล้ว
            if self.settings.get("ocr_speed", "normal") == "high":
                self.set_ocr_speed("high")

    def on_dalamud_text_received(self, message_data):
        """DEPRECATED: Now handled by DalamudMessageHandler for proper synchronization"""
        # This method is kept for compatibility but is no longer used
        # All message processing is now handled by self.dalamud_handler
        pass

    def _setup_dalamud_handler(self):
        """Setup the message handler with proper dependencies"""
        if hasattr(self, 'dalamud_handler'):
            self.dalamud_handler.set_translator(self.translator)

            # 🔧 SET MAIN APP REFERENCE for status updates
            self.dalamud_handler.main_app_ref = self


            # Create DIRECT UI updater function - NO DELAYS
            def ui_updater(translated_text, chat_type=61):
                if self.translated_ui and self.is_translating:
                    # Direct call - NO after() delay
                    self.translated_ui.update_text(translated_text, chat_type=chat_type)

                    # *** ADD TO HISTORY: เพิ่มข้อความลงใน history สำหรับ Previous Dialog ***
                    if hasattr(self, 'last_original_text') and self.last_original_text:
                        self.add_to_dialog_history(
                            original_text=self.last_original_text,
                            translated_text=translated_text
                        )
                        logging.info(f"📄 [HISTORY] Added dialog to history: {len(self.dialog_history)} entries")

                    # CRITICAL: Force tkinter to update NOW
                    self.root.update_idletasks()
                    self.root.update()
                    logging.info("[UI FORCED] Tkinter update forced after text update")

            # Pass the UI updater WITH root reference
            ui_updater.root = self.root  # Attach root for handler to use
            self.dalamud_handler.set_ui_updater(ui_updater)

            # *** TEXT HOOK INTEGRATION: เชื่อมต่อ translated_logs กับ dalamud_handler ***
            if hasattr(self, 'translated_logs_instance') and self.translated_logs_instance:
                self.dalamud_handler.set_translated_logs(self.translated_logs_instance)
                self.logging_manager.log_info("✅ Translated logs integrated with text hook")

            self.dalamud_handler.start()
    
    def _display_original_with_state(self, message_text, is_translating=True):
        """แสดงข้อความต้นฉบับพร้อมสถานะการแปลแบบ dual-state"""
        try:
            if hasattr(self, 'translated_ui') and self.translated_ui:
                print(f"🌅 Displaying original with state - translating: {is_translating}")

                # เก็บข้อความต้นฉบับไว้สำหรับเช็คภายหลัง
                self._current_original_text = message_text

                # 🎯 FORCE TRANSLATE FIX: Cache original text for force translate
                self.last_original_text = message_text
                print(f"💾 Cached original text for force translate: {message_text[:50]}...")

                # แสดงข้อความต้นฉบับพร้อมสถานะ
                if is_translating:
                    # แสดงข้อความต้นฉบับพร้อม indicator ว่ากำลังแปล
                    display_text = message_text + " [แปล...]"  # หรือใช้ visual indicator อื่น
                else:
                    display_text = message_text

                self.translated_ui.update_text(display_text)
        except Exception as e:
            print(f"Error in _display_original_with_state: {e}")

    def show_original_text_immediately(self, message_text):
        """แสดงข้อความต้นฉบับทันทีที่ได้รับจาก Dalamud บน UI (legacy method)"""
        try:
            # Redirect to new dual-state method
            self._display_original_with_state(message_text, is_translating=True)
        except Exception as e:
            print(f"Error in show_original_text_immediately: {e}")

    def _display_translation_complete(self, translated_text, original_text):
        """แสดงข้อความแปลเสร็จสมบูรณ์ โดยใช้ระบบ matching ที่ปรับปรุงแล้ว"""
        try:
            if hasattr(self, 'translated_ui') and self.translated_ui:
                print(f"🎯 Display translation complete for: {original_text[:30]}...")

                # ปรับปรุงการเปรียบเทียบข้อความ - ใช้เฉพาะส่วน core
                current_core = self._extract_core_text(getattr(self, '_current_original_text', ''))
                translation_core = self._extract_core_text(original_text)

                if current_core and translation_core:
                    # เปรียบเทียบเฉพาะส่วนหลัก (ไม่รวม [แปล...] หรือส่วนเสริม)
                    similarity = self.text_similarity(current_core, translation_core)
                    print(f"🔍 Text similarity: {similarity:.2f}")

                    if similarity >= 0.8:  # 80% เหมือนกันขึ้นไป
                        print(f"✅ Text similarity match ({similarity:.2f}) - displaying translation")
                        self.translated_ui.update_text(translated_text)
                    else:
                        print(f"⚠️ Text similarity too low ({similarity:.2f}) - message may have changed")
                        print(f"   Current core: {current_core[:40]}...")
                        print(f"   Translation core: {translation_core[:40]}...")
                else:
                    # ไม่มีข้อมูลเปรียบเทียบหรือไม่สามารถดึง core ได้ - แสดงคำแปล
                    print(f"🔄 No comparison data - displaying translation")
                    self.translated_ui.update_text(translated_text)
        except Exception as e:
            print(f"Error in _display_translation_complete: {e}")

    def _extract_core_text(self, text):
        """ดึงข้อความหลักออกมา ไม่รวม [แปล...] และส่วนเสริม"""
        if not text:
            return ""

        # ลบ [แปล...] และแท็กพิเศษ
        core_text = text.replace('[แปล...]', '').replace('[แปลกำลัง...]', '')
        core_text = core_text.replace('​', '').strip()  # ลบ zero-width space

        return core_text

    def get_dalamud_text(self):
        """ได้รับข้อความจาก Dalamud queue แทนการทำ OCR"""
        if not self.dalamud_text_queue:
            return []

        # ใช้ข้อความล่าสุด
        latest_message = self.dalamud_text_queue.pop(0)
        message_text = latest_message['text']

        # ตรวจสอบข้อความซ้ำ
        if hasattr(self, '_last_dalamud_text') and self._last_dalamud_text == message_text:
            print(f"⚠️ Skipping duplicate Dalamud text")
            return []

        self._last_dalamud_text = message_text
        print(f"📤 Processing Dalamud text: {message_text[:50]}...")

        # คืนค่าในรูปแบบเดียวกับ OCR results
        return [("dalamud", message_text)]

    # ========================================================================
    # OCR METHODS REMOVED (276 lines deleted)
    # Project is now 100% text hook - no OCR functionality
    # Removed methods:
    #   - capture_and_ocr() - main OCR processing (139 lines)
    #   - get_image_signature() - OCR caching helper (53 lines)
    #   - capture_and_ocr_all_areas() - multi-area OCR (84 lines)
    # ========================================================================

    def check_for_background_dialogue(self):
        """
        ตรวจสอบพื้นที่ในเบื้องหลังว่ามีบทสนทนาปกติหรือข้อความตัวเลือกหรือไม่
        เหมาะสำหรับใช้เมื่ออยู่ในพื้นที่ C และต้องการตรวจสอบว่ามีข้อความในพื้นที่ A+B หรือไม่

        Returns:
            str: ประเภทข้อความที่พบ หรือ None ถ้าไม่พบข้อความที่เปลี่ยนไป
        """
        # ถ้าไม่ได้อยู่ในพื้นที่ C ไม่จำเป็นต้องตรวจสอบพื้นหลัง
        current_areas = (
            self.current_area.split("+")
            if isinstance(self.current_area, str)
            else self.current_area
        )
        if set(current_areas) != set(["C"]):
            return None

        self._update_status_line("Checking background for dialogue text...")
        self.logging_manager.log_info(
            "Checking background for dialogue while in area C"
        )

        # ทำ OCR พื้นที่ A และ B เพื่อตรวจสอบว่ามีข้อความสนทนาปกติหรือไม่
        background_texts = {}

        # ให้ความสำคัญสูงกับการตรวจสอบพื้นที่ B ก่อน (เพื่อหา choice dialogue)
        # ตรวจสอบพื้นที่ B ก่อนเสมอเพื่อความรวดเร็ว
        priority_areas = ["B", "A"]

        for area in priority_areas:
            translate_area = self.settings.get_translate_area(area)
            if not translate_area:
                continue

            start_x = translate_area["start_x"]
            start_y = translate_area["start_y"]
            end_x = translate_area["end_x"]
            end_y = translate_area["end_y"]

            # ตรวจสอบพื้นที่ว่าง
            if start_x == end_x or start_y == end_y:
                continue

            try:
                # คำนวณ scale ตามขนาดหน้าจอ
                screen_size = self.settings.get("screen_size", "2560x1440")
                screen_width, screen_height = map(int, screen_size.split("x"))
                scale_x = self.root.winfo_screenwidth() / screen_width
                scale_y = self.root.winfo_screenheight() / screen_height

                # คำนวณพิกัดที่จะจับภาพ
                x1 = int(min(start_x, end_x) * scale_x)
                y1 = int(min(start_y, end_y) * scale_y)
                x2 = int(max(start_x, end_x) * scale_x)
                y2 = int(max(start_y, end_y) * scale_y)

                # จับภาพหน้าจอ
                img = ImageGrab.grab(bbox=(x1, y1, x2, y2))

                # ทำ OCR แบบรวดเร็ว (ใช้ความเร็วสูง)
                img = self.preprocess_image(img)

                # บันทึกภาพชั่วคราว
                temp_path = f"temp_background_{area}_{int(time.time()*1000)}.png"
                try:
                    img.save(temp_path)
                    # ใช้ค่าความเชื่อมั่นต่ำลงและความเร็วสูงสำหรับการตรวจสอบเบื้องหลัง
                    result = self.reader.readtext(
                        temp_path,
                        detail=0,
                        paragraph=True,
                        min_size=3,
                        text_threshold=0.5,  # ค่าต่ำกว่าปกติเพื่อให้ตรวจจับได้มากขึ้น
                    )

                    text = " ".join(result)
                    if text:
                        background_texts[area] = text

                        # ตรวจสอบ choice dialogue ทันทีสำหรับพื้นที่ B
                        if area == "B":
                            # ให้ความสำคัญกับการตรวจหา "What will you say?"
                            if (
                                "what will you say" in text.lower()
                                or "whatwill you say" in text.lower()
                                or "what willyou say" in text.lower()
                            ):
                                self.logging_manager.log_info(
                                    f"Found choice dialogue in background area B: '{text[:30]}...'"
                                )
                                return (
                                    "choice"  # พบ choice dialogue ในพื้นหลัง - สลับพื้นที่ทันที
                                )
                finally:
                    # ทำความสะอาดไฟล์ชั่วคราว
                    try:
                        if os.path.exists(temp_path):
                            os.remove(temp_path)
                    except Exception as e:
                        self.logging_manager.log_warning(
                            f"Could not remove temp file {temp_path}: {e}"
                        )
            except Exception as e:
                self._update_status_line(
                    f"Error in background check area {area}: {str(e)}"
                )
                continue

        # ตรวจสอบว่าพบบทสนทนาทั้งในพื้นที่ A และ B หรือไม่
        if "A" in background_texts and "B" in background_texts:
            name_text = background_texts["A"].strip()
            dialogue_text = background_texts["B"].strip()

            # ตรวจสอบว่าพื้นที่ A มีชื่อตัวละครจริงๆ หรือไม่
            if name_text and len(name_text) < 25:  # ชื่อตัวละครมักสั้นกว่า 25 ตัวอักษร
                self.logging_manager.log_info(
                    f"Found character name '{name_text}' in background area A"
                )

                # ตรวจสอบว่าพื้นที่ B มีข้อความบทสนทนาจริงๆ หรือไม่
                if dialogue_text and len(dialogue_text) > 5:  # บทสนทนามักยาวกว่า 5 ตัวอักษร
                    self.logging_manager.log_info(
                        f"Found dialogue text in background area B: '{dialogue_text[:30]}...'"
                    )
                    return "normal"  # พบบทสนทนาปกติในพื้นหลัง

        # ตรวจสอบเพิ่มเติมว่าพบข้อความตัวเลือกในพื้นที่ B หรือไม่
        if "B" in background_texts:
            b_text = background_texts["B"]

            # ใช้ฟังก์ชันเต็มรูปแบบในการตรวจสอบอีกครั้ง
            if self.is_choice_dialogue(b_text):
                self.logging_manager.log_info(
                    "Found choice dialogue in background area B"
                )
                return "choice"

        return None  # ไม่พบรูปแบบข้อความที่ต้องการในพื้นหลัง

    def _is_choice_dialogue_quick_check(self, text):
        """ตรวจสอบอย่างรวดเร็วว่าเป็น choice dialogue หรือไม่
        ใช้เฉพาะกับการตรวจสอบพื้นหลังเพื่อความรวดเร็ว

        Args:
            text (str): ข้อความที่ต้องการตรวจสอบ
        Returns:
            bool: True ถ้าเป็น choice dialogue
        """
        # ทำความสะอาดข้อความก่อนตรวจสอบ
        cleaned_text = text.strip().lower()

        # รูปแบบที่พบบ่อยในข้อความตัวเลือก - เน้นรูปแบบที่มักพบในเกม
        choice_patterns = [
            "what will you say?",
            "what will you say",
            "whatwill you say",
            "what willyou say",
            "what will yousay",
            "whatwillyou say",
        ]

        # ตรวจสอบอย่างรวดเร็วเฉพาะรูปแบบหลักๆ
        for pattern in choice_patterns:
            if pattern in cleaned_text:
                self._update_status_line(
                    f"Quick check: Choice dialogue detected: {pattern}"
                )
                return True

        return False

    def detect_dialogue_type_improved(self, texts):
        """วิเคราะห์ประเภทของข้อความจากผลลัพธ์ OCR ด้วยความแม่นยำสูงขึ้น

        Args:
            texts: dict ของพื้นที่และข้อความที่ได้จาก OCR

        Returns:
            str: ประเภทข้อความ ("normal", "narrator", "choice" ฯลฯ)
        """
        # ถ้าไม่มีข้อความ
        if not texts:
            return "unknown"

        # 1. ตรวจสอบบทสนทนาปกติ (normal dialogue) - มีทั้งชื่อและข้อความ (ให้ priority สูงสุด)
        if "A" in texts and "B" in texts and texts["A"] and texts["B"]:
            name_text = texts["A"].strip()
            dialogue_text = texts["B"].strip()

            # ชื่อตัวละครมักสั้น (ไม่เกิน 25 ตัวอักษร) และไม่ใช่ตัวเลขหรือเครื่องหมาย
            if (
                name_text
                and len(name_text) < 25
                and any(c.isalpha() for c in name_text)
            ):
                # ตรวจสอบว่าชื่อมีความยาวมากกว่า 1 ตัวอักษร
                if len(name_text) > 1:
                    # ตรวจสอบเพิ่มเติมว่าข้อความใน B มีลักษณะของบทสนทนา
                    if len(dialogue_text) > 3:  # ข้อความต้องมีความยาวพอสมควร
                        self.logging_manager.log_info(
                            f"Detected normal dialogue (A+B): '{name_text}: {dialogue_text[:30]}...'"
                        )
                        return "normal"

        # 2. ตรวจสอบ choice dialogue (ตัวเลือก) - ต้องตรวจสอบหลังจากบทสนทนาปกติ
        if "B" in texts and texts["B"]:
            if self.is_choice_dialogue(texts["B"]):
                self.logging_manager.log_info("Detected choice dialogue in area B")
                return "choice"

        # 3. ตรวจสอบกรณีพิเศษ - มีเฉพาะข้อความในพื้นที่ B
        if "B" in texts and texts["B"] and (not "A" in texts or not texts["A"]):
            b_text = texts["B"]

            # ตรวจสอบว่ามีชื่อคนพูดในข้อความหรือไม่
            speaker, content, _ = self.text_corrector.split_speaker_and_content(b_text)
            if speaker:
                self.logging_manager.log_info(
                    f"Detected dialogue with speaker in text: '{speaker}'"
                )
                return "speaker_in_text"
            else:
                # กรณีพิเศษ - อาจเป็นบทสนทนาต่อเนื่องจากคนเดิม
                # ตรวจสอบว่าข้อความมีลักษณะของบทสนทนาหรือไม่
                if ('"' in b_text or "'" in b_text) and len(b_text) > 5:
                    self.logging_manager.log_info(
                        f"Detected dialogue without name: '{b_text[:30]}...'"
                    )
                    return "dialog_without_name"

        # 4. ตรวจสอบบทบรรยาย (narrator text) ในพื้นที่ C
        # ต้องตรวจสอบเป็นอันดับสุดท้าย เพื่อลดความผิดพลาดในการตรวจจับ
        if "C" in texts and texts["C"]:
            narrator_text = texts["C"]
            # ถ้าข้อความไม่มีชื่อคน และมีความยาวพอสมควร น่าจะเป็นบทบรรยาย
            speaker, content, _ = self.text_corrector.split_speaker_and_content(
                narrator_text
            )

            # ต้องเป็นข้อความที่ยาวพอสมควร และไม่มีชื่อนำหน้า
            if not speaker and len(narrator_text) > 20:  # เพิ่มความยาวขั้นต่ำจาก 15 เป็น 20
                # เพิ่มการตรวจสอบลักษณะของบทบรรยาย
                # บทบรรยายมักไม่มีเครื่องหมายคำพูดในช่วงต้น และมักมีคำบรรยาย
                if '"' not in narrator_text[:15] and "'" not in narrator_text[:15]:
                    # ตรวจสอบคำที่พบบ่อยในบทบรรยาย
                    narrator_words = [
                        "the",
                        "a",
                        "an",
                        "there",
                        "it",
                        "they",
                        "you",
                        "your",
                        "this",
                        "that",
                        "he",
                        "she",
                        "his",
                        "her",
                        "their",
                        "its",
                        "our",
                        "we",
                        "I",
                        "my",
                        "me",
                        "when",
                        "as",
                        "if",
                        "then",
                        "while",
                        "after",
                        "before",
                    ]
                    word_count = sum(
                        1
                        for word in narrator_words
                        if f" {word} " in f" {narrator_text.lower()} "
                    )

                    # ต้องมีคำบรรยายอย่างน้อย 2 คำ (เพิ่มความเข้มงวด)
                    if word_count >= 2:
                        self.logging_manager.log_info(
                            f"Detected narrator text in area C: '{narrator_text[:30]}...'"
                        )
                        return "narrator"

        # 5. กรณีที่ไม่สามารถระบุได้
        return "unknown"

    def smart_switch_area(self):
        """
        สลับพื้นที่อัตโนมัติ (ปิดการใช้งานถาวร)
        """
        # ปิดการใช้งาน Auto Switch ทั้งหมด
        logging.debug("Auto area switching is permanently disabled.")
        return False

        # 2. --- เพิ่ม: ตรวจสอบ Grace Period หลังจาก Manual Switch ---
        manual_selection_grace_period = 15  # วินาที
        last_manual_time = self.settings.get("last_manual_preset_selection_time", 0)
        current_time_for_check = time.time()  # ใช้เวลาเดียวกันตลอดการตรวจสอบ

        if current_time_for_check - last_manual_time < manual_selection_grace_period:
            time_left = manual_selection_grace_period - (
                current_time_for_check - last_manual_time
            )
            logging.info(
                f"Manual preset selection grace period active ({time_left:.1f}s left). Skipping auto-switch."
            )
            return False  # ข้าม Auto-Switch
        # --- จบการตรวจสอบ Grace Period ---

        # 3. ตรวจสอบ Cooldown ของ Auto Switch เอง (ป้องกันการสลับถี่เกินไป)
        if not hasattr(self, "_last_auto_switch_time"):
            self._last_auto_switch_time = 0
        auto_switch_cooldown_duration = 3.0
        if (
            current_time_for_check - self._last_auto_switch_time
            < auto_switch_cooldown_duration
        ):
            logging.debug(f"Auto-switch cooldown active.")
            return False

        # 4. ตรวจสอบพื้นที่ปัจจุบัน
        current_areas = (
            self.current_area.split("+")
            if isinstance(self.current_area, str)
            else self.current_area
        )
        current_areas_set = set(current_areas)

        # 5. ตรวจสอบพื้นหลังถ้าอยู่ในโหมด Lore (Area C)
        if current_areas_set == set(["C"]):
            background_type = self.check_for_background_dialogue()
            if background_type in ["normal", "choice"]:
                target_preset = self.find_appropriate_preset(background_type) or 1
                preset_data = self.settings.get_preset(target_preset)
                target_area_string = (
                    preset_data.get("areas", "A+B") if preset_data else "A+B"
                )

                # ตรวจสอบว่าต้องสลับจริงหรือไม่
                if (
                    self.current_area == target_area_string
                    and self.settings.get("current_preset") == target_preset
                ):
                    logging.debug("Already in correct state for background dialogue.")
                    return False

                self._update_status_line(
                    f"✓ BG {background_type}, switching to P{target_preset}"
                )
                logging.info(
                    f"Auto switching from C to P{target_preset} ({target_area_string}) due to background {background_type}"
                )
                # เรียก switch_area พร้อม preset override
                switched = self.switch_area(
                    target_area_string, preset_number_override=target_preset
                )
                if switched:
                    self._last_auto_switch_time = time.time()  # บันทึกเวลา auto switch
                    return True
                else:
                    return False  # ถ้า switch_area ไม่ทำงาน

        # 6. ทำ OCR ทุกพื้นที่เพื่อวิเคราะห์ประเภท
        all_texts = self.capture_and_ocr_all_areas()
        if not all_texts:
            logging.debug("Smart Switch: No text detected.")
            return False

        # 7. วิเคราะห์ประเภทข้อความ
        dialogue_type = self.detect_dialogue_type_improved(all_texts)
        logging.info(f"Detected dialogue type: {dialogue_type}")

        # 8. ตรวจสอบความเสถียร
        self.update_detection_history(dialogue_type)
        stability_info = self.area_detection_stability_system()
        logging.debug(f"Stability check: {stability_info}")

        required_consecutive = (
            3 if dialogue_type == "narrator" and current_areas_set == {"A", "B"} else 2
        )
        min_confidence = 75

        if (
            not stability_info["is_stable"]
            or stability_info["stable_type"] != dialogue_type
            or stability_info["confidence"].get(dialogue_type, 0) < min_confidence
            or stability_info["consecutive_detections"] < required_consecutive
        ):
            logging.debug(f"Waiting for stable detection of {dialogue_type}...")
            return False  # ยังไม่เสถียรพอ

        # 9. ค้นหา Preset ที่เหมาะสมและสลับพื้นที่
        if dialogue_type != "unknown":
            target_preset = self.find_appropriate_preset(dialogue_type)
            if target_preset is None:
                logging.warning(f"No appropriate preset found for {dialogue_type}.")
                return False

            preset_data = self.settings.get_preset(target_preset)
            target_area_string = (
                preset_data.get("areas", "A+B") if preset_data else "A+B"
            )
            current_preset_num = self.settings.get("current_preset", 1)

            # ตรวจสอบว่าต้องสลับจริงหรือไม่ (Preset และ Area ต้องตรงกัน)
            if (
                current_preset_num == target_preset
                and self.current_area == target_area_string
            ):
                logging.debug(f"Already in correct preset/area for {dialogue_type}.")
                return False

            # --- ทำการสลับ ---
            self._update_status_line(
                f"✓ Auto switching to P{target_preset} for {dialogue_type}"
            )
            logging.info(
                f"Auto switching preset: P{current_preset_num} -> P{target_preset} ({target_area_string}) for type: {dialogue_type}"
            )
            switched = self.switch_area(
                target_area_string, preset_number_override=target_preset
            )
            if switched:
                self._last_auto_switch_time = time.time()  # บันทึกเวลา auto switch
                return True
            else:
                return False  # ถ้า switch_area ไม่ทำงาน

        return False  # ถ้าไม่เข้าเงื่อนไขใดๆ

    def is_choice_preset_active(self):
        """ตรวจสอบว่า preset ปัจจุบันเป็น choice preset หรือไม่"""
        try:
            if not hasattr(self, "control_ui") or not self.control_ui:
                return False

            current_preset = self.control_ui.current_preset
            presets = self.settings.get_all_presets()

            if 1 <= current_preset <= len(presets):
                preset = presets[current_preset - 1]
                is_choice = preset.get("role") == "choice"

                if is_choice:
                    self._update_status_line(
                        "Choice preset active - forcing choice dialogue mode"
                    )
                    logging.info(
                        f"Choice preset P{current_preset} active - treating text as choice dialogue"
                    )

                return is_choice

        except Exception as e:
            logging.error(f"Error checking choice preset: {e}")

        return False

    def is_choice_dialogue(self, text):
        """ตรวจสอบว่าเป็น choice dialogue หรือไม่"""
        # ทำความสะอาดข้อความก่อนตรวจสอบ
        cleaned_text = text.strip().lower()
        logging.debug(
            f"is_choice_dialogue checking: '{text[:50]}...' -> cleaned: '{cleaned_text[:50]}...'"
        )

        # รูปแบบเฉพาะสำหรับ choice dialogue (รองรับ OCR errors หลากหลาย)
        choice_patterns = [
            "what will you say?",
            "what will you say",
            # Space variations
            "whatwill you say?",
            "whatwill you say",
            "what willyou say?",
            "what willyou say",
            "what will yousay?",
            "what will yousay",
            "whatwillyou say?",
            "whatwillyou say",
            # Case variations (OCR mixed case)
            "what will You say?",
            "what will You say",
            "what will yOu say?",
            "what will yOu say",
            "what will YOu say?",
            "what will YOu say",
            "What will you say?",
            "What will you say",
            "WHAT WILL YOU SAY?",
            "WHAT WILL YOU SAY",
            # Common OCR character mistakes
            "vvhat will you say?",
            "vvhat will you say",  # w -> vv
            "what vvill you say?",
            "what vvill you say",  # w -> vv
            "what will yuu say?",
            "what will yuu say",  # o -> u
            "what wiII you say?",
            "what wiII you say",  # ll -> II
            "what wi11 you say?",
            "what wi11 you say",  # ll -> 11
            "vhat will you say?",
            "vhat will you say",  # w -> v
            "what wili you say?",
            "what wili you say",  # ll -> li
            # Number/letter confusions
            "what wi1l you say?",
            "what wi1l you say",  # l -> 1
            "what will y0u say?",
            "what will y0u say",  # o -> 0
            # Punctuation variations
            "what will you say .",
            "what will you say.",
            "what will you say !",
        ]

        # ตรวจสอบว่าข้อความเริ่มต้นด้วยรูปแบบ choice หรือไม่
        for pattern in choice_patterns:
            # ตรวจสอบคำขึ้นต้น
            if cleaned_text.startswith(pattern):
                self._update_status_line(
                    f"Choice dialogue detected (exact match): {pattern}"
                )
                return True

            # ตรวจสอบในส่วนต้นของข้อความ (ภายใน 30 ตัวอักษรแรก)
            if pattern in cleaned_text[:30]:
                self._update_status_line(
                    f"Choice dialogue detected near beginning: {pattern}"
                )
                return True

        # Fallback: Fuzzy matching สำหรับ OCR ที่ผิดพลาดมาก
        main_pattern = "what will you say"
        text_start = (
            cleaned_text[:20].replace("?", "").replace(".", "").replace("!", "").strip()
        )

        # ตรวจสอบ similarity ratio
        import difflib

        similarity = difflib.SequenceMatcher(None, text_start, main_pattern).ratio()

        if similarity >= 0.75:  # 75% similarity threshold
            self._update_status_line(
                f"Choice dialogue detected by fuzzy match: {similarity:.2f} similarity"
            )
            logging.info(
                f"Fuzzy choice match: '{text_start}' ~= '{main_pattern}' ({similarity:.2f})"
            )
            return True

        return False

    def toggle_translation(self):
        try:
            # 🚫 AUTO-START CANCELLATION: ยกเลิก auto-start หากผู้ใช้กดปุ่มเอง
            self.cancel_auto_start()

            if not self.is_translating:
                # ✅ FREEZE FIX: ไม่รอ thread เดิม แค่ตรวจสอบ
                if self.translation_thread and self.translation_thread.is_alive():
                    self.logging_manager.log_info("Previous translation thread still running - it will stop naturally")

                if not self.is_resizing:
                    # ถ้าใช้ Dalamud mode ไม่ต้องตรวจสอบพื้นที่แปล
                    if not self.dalamud_mode:
                        # ตรวจสอบพื้นที่ที่เปิดใช้งาน (สำหรับ OCR mode เท่านั้น)
                        active_areas = (
                            self.current_area.split("+")
                            if isinstance(self.current_area, str)
                            else [self.current_area]
                        )
                        valid_areas = True

                        for area in active_areas:
                            translate_area = self.settings.get_translate_area(area)
                            if not translate_area:
                                valid_areas = False
                                break
                            start_x = translate_area["start_x"]
                            start_y = translate_area["start_y"]
                            end_x = translate_area["end_x"]
                            end_y = translate_area["end_y"]
                            if start_x == end_x or start_y == end_y:
                                valid_areas = False
                                break

                        if not valid_areas:
                            messagebox.showwarning(
                                "Warning",
                                f"Please select translation areas for all active areas: {', '.join(active_areas)}",
                            )
                            return

                    # เริ่มการแปล
                    self.is_translating = True
                    self._setup_dalamud_handler()
                    if hasattr(self, "dalamud_handler"):
                        self.dalamud_handler.set_translation_active(True)
                    self.translation_event.set()
                    self.control_panel.set_translating(True)
                    # เพิ่มการไฮไลท์ปุ่มเมื่อเริ่มการแปล
                    self.update_button_highlight(self.start_stop_button, True)
                    self.blinking = True

                    # เริ่ม Dalamud bridge ถ้าเปิดใช้งาน
                    if self.dalamud_mode and hasattr(self, 'dalamud_bridge'):
                        # 🔧 CRITICAL FIX: Clear old messages before starting translation
                        # This prevents translating old messages when MBB starts after plugin
                        # See: FIX_BACKLOG_TRANSLATION.md for detailed explanation
                        self.logging_manager.log_info("🧹 Clearing old message queue before starting translation...")
                        self.dalamud_bridge.clear_queue()

                        # 🔧 CRITICAL FIX: Always re-set callback when translation starts
                        # This ensures callback is properly linked regardless of bridge state
                        self.logging_manager.log_info("🔧 Force setting Dalamud callback on translation start...")
                        self.dalamud_bridge.set_text_callback(self.dalamud_handler.process_message)

                        if not self.dalamud_bridge.is_running:
                            self.dalamud_bridge.start()
                            self.logging_manager.log_info("เริ่ม Dalamud Bridge")
                    # Rainbow progress bar replaces blinking animation

                    # UI INDEPENDENCE: การแปลเริ่มโดยไม่กระทบ TUI
                    self.logging_manager.log_info("Translation started via UI button")

                    # 🔄 Note: ไม่ highlight TUI button เมื่อกด Start
                    # TUI จะแสดงเองเมื่อมีข้อความแปลเข้ามาจริงๆ

                    # เริ่ม translation thread (เฉพาะเมื่อไม่ใช่โหมด Dalamud)
                    if not self.dalamud_mode:
                        self.translation_thread = threading.Thread(
                            target=self.translation_loop,
                            daemon=True,
                            name="TranslationThread",
                        )
                        self.translation_thread.start()
                        self.logging_manager.log_info("Translation thread started")
                    else:
                        self.logging_manager.log_info("🚀 Dalamud mode: Using text hook only, no OCR loop")
                else:
                    return
            else:
                # UI INDEPENDENCE: หยุดการแปลโดยไม่กระทบ TUI
                self.stop_translation()
                self.logging_manager.log_info("Translation stopped via UI button")
                return  # หยุดการทำงานที่นี่ ไม่ให้โค้ดข้างล่างทำงานต่อ

            # อัปเดตสถานะ mini UI อย่างปลอดภัย
            if hasattr(self, "mini_ui") and self.mini_ui:
                self.root.after(
                    0,
                    lambda: self.mini_ui.update_translation_status(self.is_translating),
                )
            # อัปเดตสถานะการแปลใน control_ui
            if hasattr(self, "control_ui") and hasattr(
                self.control_ui, "update_translation_status"
            ):
                self.control_ui.update_translation_status(self.is_translating)

            # 🔄 SYNC FIX: ส่ง callback ไป TranslatedUI เพื่อซิงค์สถานะ
            if hasattr(self, "translated_ui") and self.translated_ui:
                self.root.after(
                    0,
                    lambda: self._notify_translated_ui_status_change(self.is_translating),
                )

        except Exception as e:
            self.logging_manager.log_error(
                f"An error occurred in toggle_translation: {e}"
            )
            messagebox.showerror("Error", f"An error occurred: {e}")
            self.is_translating = False
            # อัปเดตสถานะ mini UI อย่างปลอดภัย
            if hasattr(self, "mini_ui") and self.mini_ui:
                self.root.after(
                    0, lambda: self.mini_ui.update_translation_status(False)
                )
            # อัปเดตสถานะการแปลใน control_ui
            if hasattr(self, "control_ui") and hasattr(
                self.control_ui, "update_translation_status"
            ):
                self.control_ui.update_translation_status(False)
            # กรณีเกิดข้อผิดพลาด ยกเลิกไฮไลท์ปุ่ม
            self.update_button_highlight(self.start_stop_button, False)

    def _notify_translated_ui_status_change(self, is_translating):
        """ส่งสัญญาณการเปลี่ยนแปลงสถานะไปยัง TranslatedUI เพื่อซิงค์ TUI"""
        try:
            if hasattr(self.translated_ui, 'update_translation_status'):
                self.translated_ui.update_translation_status(is_translating)
                self.logging_manager.log_info(f"TranslatedUI status synced: {is_translating}")
            elif hasattr(self.translated_ui, 'handle_translation_toggle'):
                self.translated_ui.handle_translation_toggle(is_translating)
                self.logging_manager.log_info(f"TranslatedUI toggle handled: {is_translating}")
            else:
                # TranslatedUI doesn't need status updates - this is expected behavior
                pass
        except Exception as e:
            self.logging_manager.log_error(f"Failed to sync TranslatedUI status: {e}")

    def stop_translation(self, from_mini_ui=False):
        """หยุดการแปลแบบ async โดยไม่ freeze UI"""
        if not self.is_translating:
            return

        try:
            # === PHASE 1: Set flags immediately (no waiting) ===
            print("🛑 Stopping translation - Phase 1: Set flags")
            self.is_translating = False
            if hasattr(self, "dalamud_handler"):
                self.dalamud_handler.set_translation_active(False)
            self.translation_event.clear()

            # === PHASE 2: Update UI immediately ===
            print("🛑 Phase 2: Update UI")
            self.control_panel.set_translating(False)
            self.update_button_highlight(self.start_stop_button, False)  # Remove highlight
            self.blinking = False
            self.mini_ui.update_translation_status(False)

            if hasattr(self, "control_ui") and hasattr(
                self.control_ui, "update_translation_status"
            ):
                self.control_ui.update_translation_status(False)

            # Stop breathing effect
            if hasattr(self, "breathing_effect"):
                self.breathing_effect.stop()

            # 🎯 AUTO TUI OFF: เมื่อหยุดแปลให้ซ่อน TUI ทันที
            if hasattr(self, 'translated_ui_window') and self.translated_ui_window.winfo_exists():
                if self.translated_ui_window.state() != "withdrawn":
                    self.translated_ui_window.withdraw()
                    self.logging_manager.log_info("🎯 [AUTO TUI] TUI hidden automatically when translation stopped")

            # === PHASE 3: Clear all queues immediately ===
            print("🛑 Phase 3: Clear queues")
            if hasattr(self, '_is_translating_dalamud'):
                self._is_translating_dalamud = False
            if hasattr(self, '_dalamud_pending_queue'):
                self._dalamud_pending_queue.clear()
            if hasattr(self, 'dalamud_text_queue'):
                self.dalamud_text_queue.clear()
            if hasattr(self, '_current_original_text'):
                self._current_original_text = None

            # === PHASE 4: Stop components async (no blocking) ===
            def stop_components_async():
                try:
                    print("🛑 Phase 4: Stopping components async")

                    # Stop Dalamud bridge if running
                    if hasattr(self, 'dalamud_bridge') and self.dalamud_bridge.is_running:
                        try:
                            self.dalamud_bridge.stop()
                            print("✅ Dalamud Bridge stopped")
                        except Exception as e:
                            print(f"⚠️ Error stopping Dalamud bridge: {e}")

                    # Signal translation thread to stop (don't wait)
                    if self.translation_thread and self.translation_thread.is_alive():
                        print("📢 Signaling translation thread to stop...")
                        # Thread will check is_translating flag and stop itself

                    # *** TUI INDEPENDENCE: ไม่ซ่อน TUI เมื่อหยุดแปล - ให้ TUI button ทำงานอิสระ ***
                    # TUI จะยังคงแสดงอยู่และแสดงสถานะปัจจุบัน ไม่ว่าการแปลจะทำงานหรือหยุด
                    print("✅ Translation stopped - TUI remains visible with current content")

                    # Finish cleanup after short delay
                    self.root.after(100, self._finish_stopping_translation)

                except Exception as e:
                    print(f"⚠️ Error in stop_components_async: {e}")
                    # Still try to finish cleanup even if error
                    self.root.after(50, self._finish_stopping_translation)

            # Start async stop in separate thread
            threading.Thread(target=stop_components_async, daemon=True).start()

            # === PHASE 5: Show/hide indicators with minimal delay ===
            # Show loading indicator briefly then hide
            self.show_loading_indicator()
            self.root.after(300, self.hide_loading_indicator)

        except Exception as e:
            self.logging_manager.log_error(f"Error in stop_translation: {e}")
            print(f"❌ Critical error in stop_translation: {e}")
            # ปลดล็อค UI และซ่อนไอคอนในกรณีเกิดข้อผิดพลาด
            self._finish_stopping_translation()

    def _hide_translated_ui_immediate(self):
        """ซ่อน TUI ทันทีเมื่อหยุดแปล - ไม่ใช้ async"""
        try:
            print("🫥 Hiding translated UI immediately")

            # 🔧 ส่ง flag ไป TUI เพื่อป้องกัน circular call
            if hasattr(self, 'translated_ui'):
                self.translated_ui._closing_from_f9 = True

            # ซ่อน translated UI window ทันที - เรียก close_window จาก translated_ui
            if hasattr(self, 'translated_ui') and hasattr(self.translated_ui, 'close_window'):
                try:
                    self.translated_ui.close_window()
                    print("✅ Translated UI window hidden immediately via close_window()")
                except Exception as e:
                    print(f"⚠️ Could not hide TUI window via close_window: {e}")
            elif hasattr(self, 'translated_ui_window'):
                try:
                    self.translated_ui_window.withdraw()
                    print("✅ Translated UI window hidden immediately via withdraw()")
                except Exception as e:
                    print(f"⚠️ Could not hide TUI window via withdraw: {e}")

            # อัปเดตสถานะปุ่ม TUI ทันที
            # NOTE: Using ButtonStateManager only - bottom_button_states removed
            if hasattr(self, "button_state_manager"):
                self.button_state_manager.button_states["tui"]["active"] = False
                self.button_state_manager.update_button_visual("tui", "toggle_off")

            # Force UI update
            if hasattr(self, 'root'):
                self.root.update_idletasks()

            # รีเซ็ตข้อมูลแสดงผล
            if hasattr(self, '_current_original_text'):
                self._current_original_text = None

        except Exception as e:
            print(f"Error in _hide_translated_ui_immediate: {e}")

    def _f9_hard_stop(self):
        """Legacy F9 function - now TUI only, no translation control"""
        try:

            # ======= PHASE 1: หยุดการทำงานทันที =======
            self.is_translating = False
            print("✅ Set is_translating = False")

            # หยุด Dalamud handler
            if hasattr(self, "dalamud_handler"):
                self.dalamud_handler.set_translation_active(False)
                print("✅ Dalamud handler stopped")

            # เคลียร์ translation event
            self.translation_event.clear()
            print("✅ Translation event cleared")

            # ======= PHASE 2: ซ่อน TUI ทันที =======
            if hasattr(self, 'translated_ui') and self.translated_ui:
                try:
                    # ตั้ง flag เพื่อป้องกัน circular call
                    self.translated_ui._closing_from_f9 = True

                    # ซ่อน window ทันที
                    if hasattr(self.translated_ui, 'root') and self.translated_ui.root.winfo_exists():
                        self.translated_ui.root.withdraw()
                        print("✅ F9: TUI window hidden successfully")
                    else:
                        print("⚠️ F9: TUI root not found or not exists")

                except Exception as e:
                    print(f"⚠️ F9: Error hiding TUI: {e}")

            # ======= PHASE 3: อัปเดต UI State และ sync กับปุ่ม START =======
            try:
                # อัปเดตปุ่ม START - เป็นส่วนสำคัญสำหรับ sync
                if hasattr(self, "start_stop_button"):
                    self.control_panel.set_translating(False)
                    self.update_button_highlight(self.start_stop_button, False)
                    print("✅ F9: START button updated and synced")

                # 🔄 UNIFIED SYNC: ใช้ฟังก์ชัน unified sync เมื่อหยุดการแปล
                self._sync_tui_button_state(False, "F9 legacy stop")
                print("✅ F9: TUI button state updated")

                # อัปเดต Mini UI
                self.blinking = False
                if hasattr(self, "mini_ui"):
                    self.mini_ui.update_translation_status(False)
                    print("✅ F9: Mini UI updated")

                # อัปเดต Control UI if exists
                if hasattr(self, "control_ui") and hasattr(self.control_ui, "update_translation_status"):
                    self.control_ui.update_translation_status(False)
                    print("✅ F9: Control UI updated")

            except Exception as e:
                print(f"⚠️ F9: Error updating UI states: {e}")

            # ======= PHASE 4: Force UI refresh =======
            try:
                self.root.update_idletasks()
                self.root.update()
                print("✅ F9: UI force refreshed")
            except Exception as e:
                print(f"⚠️ F9: Error refreshing UI: {e}")

            print("🎯 F9 LEGACY HARD STOP - deprecated function completed")

        except Exception as e:
            print(f"❌ F9 LEGACY HARD STOP - Critical Error: {e}")

    def _hide_translated_ui_all_cases(self):
        """ซ่อน translated UI ในทุกกรณีที่หยุดแปล (ปิดหน้าต่าง, W/A/S/D keys)"""
        try:
            # 🔇 LOG FLOOD FIX: Check if UI is already hidden to avoid log flooding during WASD spam
            already_hidden = False
            if hasattr(self, 'translated_ui') and hasattr(self.translated_ui, 'state'):
                already_hidden = self.translated_ui.state.is_window_hidden

            # Only log if state is changing from visible to hidden
            if not already_hidden:
                print("🫥 Hiding translated UI in all stop cases")

            # *** FIX: ใช้ state system เดียวกันกับ auto-hide system ***
            # ซ่อน translated UI window พร้อม sync state
            if hasattr(self, 'translated_ui_window') and self.translated_ui_window.winfo_exists():
                # ล้างข้อความก่อนซ่อน
                if hasattr(self, 'translated_ui') and self.translated_ui:
                    self.translated_ui.clear_displayed_text()

                self.translated_ui_window.withdraw()

                # *** SYNC FIX: Update is_window_hidden state เพื่อความสอดคล้อง ***
                if hasattr(self, 'translated_ui') and hasattr(self.translated_ui, 'state'):
                    self.translated_ui.state.is_window_hidden = True

                    # *** CRITICAL FIX: Cancel fade timer when WASD hides UI ***
                    # This prevents conflict between fade timer and WASD hide
                    if self.translated_ui.state.fade_timer_id:
                        self.root.after_cancel(self.translated_ui.state.fade_timer_id)
                        self.translated_ui.state.fade_timer_id = None
                        if not already_hidden:  # Only log if state changed
                            print("⏹️ Cancelled fade timer on WASD hide")

                    # Reset fade state
                    self.translated_ui.state.is_fading = False
                    self.translated_ui.state.just_faded_out = False

                    if not already_hidden:  # Only log if state changed
                        print("✅ Translated UI window hidden with state sync")
                else:
                    if not already_hidden:  # Only log if state changed
                        print("✅ Translated UI window hidden (no state sync available)")

            # ซ่อน translated logs window ด้วย (ถ้าเปิดอยู่)
            logs_was_visible = False
            if hasattr(self, 'translated_logs_window') and self.translated_logs_window:
                try:
                    logs_was_visible = self.translated_logs_window.winfo_exists() and self.translated_logs_window.state() != 'withdrawn'
                except:
                    pass

            if logs_was_visible:
                self.translated_logs_window.withdraw()
                print("✅ Translated logs window hidden")  # Only logs if window was actually visible

            # รีเซ็ตข้อมูลแสดงผล
            if hasattr(self, '_current_original_text'):
                self._current_original_text = None

        except Exception as e:
            print(f"Error in _hide_translated_ui_all_cases: {e}")

    def text_similarity(self, text1, text2):
        return difflib.SequenceMatcher(None, text1, text2).ratio()

    def test_area_switching(self):
        """ทดสอบระบบสลับพื้นที่อัตโนมัติ"""
        try:
            # แสดงพื้นที่ปัจจุบัน
            current_areas = (
                self.current_area.split("+")
                if isinstance(self.current_area, str)
                else self.current_area
            )
            self._update_status_line(f"Current areas: {'+'.join(current_areas)}")
            self.logging_manager.log_info(
                f"Testing auto area switch. Current areas: {'+'.join(current_areas)}"
            )

            # ทดสอบการตรวจจับในพื้นหลัง (สำหรับพื้นที่ C)
            if set(current_areas) == set(["C"]):
                self._update_status_line("Testing background detection for area C...")
                background_type = self.check_for_background_dialogue()
                if background_type:
                    self._update_status_line(
                        f"Found {background_type} dialogue in background"
                    )
                    messagebox.showinfo(
                        "Background Detection",
                        f"พบข้อความประเภท {background_type} ในพื้นหลัง\nโปรแกรมจะสลับไปยังพื้นที่ที่เหมาะสม",
                    )

            # ทดสอบการสลับพื้นที่อัตโนมัติ (ปิดใช้งานแล้ว)
            messagebox.showinfo(
                "Auto Area Switch Test",
                "การสลับพื้นที่อัตโนมัติถูกปิดใช้งานถาวรแล้ว\nใช้การสลับ Preset แบบ Manual เท่านั้น",
            )

            return False  # Always return False since auto switching is disabled
        except Exception as e:
            error_msg = f"เกิดข้อผิดพลาดในการทดสอบ: {str(e)}"
            self.logging_manager.log_error(error_msg)
            messagebox.showerror("Test Error", error_msg)
            return False

    def explain_area_switching(self):
        """แสดงหน้าต่างอธิบายระบบสลับพื้นที่อัตโนมัติ"""
        explanation = """
        ระบบสลับพื้นที่อัตโนมัติใน MagicBabel
        
        หลักการทำงาน:
        1. ตรวจจับประเภทข้อความอัตโนมัติ
        - บทสนทนาปกติ (มีชื่อ+ข้อความ) -> ใช้พื้นที่ A+B
        - บทบรรยาย -> ใช้พื้นที่ C
        - ข้อความตัวเลือก -> ใช้พื้นที่ B
        
        2. การตรวจสอบพิเศษสำหรับพื้นที่ C:
        - เมื่ออยู่ในพื้นที่ C (บทบรรยาย) ระบบจะตรวจสอบพื้นที่ A+B ในเบื้องหลังบ่อยขึ้น
        - หากพบว่าข้อความเปลี่ยนกลับเป็นบทสนทนาปกติ จะสลับกลับไปยังพื้นที่ A+B โดยอัตโนมัติ
        
        3. การป้องกันการสลับพื้นที่ถี่เกินไป:
        - ระบบมีกลไกป้องกันการสลับพื้นที่ไปมาเร็วเกินไป
        - ช่วงเวลาขั้นต่ำระหว่างการสลับพื้นที่: 3 วินาที
        
        การเปิด/ปิดระบบ:
        - ตั้งค่า "Auto Area Detection" ในหน้า Settings
        - เมื่อปิดการทำงาน จะต้องสลับพื้นที่ด้วยตนเองผ่าน Control Panel
        
        การทดสอบ:
        - ใช้ฟังก์ชัน test_area_switching() เพื่อทดสอบระบบ
        - วิธีใช้: เรียกฟังก์ชันนี้ผ่าน Python console หรือสร้างปุ่มทดสอบ
        """

        info_window = tk.Toplevel(self.root)
        info_window.title("ระบบสลับพื้นที่อัตโนมัติ")
        info_window.geometry("600x500")
        info_window.configure(bg="#1a1a1a")

        # สร้าง Text widget สำหรับแสดงข้อความ
        text_widget = tk.Text(
            info_window,
            wrap=tk.WORD,
            bg="#1a1a1a",
            fg="white",
            font=("IBM Plex Sans Thai Medium", 12),
            padx=20,
            pady=20,
        )
        text_widget.pack(expand=True, fill=tk.BOTH)
        text_widget.insert(tk.END, explanation)
        text_widget.config(state=tk.DISABLED)  # ทำให้ข้อความไม่สามารถแก้ไขได้

        # โหลดไอคอน del.png และใช้ Label แทน Button เพื่อให้โปร่งใส
        try:
            del_icon = tk.PhotoImage(file="assets/del.png")

            # สร้างปุ่มปิดใช้ Label (โปร่งใสได้)
            close_button = tk.Label(
                self.guide_window,
                image=del_icon,
                bg=self.guide_window.cget("bg"),  # พื้นหลังโปร่งใส
                cursor="hand2",
            )
            close_button.image = del_icon  # เก็บ reference

        except:
            # ถ้าโหลดไอคอนไม่ได้ ใช้ text แทน
            close_button = tk.Label(
                self.guide_window,
                text="×",
                font=("Arial", 14, "bold"),
                bg=self.guide_window.cget("bg"),
                fg="#888888",  # สีเทาอ่อน
                cursor="hand2",
            )

        guide_width = 600  # กำหนดค่าความกว้างของหน้าต่าง guide
        close_button.place(x=guide_width - 35, y=10)

        # เพิ่ม hover effect ให้แสดงสี theme_accent เมื่อ hover
        theme_accent = (
            self.appearance_manager.get_accent_color()
            if hasattr(self, "appearance_manager")
            else "#6C5CE7"
        )
        window_bg = self.guide_window.cget("bg")

        def on_enter(e):
            close_button.configure(bg=theme_accent)

        def on_leave(e):
            close_button.configure(bg=window_bg)

        def on_click(e):
            self.guide_window.destroy()

        close_button.bind("<Enter>", on_enter)
        close_button.bind("<Leave>", on_leave)
        close_button.bind("<Button-1>", on_click)  # เพิ่ม click event

        # ทำให้หน้าต่างอยู่ด้านบนและตรงกลางหน้าจอ
        info_window.update_idletasks()
        width = info_window.winfo_width()
        height = info_window.winfo_height()
        x = (info_window.winfo_screenwidth() // 2) - (width // 2)
        y = (info_window.winfo_screenheight() // 2) - (height // 2)
        info_window.geometry(f"{width}x{height}+{x}+{y}")
        info_window.attributes("-topmost", True)

    def area_detection_stability_system(self):
        """ระบบตรวจสอบความเสถียรของการตรวจจับรูปแบบข้อความเพื่อลดการสลับพื้นที่ไม่จำเป็น

        ฟังก์ชันนี้จะเก็บประวัติการตรวจจับประเภทข้อความและคำนวณความมั่นใจ
        ก่อนที่จะอนุญาตให้สลับพื้นที่ เพื่อป้องกันการสลับพื้นที่ไปมาบ่อยเกินไป

        Returns:
            dict: ข้อมูลเกี่ยวกับความเสถียรของการตรวจจับ
        """
        # สร้างหรืออัพเดตตัวแปรเก็บประวัติการตรวจจับ
        if not hasattr(self, "_detection_history"):
            self._detection_history = {
                "normal": [],  # บทสนทนาปกติ (A+B)
                "narrator": [],  # บทบรรยาย (C)
                "choice": [],  # ตัวเลือก (B)
                "other": [],  # ประเภทอื่นๆ (B)
                "unknown": [],  # ไม่สามารถระบุประเภทได้
                "last_stable_type": None,  # ประเภทล่าสุดที่มั่นคง
                "last_stable_time": 0,  # เวลาล่าสุดที่มีการเปลี่ยนประเภทที่มั่นคง
                "consecutive_detections": 0,  # จำนวนครั้งที่ตรวจพบประเภทเดิมติดต่อกัน
                "current_type": None,  # ประเภทปัจจุบัน
                "stability_score": 0,  # คะแนนความเสถียร (0-100)
            }

        # ระบบวิเคราะห์ความเสถียร
        history = self._detection_history
        current_time = time.time()

        # ประเภทข้อความที่สมเหตุสมผลที่จะสลับไปมา
        valid_types = ["normal", "narrator", "choice", "other"]

        # ตัดประวัติที่เก่าเกิน 10 วินาที
        for dtype in valid_types + ["unknown"]:
            history[dtype] = [d for d in history[dtype] if current_time - d <= 10]

        # คำนวณความถี่ของแต่ละประเภทในช่วง 5 วินาทีล่าสุด
        recent_window = 5  # ช่วงเวลาที่พิจารณา (วินาที)
        recent_counts = {}
        for dtype in valid_types:
            recent_counts[dtype] = len(
                [d for d in history[dtype] if current_time - d <= recent_window]
            )

        total_recent = sum(recent_counts.values())

        # คำนวณความมั่นใจของแต่ละประเภท
        confidence = {}
        for dtype in valid_types:
            if total_recent > 0:
                confidence[dtype] = (recent_counts[dtype] / total_recent) * 100
            else:
                confidence[dtype] = 0

        # ตรวจสอบว่ามีประเภทไหนที่มั่นใจมากพอ (มากกว่า 70%)
        stable_type = None
        max_confidence = 0
        for dtype, conf in confidence.items():
            if conf > max_confidence:
                max_confidence = conf
                stable_type = dtype

        # ตรวจสอบว่าประเภทนั้นมีความมั่นใจสูงพอ
        is_stable = max_confidence >= 70

        # อัพเดตข้อมูลความเสถียร
        if is_stable and stable_type != history["last_stable_type"]:
            history["last_stable_type"] = stable_type
            history["last_stable_time"] = current_time
            history["consecutive_detections"] = 1
        elif is_stable and stable_type == history["last_stable_type"]:
            history["consecutive_detections"] += 1

        # คะแนนความเสถียรขึ้นอยู่กับจำนวนครั้งที่ตรวจพบประเภทเดิมติดต่อกัน
        if history["consecutive_detections"] >= 3:
            history["stability_score"] = 100  # มั่นคงมาก (ตรวจพบประเภทเดิม 3 ครั้งขึ้นไป)
        else:
            history["stability_score"] = (
                history["consecutive_detections"] * 33
            )  # 33%, 66%, 99%

        # อัพเดตประเภทปัจจุบัน
        history["current_type"] = stable_type if is_stable else history["current_type"]

        return {
            "is_stable": is_stable,
            "stable_type": stable_type,
            "confidence": confidence,
            "stability_score": history["stability_score"],
            "consecutive_detections": history["consecutive_detections"],
            "time_since_last_stable": (
                current_time - history["last_stable_time"]
                if history["last_stable_time"] > 0
                else float("inf")
            ),
        }

    def switch_area_using_preset(self, dialogue_type):
        """สลับพื้นที่โดยใช้ preset ที่เหมาะสมกับประเภทข้อความแบบอัตโนมัติ (ปิดใช้งานถาวร)

        Args:
            dialogue_type: ประเภทข้อความ ("normal", "narrator", "choice", ฯลฯ)

        Returns:
            bool: False - Auto preset switching disabled permanently
        """
        # ปิดการใช้งาน Auto Preset Switching ถาวร
        logging.debug(
            f"Auto preset switching disabled for dialogue type: {dialogue_type}"
        )
        return False
        # ตรวจสอบว่ามี control_ui หรือไม่
        if not hasattr(self, "control_ui") or not self.control_ui:
            self._update_status_line(
                "Control UI not available, using direct area switch"
            )
            return self.switch_area_directly(dialogue_type)

        current_areas = (
            self.current_area.split("+")
            if isinstance(self.current_area, str)
            else self.current_area
        )
        current_areas_set = set(current_areas)

        # ตรวจสอบว่า control_ui พร้อมใช้งานหรือไม่
        if not self.control_ui.root.winfo_exists():
            self._update_status_line(
                "Control UI not available, using direct area switch"
            )
            return self.switch_area_directly(dialogue_type)

        # อัพเดต detection history สำหรับการคำนวณความเสถียร
        self.update_detection_history(dialogue_type)

        # เรียกใช้ระบบวิเคราะห์ความเสถียร
        stability_info = self.area_detection_stability_system()

        # ถ้าความเสถียรต่ำเกินไป (<66%) ให้รอก่อน
        if stability_info["stability_score"] < 66:
            self._update_status_line(
                f"Stability too low ({int(stability_info['stability_score'])}%), waiting for more consistent detection"
            )
            return False

        # ค้นหา preset ที่เหมาะสมโดยอัตโนมัติ
        target_preset = self.find_appropriate_preset(dialogue_type)

        if target_preset is None:
            self._update_status_line(
                f"Could not find appropriate preset for {dialogue_type}, keeping current areas"
            )
            return False

        # ดึงหมายเลข preset ปัจจุบัน
        current_preset = self.control_ui.current_preset

        # ถ้า preset ปัจจุบันเหมาะสมกับประเภทข้อความอยู่แล้ว ให้ข้ามการสลับ
        if current_preset == target_preset:
            self._update_status_line(
                f"Already using appropriate preset (P{current_preset}) for {dialogue_type}"
            )
            return False

        # ตรวจสอบ preset เป้าหมายว่ามีอยู่จริง
        presets = self.settings.get_all_presets()
        if target_preset > len(presets):
            self._update_status_line(
                f"Target preset P{target_preset} does not exist, keeping current preset"
            )
            return False

        # บันทึกข้อมูลก่อนสลับ preset
        old_preset = current_preset
        old_areas = current_areas

        # สลับไปที่ preset เป้าหมาย
        try:
            self._update_status_line(
                f"✓ Auto switching from P{old_preset} to P{target_preset} for {dialogue_type}"
            )
            self.logging_manager.log_info(
                f"Auto switching preset: P{old_preset} -> P{target_preset} for dialogue type: {dialogue_type}"
            )

            # เรียกใช้ฟังก์ชัน load_preset ของ control_ui
            self.control_ui.load_preset(target_preset)

            # ตรวจสอบว่าการสลับ preset สำเร็จหรือไม่
            if self.control_ui.current_preset == target_preset:
                self.logging_manager.log_info(
                    f"Successfully switched to preset P{target_preset}"
                )
                return True
            else:
                self.logging_manager.log_error(
                    f"Failed to switch to preset P{target_preset}"
                )
                return False

        except Exception as e:
            self.logging_manager.log_error(f"Error switching preset: {e}")
            return False

    def find_appropriate_preset(self, dialogue_type):
        """
        ค้นหา preset ที่เหมาะสมกับประเภทข้อความโดยวิเคราะห์โครงสร้างของแต่ละ preset

        Args:
            dialogue_type: ประเภทข้อความ ("normal", "narrator", "choice" ฯลฯ)

        Returns:
            int: หมายเลข preset ที่เหมาะสม หรือ None ถ้าไม่พบ
        """
        # ดึงข้อมูล presets ทั้งหมด
        presets = self.settings.get_all_presets()
        if not presets:
            self.logging_manager.log_warning("No presets found")
            return None

        # เตรียมวิเคราะห์พื้นที่ที่เหมาะสมกับแต่ละประเภทข้อความ
        required_areas = {
            "normal": {"A", "B"},  # ต้องการทั้ง A และ B
            "narrator": {"C"},  # ต้องการ C
            "choice": {"B"},  # ต้องการแค่ B สำหรับ choice dialogue
            "speaker_in_text": {"B"},  # ต้องการแค่ B
            "dialog_without_name": {"B"},  # ต้องการแค่ B
        }

        # ถ้าไม่มีประเภทข้อความที่ต้องการในการจับคู่ ให้ใช้ preset 1
        if dialogue_type not in required_areas:
            return 1  # default เป็น preset 1

        # ลำดับความสำคัญของ preset (preset 1 มักเป็น default)
        preset_priority = [1, 2, 3, 4, 5]

        # รายการตัวเลือก preset ที่เข้าเกณฑ์
        candidates = []

        # วนลูปตรวจสอบแต่ละ preset ว่าตรงกับความต้องการหรือไม่
        for i, preset in enumerate(presets):
            preset_number = i + 1
            areas_str = preset.get("areas", "")
            areas_set = set(areas_str.split("+"))

            # ตรวจสอบว่า preset นี้มีพื้นที่ที่ต้องการทั้งหมดหรือไม่
            if required_areas[dialogue_type].issubset(areas_set):
                # เก็บคะแนนความเหมาะสม (ใช้ลำดับความสำคัญของ preset)
                priority_score = (
                    preset_priority.index(preset_number)
                    if preset_number in preset_priority
                    else 999
                )
                candidates.append((preset_number, priority_score, len(areas_set)))

        if not candidates:
            # ถ้าไม่พบ preset ที่เหมาะสม ให้ใช้ preset 1 เป็น default
            self.logging_manager.log_warning(
                f"No suitable preset found for {dialogue_type}, using preset 1"
            )
            return 1

        # เรียงลำดับตามความสำคัญและความกระชับของพื้นที่
        # - ลำดับที่ 1: คะแนนลำดับความสำคัญ (ต่ำกว่าดีกว่า)
        # - ลำดับที่ 2: จำนวนพื้นที่ (น้อยกว่าดีกว่า เพื่อเลือก preset ที่มีเฉพาะพื้นที่ที่จำเป็น)
        candidates.sort(key=lambda x: (x[1], x[2]))

        # เลือก preset ที่เหมาะสมที่สุด
        best_preset = candidates[0][0]

        self.logging_manager.log_info(
            f"Found appropriate preset {best_preset} for {dialogue_type}"
        )
        return best_preset

    def switch_area_directly(self, dialogue_type):
        """สลับพื้นที่โดยตรงตามประเภทข้อความ (ปิดใช้งานถาวร)

        Args:
            dialogue_type: ประเภทข้อความ ("normal", "narrator", "choice", ฯลฯ)

        Returns:
            bool: False - Auto area switching disabled permanently
        """
        # ปิดการใช้งาน Auto Area Switching ถาวร
        logging.debug(
            f"Auto direct area switching disabled for dialogue type: {dialogue_type}"
        )
        return False
        current_areas = (
            self.current_area.split("+")
            if isinstance(self.current_area, str)
            else self.current_area
        )
        current_areas_set = set(current_areas)

        # กำหนดพื้นที่ที่เหมาะสมสำหรับแต่ละประเภทข้อความ
        if dialogue_type == "normal":
            # บทสนทนาปกติ (มีทั้งชื่อและข้อความ) - ใช้พื้นที่ A+B
            target_areas = ["A", "B"]
        elif dialogue_type == "narrator":
            # บทบรรยาย - ใช้พื้นที่ C
            target_areas = ["C"]
        elif dialogue_type == "choice":
            # ตัวเลือก - ใช้พื้นที่ B
            target_areas = ["B"]
        elif dialogue_type in ["speaker_in_text", "dialog_without_name"]:
            # ข้อความที่มีชื่อคนพูดอยู่ในข้อความ หรือไม่มีชื่อ - ใช้พื้นที่ B
            target_areas = ["B"]
        else:
            # ประเภทข้อความที่ไม่รู้จัก - คงพื้นที่เดิม
            self._update_status_line(
                f"Unknown dialogue type: {dialogue_type}, keeping current areas"
            )
            return False

        # ตรวจสอบความจำเป็นในการสลับพื้นที่
        target_areas_set = set(target_areas)
        if current_areas_set == target_areas_set:
            # พื้นที่ปัจจุบันเหมาะสมกับประเภทข้อความอยู่แล้ว
            return False

        # สลับพื้นที่
        new_area_str = "+".join(target_areas)
        self.switch_area(new_area_str)
        self._update_status_line(f"✓ Auto switched to area: {new_area_str}")
        self.logging_manager.log_info(
            f"Auto switched from {'+'.join(current_areas)} to {new_area_str}"
        )

        return True

    def update_detection_history(self, dialogue_type):
        """บันทึกประวัติการตรวจจับประเภทข้อความ

        Args:
            dialogue_type: ประเภทข้อความที่ตรวจพบ ("normal", "narrator", "choice", ฯลฯ)
        """
        if not hasattr(self, "_detection_history"):
            self.area_detection_stability_system()  # สร้างถ้ายังไม่มี

        # เพิ่มเวลาปัจจุบันลงในประวัติของประเภทที่ตรวจพบ
        current_time = time.time()

        # จัดประเภทข้อความให้เข้ากับหมวดหมู่หลัก
        if dialogue_type == "normal":
            self._detection_history["normal"].append(current_time)
        elif dialogue_type == "narrator":
            self._detection_history["narrator"].append(current_time)
        elif dialogue_type == "choice":
            self._detection_history["choice"].append(current_time)
        elif dialogue_type in ["speaker_in_text", "dialog_without_name"]:
            self._detection_history["other"].append(current_time)
        else:
            self._detection_history["unknown"].append(current_time)

    def translation_loop(self):
        """จัดการการแปลและแสดงผลด้วยระบบ Text Stability Check"""
        # --- ตัวแปรจัดการสถานะภายใน Loop ---
        is_processing = False
        last_processing_time = time.time()
        idle_throttle = 0.3
        cpu_status_counter = 0  # Counter for CPU status display
        dalamud_status_counter = 0  # Counter for Dalamud status update

        while self.is_translating:
            try:
                if is_processing:
                    # Use CPU-aware sleep interval
                    if self.cpu_monitor and self.cpu_monitor.is_enabled():
                        sleep_time = self.cpu_monitor.get_sleep_interval()
                        time.sleep(sleep_time)
                    else:
                        time.sleep(0.05)
                    continue

                current_time = time.time()
                wait_time = 0.1 if self.force_next_translation else idle_throttle
                if time.time() - last_processing_time < wait_time:
                    # Use CPU-aware sleep for idle throttling too
                    if self.cpu_monitor and self.cpu_monitor.is_enabled():
                        sleep_time = min(0.05, self.cpu_monitor.get_sleep_interval())
                        time.sleep(sleep_time)
                    else:
                        time.sleep(0.05)
                    continue

                # --- เริ่ม Process ---
                is_processing = True
                last_processing_time = current_time

                # --- CPU Status Display (every 20 loops) ---
                cpu_status_counter += 1
                if (
                    self.cpu_monitor
                    and cpu_status_counter % 20 == 0
                    and self.cpu_monitor.is_enabled()
                ):
                    status_msg = self.cpu_monitor.get_status_message()
                    if status_msg:  # Only display if there's a message
                        self._update_status_line(status_msg)

                # --- Dalamud Status Update (every 10 loops ~ 1 second) ---
                dalamud_status_counter += 1
                if dalamud_status_counter >= 10 and self.dalamud_mode:
                    dalamud_status_counter = 0
                    # อัพเดต info label เพื่อแสดงสถานะล่าสุด
                    try:
                        self.logging_manager.log_info("🔄 Updating Dalamud status display...")
                        self.root.after(0, self.update_info_label_with_model_color)
                    except Exception as e:
                        self.logging_manager.log_error(f"Status update error: {e}")

                # --- Smart Switch & Click Translate Check (ปิดการใช้งาน Auto Switch) ---
                # self.smart_switch_area() # Auto switching disabled permanently

                # DISABLED - 1-Click mode causes delay in text hook display
                """
                if (
                    self.settings.get("enable_click_translate", False)
                    and not self.force_next_translation
                ):
                    self._update_status_line(
                        "▶ 1-Click Mode: Waiting for trigger (click FORCE button or right-click)"
                    )
                    is_processing = False
                    time.sleep(0.1)
                    continue
                """

                # --- TEXT HOOK MODE: Check for Dalamud text hook first ---
                text_hook_data = self.get_text_hook_data()
                if text_hook_data:
                    success = self.translate_and_display_directly(text_hook_data)
                    if success:
                        self._update_status_line("✅ Text hook translation complete")
                    is_processing = False
                    continue

                # --- DALAMUD MODE: Skip OCR completely if Dalamud is enabled and running ---
                # CRITICAL FIX: Check is_running instead of just is_connected
                # This prevents OCR from running when bridge is running but temporarily disconnected
                if self.dalamud_mode and hasattr(self, 'dalamud_bridge') and self.dalamud_bridge.is_running:
                    # Don't do OCR when using Dalamud mode, even if temporarily disconnected
                    if self.dalamud_bridge.is_connected:
                        self._update_status_line("✅ Dalamud Bridge Connected")
                    else:
                        self._update_status_line("⏳ Waiting for Dalamud connection...")
                    is_processing = False
                    time.sleep(0.1)  # Reduce CPU usage
                    continue

                # --- Capture & OCR (เฉพาะเมื่อไม่ใช้ Dalamud หรือไม่เชื่อมต่อ) ---
                ocr_results = self.capture_and_ocr()

                # --- Logic การรวมข้อความ (เหมือนเดิม) ---
                # ส่วนนี้ยังคงซับซ้อนเหมือนเดิมเพื่อรองรับทุก Use Case ของคุณ
                # แต่ผลลัพธ์สุดท้ายคือตัวแปร `combined_text`
                combined_text = ""
                # (โค้ดส่วนการรวมข้อความจาก area ต่างๆ ที่ซับซ้อนของคุณจะถูกนำมาวางที่นี่...
                # แต่เพื่อความง่าย ผมจะย่อส่วนนี้ให้เห็นภาพรวม Logic ใหม่)
                temp_texts = []
                has_dalamud = False
                for area, text in ocr_results:
                    corrected_text = self.text_corrector.correct_text(text).strip()
                    if area == "dalamud":
                        has_dalamud = True
                        temp_texts.insert(0, corrected_text)  # Dalamud text ใช้เป็น combined_text โดยตรง
                    elif area == "A":
                        temp_texts.insert(0, corrected_text)  # ชื่อขึ้นก่อน
                    else:
                        temp_texts.append(corrected_text)

                # สำหรับ Dalamud text ใช้โดยตรง ไม่ต้อง join
                if has_dalamud:
                    combined_text = temp_texts[0] if temp_texts else ""
                else:
                    combined_text = ": ".join(filter(None, temp_texts))

                # --- *** ระบบตรวจสอบความเสถียรของข้อความ (Logic ใหม่!) *** ---
                stable_text_to_translate = None

                if self.force_next_translation:
                    # ถ้าบังคับแปล ให้ข้ามระบบตรวจสอบทั้งหมด รวมทั้งการตรวจสอบข้อความซ้ำ
                    if combined_text:
                        stable_text_to_translate = combined_text
                        self.last_stable_text = combined_text  # อัปเดตทันที
                    self.force_next_translation = False  # ใช้ Flag ไปแล้ว รีเซ็ต
                    # รีเซ็ตระบบตรวจสอบความนิ่งสำหรับประโยคถัดไป
                    self.unstable_text = ""
                    self.stability_counter = 0

                else:  # โหมดแปลอัตโนมัติปกติ
                    # สำหรับ Dalamud text ให้แปลทันที ไม่ต้องรอ stability
                    if has_dalamud and combined_text:
                        stable_text_to_translate = combined_text
                        self.last_stable_text = combined_text
                        # Skip ทั้ง stability check - ไปตรงไป translation section
                    elif not combined_text:
                        # ถ้าไม่เจอข้อความเลย ให้รีเซ็ตระบบ
                        self.unstable_text = ""
                        self.stability_counter = 0
                        is_processing = False
                        continue

                    # Skip stability check ถ้าเป็น Dalamud text
                    if not has_dalamud:
                        if combined_text != self.unstable_text:
                            # หากข้อความมีการเปลี่ยนแปลง (เริ่มพิมพ์ / ประโยคใหม่)
                            # ให้เริ่มนับความเสถียรใหม่
                            self.unstable_text = combined_text
                            self.stability_counter = 1
                            self._update_status_line(
                                f"▶ Watching: {self.unstable_text[:30]}..."
                            )
                            is_processing = False
                            continue  # **สำคัญ: ยังไม่แปล รอรอบถัดไป**
                        else:
                            # หากข้อความเหมือนเดิม (กำลังนิ่ง)
                            self.stability_counter += 1
                            self._update_status_line(
                                f"▶ Stabilizing ({self.stability_counter}/{self.STABILITY_THRESHOLD})..."
                            )

                        # ตรวจสอบว่าข้อความนิ่งพอที่จะแปลหรือยัง
                        if self.stability_counter >= self.STABILITY_THRESHOLD:
                            # นิ่งแล้ว! แต่ต้องเป็นประโยคใหม่ที่ไม่ใช่ประโยคเดิมที่เพิ่งแปลไป
                            if self.unstable_text != self.last_stable_text:
                                stable_text_to_translate = self.unstable_text
                                self.last_stable_text = self.unstable_text

                            # รีเซ็ตระบบเพื่อรอประโยคถัดไป
                            self.unstable_text = ""
                            self.stability_counter = 0

                # --- *** สิ้นสุด Logic ใหม่ *** ---

                # --- ส่งข้อความที่ "เสถียร" แล้วไปแปล ---
                if stable_text_to_translate:
                    # ตั้ง flag การแปล สำหรับ Dalamud rate limiting
                    if has_dalamud:
                        self._is_translating_dalamud = True

                    self._update_status_line(
                        f"✅ Translating: {stable_text_to_translate[:30]}..."
                    )

                    # ตรวจสอบว่าเป็น Choice Dialogue หรือไม่
                    is_choice = (
                        self.is_choice_dialogue(stable_text_to_translate)
                        or self.is_choice_preset_active()
                    )
                    logging.info(
                        f"Choice detection result: {is_choice} for text: '{stable_text_to_translate[:50]}...'"
                    )

                    translated_text = self.translator.translate(
                        stable_text_to_translate, is_choice_option=is_choice
                    )

                    if translated_text and not translated_text.startswith("[Error"):
                        # ใช้ dual-state display สำหรับแสดงข้อความแปล
                        self.root.after(
                            0,
                            lambda txt=translated_text: self._display_translation_complete(
                                txt, stable_text_to_translate
                            ),
                        )
                        if hasattr(self, "translated_logs_instance"):
                            self.translated_logs_instance.add_message(translated_text)
                        self.last_translation = translated_text

                    # Reset Dalamud translation flag และ process pending queue
                    if has_dalamud:
                        self._is_translating_dalamud = False
                        # Process pending queue ถ้ามี
                        if hasattr(self, '_dalamud_pending_queue') and self._dalamud_pending_queue:
                            next_message = self._dalamud_pending_queue.pop(0)
                            print(f"📋 Processing queued message: {next_message['text'][:30]}...")
                            # เพิ่มข้อความถัดไปเข้า main queue
                            self.dalamud_text_queue.clear()
                            self.dalamud_text_queue.append(next_message)
                            # Trigger translation loop อีกรอบ
                            self.translation_event.set()

                is_processing = False

            except Exception as e:
                self._update_status_line(f"Error: {e}")
                logging.error(f"Translation loop error: {e}", exc_info=True)
                # Reset Dalamud flag ในกรณี error
                if hasattr(self, '_is_translating_dalamud'):
                    self._is_translating_dalamud = False
                is_processing = False
                time.sleep(0.5)

    def get_text_hook_data(self):
        """Get text data from Dalamud bridge (real-time text hook)"""
        if not self.dalamud_bridge or not self.dalamud_mode:
            return None

        try:
            # Get latest text from bridge
            text_data = self.dalamud_bridge.get_latest_text()
            if not text_data:
                return None

            # Format for MBB processing
            combined_text = ""
            if hasattr(text_data, 'speaker') and text_data.speaker and text_data.speaker.strip():
                combined_text = f"{text_data.speaker}: {text_data.message}"
            else:
                combined_text = text_data.message if hasattr(text_data, 'message') else str(text_data)

            # Check for duplicates
            if combined_text == self.last_text_hook_data:
                return None

            self.last_text_hook_data = combined_text
            self.logging_manager.log_info(f"📨 Text hook received: {combined_text[:50]}...")

            return combined_text.strip()

        except Exception as e:
            self.logging_manager.log_error(f"Error getting text hook data: {e}")
            return None

    def translate_and_display_directly(self, text_hook_data):
        """Translate and display text hook data immediately (bypass stability check)"""
        if not text_hook_data or not text_hook_data.strip():
            return False

        try:
            # Use direct translation without stability check
            translated_text = self.translator.translate(text_hook_data, is_choice_option=False)

            if translated_text and not translated_text.startswith("[Error"):
                # Display immediately
                self.root.after(
                    0,
                    lambda txt=translated_text: self._display_translation_complete(
                        txt, text_hook_data
                    ),
                )

                # Log translation
                if hasattr(self, "translated_logs_instance"):
                    self.translated_logs_instance.add_message(translated_text)

                self.last_translation = translated_text
                self.logging_manager.log_info(f"🎯 Direct translation displayed: {translated_text[:50]}...")
                return True
            else:
                self.logging_manager.log_warning(f"Translation failed: {translated_text}")
                return False

        except Exception as e:
            self.logging_manager.log_error(f"Error in direct translation: {e}")
            return False

    def translation_loop_improved(self):
        """
        Main OCR and Translation loop with improved logic for handling multiple areas,
        context, and preventing redundant translations.
        """
        if not self.ocr_available or not self.translator_ready:
            logging.warning(
                "OCR Engine or Translator not ready. Stopping translation loop."
            )
            self.translating = False
            # Optionally update UI to reflect stopped state
            if hasattr(self, "status_line_label"):
                self._update_status_line("Error: OCR/Translator not ready.")
            return

        logging.info("Starting improved translation loop...")
        if hasattr(self, "status_line_label"):
            self._update_status_line("Translation loop running...")

        # Initialize last state variables for comparison
        self.last_processed_text_a = ""
        self.last_processed_text_b = ""
        self.last_speaker = None
        self.last_translated_content_only = (
            ""  # Store only the content part of the last successful translation
        )

        while self.translating:
            try:
                start_time = time.time()

                # --- Area Capture and OCR ---
                if not self.area_manager or not self.area_manager.current_area_keys:
                    logging.warning("No active OCR areas selected.")
                    time.sleep(0.5)
                    continue

                area_key_a = self.area_manager.current_area_keys[0]
                area_key_b = (
                    self.area_manager.current_area_keys[1]
                    if len(self.area_manager.current_area_keys) > 1
                    else None
                )

                img_a, bbox_a = self.capture_screen_area(area_key_a)
                img_b, bbox_b = (
                    self.capture_screen_area(area_key_b) if area_key_b else (None, None)
                )

                if img_a is None:
                    logging.warning(f"Failed to capture Area A ({area_key_a}).")
                    time.sleep(0.2)
                    continue

                # Image Hashing and Cache Check
                img_hash_a = self.get_image_signature(img_a)
                img_hash_b = (
                    self.get_image_signature(img_b) if img_b is not None else None
                )

                cached_result_a = self.get_cached_ocr_result(area_key_a, img_hash_a)
                cached_result_b = (
                    self.get_cached_ocr_result(area_key_b, img_hash_b)
                    if area_key_b and img_hash_b
                    else None
                )

                text_a = ""
                text_b = ""

                # OCR Area A if not cached
                if cached_result_a is not None:
                    text_a = cached_result_a
                    logging.debug(f"Using cached OCR for Area A: {text_a[:30]}...")
                else:
                    # Preprocess image A (optional, depending on settings)
                    processed_img_a = self.preprocess_image(
                        img_a
                    )  # Add area_type if needed
                    ocr_result_a = self.ocr_engine.recognize(processed_img_a)
                    text_a = ocr_result_a if ocr_result_a else ""
                    self.cache_ocr_result(area_key_a, img_hash_a, text_a)
                    logging.debug(f"OCR Result Area A: {text_a[:30]}...")

                # OCR Area B if present and not cached
                if area_key_b and img_b is not None:
                    if cached_result_b is not None:
                        text_b = cached_result_b
                        logging.debug(f"Using cached OCR for Area B: {text_b[:30]}...")
                    else:
                        processed_img_b = self.preprocess_image(
                            img_b
                        )  # Add area_type if needed
                        ocr_result_b = self.ocr_engine.recognize(processed_img_b)
                        text_b = ocr_result_b if ocr_result_b else ""
                        self.cache_ocr_result(area_key_b, img_hash_b, text_b)
                        logging.debug(f"OCR Result Area B: {text_b[:30]}...")

                # --- Text Processing and Speaker Detection ---
                processed_text_a = text_a.strip() if text_a else ""
                processed_text_b = text_b.strip() if text_b else ""

                # Reset variables for this iteration
                speaker = None
                content_to_translate = ""
                dialogue_type_detected = DialogueType.NORMAL  # Default to NORMAL
                final_text_for_translation = ""  # Text to actually send for translation

                # --- Logic Modification Start ---
                if processed_text_a:
                    # If Area A has text, try to split speaker from Area A primarily
                    # Use the enhanced detector if available, otherwise fallback to text_corrector
                    temp_speaker, temp_content_a, temp_type = (
                        None,
                        processed_text_a,
                        DialogueType.NORMAL,
                    )  # Initialize fallbacks
                    if hasattr(self, "enhanced_detector") and self.enhanced_detector:
                        temp_speaker, temp_content_a, temp_type = (
                            self.enhanced_detector.enhanced_split_speaker_and_content(
                                processed_text_a, previous_speaker=self.last_speaker
                            )
                        )
                    elif hasattr(self, "text_corrector"):
                        temp_speaker, temp_content_a, temp_type = (
                            self.text_corrector.split_speaker_and_content(
                                processed_text_a
                            )
                        )
                    else:  # Fallback if neither detector is available
                        logging.warning("No name detector (enhanced or basic) found.")

                    if temp_speaker:
                        # Speaker found in Area A
                        speaker = temp_speaker
                        content_to_translate = temp_content_a
                        dialogue_type_detected = (
                            temp_type if temp_type else DialogueType.CHARACTER
                        )  # Use detected type or default to CHARACTER

                        # If Area B also has text, consider appending it
                        if processed_text_b:
                            # Heuristic: Append B if it seems like a continuation
                            # (e.g., A is short, or B starts similarly to A's end)
                            if (
                                len(temp_content_a.split()) < 7
                                or self.text_similarity(
                                    temp_content_a[-20:], processed_text_b[:20]
                                )
                                > 0.25
                            ):
                                content_to_translate += " " + processed_text_b
                                logging.debug(
                                    f"Appended text from Area B to Area A content."
                                )
                            else:
                                logging.warning(
                                    f"Area B text ('{processed_text_b[:30]}...') not appended to Area A speaker '{speaker}' due to low similarity/long A content."
                                )
                        # Prepare text for translation API (includes speaker)
                        final_text_for_translation = (
                            f"{speaker}: {content_to_translate}"
                        )

                    else:
                        # No speaker found in Area A, treat all of A as content
                        speaker = None  # Explicitly no speaker identified from Area A
                        content_to_translate = processed_text_a
                        dialogue_type_detected = (
                            temp_type if temp_type else DialogueType.NORMAL
                        )  # Use detected type

                        # If Area B has text, append it (more likely to be part of the same block)
                        if processed_text_b:
                            content_to_translate += " " + processed_text_b
                            logging.debug(
                                f"Appended text from Area B to Area A (no speaker found in A)."
                            )

                        # Text for translation API is just the content
                        final_text_for_translation = content_to_translate

                elif processed_text_b:
                    # If Area A is empty, but Area B has text
                    # *** CRITICAL: Do NOT attempt to split speaker from Area B ***
                    # Treat all of Area B as content, no speaker identified from areas.
                    speaker = None  # Explicitly no speaker found
                    content_to_translate = processed_text_b
                    final_text_for_translation = (
                        content_to_translate  # Text for translation is just B's content
                    )
                    # Try to detect type from B's content alone (e.g., might be System message)
                    dialogue_type_detected = DialogueType.NORMAL  # Default
                    if hasattr(self, "enhanced_detector") and self.enhanced_detector:
                        _, _, dialogue_type_detected = (
                            self.enhanced_detector.enhanced_split_speaker_and_content(
                                processed_text_b
                            )
                        )
                    elif hasattr(self, "text_corrector"):
                        _, _, dialogue_type_detected = (
                            self.text_corrector.split_speaker_and_content(
                                processed_text_b
                            )
                        )
                    # Keep NORMAL if no specific type detected from B alone

                else:
                    # Both Area A and B are empty
                    # Clear the display if it's currently showing something and exists
                    if (
                        self.last_translated_content_only
                        and self.active_translation_display
                        and hasattr(self.active_translation_display, "winfo_exists")
                        and self.active_translation_display.winfo_exists()
                    ):
                        if hasattr(self.active_translation_display, "update_text"):
                            self.active_translation_display.update_text("")
                            self.last_translated_content_only = (
                                ""  # Reset cache as display is cleared
                            )
                            self.last_speaker = None
                        else:
                            logging.warning(
                                "active_translation_display exists but has no update_text method."
                            )

                    # Prevent busy-waiting if OCR yields nothing consistently
                    time.sleep(
                        self.settings.get("ocr_interval", 0.1) + 0.05
                    )  # Slightly longer sleep
                    continue  # Skip to the next iteration

                # --- Logic Modification End ---

                # --- Check if translation should proceed ---
                should_translate_this_loop = False
                if content_to_translate:
                    # Basic check: Is the content different enough from the last translated content?
                    similarity_threshold = 0.95  # High threshold - only translate if significantly different

                    # Normalize content for comparison (optional, e.g., lowercasing)
                    current_content_norm = content_to_translate  # .lower()
                    last_content_norm = self.last_translated_content_only  # .lower()

                    if speaker == self.last_speaker:
                        # If speaker is the same, content needs to be different
                        if (
                            self.text_similarity(
                                current_content_norm, last_content_norm
                            )
                            < similarity_threshold
                        ):
                            should_translate_this_loop = True
                        # else: logging.debug("Skipping translation: Same speaker, similar content.")
                    else:
                        # If speaker is different, or no last speaker, translate new content
                        should_translate_this_loop = True

                # --- Translation Block ---
                if should_translate_this_loop and content_to_translate:
                    # Ensure translator object exists
                    if not hasattr(self, "translator") or not self.translator:
                        logging.error("Translator object not available!")
                        time.sleep(0.5)  # Wait before retrying or stopping
                        continue  # Or handle error more gracefully

                    # Check for choice dialogue based on the content_to_translate
                    is_choice = False
                    if hasattr(self.translator, "is_similar_to_choice_prompt"):
                        is_choice, _, _ = self.translator.is_similar_to_choice_prompt(
                            content_to_translate
                        )
                    else:
                        logging.error(
                            "Translator object missing 'is_similar_to_choice_prompt' method!"
                        )

                    if is_choice:
                        dialogue_type_detected = DialogueType.CHOICE
                        logging.info(
                            f"Choice dialogue detected: {content_to_translate[:50]}..."
                        )
                        # Handle choice translation
                        translated_text = ""
                        if hasattr(self.translator, "translate_choice"):
                            translated_text = self.translator.translate_choice(
                                content_to_translate
                            )
                        else:
                            logging.error(
                                "Translator object missing 'translate_choice' method!"
                            )

                        if translated_text and "[Error:" not in translated_text:
                            self.update_translation_display(
                                translated_text, None
                            )  # Update UI for choice
                            self.add_translated_log(
                                "Choice", content_to_translate, translated_text
                            )
                            # Update last translation cache specifically for choices
                            self.last_translated_content_only = (
                                content_to_translate  # Cache original choice block
                            )
                            self.last_speaker = "Choice"  # Set speaker context
                        else:
                            logging.warning(
                                f"Choice translation failed or returned error for: {content_to_translate[:50]}"
                            )

                    elif (
                        final_text_for_translation
                    ):  # Ensure we have something non-choice to translate
                        logging.info(
                            f"Translating: {final_text_for_translation[:60]}..."
                        )
                        # Normal translation
                        translated_text = ""
                        if hasattr(self.translator, "translate"):
                            translated_text = self.translator.translate(
                                final_text_for_translation
                            )
                        else:
                            logging.error(
                                "Translator object missing 'translate' method!"
                            )

                        # Update cache and UI
                        if translated_text and "[Error:" not in translated_text:

                            # Extract only the translated part if speaker was prepended by the API
                            display_translation = translated_text
                            if speaker and translated_text.startswith(speaker + ":"):
                                potential_display = translated_text[
                                    len(speaker) + 1 :
                                ].strip()
                                if (
                                    potential_display
                                ):  # Ensure something remains after stripping speaker
                                    display_translation = potential_display
                                # else: Keep the full translated_text if only speaker was returned

                            self.update_translation_display(
                                display_translation, speaker
                            )
                            self.add_translated_log(
                                speaker if speaker else "Narrator/System",
                                content_to_translate,
                                display_translation,
                            )

                            # Update last successful translation caches
                            self.last_translated_content_only = content_to_translate
                            self.last_speaker = speaker  # Can be None

                            # Update dialogue context if applicable
                            if hasattr(self.dialogue_context, "add_entry") and speaker:
                                self.dialogue_context.add_entry(
                                    speaker,
                                    content_to_translate,
                                    display_translation,
                                    current_time,
                                )
                        else:
                            # Handle translation failure or error response
                            logging.warning(
                                f"Translation failed or returned error/empty for: {final_text_for_translation[:60]}"
                            )
                            # Do not update last translated content on failure

                # --- End of Translation Block ---

                # --- Post-Translation Actions ---

                # Smart area switching logic can be called here
                # Consider basing it on dialogue_type_detected or content patterns
                # self.smart_switch_area(dialogue_type_detected, content_to_translate)

                # Update last processed raw texts (even if translation skipped)
                self.last_processed_text_a = processed_text_a
                self.last_processed_text_b = processed_text_b
                # Note: self.last_speaker is updated only on successful translation or choice detection

                # --- Loop Timing and Control ---
                elapsed = time.time() - start_time
                ocr_interval = self.settings.get(
                    "ocr_interval", 0.1
                )  # Get interval from settings
                sleep_time = max(0, ocr_interval - elapsed)
                time.sleep(sleep_time)

            except Exception as loop_error:
                logging.exception(
                    f"Error in translation loop: {loop_error}"
                )  # Use logging.exception for traceback
                # Consider adding a mechanism to stop the loop after too many consecutive errors
                # Update status UI to indicate error
                if hasattr(self, "status_line_label"):
                    self._update_status_line(f"Error: {loop_error}")
                time.sleep(1)  # Longer sleep after an error

        # --- Loop End ---
        logging.info("Translation loop stopped.")
        if hasattr(self, "status_line_label"):
            self._update_status_line("Translation stopped.")
        self._finish_stopping_translation()  # Call the cleanup method

    # --- Helper method potentially needed by the loop ---
    def _finish_stopping_translation(self):
        """Additional cleanup actions after the loop variable is set to False."""
        # Example: Ensure translator resources are released if necessary
        logging.debug("Executing post-translation loop cleanup.")
        # Maybe hide the UI?
        # self._hide_translated_ui_safely()

    def format_original_text_for_display(self, text, max_words=30):
        """Format original text for status display - single line, first 30 words"""
        if not text or not text.strip():
            return ""  # No message when no text

        # Clean the text and ensure single line
        clean_text = text.strip()
        # Replace all newlines and multiple spaces with single space
        clean_text = " ".join(clean_text.split())
        words = clean_text.split()

        if len(words) <= max_words:
            display_text = clean_text
        else:
            display_text = " ".join(words[:max_words]) + "..."

        # Limit total length to prevent UI overflow (single line)
        if len(display_text) > 120:
            display_text = display_text[:117] + "..."

        return f"📝 Original: {display_text}"

    def update_original_text_display(self, original_text):
        """Update status line with original text display and set 10-second auto-hide timer"""
        if original_text and original_text.strip():
            self.current_original_text = original_text
            formatted_text = self.format_original_text_for_display(original_text)
            self._update_status_line(formatted_text)

            # Cancel previous timer if exists
            if self.original_text_timer:
                self.original_text_timer.cancel()

            # Set 10-second timer to hide original text
            self.original_text_timer = threading.Timer(10.0, self._hide_original_text_display)
            self.original_text_timer.daemon = True
            self.original_text_timer.start()

    def _hide_original_text_display(self):
        """Hide original text display after timeout"""
        try:
            self.current_original_text = ""
            self._update_status_line("")  # Clear status line completely
        except Exception as e:
            logging.error(f"Error hiding original text display: {e}")

    def _update_status_line(self, message):
        """อัพเดทข้อความสถานะในบรรทัดเดียว และ Rainbow Progress Bar"""
        print(f"\r{message:<60}", end="", flush=True)  # ใช้ 60 ช่องสำหรับข้อความ
        self.logging_manager.update_status(message)

        # Update status label (rainbow progress bar disabled)
        if hasattr(self, "status_label"):
            self.status_label.config(text=message)

    def save_ui_positions(self):
        self.last_main_ui_pos = self.root.geometry()
        if hasattr(self, "mini_ui"):
            self.last_mini_ui_pos = self.mini_ui.mini_ui.geometry()
        if hasattr(self, "translated_ui_window"):
            self.last_translated_ui_pos = self.translated_ui_window.geometry()

    def load_ui_positions(self):
        if self.last_main_ui_pos:
            self.root.geometry(self.last_main_ui_pos)
        if self.last_mini_ui_pos and hasattr(self, "mini_ui"):
            self.mini_ui.mini_ui.geometry(self.last_mini_ui_pos)
        if self.last_translated_ui_pos and hasattr(self, "translated_ui_window"):
            self.translated_ui_window.geometry(self.last_translated_ui_pos)

    def do_move(self, event):
        # ตรวจสอบว่าไม่ได้อยู่ในระหว่างการทำงานหนัก
        if (
            hasattr(self, "_processing_intensive_task")
            and self._processing_intensive_task
        ):
            return  # ไม่อนุญาตให้เคลื่อนย้ายหน้าต่างระหว่างการทำงานหนัก

        if self.x is not None and self.y is not None:
            deltax = event.x - self.x
            deltay = event.y - self.y
            x = self.root.winfo_x() + deltax
            y = self.root.winfo_y() + deltay
            self.root.geometry(f"+{x}+{y}")
        self.save_ui_positions()

    def lock_ui_movement(self):
        """ล็อคการเคลื่อนย้ายหน้าต่างชั่วคราวเพื่อป้องกันการเคลื่อนที่โดยไม่ตั้งใจ"""
        self._processing_intensive_task = True
        self.logging_manager.log_info("UI movement locked")

    def unlock_ui_movement(self):
        """ปลดล็อคการเคลื่อนย้ายหน้าต่าง"""
        self._processing_intensive_task = False
        self.logging_manager.log_info("UI movement unlocked")

    def _finish_stopping_translation(self):
        """จัดการการทำงานสุดท้ายหลังหยุดการแปล เช่น ปลดล็อค UI และซ่อนไอคอนกำลังโหลด"""
        if hasattr(self, "hide_loading_indicator"):
            self.hide_loading_indicator()
        # ปลดล็อค UI การเคลื่อนย้าย
        self.unlock_ui_movement()

        # 🔄 SYNC FIX: ส่ง callback ไป TranslatedUI เมื่อหยุดการแปลเสร็จสิ้น
        self._notify_translated_ui_status_change(False)

    def toggle_ui(self):
        if self.settings.get("enable_ui_toggle"):
            self.save_ui_positions()
            if self.root.state() == "normal":
                # สลับจาก Main UI เป็น Mini UI
                self.main_window_pos = self.root.geometry()
                self.root.withdraw()
                self.mini_ui.mini_ui.deiconify()
                self.mini_ui.mini_ui.lift()
                self.mini_ui.mini_ui.attributes("-topmost", True)
                if self.last_mini_ui_pos:
                    self.mini_ui.mini_ui.geometry(self.last_mini_ui_pos)
            else:
                # สลับจาก Mini UI เป็น Main UI
                self.root.deiconify()
                self.root.attributes("-topmost", True)
                self.root.lift()
                if self.last_main_ui_pos:
                    self.root.geometry(self.last_main_ui_pos)
                self.mini_ui.mini_ui.withdraw()

            # ทำให้แน่ใจว่า Translated UI ยังคงแสดงอยู่ถ้ากำลังแปลอยู่
            if self.is_translating and self.translated_ui_window.winfo_exists():
                self.translated_ui_window.lift()
                self.translated_ui_window.attributes("-topmost", True)

            # อัพเดทสถานะของ Mini UI
            if hasattr(self, "mini_ui"):
                self.mini_ui.update_translation_status(self.is_translating)
                # อัปเดตสถานะการแปลใน control_ui
                if hasattr(self, "control_ui") and hasattr(
                    self.control_ui, "update_translation_status"
                ):
                    self.control_ui.update_translation_status(self.is_translating)

    def toggle_mini_ui(self):
        """Toggle between Main UI and Mini UI"""
        # NOTE: ปุ่ม MINI ไม่ต้องการ highlight เพราะเป็นการ transform UI ไม่ใช่การเปิด/ปิดหน้าต่าง
        # การ highlight จึงไม่เหมาะสมสำหรับปุ่มประเภทนี้ที่เปลี่ยนแปลงรูปแบบการแสดงผล

        try:
            self.save_ui_positions()

            if self.root.state() == "normal":
                # Switch to Mini UI
                main_x = self.root.winfo_x()
                main_y = self.root.winfo_y()
                main_width = self.root.winfo_width()
                main_height = self.root.winfo_height()

                self.root.withdraw()

                # Ensure mini UI exists before showing
                if hasattr(self, "mini_ui") and self.mini_ui and hasattr(self.mini_ui, "mini_ui"):
                    self.mini_ui.mini_ui.deiconify()
                    self.mini_ui.mini_ui.lift()
                    self.mini_ui.mini_ui.attributes("-topmost", True)

                    # Position Mini UI at the center of Main UI's last position
                    self.mini_ui.position_at_center_of_main(
                        main_x, main_y, main_width, main_height
                    )
                else:
                    # If mini UI doesn't exist, show main UI again
                    self.root.deiconify()
                    self.logging_manager.log_error("Mini UI not found, staying in main UI")

            else:
                # Switch to Main UI
                self.root.deiconify()
                self.root.lift()
                self.root.attributes("-topmost", True)
                if self.last_main_ui_pos:
                    self.root.geometry(self.last_main_ui_pos)

                # Safely withdraw mini UI
                if hasattr(self, "mini_ui") and self.mini_ui and hasattr(self.mini_ui, "mini_ui"):
                    self.mini_ui.mini_ui.withdraw()

            # Update Mini UI status safely
            if hasattr(self, "mini_ui") and self.mini_ui:
                self.mini_ui.update_translation_status(self.is_translating)

        except Exception as e:
            self.logging_manager.log_error(f"Error in toggle_mini_ui: {e}")
            # Ensure main UI is visible if error occurs
            try:
                self.root.deiconify()
                self.root.lift()
            except:
                pass

    def toggle_main_ui(self):
        self.save_ui_positions()
        if self.root.state() == "normal":
            self.root.withdraw()
        else:
            self.root.deiconify()
            self.root.overrideredirect(True)  # เพิ่มบรรทัดนี้
            if self.last_main_ui_pos:
                self.root.geometry(self.last_main_ui_pos)

    def start_move(self, event):
        self.x = event.x
        self.y = event.y

    def stop_move(self, event):
        self.x = None
        self.y = None

    def update_mini_ui_move(self):
        original_do_move = self.mini_ui.do_move_mini_ui

        def new_do_move_mini_ui(event):
            original_do_move(event)
            self.save_ui_positions()

        self.mini_ui.do_move_mini_ui = new_do_move_mini_ui

    def setup_ui_position_tracking(self):
        self.update_mini_ui_move()
        self.load_ui_positions()

    def blink(self):
        """สร้าง breathing effect แทนการกระพริบ"""
        if self.blinking:
            # ถ้ายังไม่มี breathing_effect ให้สร้างใหม่
            if not hasattr(self, "breathing_effect"):
                self.breathing_effect = self.create_breathing_effect()

            # เริ่ม breathing effect
            self.breathing_effect.start()
        else:
            # หยุด breathing effect เมื่อไม่ได้ทำงาน
            if hasattr(self, "breathing_effect"):
                self.breathing_effect.stop()
                # รีเซ็ตกลับไปที่ไอคอนสีดำเมื่อหยุด
                # Rainbow progress bar handles status display

    # ========================================
    # PREVIOUS DIALOG SYSTEM METHODS
    # ========================================

    def add_test_dialog_history(self):
        """Add some test dialog history for testing Previous Dialog system"""
        test_dialogs = [
            {
                "original": "Hello, how are you?",
                "translated": "สวัสดี คุณเป็นอย่างไร?",
                "speaker": "Test NPC 1",
                "timestamp": time.time() - 300
            },
            {
                "original": "The weather is nice today.",
                "translated": "อากาศดีมากวันนี้",
                "speaker": "Test NPC 2",
                "timestamp": time.time() - 200
            },
            {
                "original": "Thank you for your help!",
                "translated": "ขอบคุณสำหรับความช่วยเหลือ!",
                "speaker": "Test NPC 3",
                "timestamp": time.time() - 100
            }
        ]

        for dialog in test_dialogs:
            self.add_to_dialog_history(
                original_text=dialog["original"],
                translated_text=dialog["translated"],
                speaker=dialog["speaker"]
            )

        logging.info(f"📄 [TEST] Added {len(test_dialogs)} test dialogs to history")

    def add_to_dialog_history(self, original_text, translated_text, speaker=None, chat_type=None):
        """
        เพิ่มข้อความลงใน dialog history สำหรับ Previous Dialog system

        Args:
            original_text (str): ข้อความต้นฉบับ
            translated_text (str): ข้อความที่แปลแล้ว
            speaker (str, optional): ชื่อตัวละคร
            chat_type (str, optional): ประเภทแชท (Say/Tell/Party/etc.)
        """
        try:
            import time

            # Extract speaker from text if not provided
            if not speaker and hasattr(self, 'text_corrector'):
                try:
                    speaker, _, _ = self.text_corrector.split_speaker_and_content(original_text)
                    if not speaker:
                        speaker = "Unknown"
                except:
                    speaker = "Unknown"
            else:
                speaker = speaker or "Unknown"

            # Create dialog entry
            entry = {
                "original": original_text.strip(),
                "translated": translated_text.strip(),
                "timestamp": time.time(),
                "speaker": speaker,
                "chat_type": chat_type or "Say"
            }

            # Add to history
            self.dialog_history.append(entry)

            # Limit history size
            if len(self.dialog_history) > self.max_history:
                self.dialog_history.pop(0)
                logging.info(f"📄 [HISTORY] Removed oldest entry, keeping {self.max_history} entries")

            # Update current index to latest
            self.current_history_index = len(self.dialog_history) - 1

            logging.info(f"📄 [HISTORY] Added entry for '{speaker}': {len(self.dialog_history)}/{self.max_history}")

        except Exception as e:
            logging.error(f"❌ [HISTORY] Error adding to dialog history: {e}")

    def show_previous_dialog(self):
        """แสดงข้อความก่อนหน้า + reset fade timer"""
        try:
            if not self.dialog_history:
                logging.info("📄 [PREVIOUS] No dialog history available")
                return

            # ตรวจสอบว่ามีข้อความพอสำหรับ previous หรือไม่
            if len(self.dialog_history) < 2:
                logging.info("📄 [PREVIOUS] Not enough dialog history (need at least 2)")
                return

            # *** FIX v1.5.22: Simplified navigation logic without flag ***
            # Simple decrement with wrap-around
            self.current_history_index -= 1

            # ถ้าย้อนเกิน ให้วนกลับไปล่าสุด
            if self.current_history_index < 0:
                self.current_history_index = len(self.dialog_history) - 1

            # Get dialog entry
            current_dialog = self.dialog_history[self.current_history_index]

            # Display the previous dialog
            self.display_previous_dialog(current_dialog)

            # *** CRITICAL: Reset fade timer for user activity ***
            if hasattr(self, 'translated_ui') and hasattr(self.translated_ui, 'reset_fade_timer_for_user_activity'):
                self.translated_ui.reset_fade_timer_for_user_activity("previous_dialog")
                logging.info("🔄 [PREVIOUS] Fade timer reset completed")

            logging.info(f"📄 [PREVIOUS] Showing dialog {self.current_history_index + 1}/{len(self.dialog_history)}")

        except Exception as e:
            logging.error(f"❌ [PREVIOUS] Error in show_previous_dialog: {e}")

    def display_previous_dialog(self, dialog_entry):
        """แสดงข้อความจาก history บน TUI"""
        try:
            if hasattr(self, 'translated_ui') and self.translated_ui:
                # *** FIX: แสดงข้อความต้นฉบับโดยไม่ใส่ [PREVIOUS] prefix เพื่อรักษา verified mark ***
                # Format exactly like normal display: speaker: translated_text
                # *** FIX: ตรวจสอบและลบชื่อ speaker ที่ซ้ำ (เฉพาะใน Previous Dialog) ***
                translated_content = dialog_entry['translated']
                speaker_name = dialog_entry['speaker']

                # ตรวจสอบว่า translated_content เริ่มด้วยชื่อ speaker หรือไม่
                # *** FIX: ปรับปรุงการตรวจสอบให้ flexible กับ special characters ***
                if speaker_name and translated_content:
                    # ลองหาชื่อ speaker ในรูปแบบต่างๆ
                    speaker_base = speaker_name.rstrip("'\"")  # ลบ apostrophe/quote ท้าย

                    # ตรวจสอบทั้ง speaker_name เต็ม และ speaker_base
                    found_prefix = None
                    if translated_content.startswith(f"{speaker_name}:"):
                        found_prefix = f"{speaker_name}:"
                    elif translated_content.startswith(f"{speaker_base}:"):
                        found_prefix = f"{speaker_base}:"

                    if found_prefix:
                        # ลบชื่อ speaker ที่ซ้ำออก (เฉพาะใน Previous Dialog)
                        translated_content = translated_content[len(found_prefix):].strip()

                display_text = f"{speaker_name}: {translated_content}"

                # *** FIX: ใช้ update_text เหมือนใน TUI_sim testing ***
                # Force show TUI first to ensure it's visible
                if hasattr(self.translated_ui, 'show'):
                    self.translated_ui.show()

                # Update text using the same method as in TUI test files
                self.translated_ui.update_text(display_text)

                # Force UI update
                if hasattr(self.translated_ui, 'root'):
                    self.translated_ui.root.update_idletasks()
                    self.translated_ui.root.update()

                # Show feedback with position indicator - larger and more prominent
                time_ago = int(time.time() - dialog_entry['timestamp'])
                feedback = f"💬 [PREVIOUS DIALOG] ({time_ago}s ago) | Dialog {self.current_history_index + 1}/{len(self.dialog_history)}"
                self.translated_ui.show_feedback_message(feedback, bg_color="#2196F3", font_size=16)

                logging.info(f"📄 [DISPLAY] Showed previous dialog from '{dialog_entry['speaker']}'")

        except Exception as e:
            logging.error(f"❌ [DISPLAY] Error in display_previous_dialog: {e}")

    # ========================================

    # force_translate method removed - replaced by previous dialog system


    # get_cached_original_text method removed - was for force translate only

    # learn_from_force_translate method removed - no longer needed

    def update_highlight_on_preset_change(self, areas):
        """อัพเดทการแสดงพื้นที่ไฮไลท์เมื่อมีการเปลี่ยน preset
        Args:
            areas (list): รายการพื้นที่ที่ต้องแสดง
        """
        try:
            # ถ้ากำลังแสดงพื้นที่อยู่
            if self.is_area_shown:
                # บันทึกสถานะการแสดงผล
                was_showing = True
                # ซ่อนพื้นที่เก่า
                self.hide_show_area()
                # แสดงพื้นที่ใหม่ทันที
                self.show_area()
                # อัพเดทสถานะปุ่ม
                # show_area_button update removed - Edit Area functionality not used
                # show_area_button highlight update removed - Edit Area functionality not used

            logging.info(f"Updated highlight areas: {areas}")

        except Exception as e:
            logging.error(f"Error updating highlights: {e}")

    def switch_area(self, areas, preset_number_override=None):
        """
        Switch the active translation area(s) centrally. (Fixed max_presets error, Refined Overlay Update)
        """
        try:
            # 1. Validate and Canonicalize Input 'areas'
            if isinstance(areas, list):
                valid_areas = sorted([a for a in areas if a in ["A", "B", "C"]])
            elif isinstance(areas, str):
                valid_areas = sorted(
                    [a for a in areas.split("+") if a in ["A", "B", "C"]]
                )
            else:
                logging.error(
                    f"Invalid type for 'areas' in switch_area: {type(areas)}."
                )
                valid_areas = ["A"]  # Fallback

            if not valid_areas:
                logging.warning(
                    "No valid areas provided to switch_area. Defaulting to 'A'."
                )
                valid_areas = ["A"]

            new_area_str = "+".join(valid_areas)
            current_preset_in_settings = self.settings.get("current_preset", 1)

            # --- Check if state actually changed ---
            needs_update = False
            # ตรวจสอบว่า area เปลี่ยนแปลง หรือมีการ override preset ที่ต่างจากเดิม
            if not hasattr(self, "current_area") or self.current_area != new_area_str:
                needs_update = True
            elif (
                preset_number_override is not None
                and current_preset_in_settings != preset_number_override
            ):
                needs_update = True

            if not needs_update:
                logging.debug(
                    f"switch_area called for '{new_area_str}' (Preset {preset_number_override if preset_number_override else current_preset_in_settings}), no state change needed."
                )
                # แม้ state ไม่เปลี่ยน แต่ถ้า Show Area เปิดอยู่ ก็ควร refresh เผื่อพิกัดเปลี่ยน
                if self.is_area_shown:
                    self.root.after(10, self._refresh_area_overlay)  # ใช้ after เล็กน้อย
                return False

            # --- State is changing ---
            previous_area_str = getattr(self, "current_area", "N/A")
            logging.info(
                f"Switching area from '{previous_area_str}' to '{new_area_str}'..."
            )

            # 2. Update MBB State
            self.current_area = new_area_str

            # 3. Update Settings ("current_area")
            self.settings.set("current_area", self.current_area)

            # 4. Determine and Update Settings ("current_preset")
            determined_preset_num = current_preset_in_settings
            max_presets_count = 5  # ใช้ค่าคงที่

            if preset_number_override is not None:
                if 1 <= preset_number_override <= max_presets_count:
                    determined_preset_num = preset_number_override
                    logging.info(
                        f"Using provided preset override: {determined_preset_num}"
                    )
                    if current_preset_in_settings != determined_preset_num:
                        self.settings.set("current_preset", determined_preset_num)
                        # ไม่ต้องบันทึก manual time ที่นี่
                else:
                    logging.warning(
                        f"Invalid preset override {preset_number_override} ignored."
                    )
                    determined_preset_num = current_preset_in_settings
            else:
                # หา preset ที่ match กับ area combo ใหม่
                all_presets = self.settings.get_all_presets()
                match_found = False
                for i, preset_data in enumerate(all_presets):
                    preset_num = i + 1
                    preset_areas_sorted = sorted(
                        preset_data.get("areas", "").split("+")
                    )
                    if valid_areas == preset_areas_sorted:
                        determined_preset_num = preset_num
                        match_found = True
                        logging.info(
                            f"New area '{self.current_area}' matches Preset {determined_preset_num}."
                        )
                        break
                if not match_found:
                    logging.info(
                        f"New area '{self.current_area}' doesn't match preset definition. Keeping preset number {determined_preset_num}."
                    )

                # บันทึก preset ที่หาเจอ/คงไว้ ลง settings ถ้าต่างจากค่าเดิม
                if current_preset_in_settings != determined_preset_num:
                    self.settings.set("current_preset", determined_preset_num)
                    logging.info(
                        f"Set current_preset in settings to {determined_preset_num}"
                    )

            # OCR Area Selection removed - update_area_button_highlights call deleted (2 lines)

            # 5. Update Control UI Display (if it exists)
            if (
                hasattr(self, "control_ui")
                and self.control_ui
                and self.control_ui.root.winfo_exists()
            ):
                self.control_ui.update_display(self.current_area, determined_preset_num)
                logging.info(
                    f"Instructed Control UI update: areas='{self.current_area}', preset={determined_preset_num}"
                )

            # --- 7. Update Highlighted Area Overlay (Refined) ---
            if self.is_area_shown:
                # ใช้ self.root.after() เพื่อให้การอัพเดท UI เกิดขึ้นใน event loop รอบถัดไปเล็กน้อย
                # ช่วยให้ state update เสร็จสมบูรณ์ก่อน และ Tkinter พร้อมวาดใหม่
                logging.debug("Scheduling area overlay refresh.")
                self.root.after(10, self._refresh_area_overlay)  # หน่วงเวลาเล็กน้อย (10ms)

            # 8. Previous dialog system handles translation requests
            self.force_next_translation = True

            logging.info(
                f"Area switch to '{self.current_area}' completed (Preset {determined_preset_num})."
            )
            return True

        except Exception as e:
            self.logging_manager.log_error(f"Error in switch_area: {e}")
            import traceback

            traceback.print_exc()
            return False

    def _refresh_area_overlay(self):
        """Helper method to hide and immediately show the area overlay."""
        try:
            if self.is_area_shown:  # ตรวจสอบอีกครั้งเผื่อสถานะเปลี่ยนไป
                logging.info("Refreshing area overlay...")
                self.hide_show_area()
                self.show_area()
                # อาจจะต้องอัพเดทปุ่ม Show Area ด้วย ถ้าจำเป็น
                # show_area_button checks removed - Edit Area functionality not used
            else:
                logging.debug(
                    "Skipping overlay refresh because is_area_shown is False."
                )
        except Exception as e:
            logging.error(f"Error refreshing area overlay: {e}")

    def _sync_tui_button_state(self, is_visible, source="unknown"):
        """🔄 UNIFIED TUI BUTTON SYNC: ซิงค์สถานะ TUI button จากทุกแหล่ง"""
        try:
            # อัปเดตสถานะ TUI button ใน button_state_manager
            if hasattr(self, "button_state_manager"):
                self.button_state_manager.button_states["tui"]["active"] = is_visible
                visual_state = "toggle_on" if is_visible else "toggle_off"
                self.button_state_manager.update_button_visual("tui", visual_state)

            # NOTE: Using ButtonStateManager only - bottom_button_states removed

            state_text = "ON" if is_visible else "OFF"
            self.logging_manager.log_info(f"✅ TUI button synced to {state_text} state from {source}")

        except Exception as e:
            self.logging_manager.log_error(f"❌ Error syncing TUI button state: {e}")

    def hide_and_stop_translation(self):
        """ซ่อน UI เมื่อกดปุ่ม WASD (ใช้กับฟีเจอร์ auto-hide) - ไม่หยุดการแปล"""
        if self.settings.get("enable_wasd_auto_hide"):
            try:
                # ⚔️ CHECK: ถ้า TUI อยู่ใน Battle Chat Mode → ไม่ซ่อน
                if hasattr(self, 'translated_ui') and self.translated_ui:
                    if hasattr(self.translated_ui, 'battle_mode_active'):
                        if self.translated_ui.battle_mode_active:
                            self.logging_manager.log_info("⚔️ [WASD] Battle Chat active - ignoring WASD hide")
                            return  # ออกจาก function ทันที

                # บันทึกล็อก
                self.logging_manager.log_info(
                    "WASD auto-hide triggered - hiding UI only (translation continues)"
                )

                # 🎯 SYNC FIX: ซ่อน translated_ui ในทุกกรณี (รวม WASD keys)
                self._hide_translated_ui_all_cases()
                self.logging_manager.log_info("✅ ซ่อน Translated UI จาก WASD auto-hide")

                # 🔄 UNIFIED SYNC: ใช้ฟังก์ชัน unified sync
                self._sync_tui_button_state(False, "WASD auto-hide")

                # 🚫 NOTE: ไม่หยุดการแปล - ให้การแปลดำเนินต่อไปใน background
                # การซ่อน TUI เท่านั้น ตามการตั้งค่า enable_auto_hide setting

                # จัดการ thread ในเบื้องหลัง
                def stop_translation_background():
                    try:
                        # ✅ FREEZE FIX: ไม่รอ thread เสร็จสิ้น ในโหมด auto-hide ด้วย
                        if (
                            self.translation_thread
                            and self.translation_thread.is_alive()
                        ):
                            self.logging_manager.log_info(
                                "Signaling translation thread to stop (auto-hide)"
                            )
                            # ไม่ใช้ join() - thread จะจบเองเมื่อตรวจพบ is_translating = False
                        else:
                            self.logging_manager.log_info(
                                "Translation thread already stopped (auto-hide)"
                            )

                        # ซ่อนไอคอนกำลังโหลดหลังจากเสร็จสิ้น - ลดดีเลย์เหลือ 200ms
                        self.root.after(200, self.hide_loading_indicator)

                        # 🔄 SYNC FIX: ส่ง callback ไป TranslatedUI เมื่อหยุดจาก WASD
                        self.root.after(100, lambda: self._notify_translated_ui_status_change(False))
                    except Exception as e:
                        self.logging_manager.log_error(
                            f"Error in hide_and_stop_translation background: {e}"
                        )
                        # ซ่อนไอคอนกำลังโหลดในกรณีที่เกิดข้อผิดพลาด
                        self.root.after(0, self.hide_loading_indicator)

                # เริ่ม thread สำหรับหยุดการแปลในเบื้องหลัง
                threading.Thread(
                    target=stop_translation_background, daemon=True
                ).start()

            except Exception as e:
                self.logging_manager.log_error(
                    f"Error in hide_and_stop_translation: {e}"
                )
                if hasattr(self, "hide_loading_indicator"):
                    self.hide_loading_indicator()

    def exit_program(self):
        self.stop_translation()
        self.hide_show_area()
        self.remove_all_hotkeys()
        try:
            keyboard.unhook_all()
        except Exception as e:
            self.logging_manager.log_error(f"Error unhooking keyboard: {e}")

        # จัดการ font_manager ก่อนปิดโปรแกรม
        if hasattr(self, "font_manager") and hasattr(
            self.font_manager, "font_settings"
        ):
            # ทำความสะอาด observers ถ้าจำเป็น
            if hasattr(self.font_manager.font_settings, "save_settings"):
                try:
                    self.font_manager.font_settings.save_settings()
                    self.logging_manager.log_info("บันทึกการตั้งค่าฟอนต์ก่อนปิดโปรแกรม")
                except Exception as e:
                    self.logging_manager.log_error(f"ไม่สามารถบันทึกการตั้งค่าฟอนต์: {e}")

        # เพิ่ม translated_logs_window เข้าไปในรายการ windows ที่ต้องปิด
        windows_to_close = [
            self.translated_ui_window,
            self.translated_logs_window,  # เพิ่มบรรทัดนี้
            self.mini_ui.mini_ui,
        ]
        if hasattr(self.settings_ui, "settings_window"):
            windows_to_close.append(self.settings_ui.settings_window)
        if hasattr(self.settings_ui, "advance_ui") and self.settings_ui.advance_ui:
            windows_to_close.append(self.settings_ui.advance_ui.advance_window)

        for window in windows_to_close:
            if window:
                try:
                    window.destroy()
                except Exception as e:
                    self.logging_manager.log_error(f"Error destroying window: {e}")

        # ✅ FREEZE FIX: ไม่รอ thread จบตอนปิดโปรแกรม - thread เป็น daemon อยู่แล้วจะจบเอง
        if self.translation_thread and self.translation_thread.is_alive():
            self.logging_manager.log_info("Translation thread will stop naturally on program exit")

        # 🔒 AUTO-START CLEANUP: ทำความสะอาด auto-start timers
        try:
            if hasattr(self, 'auto_start_timer_id') and self.auto_start_timer_id:
                self.root.after_cancel(self.auto_start_timer_id)
                self.logging_manager.log_info("Auto-start timer cancelled on exit")

            if hasattr(self, 'auto_start_pending'):
                self.auto_start_pending = False

        except Exception as cleanup_error:
            self.logging_manager.log_error(f"Error cleaning up auto-start: {cleanup_error}")

        try:
            self.root.quit()
            self.root.destroy()
        except Exception as e:
            self.logging_manager.log_error(f"Error destroying root window: {e}")

        self.logging_manager.log_info("MagicBabel application closed")
        sys.exit(0)

    # ========================================================================
    # SWAP DATA METHODS REMOVED (90 lines deleted)
    # Methods deleted:
    #   - _get_current_npc_game_name() - read game name from npc.json (36 lines)
    #   - swap_npc_data() - launch swap_data.py subprocess (32 lines)
    #   - _update_swap_button_text() - update swap button UI (20 lines)
    # Reason: Project uses single npc.json (FFXIV only), no need to swap
    # ========================================================================

    def show_starter_guide(self, force_show=False):  # เพิ่ม parameter force_show
        """แสดงหน้าต่างแนะนำการใช้งานโปรแกรมสำหรับผู้ใช้ใหม่ รองรับไฟล์คู่มือแบบไดนามิก"""
        try:
            # *** 1. ตรวจสอบว่าหน้าต่าง Guide เปิดอยู่แล้วหรือไม่ ***
            if (
                hasattr(self, "guide_window")
                and self.guide_window
                and self.guide_window.winfo_exists()
            ):
                # ถ้าหน้าต่าง Guide เปิดอยู่แล้ว ให้ปิดแทน (toggle)
                self.logging_manager.log_info(
                    "Starter Guide window already exists. Closing it."
                )
                try:
                    self.guide_window.destroy()
                    self.guide_window = None
                    self.logging_manager.log_info("Guide window closed successfully.")
                except Exception as e:
                    self.logging_manager.log_error(f"Error closing guide window: {e}")
                return

            # *** 2. ตรวจสอบค่า show_guide_var และ force_show (เหมือนเดิม) ***
            if not force_show and not self.show_guide_var.get():
                self.logging_manager.log_info(
                    "Starter guide is disabled by user setting. Skipping."
                )
                return

            # --- ส่วนที่เหลือคือการสร้างหน้าต่างใหม่ (เหมือนเดิม แต่มีการปรับปรุง event handling) ---
            self.logging_manager.log_info("===== เริ่มต้นการแสดง Starter Guide =====")

            # ค้นหาไฟล์ guide*.png (เหมือนเดิม)
            guide_files = []
            current_dir = (
                os.getcwd()
            )  # ใช้ os.getcwd() หรือ os.path.dirname(__file__) ตามความเหมาะสม
            try:  # เพิ่ม try-except รอบ getcwd เผื่อกรณีพิเศษ
                current_dir = os.path.dirname(os.path.abspath(__file__))
            except NameError:
                current_dir = os.getcwd()

            self.logging_manager.log_info(f"ค้นหาไฟล์ใน directory: {current_dir}")

            # ค้นหาใน current directory
            for file in os.listdir(current_dir):
                if file.lower().startswith("guide") and file.lower().endswith(".png"):
                    guide_files.append(os.path.join(current_dir, file))
                    # logging.info(f"พบไฟล์: {file}") # อาจจะ log เยอะไป

            # ค้นหาในโฟลเดอร์ Guide
            guide_dir = os.path.join(current_dir, "Guide")
            if os.path.exists(guide_dir) and os.path.isdir(guide_dir):
                self.logging_manager.log_info(f"ค้นหาไฟล์ในโฟลเดอร์ Guide: {guide_dir}")
                for file in os.listdir(guide_dir):
                    if file.lower().startswith("guide") and file.lower().endswith(
                        ".png"
                    ):
                        # เช็คว่าไฟล์ซ้ำกับที่เจอใน current dir หรือไม่
                        full_path = os.path.join(guide_dir, file)
                        if full_path not in guide_files:
                            guide_files.append(full_path)
                            # logging.info(f"พบไฟล์ในโฟลเดอร์ Guide: {file}") # อาจจะ log เยอะไป

            # เรียงลำดับไฟล์ (เหมือนเดิม)
            def extract_number(filename):
                try:
                    match = re.search(r"guide(\d+)", os.path.basename(filename).lower())
                    if match:
                        return int(match.group(1))
                    return 999
                except:
                    return 999

            guide_files.sort(key=extract_number)
            self.logging_manager.log_info(f"พบไฟล์ guide ทั้งหมด {len(guide_files)} ไฟล์")

            if not guide_files:
                self.logging_manager.log_info(
                    "ไม่พบไฟล์คู่มือ guide*.png เลย - เปิดคู่มือออนไลน์แทน"
                )
                try:
                    webbrowser.open("https://iarcanar99.github.io/magicite_babel/")
                    self.logging_manager.log_info(
                        "เปิดคู่มือออนไลน์สำเร็จ: https://iarcanar99.github.io/magicite_babel/"
                    )
                except Exception as e:
                    self.logging_manager.log_error(f"ไม่สามารถเปิดคู่มือออนไลน์ได้: {e}")
                    messagebox.showwarning("ข้อผิดพลาด", f"ไม่สามารถเปิดคู่มือออนไลน์ได้\n{e}")
                return

            # สร้างหน้าต่างใหม่
            self.guide_window = tk.Toplevel(self.root)
            self.guide_window.title("Starter Guide")
            self.guide_window.overrideredirect(True)
            self.guide_window.attributes("-topmost", True)

            # การคำนวณตำแหน่งกลางจอ (เหมือนเดิม)
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            guide_width = 800
            guide_height = 600
            x_pos = (screen_width - guide_width) // 2
            y_pos = (screen_height - guide_height) // 2
            self.guide_window.geometry(f"{guide_width}x{guide_height}+{x_pos}+{y_pos}")
            self.guide_window.configure(bg="#333333")

            # *** 3. เพิ่ม Protocol Handler สำหรับการปิดหน้าต่าง ***
            def handle_guide_close():
                self.logging_manager.log_info("Guide window closed.")
                if hasattr(self, "guide_window") and self.guide_window:
                    # *** 5. เพิ่มการตรวจสอบว่าหน้าต่างยังมีอยู่ก่อนทำลาย ***
                    # (อาจถูกทำลายไปแล้วโดยวิธีอื่น)
                    if self.guide_window.winfo_exists():
                        self.guide_window.destroy()
                    # ในทุกกรณี ตั้งค่าตัวแปรกลับเป็น None
                    self.guide_window = None

            self.guide_window.protocol("WM_DELETE_WINDOW", handle_guide_close)

            # โหลดภาพคู่มือ (เหมือนเดิม)
            self.guide_photo_images = []
            successful_loads = 0
            for img_file in guide_files:
                try:
                    image = Image.open(img_file)
                    img_width, img_height = image.size
                    ratio = min(
                        (guide_width - 40) / img_width,
                        (guide_height - 100) / img_height,
                    )
                    new_width = int(img_width * ratio)
                    new_height = int(img_height * ratio)
                    resized_image = image.resize(
                        (new_width, new_height), Image.Resampling.LANCZOS
                    )
                    photo = ImageTk.PhotoImage(resized_image)
                    self.guide_photo_images.append(photo)
                    successful_loads += 1
                except Exception as e:
                    self.logging_manager.log_error(
                        f"ไม่สามารถโหลดไฟล์ {os.path.basename(img_file)}: {e}"
                    )

            if successful_loads == 0:
                self.logging_manager.log_error("ไม่สามารถโหลดไฟล์คู่มือใดๆ ได้เลย")
                handle_guide_close()  # เรียกใช้ฟังก์ชันปิดที่สร้างไว้
                messagebox.showerror("ข้อผิดพลาด", "ไม่สามารถโหลดไฟล์คู่มือได้")
                return

            # ติดตามหน้าปัจจุบัน (เหมือนเดิม)
            self.current_guide_page = 0
            self.total_guide_pages = len(self.guide_photo_images)
            self.logging_manager.log_info(
                f"จำนวนหน้าคู่มือทั้งหมด: {self.total_guide_pages} หน้า"
            )

            # สร้าง frame หลัก (เหมือนเดิม)
            main_frame = tk.Frame(self.guide_window, bg="#333333")
            main_frame.pack(fill=tk.BOTH, expand=True)

            # โหลดไอคอน del.png และใช้ Label แทน Button เพื่อให้โปร่งใส
            try:
                del_icon = tk.PhotoImage(file="assets/del.png")

                # ใช้ Label เพื่อให้พื้นหลังโปร่งใส
                close_button = tk.Label(
                    self.guide_window,
                    image=del_icon,
                    bg=self.guide_window.cget("bg"),  # ใช้สีพื้นหน้าต่าง
                    cursor="hand2",
                )
                close_button.image = del_icon  # เก็บ reference

            except:
                # ถ้าโหลดไอคอนไม่ได้ ใช้ text แทน
                close_button = tk.Label(
                    self.guide_window,
                    text="×",
                    font=("Arial", 16, "bold"),
                    bg=self.guide_window.cget("bg"),
                    fg="#888888",  # สีเทาอ่อน
                    cursor="hand2",
                )

            close_button.place(x=guide_width - 40, y=10)

            # เพิ่ม hover effect ให้แสดงสี theme_accent เมื่อ hover
            theme_accent = (
                self.appearance_manager.get_accent_color()
                if hasattr(self, "appearance_manager")
                else "#6C5CE7"
            )
            window_bg = self.guide_window.cget("bg")

            def on_enter(e):
                close_button.configure(bg=theme_accent)

            def on_leave(e):
                close_button.configure(bg=window_bg)

            def on_click(e):
                handle_guide_close()  # เรียกฟังก์ชันที่สร้างไว้

            close_button.bind("<Enter>", on_enter)
            close_button.bind("<Leave>", on_leave)
            close_button.bind("<Button-1>", on_click)  # เพิ่ม click event

            # สร้างแคนวาส (เหมือนเดิม)
            self.guide_canvas = tk.Canvas(
                main_frame,
                width=guide_width,
                height=guide_height - 80,
                bg="#333333",
                highlightthickness=0,
            )
            self.guide_canvas.pack(pady=(20, 0))

            # สร้าง frame ล่าง (เหมือนเดิม)
            bottom_frame = tk.Frame(main_frame, bg="#333333", height=60)
            bottom_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=10)
            bottom_frame.pack_propagate(False)

            # Checkbutton "ไม่ต้องแสดงอีก" (เหมือนเดิม)
            dont_show_check = Checkbutton(
                bottom_frame,
                text="ไม่ต้องแสดงอีก",
                variable=self.show_guide_var,
                onvalue=False,
                offvalue=True,
                command=self._toggle_show_guide_setting,
                bg="#333333",
                fg="#FFFFFF",
                selectcolor="#444444",
                activebackground="#333333",
                activeforeground="#FFFFFF",
                bd=0,
                font=("Tahoma", 10),
            )
            dont_show_check.pack(side=tk.LEFT, padx=(20, 0), anchor=tk.W)

            # Frame กลางสำหรับปุ่มนำทาง (เหมือนเดิม)
            nav_center_frame = tk.Frame(bottom_frame, bg="#333333")
            nav_center_frame.pack(expand=True)

            # ปุ่มย้อนกลับ (เหมือนเดิม)
            self.prev_button = tk.Button(
                nav_center_frame,
                text="<",
                font=("Arial", 14, "bold"),
                bg="#555555",
                fg="#FFFFFF",
                bd=0,
                padx=10,
                pady=0,
                command=self.show_prev_guide_page,
            )
            self.prev_button.pack(side=tk.LEFT, padx=(0, 10))

            # เลขหน้า (เหมือนเดิม)
            page_frame = tk.Frame(nav_center_frame, bg="#444444", padx=10, pady=3)
            page_frame.pack(side=tk.LEFT)
            self.page_label = tk.Label(
                page_frame,
                text=f"1/{self.total_guide_pages}",
                font=("Arial", 12, "bold"),
                bg="#444444",
                fg="#FFFFFF",
            )
            self.page_label.pack()

            # ปุ่มถัดไป (เหมือนเดิม)
            self.next_button = tk.Button(
                nav_center_frame,
                text=">",
                font=("Arial", 14, "bold"),
                bg="#555555",
                fg="#FFFFFF",
                bd=0,
                padx=10,
                pady=0,
                command=self.show_next_guide_page,
            )
            self.next_button.pack(side=tk.LEFT, padx=(10, 0))

            # Hover effect ปุ่ม Prev/Next (เหมือนเดิม)
            for button in [self.prev_button, self.next_button]:
                button.bind(
                    "<Enter>",
                    lambda e, b=button: b.config(bg="#777777", cursor="hand2"),
                )
                button.bind("<Leave>", lambda e, b=button: b.config(bg="#555555"))

            # ตั้งค่าสถานะปุ่มเริ่มต้น (เหมือนเดิม)
            if self.current_guide_page == 0:
                self.prev_button.config(state=tk.DISABLED)
            if self.total_guide_pages <= 1:
                self.next_button.config(state=tk.DISABLED)

            # ผูกปุ่ม Escape (ใช้ handle_guide_close)
            self.guide_window.bind("<Escape>", lambda e: handle_guide_close())

            # เพิ่มการเคลื่อนย้ายหน้าต่าง
            self.guide_drag_x = 0
            self.guide_drag_y = 0

            def start_drag(event):
                # *** ตรวจสอบก่อนเริ่มลาก ***
                if (
                    hasattr(self, "guide_window")
                    and self.guide_window
                    and self.guide_window.winfo_exists()
                ):
                    self.guide_drag_x = event.x
                    self.guide_drag_y = event.y
                else:  # ถ้าหน้าต่างไม่มีแล้ว ไม่ต้องทำอะไร
                    self.guide_drag_x = None
                    self.guide_drag_y = None

            def do_drag(event):
                # *** 4. ตรวจสอบว่าหน้าต่างยังอยู่ และเริ่มลากหรือยัง ก่อนเข้าถึง winfo ***
                if (
                    hasattr(self, "guide_window")
                    and self.guide_window
                    and self.guide_window.winfo_exists()
                    and self.guide_drag_x is not None
                ):
                    try:
                        deltax = event.x - self.guide_drag_x
                        deltay = event.y - self.guide_drag_y
                        x = self.guide_window.winfo_x() + deltax
                        y = self.guide_window.winfo_y() + deltay
                        self.guide_window.geometry(f"+{x}+{y}")
                    except tk.TclError as e:
                        # จัดการ error กรณี window หายไประหว่างลาก
                        logging.warning(
                            f"Error during guide drag (window might be closed): {e}"
                        )
                        self.guide_drag_x = None  # หยุดการลาก
                        self.guide_drag_y = None
                else:
                    # หยุดการลากถ้าหน้าต่างหายไปหรือไม่เคยเริ่มลาก
                    self.guide_drag_x = None
                    self.guide_drag_y = None

            # ผูกเหตุการณ์คลิกและลาก (เหมือนเดิม)
            for widget in [
                main_frame,
                self.guide_canvas,
                bottom_frame,
                nav_center_frame,
                page_frame,
                self.page_label,
            ]:
                widget.bind("<Button-1>", start_drag)
                widget.bind("<B1-Motion>", do_drag)

            # แสดงภาพคู่มือหน้าแรก
            self.update_guide_page()  # เรียกเมธอดนี้

            self.logging_manager.log_info(
                f"แสดงหน้าต่าง Starter Guide ({self.total_guide_pages} หน้า) สำเร็จ"
            )

        except Exception as e:
            self.logging_manager.log_error(f"เกิดข้อผิดพลาดในการแสดง Starter Guide: {e}")
            import traceback

            self.logging_manager.log_error(traceback.format_exc())
            if (
                hasattr(self, "guide_window")
                and self.guide_window
                and self.guide_window.winfo_exists()
            ):
                try:
                    self.guide_window.destroy()
                except:
                    pass
                self.guide_window = None  # ตั้งค่ากลับเป็น None

    def _toggle_show_guide_setting(self):
        """อัพเดทค่า setting 'show_starter_guide' เมื่อ Checkbutton ถูกคลิก"""
        try:
            new_value = self.show_guide_var.get()
            self.settings.set("show_starter_guide", new_value)
            # ไม่จำเป็นต้อง save_settings() ที่นี่ เพราะ set() จัดการให้แล้ว
            self.logging_manager.log_info(
                f"Setting 'show_starter_guide' updated to: {new_value}"
            )
        except Exception as e:
            self.logging_manager.log_error(
                f"Error updating show_starter_guide setting: {e}"
            )

    def resize_guide_image(self, image, width, height):
        """ปรับขนาดรูปภาพให้พอดีกับพื้นที่แสดงผล แต่ยังคงรักษาสัดส่วน"""
        try:
            img_width, img_height = image.size
            ratio = min(width / img_width, height / img_height)

            new_width = int(img_width * ratio)
            new_height = int(img_height * ratio)

            return image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        except Exception as e:
            self.logging_manager.log_error(f"ข้อผิดพลาดในการปรับขนาดภาพ: {e}")
            return image  # คืนค่าภาพเดิมถ้าปรับขนาดไม่สำเร็จ

    def update_guide_page(self):
        """อัพเดตหน้าคู่มือตามหน้าปัจจุบัน"""
        try:
            # ล้างแคนวาส
            self.guide_canvas.delete("all")

            # ตรวจสอบความถูกต้องของดัชนีหน้า
            if not hasattr(self, "guide_photo_images") or not self.guide_photo_images:
                self.logging_manager.log_error("ไม่พบรายการภาพคู่มือ")
                return

            if not hasattr(self, "total_guide_pages"):
                self.total_guide_pages = len(self.guide_photo_images)

            if self.current_guide_page < 0:
                self.current_guide_page = 0
            elif self.current_guide_page >= self.total_guide_pages:
                self.current_guide_page = self.total_guide_pages - 1

            # บันทึกล็อกการเปลี่ยนหน้า
            self.logging_manager.log_info(
                f"กำลังแสดงหน้าที่ {self.current_guide_page + 1}/{self.total_guide_pages}"
            )

            # แสดงภาพตรงกลางแคนวาส
            canvas_width = self.guide_canvas.winfo_width()
            canvas_height = self.guide_canvas.winfo_height()

            if canvas_width <= 1:  # ถ้ายังไม่ได้เรนเดอร์
                canvas_width = 800
            if canvas_height <= 1:
                canvas_height = 540  # 600 - 60

            self.guide_canvas.create_image(
                canvas_width // 2,
                canvas_height // 2,
                image=self.guide_photo_images[self.current_guide_page],
            )

            # อัพเดตเลขหน้า
            if hasattr(self, "page_label"):
                self.page_label.config(
                    text=f"{self.current_guide_page + 1}/{self.total_guide_pages}"
                )

            # อัพเดตสถานะปุ่มย้อนกลับ
            if hasattr(self, "prev_button"):
                if self.current_guide_page == 0:
                    self.prev_button.config(state=tk.DISABLED)
                else:
                    self.prev_button.config(state=tk.NORMAL)

            # อัพเดตสถานะปุ่มถัดไป
            if hasattr(self, "next_button"):
                if self.current_guide_page >= self.total_guide_pages - 1:
                    self.next_button.config(state=tk.DISABLED)
                else:
                    self.next_button.config(state=tk.NORMAL)

        except Exception as e:
            self.logging_manager.log_error(f"เกิดข้อผิดพลาดในการอัพเดตหน้าคู่มือ: {e}")

    def show_next_guide_page(self):
        """แสดงหน้าคู่มือถัดไป"""
        if (
            hasattr(self, "total_guide_pages")
            and self.current_guide_page < self.total_guide_pages - 1
        ):
            self.current_guide_page += 1
            self.update_guide_page()
            self.logging_manager.log_info(
                f"เปลี่ยนไปหน้าถัดไป: {self.current_guide_page + 1}/{self.total_guide_pages}"
            )

    def show_prev_guide_page(self):
        """แสดงหน้าคู่มือก่อนหน้า"""
        if hasattr(self, "total_guide_pages") and self.current_guide_page > 0:
            self.current_guide_page -= 1
            self.update_guide_page()
            self.logging_manager.log_info(
                f"เปลี่ยนไปหน้าก่อนหน้า: {self.current_guide_page + 1}/{self.total_guide_pages}"
            )

    def show_loading_indicator(self):
        """แสดงไอคอนกำลังโหลด - ปิดการใช้งานเพื่อลบ white window แว้บ"""
        # ปิดการใช้งาน loading indicator เพื่อลบ white window ที่แว้บขึ้นมา
        # ใช้ rainbow progress bar และสถานะข้อความแทน
        pass

    def hide_loading_indicator(self):
        """ซ่อนไอคอนกำลังโหลด - ปิดการใช้งาน"""
        # ปิดการใช้งาน loading indicator
        pass


class LoadingIndicator:
    """แสดงไอคอนกำลังโหลดแบบ modern sound wave animation"""

    def __init__(self, parent):
        self.parent = parent
        self.window = None
        self.canvas = None
        self.bars = []
        self.is_showing = False
        self.animation_job = None

        # ค่าสำหรับการทำ animation
        self.bar_count = 4  # จำนวนแท่ง
        self.bar_width = 6  # ความกว้างของแต่ละแท่ง
        self.bar_spacing = 4  # ระยะห่างระหว่างแท่ง
        self.bar_base_height = 12  # ความสูงพื้นฐาน
        self.bar_height_variance = 8  # ความแตกต่างของความสูงระหว่างขึ้น-ลง
        self.animation_speed = 80  # ความเร็วในการเคลื่อนไหว (ms)

        # สีของแท่ง (ควรสอดคล้องกับธีมของแอพ)
        self.bar_color = appearance_manager.get_accent_color()

    def create_window(self):
        """สร้างหน้าต่างสำหรับแสดงไอคอนกำลังโหลด"""
        if self.window and self.window.winfo_exists():
            return

        # สร้างหน้าต่างใหม่
        self.window = tk.Toplevel(self.parent)
        self.window.overrideredirect(True)  # ไม่มีกรอบหน้าต่าง
        self.window.attributes("-topmost", True)  # แสดงด้านบนสุด

        # กำหนดขนาดตามที่ต้องการ
        window_width = (
            (self.bar_width * self.bar_count)
            + (self.bar_spacing * (self.bar_count - 1))
            + 20
        )
        window_height = self.bar_base_height + self.bar_height_variance + 20

        # กำหนดตำแหน่งตรงกลางของ parent
        parent_x = self.parent.winfo_rootx() + self.parent.winfo_width() // 2
        parent_y = self.parent.winfo_rooty() + self.parent.winfo_height() // 2
        x = parent_x - window_width // 2
        y = parent_y - window_height // 2

        self.window.geometry(f"{window_width}x{window_height}+{x}+{y}")

        # สร้างสีพื้นหลังโปร่งใส - แก้ไขส่วนนี้
        self.window.configure(bg="black")
        self.window.wm_attributes(
            "-transparentcolor", "black"
        )  # เพิ่มบรรทัดนี้ ทำให้สีดำกลายเป็นโปร่งใส
        self.window.attributes("-alpha", 0.9)  # ความโปร่งใสเล็กน้อย

        # สร้าง Canvas สำหรับวาดแท่ง
        self.canvas = tk.Canvas(
            self.window,
            width=window_width,
            height=window_height,
            bg="black",
            highlightthickness=0,
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # สร้างแท่งสำหรับ animation
        self.create_bars()

        # อัพเดตแสดงผลทันที
        self.window.update_idletasks()

    def create_bars(self):
        """สร้างแท่งสำหรับทำ animation"""
        self.bars = []
        start_x = 10  # ระยะห่างจากขอบซ้าย

        # ทำให้แท่งมีสีเรืองแสงมากขึ้น - แก้ไขส่วนนี้
        glow_color = appearance_manager.get_theme_color("accent_light")
        if not glow_color:
            glow_color = "#00ffff"  # ใช้สีฟ้าเรืองแสงถ้าไม่พบในธีม

        for i in range(self.bar_count):
            # สร้างแท่งแต่ละแท่งด้วยความสูงสุ่ม
            x = start_x + i * (self.bar_width + self.bar_spacing)
            height = self.bar_base_height + random.randint(0, self.bar_height_variance)

            # คำนวณตำแหน่ง y เริ่มต้นเพื่อให้แท่งอยู่ตรงกลางตามแนวดิ่ง
            y_center = self.window.winfo_height() // 2
            y1 = y_center - height // 2
            y2 = y1 + height

            # สร้างแท่งด้วยสี่เหลี่ยมมนพร้อมขอบเรืองแสง
            bar = self.canvas.create_rectangle(
                x,
                y1,
                x + self.bar_width,
                y2,
                fill=glow_color,  # ใช้สีเรืองแสง
                outline=glow_color,  # ขอบสีเดียวกับพื้น
                width=1,  # ความหนาของขอบ
                stipple="",  # ไม่ใช้ลวดลาย
            )
            self.bars.append({"id": bar, "height": height})

    def animate(self):
        """ทำ animation แท่งขึ้นลงเหมือนคลื่นเสียง"""
        if not self.is_showing or not self.window or not self.window.winfo_exists():
            return

        y_center = self.window.winfo_height() // 2

        for i, bar in enumerate(self.bars):
            # สุ่มความสูงใหม่
            new_height = self.bar_base_height + random.randint(
                0, self.bar_height_variance
            )

            # คำนวณตำแหน่งใหม่
            x1, _, x2, _ = self.canvas.coords(bar["id"])
            y1 = y_center - new_height // 2
            y2 = y1 + new_height

            # ปรับตำแหน่งแท่ง
            self.canvas.coords(bar["id"], x1, y1, x2, y2)

            # อัพเดทความสูงสำหรับรอบถัดไป
            self.bars[i]["height"] = new_height

        # ตั้งเวลาสำหรับเฟรมถัดไป
        self.animation_job = self.window.after(self.animation_speed, self.animate)

    def show(self):
        """แสดงไอคอนกำลังโหลด"""
        self.is_showing = True
        self.create_window()
        self.animate()

        # บังคับให้อัพเดตหน้าจอทันที
        if self.window:
            self.window.update_idletasks()
            self.window.update()

    def hide(self):
        """ซ่อนไอคอนกำลังโหลด"""
        self.is_showing = False

        # ยกเลิก animation task ที่กำลังทำงานอยู่
        if self.animation_job and self.window and self.window.winfo_exists():
            self.window.after_cancel(self.animation_job)
            self.animation_job = None

        # ปิดหน้าต่าง
        if self.window and self.window.winfo_exists():
            self.window.destroy()
            self.window = None


class CrashErrorHandler:
    def __init__(self):
        self.error_log_file = "MBB_errors.log"
        self.setup_logging()
        self.setup_global_exception_handler()

    def setup_logging(self):
        logging.basicConfig(
            level=logging.ERROR,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(self.error_log_file, encoding="utf-8"),
                logging.StreamHandler(),
            ],
        )

    def log_error(self, exc_type, exc_value, exc_traceback, context=""):
        error_msg = f"""
{'='*80}
CRASH ERROR DETECTED - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'='*80}
Context: {context}
Error Type: {exc_type.__name__}
Error Message: {str(exc_value)}
Traceback:
{''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))}
{'='*80}
"""
        logging.error(error_msg)
        return error_msg

    def show_user_error_dialog(self, error_summary, full_error=""):
        try:
            root = tk.Tk()
            root.withdraw()

            error_title = "Magic Babel - Critical Error"

            short_msg = f"""การทำงานของ Magic Babel พบข้อผิดพลาดร้ายแรง:

{error_summary}

- ข้อมูลรายละเอียดได้ถูกบันทึกไว้ใน: {self.error_log_file}
- โปรแกรมจะยังคงพยายามทำงานต่อไป
- หากปัญหาเกิดขึ้นซ้ำ กรุณาปิดและเปิดโปรแกรมใหม่

คุณต้องการดูรายละเอียดเพิ่มเติมหรือไม่?"""

            result = messagebox.askyesno(error_title, short_msg)

            if result and full_error:
                detail_window = tk.Toplevel()
                detail_window.title(f"รายละเอียดข้อผิดพลาด - Magic Babel v{__version__}")
                detail_window.geometry("800x600")

                text_frame = tk.Frame(detail_window)
                text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

                scrollbar = tk.Scrollbar(text_frame)
                scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

                text_widget = tk.Text(
                    text_frame, wrap=tk.WORD, yscrollcommand=scrollbar.set
                )
                text_widget.pack(fill=tk.BOTH, expand=True)
                text_widget.insert(tk.END, full_error)
                text_widget.config(state=tk.DISABLED)

                scrollbar.config(command=text_widget.yview)

                close_btn = tk.Button(
                    detail_window, text="ปิด", command=detail_window.destroy
                )
                close_btn.pack(pady=5)

                detail_window.transient(root)
                detail_window.grab_set()
                detail_window.mainloop()

            root.destroy()
        except Exception as dialog_error:
            print(f"Error showing error dialog: {dialog_error}")

    def handle_exception(self, exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        full_error = self.log_error(
            exc_type, exc_value, exc_traceback, "Global Exception Handler"
        )

        error_summary = f"{exc_type.__name__}: {str(exc_value)[:200]}"
        if len(str(exc_value)) > 200:
            error_summary += "..."

        try:
            threading.Thread(
                target=self.show_user_error_dialog,
                args=(error_summary, full_error),
                daemon=True,
            ).start()
        except:
            print("Failed to show error dialog")

    def handle_thread_exception(self, exc_type, exc_value, exc_traceback, thread=None):
        context = f"Thread: {thread.name if thread else 'Unknown'}"
        full_error = self.log_error(exc_type, exc_value, exc_traceback, context)

        error_summary = f"Thread Error - {exc_type.__name__}: {str(exc_value)[:150]}"
        if len(str(exc_value)) > 150:
            error_summary += "..."

        try:
            self.show_user_error_dialog(error_summary, full_error)
        except:
            print("Failed to show thread error dialog")

    def setup_global_exception_handler(self):
        sys.excepthook = self.handle_exception

        original_threading_excepthook = getattr(threading, "excepthook", None)
        if original_threading_excepthook:

            def thread_exception_handler(args):
                self.handle_thread_exception(
                    args.exc_type, args.exc_value, args.exc_traceback, args.thread
                )

            threading.excepthook = thread_exception_handler


if __name__ == "__main__":
    crash_handler = CrashErrorHandler()

    try:
        root = tk.Tk()
        app = MagicBabelApp(root)
        app.setup_ui_position_tracking()
        root.mainloop()
    except Exception as e:
        error_msg = crash_handler.log_error(
            type(e), e, e.__traceback__, "Main Application Startup"
        )
        crash_handler.show_user_error_dialog(
            f"Startup Error: {str(e)[:100]}...", error_msg
        )
