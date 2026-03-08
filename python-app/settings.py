import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import logging
from translator_factory import TranslatorFactory
from appearance import appearance_manager
from advance_ui import AdvanceUI
from simplified_hotkey_ui import SimplifiedHotkeyUI  # import จากไฟล์ใหม่
from font_manager import FontUI, initialize_font_manager
from version import __version__


def is_valid_hotkey(hotkey):
    hotkey = hotkey.lower()
    valid_keys = set("abcdefghijklmnopqrstuvwxyz0123456789")
    valid_functions = set(
        ["f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9", "f10", "f11", "f12"]
    )
    valid_modifiers = set(["ctrl", "alt", "shift"])

    parts = hotkey.split("+")

    # กรณีที่มีแค่ key เดียว
    if len(parts) == 1:
        return parts[0] in valid_keys or parts[0] in valid_functions

    # กรณีที่มี modifier และ key
    if len(parts) > 1:
        modifiers = parts[:-1]
        key = parts[-1]
        return all(mod in valid_modifiers for mod in modifiers) and (
            key in valid_keys or key in valid_functions
        )

    return False


# ==================================================================
# ลบคลาส HotkeyUI แบบเก่าออกไปทั้งหมด (HotkeyUI ถูกลบไปแล้ว)
# ==================================================================


class Settings:
    VALID_MODELS = {
        "gemini-2.5-flash": {
            "display_name": "gemini-2.5-flash",
            "type": "gemini",
        },
        "gemini-2.5-flash-lite": {
            "display_name": "gemini-2.5-flash-lite",
            "type": "gemini",
        },
        "gemini-2.5-pro": {
            "display_name": "gemini-2.5-pro",
            "type": "gemini",
        },
        "gemini-2.0-flash": {
            "display_name": "gemini-2.0-flash",
            "type": "gemini",
        },
    }

    DEFAULT_API_PARAMETERS = {
        # Main parameters for the model
        "model": "gemini-2.5-flash",
        "displayed_model": "gemini-2.5-flash",
        "max_tokens": 500,
        "temperature": 0.8,
        "top_p": 0.9,
        "role_mode": "rpg_general",
        # Language mode settings
        "language_mode": "en_to_th",  # Current: en→th, Future: "zh_tw_to_en_th"
        # Translation settings
        "translation_settings": {
            "source_languages": [
                "en"
            ],  # Currently English only, future: ["zh-tw", "en"]
            "target_language": "th",  # Primary target, future: ["en", "th"] for Chinese source
            "preserve_names": True,
            "modern_style": True,
            "flirty_tone": True,
            "use_emojis": True,
        },
        # Special characters handling
        "special_chars": {
            "english_range": ["a-zA-Z0-9"],  # Current support
            "chinese_traditional_range": [
                "\u4e00-\u9fff"
            ],  # Future: Traditional Chinese
            "thai_range": ["\u0e00-\u0e7f"],
            "allowed_symbols": ["...", "—", "!", "?", "💕", "✨", "🥺", "😏"],
        },
    }

    def __init__(self):
        # กำหนดค่า default ทั้งหมด รวมถึง field ใหม่
        self.default_settings = {
            "api_parameters": self.DEFAULT_API_PARAMETERS.copy(),
            "transparency": 0.8,
            "font_size": 24,
            "font": "Anuphan",  # ฟอนต์เริ่มต้น (bundled)
            "line_spacing": -50,  # ค่า default สำหรับ line spacing
            "text_transparency": 0.8,  # ค่า default สำหรับ text transparency
            "width": 960,
            "height": 240,
            "enable_previous_dialog": True,  # เปิดใช้งาน Previous Dialog ด้วย right-click
            "enable_wasd_auto_hide": True,
            "enable_tui_auto_show": True,  # เปิดใช้งาน TUI auto-show เมื่อพบข้อความ text hook
            "enable_ui_toggle": True,  # อาจไม่ใช้ แต่คงไว้
            "enable_auto_area_switch": False,  # ค่า default สำหรับ auto area switch (ปิดใช้งานถาวร)
            "enable_click_translate": False,  # เพิ่มการตั้งค่าใหม่สำหรับ Click Translate โดยค่าเริ่มต้นเป็น False
            "dalamud_enabled": False,  # เพิ่มการตั้งค่าสำหรับ Dalamud Bridge mode
            "auto_start_translation": False,  # เปิด/ปิด auto-start translation
            "auto_start_delay": 3,  # หน่วงเวลาก่อนเริ่ม auto-start (วินาที)
            "dalamud_auto_start": True,  # auto-start เฉพาะโหมด Dalamud เท่านั้น
            "enable_translation_warmup": True,  # เปิด/ปิด warmup injection เพื่อ pre-initialize Gemini API
            "warmup_delay": 0.8,  # หน่วงเวลาก่อน warmup injection (วินาที)
            "enable_battle_chat_mode": True,  # เปิด Battle Chat Mode สำหรับ ChatType 68
            "enable_conversation_logging": False,  # บันทึกบทสนทนา (dev/debug)
            "tui_positions": {  # จำตำแหน่ง TUI แยกตามโหมด (Dialog, Battle, Cutscene)
                "dialog": {"x": None, "y": None},
                "battle": {"x": None, "y": None},
                "cutscene": {"x": None, "y": None}
            },
            "tui_sizes": {  # จำขนาด TUI แยกตามโหมด
                "dialog": {"width": 960, "height": 240},
                "battle": {"width": None, "height": None},  # Auto-calculate
                "cutscene": {"width": None, "height": None}  # Auto-calculate
            },
            "tui_colors": {  # จำสีพื้นหลัง TUI แยกตามโหมด
                "dialog": appearance_manager.bg_color,
                "battle": appearance_manager.bg_color,
                "cutscene": appearance_manager.bg_color
            },
            "tui_alphas": {  # จำความโปร่งใส TUI แยกตามโหมด
                "dialog": 0.97,
                "battle": 0.97,
                "cutscene": 0.97
            },
            "bg_color": appearance_manager.bg_color,  # ดึงจาก appearance_manager (legacy)
            "bg_alpha": 0.97,  # ค่า transparency เริ่มต้น (97% เกือบทึบ)
            "bg_swatch_mode": 1,  # ค่า default swatch mode
            "bg_swatch_transparency": 0.97,  # ค่า default swatch transparency (97%)
            "translate_areas": {  # พิกัดเริ่มต้นเป็น 0
                "A": {"start_x": 0, "start_y": 0, "end_x": 0, "end_y": 0},
                "B": {"start_x": 0, "start_y": 0, "end_x": 0, "end_y": 0},
                "C": {"start_x": 0, "start_y": 0, "end_x": 0, "end_y": 0},
            },
            "current_area": "A+B",  # พื้นที่เริ่มต้น
            "current_preset": 1,  # preset เริ่มต้น
            "last_manual_preset_selection_time": 0,  # *** เพิ่ม field นี้ ***
            "display_scale": None,
            "screen_size": "2560x1440",  # ขนาดหน้าจออ้างอิงเริ่มต้น
            "shortcuts": {  # ค่า default shortcuts
                "toggle_ui": "alt+l",
                "start_stop_translate": "f9",
                "previous_dialog": "r-click",  # Previous Dialog shortcut
                "previous_dialog_key": "f10",  # Previous Dialog key
            },
            "logs_ui": {  # ค่า default logs UI
                "width": 480,
                "height": 320,
                "font_size": 16,
                "visible": True,
            },
            "buffer_settings": {  # ค่า default buffer settings
                "cache_timeout": 300,
                "max_cache_size": 100,
                "similarity_threshold": 0.85,
            },
            "logs_settings": {  # ค่า default logs settings
                "enable_dual_logs": True,
                "translation_only_logs": True,
                "logs_path": "logs",
                "clean_logs_after_days": 7,
            },
            "area_presets": [],  # เริ่มต้น list ว่าง ให้ ensure_default_values จัดการ
            "custom_themes": {},  # เริ่มต้น custom themes ว่าง
            "theme": "Theme4",  # ธีมเริ่มต้น
            "show_starter_guide": True,  # แสดง guide ตอนเปิดครั้งแรก
            "cpu_limit": 80,  # ค่า default CPU limit
            # CPU Monitoring Settings
            "enable_cpu_monitoring": True,  # เปิด/ปิด CPU monitoring
            "cpu_high_threshold": 70,  # เกินนี้ถือว่า CPU สูง (Gaming mode)
            "cpu_low_threshold": 30,  # ต่ำกว่านี้ถือว่า CPU ต่ำ (Idle mode)
            "cpu_high_interval": 0.5,  # วินาที - ช้าลงเมื่อ CPU สูง
            "cpu_medium_interval": 0.3,  # วินาที - ปกติ
            "cpu_low_interval": 0.15,  # วินาที - เร็วขึ้นเมื่อ CPU ต่ำ
        }
        self.settings = {}  # เริ่มต้น settings เป็น dict ว่าง
        self.load_settings()  # โหลดค่าจากไฟล์ (ถ้ามี)
        self.ensure_default_values()  # ตรวจสอบและเติมค่า default ที่ขาดไป

    def validate_model_parameters(self, params):
        """Validate the given parameters."""
        if not isinstance(params, dict):
            raise ValueError("Parameters must be a dictionary")

        # Check for valid model
        if "model" in params:
            if params["model"] not in self.VALID_MODELS:
                valid_models = list(self.VALID_MODELS.keys())
                raise ValueError(f"Invalid model. Must be one of: {valid_models}")

        # Validate numeric values
        if "max_tokens" in params:
            max_tokens = int(params["max_tokens"])
            if not (100 <= max_tokens <= 2000):
                raise ValueError("max_tokens must be between 100 and 2000")

        if "temperature" in params:
            temp = float(params["temperature"])
            if not (0.1 <= temp <= 1.0):
                raise ValueError("temperature must be between 0.1 and 1.0")

        return True

    def get_display_scale(self):
        """Return the stored display scale or None if not set."""
        return self.settings.get("display_scale")

    def set_display_scale(self, scale):
        """Save the display scale if valid."""
        try:
            scale = float(scale)
            if 0.5 <= scale <= 3.0:
                self.settings["display_scale"] = scale
                self.save_settings()
                print(f"Display scale saved: {int(scale * 100)}%")
                return True
            else:
                print(f"Invalid scale value: {scale}")
                return False
        except Exception as e:
            print(f"Error saving display scale: {e}")
            return False

    def validate_display_scale(self, scale):
        """Validate the display scale value."""
        try:
            scale = float(scale)
            if 0.5 <= scale <= 3.0:
                return {
                    "is_valid": True,
                    "message": "Valid scale value",
                    "value": scale,
                }
            return {
                "is_valid": False,
                "message": f"Scale must be between 50% and 300%, got {int(scale * 100)}%",
                "value": None,
            }
        except (ValueError, TypeError):
            return {
                "is_valid": False,
                "message": "Invalid scale value type",
                "value": None,
            }

    def set_bg_color(self, color):
        """Set and save the background color."""
        self.settings["bg_color"] = color
        self.save_settings()
        appearance_manager.update_bg_color(color)

    def get(self, key, default=None):
        if key == "bg_color":
            return self.settings.get("bg_color", appearance_manager.bg_color)
        return self.settings.get(key, default)

    def set(self, key, value, save_immediately=True):
        self.settings[key] = value
        if save_immediately:
            self.save_settings()

    def load_settings(self):
        try:
            with open("settings.json", "r", encoding="utf-8") as f:
                self.settings = json.load(f)
        except FileNotFoundError:
            self.settings = {
                "transparency": 0.8,
                "font_size": 24,
                "font": "Anuphan",
                "width": 960,
                "height": 240,
                    "enable_previous_dialog": True,  # เปิดใช้งาน Previous Dialog ด้วย right-click
                "enable_wasd_auto_hide": True,
                "enable_tui_auto_show": True,  # เปิดใช้งาน TUI auto-show เมื่อพบข้อความ text hook
                "enable_ui_toggle": True,
                "translate_areas": {
                    "A": {"start_x": 0, "start_y": 0, "end_x": 0, "end_y": 0},
                    "B": {"start_x": 0, "start_y": 0, "end_x": 0, "end_y": 0},
                    "C": {"start_x": 0, "start_y": 0, "end_x": 0, "end_y": 0},
                },
                "api_parameters": {
                    "model": "gemini-2.0-flash",
                    "max_tokens": 500,
                    "temperature": 0.7,
                    "top_p": 0.9,
                },
                "shortcuts": {"toggle_ui": "alt+h", "start_stop_translate": "f9"},
                "logs_ui": {
                    "width": 480,
                    "height": 320,
                    "font_size": 16,
                    "visible": True,
                },
            }

    def save_settings(self):
        """Save all current settings to file."""
        try:
            # จัดการ API parameters
            if "api_parameters" in self.settings:
                api_params = self.settings["api_parameters"]

                # <--- แก้ไขตรงนี้: ปรับการปัดเศษเป็น 2 ตำแหน่ง ---
                if "temperature" in api_params:
                    api_params["temperature"] = round(api_params["temperature"], 2)
                if "top_p" in api_params:
                    api_params["top_p"] = round(api_params["top_p"], 2)
                # ---------------------------------------------------

            # จัดการ current_area
            if "current_area" in self.settings:
                current_areas = self.settings["current_area"]
                if isinstance(current_areas, list):
                    self.settings["current_area"] = "+".join(current_areas)

            # ตรวจสอบและจัดการ area_presets
            if "area_presets" not in self.settings:
                self.settings["area_presets"] = [
                    {"name": "Preset 1", "areas": "A+B"},
                    {"name": "Preset 2", "areas": "C"},
                    {"name": "Preset 3", "areas": "A"},
                    {"name": "Preset 4", "areas": "B"},
                    {"name": "Preset 5", "areas": "A+B+C"},
                ]

            # บันทึกไฟล์
            with open("settings.json", "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)

        except Exception as e:
            logging.error(f"Error saving settings: {e}")
            raise

    def ensure_default_values(self):
        """Add default values if missing and ensure preset structure."""
        changes_made = False  # Flag ตรวจสอบว่ามีการเปลี่ยนแปลงค่าหรือไม่

        # วนลูปตรวจสอบทุก key ใน default_settings
        for key, default_value in self.default_settings.items():
            if key not in self.settings:
                # ถ้า key ไม่มีใน settings ที่โหลดมา ให้ใช้ค่า default
                self.settings[key] = default_value
                changes_made = True
                logging.info(f"Added missing setting '{key}' with default value.")

            # --- ตรวจสอบโครงสร้างภายในที่ซับซ้อน (เช่น dicts) ---
            elif key == "api_parameters":
                # ตรวจสอบว่า key ย่อยใน api_parameters มีครบหรือไม่
                if not isinstance(self.settings[key], dict):
                    self.settings[key] = self.default_settings[key].copy()
                    changes_made = True
                else:
                    for sub_key, sub_default in self.default_settings[key].items():
                        if sub_key not in self.settings[key]:
                            self.settings[key][sub_key] = sub_default
                            changes_made = True
                            logging.info(f"Added missing api_parameter '{sub_key}'.")
                        # อาจเพิ่มการตรวจสอบ type ของ sub_key ได้อีก
            elif key == "translate_areas":
                if not isinstance(self.settings[key], dict):
                    self.settings[key] = self.default_settings[key].copy()
                    changes_made = True
                else:
                    for area in ["A", "B", "C"]:
                        if area not in self.settings[key] or not isinstance(
                            self.settings[key].get(area), dict
                        ):
                            self.settings[key][area] = {
                                "start_x": 0,
                                "start_y": 0,
                                "end_x": 0,
                                "end_y": 0,
                            }
                            changes_made = True
                            logging.info(
                                f"Added/Reset missing translate_area '{area}'."
                            )
            elif key == "shortcuts":
                if not isinstance(self.settings[key], dict):
                    self.settings[key] = self.default_settings[key].copy()
                    changes_made = True
                else:
                    for action, default_hotkey in self.default_settings[key].items():
                        if action not in self.settings[key]:
                            self.settings[key][action] = default_hotkey
                            changes_made = True
                            logging.info(f"Added missing shortcut '{action}'.")
            elif key == "logs_ui":  # ตรวจสอบ key ย่อยของ logs_ui
                if not isinstance(self.settings[key], dict):
                    self.settings[key] = self.default_settings[key].copy()
                    changes_made = True
                else:
                    for sub_key, sub_default in self.default_settings[key].items():
                        if sub_key not in self.settings[key]:
                            self.settings[key][sub_key] = sub_default
                            changes_made = True
                            logging.info(f"Added missing logs_ui setting '{sub_key}'.")
            elif key == "tui_positions":  # ตรวจสอบ key ย่อยของ tui_positions
                if not isinstance(self.settings[key], dict):
                    self.settings[key] = self.default_settings[key].copy()
                    changes_made = True
                else:
                    for mode in ["dialog", "battle", "cutscene"]:
                        if mode not in self.settings[key] or not isinstance(
                            self.settings[key].get(mode), dict
                        ):
                            self.settings[key][mode] = {"x": None, "y": None}
                            changes_made = True
                            logging.info(f"Added missing tui_positions mode '{mode}'.")
            # --- จบการตรวจสอบโครงสร้างภายใน ---

        # --- ส่วนสำคัญ: ตรวจสอบและจัดการ area_presets (เหมือนเดิม แต่รวมอยู่ใน Loop ใหญ่) ---
        default_presets_structure = [
            {"name": "dialog", "role": "dialog", "areas": "A+B", "coordinates": {}},
            {"name": "lore", "role": "lore", "areas": "C", "coordinates": {}},
            {"name": "choice", "role": "choice", "areas": "A+B", "coordinates": {}},
            {"name": "Preset 4", "role": "custom", "areas": "B", "coordinates": {}},
            {"name": "Preset 5", "role": "custom", "areas": "A+B+C", "coordinates": {}},
        ]
        presets_changed_flag = False  # ใช้ flag แยกสำหรับ preset โดยเฉพาะ

        # ตรวจสอบ area_presets อีกครั้งหลัง ensure ค่า default ทั่วไปแล้ว
        if (
            not isinstance(self.settings.get("area_presets"), list)
            or len(self.settings["area_presets"]) != 5
        ):
            logging.warning(
                "Area presets missing or invalid length. Recreating defaults."
            )
            self.settings["area_presets"] = default_presets_structure
            presets_changed_flag = True
            if "current_preset" not in self.settings or not (
                1 <= self.settings["current_preset"] <= 5
            ):
                self.settings["current_preset"] = 1  # ตั้งเป็น 1 เมื่อสร้างใหม่
        else:
            # ตรวจสอบโครงสร้างแต่ละ preset
            for i, preset in enumerate(self.settings["area_presets"]):
                preset_num = i + 1
                default_struct = default_presets_structure[i]
                changed_this_preset = False

                # ตรวจสอบ type ของ preset เอง
                if not isinstance(preset, dict):
                    self.settings["area_presets"][
                        i
                    ] = default_struct  # แทนที่ด้วย default ถ้า type ผิด
                    presets_changed_flag = True
                    continue  # ไป preset ถัดไป

                # ตรวจ/เพิ่ม 'role'
                if preset.get("role") not in [
                    "dialog",
                    "lore",
                    "choice",
                    "custom",
                ]:  # ตรวจสอบค่า role ที่ถูกต้อง
                    preset["role"] = default_struct["role"]
                    changed_this_preset = True
                # ตรวจ/เพิ่ม 'name'
                if (
                    "name" not in preset
                    or not isinstance(preset.get("name"), str)
                    or not preset["name"]
                ):
                    preset["name"] = default_struct["name"]
                    changed_this_preset = True
                # บังคับ Preset 1, 2, 3
                if preset_num == 1 and (
                    preset.get("role") != "dialog"
                    or preset.get("name") != "dialog"
                    or preset.get("areas") != "A+B"
                ):
                    preset["role"] = "dialog"
                    preset["name"] = "dialog"
                    preset["areas"] = "A+B"
                    changed_this_preset = True
                elif preset_num == 2 and (
                    preset.get("role") != "lore"
                    or preset.get("name") != "lore"
                    or preset.get("areas") != "C"
                ):
                    preset["role"] = "lore"
                    preset["name"] = "lore"
                    preset["areas"] = "C"
                    changed_this_preset = True
                elif preset_num == 3 and (
                    preset.get("role") != "choice"
                    or preset.get("name") != "choice"
                    or preset.get("areas") != "B"
                ):
                    preset["role"] = "choice"
                    preset["name"] = "choice"
                    preset["areas"] = "B"
                    changed_this_preset = True
                # ตรวจ/เพิ่ม coordinates
                if "coordinates" not in preset or not isinstance(
                    preset.get("coordinates"), dict
                ):
                    preset["coordinates"] = {}
                    changed_this_preset = True

                if changed_this_preset:
                    presets_changed_flag = True
                    logging.info(f"Preset {preset_num} structure updated/corrected.")

        # ตรวจ current_preset อีกครั้ง หลัง area_presets ถูกจัดการแล้ว
        if not (
            1
            <= self.settings.get("current_preset", 1)
            <= len(self.settings["area_presets"])
        ):
            logging.warning(
                f"Invalid current_preset found ({self.settings.get('current_preset')}). Resetting to 1."
            )
            self.settings["current_preset"] = 1
            presets_changed_flag = True

        # --- จบส่วน area_presets ---

        # บันทึกค่าลงไฟล์ ถ้ามีการเปลี่ยนแปลง หรือถ้าไฟล์ไม่มีอยู่
        if changes_made or presets_changed_flag or not os.path.exists("settings.json"):
            logging.info(
                "Saving settings due to missing values or preset structure changes."
            )
            self.save_settings()

    def get_preset(self, preset_number):
        """รับค่า preset ตามหมายเลข"""
        presets = self.settings.get("area_presets", [])
        if 1 <= preset_number <= len(presets):
            return presets[preset_number - 1]
        return None

    def get_preset_role(self, preset_number):
        """รับค่า role ของ preset ตามหมายเลข"""
        preset_data = self.get_preset(preset_number)
        if preset_data:
            # ใช้ค่า role จาก preset_data หรือ fallback เป็น 'custom' ถ้าไม่มี
            return preset_data.get("role", "custom")
        # ถ้าหา preset ไม่เจอ ให้ถือว่าเป็น custom (หรืออาจจะคืน None แล้วให้ที่เรียกไปจัดการ)
        logging.warning(
            f"Preset {preset_number} not found when getting role, assuming 'custom'."
        )
        return "custom"

    def get_preset_display_name(self, preset_number):
        """รับค่า name (ชื่อที่แสดง) ของ preset ตามหมายเลข

        ให้แสดงชื่อประเภทให้ชัดเจน:
        - preset 1 = "dialog"
        - preset 2 = "lore"
        - preset 3 = "choice"
        - preset 4 = "Preset 4" (หรือชื่อที่ผู้ใช้กำหนดเอง)
        - preset 5 = "Preset 5" (หรือชื่อที่ผู้ใช้กำหนดเอง)
        """
        # กำหนดชื่อคงที่สำหรับ preset 1-3
        if preset_number == 1:
            return "dialog"
        elif preset_number == 2:
            return "lore"
        elif preset_number == 3:
            return "choice"
        elif preset_number in [4, 5]:
            # สำหรับ preset 4-5 ให้ตรวจสอบว่ามีชื่อ custom หรือไม่
            preset_data = self.get_preset(preset_number)
            if (
                preset_data
                and "custom_name" in preset_data
                and preset_data["custom_name"]
            ):
                return preset_data["custom_name"]
            # ถ้าไม่มีชื่อ custom ให้ใช้ชื่อเริ่มต้น
            return f"Preset {preset_number}"
        else:
            # สำหรับหมายเลขอื่นๆ ที่อาจจะมีเพิ่มในอนาคต
            logging.warning(
                f"Preset {preset_number} number outside of standard range (1-5), using default name."
            )
            return f"Preset {preset_number}"

    def set_preset_custom_name(self, preset_number, custom_name):
        """ตั้งค่าชื่อ custom ให้กับ preset

        Args:
            preset_number: หมายเลข preset (ควรเป็น 4 หรือ 5)
            custom_name: ชื่อ custom ที่ต้องการตั้ง

        Returns:
            bool: True ถ้าสำเร็จ, False ถ้าไม่สำเร็จ
        """
        # ตรวจสอบว่า preset_number ถูกต้องหรือไม่
        if not (1 <= preset_number <= 5):
            logging.error(f"Invalid preset number for custom name: {preset_number}")
            return False

        # ไม่อนุญาตให้เปลี่ยนชื่อ preset 1-3
        if preset_number <= 3:
            logging.warning(f"Cannot set custom name for system preset {preset_number}")
            return False

        try:
            # ดึงข้อมูล preset ปัจจุบัน
            presets = self.settings.get("area_presets", [])
            if not presets or len(presets) < preset_number:
                logging.error(
                    f"Preset {preset_number} not found for setting custom name"
                )
                return False

            # อัพเดตชื่อ custom
            preset_index = preset_number - 1
            presets[preset_index]["custom_name"] = custom_name

            # บันทึกลงไฟล์
            self.settings["area_presets"] = presets
            self.save_settings()

            logging.info(f"Set custom name '{custom_name}' for preset {preset_number}")
            return True

        except Exception as e:
            logging.error(f"Error setting custom name for preset {preset_number}: {e}")
            import traceback

            traceback.print_exc()
            return False

    def get_all_presets(self):
        """รับค่า presets ทั้งหมด"""
        presets = self.settings.get("area_presets", [])
        if not presets:
            # ถ้าไม่มี preset ให้สร้าง preset เริ่มต้น
            presets = [
                {"name": "Preset 1", "areas": "A+B"},  # Default preset 1
                {"name": "Preset 2", "areas": "C"},  # Default preset 2
                {"name": "Preset 3", "areas": "A"},  # Default preset 3
                {"name": "Preset 4", "areas": "B"},  # Default preset 4
                {"name": "Preset 5", "areas": "A+B+C"},  # Default preset 5
            ]
            self.settings.set("area_presets", presets)
            self.settings.save_settings()
        return presets

    def validate_coordinates(self, coordinates):
        """ตรวจสอบความถูกต้องของพิกัดสำหรับแต่ละพื้นที่
        Args:
            coordinates (dict): Dictionary ของพิกัดแต่ละพื้นที่
                เช่น: {
                    'A': {'start_x': 100, 'start_y': 100, 'end_x': 200, 'end_y': 200},
                    'B': {'start_x': 300, 'start_y': 300, 'end_x': 400, 'end_y': 400}
                }
        Returns:
            bool: True ถ้าพิกัดถูกต้อง, False ถ้าไม่ถูกต้อง
        """
        required_keys = {"start_x", "start_y", "end_x", "end_y"}

        try:
            for area, coords in coordinates.items():
                # ตรวจสอบว่ามี key ครบทุกตัว
                if not all(key in coords for key in required_keys):
                    logging.error(f"Missing required coordinate keys for area {area}")
                    return False

                # ตรวจสอบว่าค่าพิกัดเป็นตัวเลขทั้งหมด
                if not all(
                    isinstance(coords[key], (int, float)) for key in required_keys
                ):
                    logging.error(f"Invalid coordinate values for area {area}")
                    return False

                # ตรวจสอบว่าค่าพิกัดมีความสมเหตุสมผล
                if (
                    coords["end_x"] <= coords["start_x"]
                    or coords["end_y"] <= coords["start_y"]
                ):
                    logging.error(f"Invalid coordinate ranges for area {area}")
                    return False

                # ตรวจสอบว่าค่าพิกัดไม่ติดลบ
                if any(coords[key] < 0 for key in required_keys):
                    logging.error(f"Negative coordinates found for area {area}")
                    return False

            return True

        except Exception as e:
            logging.error(f"Error validating coordinates: {e}")
            return False

    def save_preset(self, preset_number, areas, coordinates):
        """บันทึก preset พร้อมพิกัด และรักษา role/name ที่ถูกต้อง
        Args:
            preset_number: หมายเลข preset (1-5)
            areas: สตริงของพื้นที่ เช่น "A+B"
            coordinates: dict ของพิกัดแต่ละพื้นที่
        """
        try:
            # ตรวจสอบความถูกต้องของพิกัด
            if not self.validate_coordinates(coordinates):
                raise ValueError("Invalid coordinates provided")

            # ตรวจสอบหมายเลข Preset
            if not (1 <= preset_number <= 5):
                raise ValueError(f"Invalid preset number: {preset_number}")

            # ดึงข้อมูล presets ทั้งหมด (ควรจะอัพเดทล่าสุดแล้วจาก ensure_default_values)
            presets = self.settings.get("area_presets", [])

            # --- ส่วนสำคัญ: ดึง Role และ Name ที่ถูกต้องสำหรับ Preset นี้ ---
            default_presets_structure = [  # โครงสร้างอ้างอิง
                {"name": "dialog", "role": "dialog", "areas": "A+B"},
                {"name": "lore", "role": "lore", "areas": "C"},
                {"name": "choice", "role": "choice", "areas": "A+B"},
                {"name": "Preset 4", "role": "custom", "areas": "B"},
                {"name": "Preset 5", "role": "custom", "areas": "A+B+C"},
            ]
            preset_index = preset_number - 1

            # ค่า role และ name เริ่มต้น (อาจถูกแก้ไขต่อไป)
            correct_name = default_presets_structure[preset_index]["name"]
            correct_role = default_presets_structure[preset_index]["role"]

            # เก็บค่า custom_name ไว้ถ้ามี (สำหรับ preset 4-5)
            custom_name = None
            if 0 <= preset_index < len(presets) and preset_number >= 4:
                if "custom_name" in presets[preset_index]:
                    custom_name = presets[preset_index]["custom_name"]

            # สำหรับ Preset 1, 2, 3 จะใช้ Area ที่กำหนดตายตัวเสมอ
            if correct_role in ["dialog", "lore", "choice"]:
                correct_areas = default_presets_structure[preset_index]["areas"]
                if areas != correct_areas:
                    logging.warning(
                        f"Preset {preset_number} ({correct_role}) area is fixed to '{correct_areas}'. Ignoring requested areas '{areas}'."
                    )
                    areas = correct_areas  # บังคับใช้ Area ที่ถูกต้องสำหรับ Role นี้
            # --- จบส่วนดึง Role/Name/Area ที่ถูกต้อง ---

            # สร้างข้อมูล preset ใหม่ (ใช้ correct_name และ correct_role)
            preset_data = {
                "name": correct_name,
                "role": correct_role,
                "areas": areas,  # ใช้ area ที่อาจถูกบังคับแก้ไข
                "coordinates": coordinates,  # ใช้ coordinates ที่ผู้ใช้กำหนด
            }

            # เพิ่ม custom_name กลับเข้าไปถ้ามี (สำหรับ preset 4-5)
            if custom_name and preset_number >= 4:
                preset_data["custom_name"] = custom_name

            # อัพเดต preset ในตำแหน่งที่กำหนด (เหมือนเดิม)
            if 0 <= preset_index < len(presets):
                presets[preset_index] = preset_data
            else:
                # กรณีนี้ไม่ควรเกิดถ้า ensure_default_values ทำงานถูกต้อง แต่ใส่เผื่อไว้
                logging.error(
                    f"Preset index {preset_index} out of bounds. Cannot save preset."
                )
                return False

            # บันทึกลงไฟล์
            self.settings["area_presets"] = presets
            self.save_settings()

            # ใช้ชื่อที่แสดงจริงในการ log (อาจเป็น custom_name)
            display_name = self.get_preset_display_name(preset_number)
            logging.info(
                f"Saved preset {preset_number} ('{display_name}', role: '{correct_role}') with areas: {areas}"
            )
            return True
        except Exception as e:
            logging.error(f"Error saving preset: {e}")
            import traceback

            traceback.print_exc()
            return False

    def get_all_presets(self):
        """รับค่า presets ทั้งหมด"""
        return self.settings.get("area_presets", [])

    def validate_preset(self, preset_number, preset_data):
        """ตรวจสอบความถูกต้องของข้อมูล preset
        Args:
            preset_number: หมายเลข preset (1-5)
            preset_data: ข้อมูล preset ที่จะบันทึก
        Returns:
            bool: True ถ้าข้อมูลถูกต้อง
        """
        try:
            if not 1 <= preset_number <= 5:
                return False

            if not isinstance(preset_data, dict):
                return False

            required_keys = {"name", "areas", "coordinates"}
            if not all(key in preset_data for key in required_keys):
                return False

            # ตรวจสอบพื้นที่
            areas = preset_data["areas"].split("+")
            if not all(area in ["A", "B", "C"] for area in areas):
                return False

            # ตรวจสอบพิกัด
            if not self.validate_coordinates(preset_data["coordinates"]):
                return False

            return True

        except Exception as e:
            logging.error(f"Error validating preset: {e}")
            return False

    def set_current_preset(self, preset_number):
        """ตั้งค่า preset ปัจจุบัน
        Args:
            preset_number: int ระหว่าง 1-5
        """
        if not 1 <= preset_number <= 5:
            raise ValueError("Invalid preset number")
        self.settings["current_preset"] = preset_number
        self.save_settings()

    def get_current_preset(self):
        """รับค่า preset ปัจจุบัน
        Returns:
            int: หมายเลข preset ปัจจุบัน (1-5)
        """
        return self.settings.get("current_preset", 1)

    def get_logs_settings(self):
        """Return the settings for the logs UI."""
        return self.settings.get(
            "logs_ui", {"width": 480, "height": 320, "font_size": 16, "font_family": "Anuphan", "visible": True}
        )

    def set_logs_settings(
        self, width=None, height=None, font_size=None, font_family=None, visible=None, x=None, y=None,
        transparency_mode=None, logs_reverse_mode=None
    ):
        """Update the logs UI settings."""
        if "logs_ui" not in self.settings:
            self.settings["logs_ui"] = {}

        if width is not None:
            self.settings["logs_ui"]["width"] = width
        if height is not None:
            self.settings["logs_ui"]["height"] = height
        if font_size is not None:
            self.settings["logs_ui"]["font_size"] = font_size
        if font_family is not None:
            self.settings["logs_ui"]["font_family"] = font_family
        if visible is not None:
            self.settings["logs_ui"]["visible"] = visible
        if x is not None:
            self.settings["logs_ui"]["x"] = x
        if y is not None:
            self.settings["logs_ui"]["y"] = y
        if transparency_mode is not None:
            self.settings["logs_ui"]["transparency_mode"] = transparency_mode
        if logs_reverse_mode is not None:
            self.settings["logs_reverse_mode"] = logs_reverse_mode

        self.save_settings()

    def clear_logs_position_cache(self):
        """Clear the cached logs position data."""
        if "logs_ui" in self.settings:
            # Clear position-related cache
            self.settings["logs_ui"].pop("x", None)
            self.settings["logs_ui"].pop("y", None)
            self.save_settings()

    def get_shortcut(self, action, default=None):
        return self.settings.get("shortcuts", {}).get(action, default)

    def set_shortcut(self, action, shortcut):
        if "shortcuts" not in self.settings:
            self.settings["shortcuts"] = {}
        self.settings["shortcuts"][action] = shortcut
        self.save_settings()

    def set_screen_size(self, size):
        self.settings["screen_size"] = size
        self.save_settings()

    def set_current_area(self, area):
        self.settings["current_area"] = area
        self.save_settings()

    def get_current_area(self):
        return self.settings.get("current_area", "A")

    def set_translate_area(self, start_x, start_y, end_x, end_y, area):
        """Save the translation area without brush points."""
        self.settings["translate_areas"] = self.settings.get("translate_areas", {})
        self.settings["translate_areas"][area] = {
            "start_x": start_x,
            "start_y": start_y,
            "end_x": end_x,
            "end_y": end_y,
        }
        self.save_settings()

    def get_translate_area(self, area):
        """Return the translation area data."""
        translate_areas = self.settings.get("translate_areas", {})
        return translate_areas.get(area, None)

    def set_api_parameters(
        self,
        model=None,
        max_tokens=None,
        temperature=None,
        top_p=None,
        role_mode=None,
        language_mode=None,
    ):
        try:
            if "api_parameters" not in self.settings:
                self.settings["api_parameters"] = {}

            api_params = self.settings["api_parameters"]
            changes = []

            if model is not None:
                if model not in self.VALID_MODELS:
                    raise ValueError(f"Invalid model: {model}")
                old_model = api_params.get("model")
                model_info = self.VALID_MODELS[model]
                api_params.update(
                    {"model": model, "displayed_model": model_info["display_name"]}
                )
                changes.append(f"Model: {old_model} -> {model}")

            if max_tokens is not None:
                if not (100 <= max_tokens <= 2000):
                    raise ValueError("Max tokens must be between 100 and 2000")
                old_tokens = api_params.get("max_tokens")
                api_params["max_tokens"] = max_tokens
                changes.append(f"Max tokens: {old_tokens} -> {max_tokens}")

            if temperature is not None:
                if not (0.0 <= temperature <= 1.0):
                    raise ValueError("Temperature must be between 0.0 and 1.0")
                old_temp = api_params.get("temperature")
                api_params["temperature"] = round(temperature, 2)
                changes.append(f"Temperature: {old_temp} -> {temperature}")

            # Gemini supports top_p parameter
            if top_p is not None:
                if not (0.0 <= top_p <= 1.0):
                    raise ValueError("Top P must be between 0.0 and 1.0")
                old_top_p = api_params.get("top_p")
                api_params["top_p"] = round(top_p, 2)
                changes.append(f"Top P: {old_top_p} -> {top_p}")

            if role_mode is not None:
                valid_roles = ["rpg_general", "adult_enhanced"]
                if role_mode not in valid_roles:
                    raise ValueError(f"Role mode must be one of: {valid_roles}")
                old_role = api_params.get("role_mode")
                api_params["role_mode"] = role_mode
                changes.append(f"Role mode: {old_role} -> {role_mode}")

            if language_mode is not None:
                valid_language_modes = ["en_to_th", "zh_tw_to_en_th"]
                if language_mode not in valid_language_modes:
                    raise ValueError(
                        f"Language mode must be one of: {valid_language_modes}"
                    )
                old_lang_mode = api_params.get("language_mode")
                api_params["language_mode"] = language_mode
                changes.append(f"Language mode: {old_lang_mode} -> {language_mode}")

            self.save_settings()

            if changes:
                logging.info("\n=== API Parameters Updated ===")
                for change in changes:
                    logging.info(change)
                logging.info(f"Current Settings: {api_params}")
                logging.info("============================\n")

            return True, None
        except Exception as e:
            logging.error(f"Error setting API parameters: {str(e)}")
            return False, str(e)

    def get_displayed_model(self):
        """Return the model name for UI display."""
        api_params = self.get_api_parameters()
        return api_params.get(
            "displayed_model", api_params.get("model", "gemini-2.0-flash")
        )

    def get_api_parameters(self):
        """Return the current API parameters."""
        default_params = {
            "model": "gemini-2.0-flash",
            "displayed_model": "gemini-2.0-flash",
            "max_tokens": 500,
            "temperature": 0.7,
            "top_p": 0.9,
            "role_mode": "rpg_general",
        }
        params = self.settings.get("api_parameters", default_params).copy()

        # ตรวจสอบและลบ proxies ถ้ามี
        if "proxies" in params:
            del params["proxies"]

        # ปรับค่า displayed_model
        if params.get("model") == "gemini-2.0-flash":
            params["displayed_model"] = "gemini-2.0-flash"

        if "temperature" in params:
            params["temperature"] = round(params["temperature"], 2)
        if "top_p" in params:
            params["top_p"] = round(params["top_p"], 2)

        return params

    def get_all_settings(self):
        """รับการตั้งค่าทั้งหมดในรูปแบบ dictionary

        Returns:
            dict: การตั้งค่าทั้งหมดที่มีอยู่ในระบบ
        """
        return self.settings


class SettingsUI:
    def __init__(
        self,
        parent,
        settings,
        apply_settings_callback,
        update_hotkeys_callback,
        main_app=None,
    ):
        self.parent = parent
        self.settings = settings
        self.apply_settings_callback = apply_settings_callback
        self.update_hotkeys_callback = update_hotkeys_callback
        self.main_app = main_app  # เก็บ reference ของ MagicBabelApp
        self.settings_window = None
        self.settings_visible = False
        self.on_close_callback = None
        self.create_settings_window()
        self.advance_ui = None
        self.hotkey_ui = None
        self.font_ui = None  # เพิ่มบรรทัดนี้เพื่อเก็บอ้างอิงถึง FontUI
        self.font_manager = None  # เพิ่มบรรทัดนี้เพื่อเก็บอ้างอิงถึง FontManager

    tk.Canvas.create_rounded_rect = lambda self, x1, y1, x2, y2, radius=25, **kwargs: (
        self.create_arc(
            x1, y1, x1 + 2 * radius, y1 + 2 * radius, start=90, extent=90, **kwargs
        )
        + self.create_arc(
            x2 - 2 * radius, y1, x2, y1 + 2 * radius, start=0, extent=90, **kwargs
        )
        + self.create_arc(
            x2 - 2 * radius, y2 - 2 * radius, x2, y2, start=270, extent=90, **kwargs
        )
        + self.create_arc(
            x1, y2 - 2 * radius, x1 + 2 * radius, y2, start=180, extent=90, **kwargs
        )
        + self.create_rectangle(x1 + radius, y1, x2 - radius, y2, **kwargs)
        + self.create_rectangle(x1, y1 + radius, x2, y2 - radius, **kwargs)
    )

    def create_settings_section(self, parent, title, padx=10, pady=5):
        """สร้าง Frame สำหรับกลุ่มการตั้งค่าพร้อมหัวข้อ

        Args:
            parent: parent container
            title: ชื่อหัวข้อของ section
            padx: padding แนวนอน
            pady: padding แนวตั้ง

        Returns:
            tk.Frame: frame ที่สร้างขึ้นสำหรับใส่ widget
        """
        section_frame = tk.LabelFrame(
            parent,
            text=title,
            bg=appearance_manager.bg_color,
            fg="white",
            font=("IBM Plex Sans Thai Medium", 10, "bold"),
            bd=1,
            relief=tk.GROOVE,
            padx=padx,
            pady=pady,
        )
        section_frame.pack(fill=tk.X, padx=10, pady=5)
        return section_frame

    def create_settings_window(self):
        self.settings_window = tk.Toplevel(self.parent)
        self.settings_window.overrideredirect(True)
        appearance_manager.apply_style(self.settings_window)
        self.create_settings_ui()
        self.settings_window.withdraw()

        # เพิ่ม protocol handler
        self.settings_window.protocol("WM_DELETE_WINDOW", self.close_settings)

    def open_settings(self, parent_x, parent_y, parent_width):
        """Open settings window at specified position relative to parent"""
        x = parent_x + parent_width + 10
        y = parent_y
        self.settings_window.geometry(f"+{x}+{y}")

        # โหลดการตั้งค่าปัจจุบัน (เอาส่วน transparency ออก)

        # ลบส่วน font และ size ออกแล้ว (ทำได้โดยตรงบน TUI)

        # ตั้งค่า variables สำหรับ toggle switches (เฉพาะที่ยังคงมี UI)
        self.auto_hide_var.set(self.settings.get("enable_wasd_auto_hide", False))
        self.cpu_monitoring_var.set(self.settings.get("enable_cpu_monitoring", True))
        self.tui_auto_show_var.set(self.settings.get("enable_tui_auto_show", True))
        self.battle_chat_mode_var.set(self.settings.get("enable_battle_chat_mode", True))  # ⚔️ Battle Chat Mode

        # Track initial values for change detection
        self.initial_values = {
            "auto_hide": self.auto_hide_var.get(),
            "cpu_monitoring": self.cpu_monitoring_var.get(),
            "tui_auto_show": self.tui_auto_show_var.get(),
            "battle_chat_mode": self.battle_chat_mode_var.get(),  # ⚔️ Battle Chat Mode
        }
        self.has_changes = False

        # อัพเดตสถานะของ toggle switches
        self.indicators = getattr(self, "indicators", {})
        for indicator_id, data in self.indicators.items():
            variable = data["variable"]
            self.update_switch_ui(indicator_id, variable.get())

        # อัพเดตชอร์ตคัท
        toggle_ui_shortcut = self.settings.get_shortcut("toggle_ui", "alt+h")
        start_stop_shortcut = self.settings.get_shortcut("start_stop_translate", "f9")
        self.toggle_ui_btn.config(text=toggle_ui_shortcut.upper())
        self.start_stop_btn.config(text=start_stop_shortcut.upper())

        # แสดงหน้าต่าง
        self.settings_window.deiconify()
        self.settings_window.lift()
        self.settings_window.attributes("-topmost", True)
        self.settings_visible = True

        # รีเซ็ตข้อความบนปุ่ม
        if hasattr(self, "hotkey_button"):
            self.hotkey_button.config(text="HOTKEY")
        if hasattr(self, "font_button"):
            self.font_button.config(text="FONT")

    def create_tooltip(self, widget, text):
        """สร้าง tooltip สำหรับ widget"""

        def enter(event):
            # สร้าง tooltip
            x, y, _, _ = widget.bbox("insert")
            x += widget.winfo_rootx() + 25
            y += widget.winfo_rooty() + 25

            # สร้าง top level
            self.tooltip = tk.Toplevel(widget)
            self.tooltip.overrideredirect(True)
            self.tooltip.geometry(f"+{x}+{y}")

            # สร้าง label
            label = tk.Label(
                self.tooltip,
                text=text,
                bg="#333333",
                fg="white",
                relief=tk.SOLID,
                borderwidth=1,
                font=("IBM Plex Sans Thai Medium", 8),
                padx=5,
                pady=2,
            )
            label.pack()

        def leave(event):
            # ลบ tooltip
            if hasattr(self, "tooltip"):
                self.tooltip.destroy()

        # ผูก event
        widget.bind("<Enter>", enter)
        widget.bind("<Leave>", leave)

    def open(self):
        """Toggle the advance window visibility"""
        if self.advance_window is None or not self.advance_window.winfo_exists():
            self.create_advance_window()

        if self.advance_window.winfo_viewable():
            self.close()  # ถ้ากำลังแสดงอยู่ให้ซ่อน
            if hasattr(self.parent, "advance_button"):
                self.parent.advance_button.config(text="Screen/API")
        else:
            # คำนวณตำแหน่งให้อยู่ทางขวาของ settings ui โดยเว้นระยะ 5px
            parent_x = self.parent.winfo_x()
            parent_y = self.parent.winfo_y()
            parent_width = self.parent.winfo_width()

            # กำหนดตำแหน่งใหม่
            x = parent_x + parent_width + 5  # เว้นระยะห่าง 5px
            y = parent_y  # ให้อยู่ระดับเดียวกับ settings ui

            self.advance_window.geometry(f"+{x}+{y}")
            self.advance_window.deiconify()
            self.advance_window.lift()  # ยกให้อยู่บนสุด
            self.advance_window.attributes("-topmost", True)

            self.load_current_settings()
            self.is_changed = False
            self.update_save_button()

            if hasattr(self.parent, "advance_button"):
                self.parent.advance_button.config(text="Close Advanced")

    def close_settings(self):
        self.settings_window.withdraw()
        self.settings_visible = False
        if self.advance_ui:
            self.advance_ui.close()
        if self.hotkey_ui:
            self.hotkey_ui.close()
        # ไม่ปิด font manager เมื่อปิด settings window
        # ปล่อยให้ font manager ทำงานต่อไปได้

        self.hotkey_button.config(text="HotKey")  # รีเซ็ตข้อความบนปุ่ม
        self.font_button.config(text="FONT")  # รีเซ็ตข้อความบนปุ่มฟอนต์

        # เรียก callback ถ้ามี
        if hasattr(self, "on_close_callback") and self.on_close_callback:
            self.on_close_callback()

    def validate_window_size(self, event=None):
        """DISABLED: Width/Height validation (ทำได้โดยตรงบน TUI)"""
        # ฟังก์ชันนี้ถูกปิดใช้งานแล้วเพราะลบ width/height UI controls ออกแล้ว
        return True

    def create_settings_ui(self):
        """Initialize and setup all UI components"""
        # ส่วนหัวของหน้าต่าง
        header_frame = tk.Frame(self.settings_window, bg=appearance_manager.bg_color)
        header_frame.pack(fill=tk.X)
        # ปุ่มปิด (X)
        close_button = appearance_manager.create_styled_button(
            header_frame, "X", self.close_settings
        )
        close_button.place(x=5, y=5, width=20, height=20)
        # ชื่อหน้าต่าง
        tk.Label(
            header_frame,
            text="SETTINGS",
            bg=appearance_manager.bg_color,
            fg="white",
            font=("Nasalization Rg", 14, "bold"),
        ).pack(pady=(5, 0))

        # เพิ่มคำอธิบายการตั้งค่า
        tk.Label(
            header_frame,
            text="การตั้งค่าการทำงาน",
            bg=appearance_manager.bg_color,
            fg="#AAAAAA",
            font=("IBM Plex Sans Thai Medium", 8),
        ).pack(pady=(0, 5))

        # สร้าง main frame สำหรับใส่ content
        main_frame = tk.Frame(self.settings_window, bg=appearance_manager.bg_color)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10)

        # ====== SECTION 1: FEATURES TOGGLES ======
        features_section = self.create_settings_section(
            main_frame, "การตั้งค่าฟังก์ชันการทำงาน"
        )

        # Toggle Variables (เฉพาะที่ต้องการ)
        self.auto_hide_var = tk.BooleanVar()
        self.cpu_monitoring_var = tk.BooleanVar()  # CPU Monitoring toggle
        self.tui_auto_show_var = tk.BooleanVar()  # Auto Show TUI toggle
        self.battle_chat_mode_var = tk.BooleanVar()  # ⚔️ Battle Chat Mode toggle

        # Toggle Switches (เฉพาะ features ที่เก็บไว้)
        self.create_toggle_switch(
            features_section, "Auto-hide UI when WASD pressed (UI only)", self.auto_hide_var
        )
        self.create_toggle_switch(
            features_section,
            "Smart Performance (CPU Monitoring)",
            self.cpu_monitoring_var
        )
        # TUI Auto Show - always enabled with dark green indicator
        self.create_toggle_switch(
            features_section,
            "Auto Show TUI (แสดง TUI อัตโนมัติเมื่อพบข้อความ)",
            self.tui_auto_show_var,
        )

        # ====== SECTION 3: ADVANCED SETTINGS ======
        advanced_section = self.create_settings_section(main_frame, "การตั้งค่าขั้นสูง")

        # สร้าง 3 ปุ่มตามโค้ดเดิม แต่จัดวางใหม่ เพิ่มเป็น 4 ปุ่ม
        button_style = {
            "font": ("Nasalization Rg", 9),
            "width": 10,
            "padx": 5,
            "pady": 2,
            "bd": 1,
            "relief": tk.RAISED,
        }

        button_frame = tk.Frame(advanced_section, bg=appearance_manager.bg_color)
        button_frame.pack(fill=tk.X, pady=5)

        # ปุ่ม Font Manager (เพิ่มใหม่)
        self.font_button = tk.Button(
            button_frame,
            text="FONT",
            command=self.toggle_font_ui,
            bg="#404040",
            fg="white",
            **button_style,
        )
        self.font_button.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)


        self.model_button = tk.Button(
            button_frame,
            text="MODEL",
            command=self.toggle_model_settings,
            bg="#404040",
            fg="white",
            **button_style,
        )
        self.model_button.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)

        self.hotkey_button = tk.Button(
            button_frame,
            text="HOTKEY",
            command=self.toggle_hotkey_ui,
            bg="#404040",
            fg="white",
            **button_style,
        )
        self.hotkey_button.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)

        # เพิ่ม hover effect
        for button in [
            self.font_button,
            self.model_button,
            self.hotkey_button,
        ]:
            button.bind("<Enter>", lambda e, b=button: b.config(bg="#606060"))
            button.bind("<Leave>", lambda e, b=button: b.config(bg="#404040"))

        # ====== TEST HOOK SECTION ======
        test_section = self.create_settings_section(main_frame, "Test Hook")

        test_button_frame = tk.Frame(test_section, bg=appearance_manager.bg_color)
        test_button_frame.pack(fill=tk.X, pady=5)

        # Test Dialog (ChatType 61)
        self.test_dialog_frame = self.create_test_button_with_subtitle(
            test_button_frame, "Dialog", "ChatType 61", self.inject_test_dialog
        )
        self.test_dialog_frame.pack(side=tk.LEFT, padx=5, expand=True)

        # Test Battle (ChatType 68)
        self.test_battle_frame = self.create_test_button_with_subtitle(
            test_button_frame, "Battle", "ChatType 68", self.inject_test_battle
        )
        self.test_battle_frame.pack(side=tk.LEFT, padx=5, expand=True)

        # Test Cutscene (ChatType 71)
        self.test_cutscene_frame = self.create_test_button_with_subtitle(
            test_button_frame, "Cutscene", "ChatType 71", self.inject_test_cutscene
        )
        self.test_cutscene_frame.pack(side=tk.LEFT, padx=5, expand=True)

        # ⚔️ BATTLE CHAT: Toggle switch for Battle Chat Mode
        self.create_toggle_switch(
            test_section,
            "Enable Battle Chat Mode (แสดงด้านบนจอ)",
            self.battle_chat_mode_var
        )

        # ====== SECTION 4: SHORTCUTS AND INFO ======
        info_section = self.create_settings_section(main_frame, "ข้อมูลโปรแกรม")

        # แสดงชอร์ตคัทเป็นปุ่ม
        shortcut_frame = tk.Frame(info_section, bg=appearance_manager.bg_color)
        shortcut_frame.pack(fill=tk.X)

        # ดึงค่าชอร์ตคัทจาก settings
        toggle_ui_shortcut = self.settings.get_shortcut("toggle_ui", "alt+l")
        start_stop_shortcut = self.settings.get_shortcut("start_stop_translate", "f9")

        # สร้าง label เพื่อแสดงคำอธิบาย
        tk.Label(
            shortcut_frame,
            text="Toggle UI:",
            bg=appearance_manager.bg_color,
            fg="#AAAAAA",
            font=("IBM Plex Sans Thai Medium", 8),
            width=8,
            anchor="e",
        ).pack(side=tk.LEFT, padx=(5, 2))

        # สร้างปุ่มแสดงชอร์ตคัท Toggle UI
        self.toggle_ui_btn = tk.Label(
            shortcut_frame,
            text=toggle_ui_shortcut.upper(),
            bg="#333333",
            fg="white",
            font=("IBM Plex Sans Thai Medium", 8, "bold"),
            bd=1,
            relief=tk.RAISED,
            padx=5,
            pady=1,
            width=6,
            anchor="center",
        )
        self.toggle_ui_btn.pack(side=tk.LEFT)

        # เว้นระยะระหว่างชอร์ตคัท
        tk.Frame(shortcut_frame, width=10, bg=appearance_manager.bg_color).pack(
            side=tk.LEFT
        )

        # Start/Stop ชอร์ตคัท
        tk.Label(
            shortcut_frame,
            text="Start/Stop:",
            bg=appearance_manager.bg_color,
            fg="#AAAAAA",
            font=("IBM Plex Sans Thai Medium", 8),
            width=8,
            anchor="e",
        ).pack(side=tk.LEFT, padx=(0, 2))

        # สร้างปุ่มแสดงชอร์ตคัท Start/Stop
        self.start_stop_btn = tk.Label(
            shortcut_frame,
            text=start_stop_shortcut.upper(),
            bg="#333333",
            fg="white",
            font=("IBM Plex Sans Thai Medium", 8, "bold"),
            bd=1,
            relief=tk.RAISED,
            padx=5,
            pady=1,
            width=6,
            anchor="center",
        )
        self.start_stop_btn.pack(side=tk.LEFT)

        # สร้าง version label
        version_frame = tk.Frame(info_section, bg=appearance_manager.bg_color)
        version_frame.pack(fill=tk.X, pady=5)
        self.version_label = tk.Label(
            version_frame,
            text=f"MagicBabel Dalamud v{__version__} by iarcanar",
            bg=appearance_manager.bg_color,
            fg="#AAAAAA",
            font=("IBM Plex Sans Thai Medium", 8),
            anchor="center",
        )
        self.version_label.pack(fill=tk.X)

        # Status message label (สำหรับแสดงข้อความชั่วคราวเมื่อกด Apply)
        self.status_label = tk.Label(
            main_frame,
            text="",
            bg=appearance_manager.bg_color,
            fg="#4CAF50",  # สีเขียว
            font=("IBM Plex Sans Thai Medium", 10, "bold"),
        )
        self.status_label.pack(pady=2)

        # เพิ่มปุ่ม APPLY
        # Initial state: disabled (dark grey)
        self.apply_button = tk.Button(
            main_frame,
            text="APPLY",
            command=self.apply_settings,
            bg="#2a2a2a",  # Dark grey when no changes
            fg="#666666",  # Dimmed text
            font=("Nasalization Rg", 10, "bold"),
            bd=0,
            relief=tk.FLAT,
            padx=20,
            pady=8,
            cursor="arrow",  # Normal cursor when disabled
            state=tk.DISABLED  # Initially disabled
        )
        self.apply_button.pack(pady=(5, 10))

        # Store colors for easy reference
        self.apply_colors = {
            "inactive": {"bg": "#2a2a2a", "fg": "#666666"},
            "active": {"bg": "#1E88E5", "fg": "white"},  # Blue theme color
            "hover": {"bg": "#2196F3", "fg": "white"},    # Lighter blue
            "applied": {"bg": "#4CAF50", "fg": "white"}
        }

        # Initial hover bindings (will be updated based on state)
        self.apply_button_hover_enter = None
        self.apply_button_hover_leave = None

        # Window Movement Bindings
        self.settings_window.bind("<Button-1>", self.start_move_settings)
        self.settings_window.bind("<ButtonRelease-1>", self.stop_move_settings)
        self.settings_window.bind("<B1-Motion>", self.do_move_settings)

        # ตั้งค่าเริ่มต้น (เอาส่วน transparency ออก)

    def create_settings_section(self, parent, title, padx=10, pady=5):
        """สร้าง Frame สำหรับกลุ่มการตั้งค่าพร้อมหัวข้อ

        Args:
            parent: parent container
            title: ชื่อหัวข้อของ section
            padx: padding แนวนอน
            pady: padding แนวตั้ง

        Returns:
            tk.Frame: frame ที่สร้างขึ้นสำหรับใส่ widget
        """
        section_frame = tk.LabelFrame(
            parent,
            text=title,
            bg=appearance_manager.bg_color,
            fg="white",
            font=("IBM Plex Sans Thai Medium", 10, "bold"),
            bd=1,
            relief=tk.GROOVE,
            padx=padx,
            pady=pady,
        )
        section_frame.pack(fill=tk.X, padx=10, pady=5)
        return section_frame



    def create_pin_verification_window(self):
        """สร้างหน้าต่างยืนยัน PIN สำหรับเข้าถึงการตั้งค่า Model - Professional Design"""
        # สร้างหน้าต่างใหม่ขนาดใหญ่ขึ้น
        pin_window = tk.Toplevel(self.settings_window)
        pin_window.title("🚀 AI Model Access")
        pin_window.geometry("420x280")
        pin_window.overrideredirect(True)  # ไม่แสดง title bar
        pin_window.configure(bg="#1a1a1a")

        # จัดตำแหน่งหน้าต่างให้อยู่ตรงกลางของ parent
        parent_x = self.settings_window.winfo_x() + (
            self.settings_window.winfo_width() // 2
        )
        parent_y = self.settings_window.winfo_y() + (
            self.settings_window.winfo_height() // 2
        )
        pin_window.geometry(f"+{parent_x - 210}+{parent_y - 140}")

        # สร้างขอบกรอบสีฟ้าสำหรับ accent
        border_frame = tk.Frame(pin_window, bg="#4a9eff", relief="flat", bd=0)
        border_frame.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        # สร้างกรอบหลักภายในขอบ
        main_container = tk.Frame(border_frame, bg="#2d2d2d", relief="flat", bd=0)
        main_container.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # Header section ที่สามารถลากได้
        header_frame = tk.Frame(main_container, bg="#3d3d3d", height=60)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)
        header_frame.configure(cursor="hand2")

        # Close button
        close_btn = tk.Button(
            header_frame,
            text="✕",
            font=("Segoe UI", 12, "bold"),
            bg="#3d3d3d",
            fg="#b8b8b8",
            bd=0,
            relief="flat",
            width=3,
            command=pin_window.destroy,
            cursor="hand2",
        )
        close_btn.pack(side=tk.RIGHT, padx=15, pady=15)

        # Header title
        header_label = tk.Label(
            header_frame,
            text="🚀 AI Model Configuration Access",
            bg="#3d3d3d",
            fg="#ffffff",
            font=("Segoe UI", 16, "bold"),
        )
        header_label.pack(side=tk.LEFT, padx=20, pady=15)

        # Content area
        content_frame = tk.Frame(main_container, bg="#2d2d2d")
        content_frame.pack(fill=tk.BOTH, expand=True, padx=25, pady=20)

        # Description with icons
        desc_label = tk.Label(
            content_frame,
            text="🔐 Enter access code to unlock advanced AI model settings\n⚙️ Configure Gemini parameters and translation modes\n🎯 Professional model tuning capabilities",
            bg="#2d2d2d",
            fg="#b8b8b8",
            font=("Segoe UI", 10),
            justify=tk.CENTER,
        )
        desc_label.pack(pady=(0, 20))

        # PIN entry section với styling ใหม่
        entry_container = tk.Frame(content_frame, bg="#2d2d2d")
        entry_container.pack(pady=10)

        entry_label = tk.Label(
            entry_container,
            text="Access Code:",
            bg="#2d2d2d",
            fg="#ffffff",
            font=("Segoe UI", 12, "bold"),
        )
        entry_label.pack()

        # Enhanced PIN entry with border
        entry_border = tk.Frame(entry_container, bg="#4a9eff")
        entry_border.pack(pady=(8, 0))

        pin_var = tk.StringVar()
        pin_entry = tk.Entry(
            entry_border,
            textvariable=pin_var,
            show="●",  # ใช้ dot แทน asterisk
            width=15,
            bg="#3d3d3d",
            fg="#ffffff",
            insertbackground="#4a9eff",
            justify="center",
            font=("Segoe UI", 14, "bold"),
            bd=0,
            relief="flat",
        )
        pin_entry.pack(ipady=10, padx=2, pady=2)
        pin_entry.focus_set()

        # Error label với styling ใหม่
        error_label = tk.Label(
            content_frame,
            text="",
            bg="#2d2d2d",
            fg="#f44336",  # สีแดงสด
            font=("Segoe UI", 10),
            wraplength=350,
            justify=tk.CENTER,
        )
        error_label.pack(pady=(10, 0))

        # Submit button ที่สวยงาม
        button_frame = tk.Frame(content_frame, bg="#2d2d2d")
        button_frame.pack(pady=(15, 5))

        submit_button = tk.Button(
            button_frame,
            text="🚀 Access Model Settings",
            bg="#4a9eff",
            fg="#ffffff",
            activebackground="#6bb6ff",
            activeforeground="#ffffff",
            font=("Segoe UI", 12, "bold"),
            bd=0,
            relief="flat",
            padx=25,
            pady=10,
            cursor="hand2",
        )

        # Hover effects
        def on_enter(e):
            submit_button.configure(bg="#6bb6ff")

        def on_leave(e):
            submit_button.configure(bg="#4a9eff")

        submit_button.bind("<Enter>", on_enter)
        submit_button.bind("<Leave>", on_leave)

        # ฟังก์ชันตรวจสอบ PIN พร้อม animation
        def verify_pin():
            correct_pin = "051125"  # PIN ที่กำหนดไว้
            entered_pin = pin_var.get().strip()

            if entered_pin == correct_pin:
                # PIN ถูกต้อง - แสดง success animation
                submit_button.config(text="✅ Access Granted!", bg="#4caf50")
                error_label.config(
                    text="🎉 Welcome to AI Model Configuration", fg="#4caf50"
                )

                # ปิดหน้าต่างหลังจาก delay เล็กน้อย
                def open_model_settings():
                    pin_window.destroy()
                    # เปิดหน้าต่าง Model Settings
                    if not hasattr(self, "model_settings"):
                        from model import ModelSettings

                        # ตรวจสอบว่า self.main_app มีเมธอด update_api_settings หรือไม่
                        if hasattr(self.main_app, "update_api_settings"):
                            main_app_ref = self.main_app
                            logging.info("Found update_api_settings in main_app")
                        else:
                            # ลองใช้ parent ถ้า main_app ไม่มี
                            if hasattr(self.parent, "update_api_settings"):
                                main_app_ref = self.parent
                                logging.info(
                                    "Found update_api_settings in parent, using parent as main_app"
                                )
                            else:
                                # กรณีที่ไม่พบในทั้งสองที่
                                main_app_ref = None
                                logging.warning(
                                    "Could not find update_api_settings in either main_app or parent, model changes may not apply correctly"
                                )

                        self.model_settings = ModelSettings(
                            self.settings_window,
                            self.settings,
                            self.apply_settings_callback,
                            main_app=main_app_ref,
                        )

                    self.model_settings.open()
                    self.model_button.config(text="Close Model")

                pin_window.after(1500, open_model_settings)
            else:
                # PIN ไม่ถูกต้อง - แสดง error animation
                submit_button.config(text="❌ Access Denied", bg="#f44336")
                error_label.config(
                    text="🔒 โปรดติดต่อผู้พัฒนาเพื่อขอรหัสเข้าถึงฟังก์ชันนี้", fg="#f44336"
                )
                pin_var.set("")  # ล้างช่อง PIN
                pin_entry.focus_set()

                # รีเซ็ตปุ่มหลัง 2 วินาที
                pin_window.after(
                    2000,
                    lambda: [
                        submit_button.config(
                            text="🚀 Access Model Settings", bg="#4a9eff"
                        ),
                        error_label.config(text=""),
                    ],
                )

        # ผูกการทำงานให้กับปุ่ม Submit
        submit_button.config(command=verify_pin)
        submit_button.pack(pady=10)

        # ผูกปุ่ม Enter ให้ทำงานเหมือนกดปุ่ม Submit
        pin_entry.bind("<Return>", lambda event: verify_pin())

        # Setup window dragging
        def start_move(event):
            pin_window.x = event.x
            pin_window.y = event.y

        def stop_move(event):
            pin_window.x = None
            pin_window.y = None

        def do_move(event):
            if hasattr(pin_window, "x") and hasattr(pin_window, "y"):
                deltax = event.x - pin_window.x
                deltay = event.y - pin_window.y
                x = pin_window.winfo_x() + deltax
                y = pin_window.winfo_y() + deltay
                pin_window.geometry(f"+{x}+{y}")

        header_frame.bind("<Button-1>", start_move)
        header_frame.bind("<ButtonRelease-1>", stop_move)
        header_frame.bind("<B1-Motion>", do_move)
        header_label.bind("<Button-1>", start_move)
        header_label.bind("<ButtonRelease-1>", stop_move)
        header_label.bind("<B1-Motion>", do_move)

        # ทำให้หน้าต่างนี้อยู่ด้านบนเสมอ
        pin_window.lift()
        pin_window.attributes("-topmost", True)
        pin_window.grab_set()  # ป้องกันการคลิกหน้าต่างอื่น

    def _open_model_settings(self):
        """เปิดหน้าต่างตั้งค่า Model หลังจากยืนยัน PIN แล้ว"""
        if not hasattr(self, "model_settings"):
            # สร้าง ModelSettings ถ้ายังไม่มี
            from model import ModelSettings

            # ตรวจสอบว่า self.main_app มีเมธอด update_api_settings หรือไม่
            if hasattr(self.main_app, "update_api_settings"):
                main_app_ref = self.main_app
                logging.info("Found update_api_settings in main_app")
            else:
                # ลองใช้ parent ถ้า main_app ไม่มี
                if hasattr(self.parent, "update_api_settings"):
                    main_app_ref = self.parent
                    logging.info(
                        "Found update_api_settings in parent, using parent as main_app"
                    )
                else:
                    # กรณีที่ไม่พบในทั้งสองที่
                    main_app_ref = None
                    logging.warning(
                        "Could not find update_api_settings in either main_app or parent, model changes may not apply correctly"
                    )

            self.model_settings = ModelSettings(
                self.settings_window,
                self.settings,
                self.apply_settings_callback,
                main_app=main_app_ref,  # ส่ง reference ของ main_app ที่มีเมธอด update_api_settings
            )

        # เปิดหน้าต่าง model settings
        self.model_settings.open()
        self.model_button.config(text="Close Model")

    def toggle_model_settings(self):
        """Toggle Model Settings window with PIN verification"""
        if (
            hasattr(self, "model_settings")
            and self.model_settings.model_window
            and self.model_settings.model_window.winfo_exists()
            and self.model_settings.model_window.winfo_viewable()
        ):
            # ถ้าหน้าต่าง model settings เปิดอยู่แล้ว ให้ปิดหน้าต่าง
            self.model_settings.close()
            self.model_button.config(text="Model")
        else:
            # ถ้าหน้าต่าง model settings ปิดอยู่ ให้แสดงหน้าต่างยืนยัน PIN
            # เรียกใช้ฟังก์ชัน PIN verification ที่ปรับปรุงแล้ว
            self.create_pin_verification_window()

    def toggle_hotkey_ui(self):
        """เปิด/ปิดหน้าต่าง Hotkey UI"""
        try:
            if (
                not hasattr(self, "simplified_hotkey_ui")
                or self.simplified_hotkey_ui is None
            ):
                self.simplified_hotkey_ui = SimplifiedHotkeyUI(
                    self.settings_window, self.settings, self.update_hotkeys_callback
                )

            if (
                self.simplified_hotkey_ui.window
                and self.simplified_hotkey_ui.window.winfo_exists()
            ):
                self.simplified_hotkey_ui.close()
                self.hotkey_button.config(text="HotKey")
            else:
                self.simplified_hotkey_ui.open()
                self.hotkey_button.config(text="Close Hotkeys")

        except Exception as e:
            logging.error(f"Error in toggle_hotkey_ui: {e}")
            messagebox.showerror("Error", f"เกิดข้อผิดพลาดในการเปิด Hotkey UI: {e}")

    def toggle_font_ui(self):
        """เปิด/ปิดหน้าต่าง Font Manager"""
        try:
            # สร้าง font_manager หากยังไม่มี
            if not self.font_manager:
                self.font_manager = initialize_font_manager(None, self.settings)

            # สร้าง font_ui หากยังไม่มี หรือหน้าต่างถูกปิดไปแล้ว
            if (
                not self.font_ui
                or not hasattr(self.font_ui, "font_window")
                or not self.font_ui.font_window
                or not self.font_ui.font_window.winfo_exists()
            ):
                self.font_ui = FontUI(
                    self.settings_window,
                    self.font_manager,
                    self.settings,
                    self.main_app.apply_font_with_target if hasattr(self.main_app, 'apply_font_with_target') else self.apply_settings_callback,
                )

            # ถ้าหน้าต่างกำลังแสดงอยู่ ให้ปิด
            if (
                hasattr(self.font_ui, "font_window")
                and self.font_ui.font_window
                and self.font_ui.font_window.winfo_exists()
                and self.font_ui.font_window.winfo_viewable()
            ):
                self.font_ui.close_font_ui()
                self.font_button.config(text="FONT")
            # ถ้าหน้าต่างปิดอยู่ ให้เปิด
            else:
                self.font_ui.open_font_ui(
                    translated_ui=(
                        self.main_app.translated_ui
                        if hasattr(self.main_app, "translated_ui")
                        else None
                    )
                )
                self.font_button.config(text="Close Font")

        except Exception as e:
            logging.error(f"Error toggling font UI: {e}")
            messagebox.showerror("Error", f"เกิดข้อผิดพลาดในการเปิด Font Manager: {e}")

    # ─── Test Hook Injection Methods ───

    def create_test_button_with_subtitle(self, parent, text, subtitle, command):
        """สร้างปุ่มทดสอบพร้อม subtitle"""
        frame = tk.Frame(parent, bg=appearance_manager.bg_color)

        button = tk.Button(
            frame,
            text=text,
            command=command,
            bg="#404040",
            fg="white",
            font=("IBM Plex Sans Thai Medium", 9),
            bd=0,
            padx=10,
            pady=3,
            cursor="hand2",
        )
        button.pack()
        button.bind("<Enter>", lambda e: button.config(bg="#606060"))
        button.bind("<Leave>", lambda e: button.config(bg="#404040"))

        subtitle_label = tk.Label(
            frame,
            text=subtitle,
            bg=appearance_manager.bg_color,
            fg="#666666",
            font=("IBM Plex Sans Thai Medium", 7),
        )
        subtitle_label.pack()

        return frame

    def _inject_test_message(self, msg_type, speaker, message, chat_type):
        """Base method สำหรับ inject test message"""
        import time

        if not self.main_app or not hasattr(self.main_app, 'dalamud_handler'):
            logging.warning("[TEST] Main app or dalamud_handler not available")
            return
        if not self.main_app.dalamud_handler:
            logging.warning("[TEST] Dalamud handler not ready")
            return

        test_message = {
            "Type": msg_type,
            "Speaker": speaker,
            "Message": message,
            "Timestamp": int(time.time() * 1000),
            "ChatType": chat_type
        }

        self.main_app.dalamud_handler.process_message(test_message)
        logging.info(f"[TEST] Injected {msg_type} (ChatType {chat_type})")

    def inject_test_dialog(self):
        """Inject test dialog message (ChatType 61)"""
        self._inject_test_message(
            "dialogue", "Tataru",
            "Welcome back, adventurer! How may I assist you today?",
            61
        )

    def inject_test_battle(self):
        """Inject test battle message (ChatType 68)"""
        self._inject_test_message(
            "battle", "Gaius",
            "The weak shall be consumed by the strong!",
            68
        )

    def inject_test_cutscene(self):
        """Inject test cutscene message (ChatType 71)"""
        self._inject_test_message(
            "cutscene", "Hydaelyn",
            "Hear... Feel... Think... Your journey has only just begun.",
            71
        )

    def create_toggle_switch(self, parent, text, variable, always_on=False):
        """สร้าง Toggle Switch ที่กระชับและชัดเจน

        Args:
            parent: Parent widget
            text: Label text
            variable: BooleanVar to control
            always_on: If True, switch is always on with dark green color
        """
        # สร้าง Frame หลักสำหรับ container
        container = tk.Frame(parent, bg=appearance_manager.bg_color)
        container.pack(fill=tk.X, pady=2)

        # สร้าง label ที่คลิกได้
        label = tk.Label(
            container,
            text=text,
            bg=appearance_manager.bg_color,
            fg=appearance_manager.fg_color,
            font=("IBM Plex Sans Thai Medium", 10),
            cursor="hand2",
        )
        label.pack(side=tk.LEFT, fill=tk.X, expand=True, anchor="w")
        label.bind("<Button-1>", lambda e: self.toggle_switch_state(variable))

        # สร้าง Frame สำหรับ switch ที่มีขนาดที่แน่นอน
        switch_width = 40
        switch_height = 20
        switch_frame = tk.Frame(
            container,
            bg=appearance_manager.bg_color,
            width=switch_width,
            height=switch_height,
        )
        switch_frame.pack(side=tk.RIGHT, padx=5)
        switch_frame.pack_propagate(False)

        # สร้าง bg switch แบบใหม่ - ใช้ Label แทน Canvas เพื่อความง่าย - CYBERPUNK
        if always_on:
            # Dark cyan for always-on switches (CYBERPUNK)
            variable.set(True)  # Force to True
            bg_color = "#008B8B"  # Dark cyan
        else:
            bg_color = appearance_manager.get_theme_color("accent", "#00FFFF") if variable.get() else appearance_manager.get_theme_color("button_inactive_bg", "#2a2a3e")
        switch_bg = tk.Label(
            switch_frame,
            bg=bg_color,
            width=3,  # ตั้งค่าความกว้างคงที่
            height=1,  # ตั้งค่าความสูงคงที่
            bd=0,
        )
        switch_bg.place(
            relx=0.5,
            rely=0.5,
            anchor="center",
            width=switch_width - 4,
            height=switch_height - 8,
        )

        # ปรับขอบมน
        switch_bg.configure(
            relief=tk.RIDGE, borderwidth=1
        )  # ใช้ relief=RIDGE เพื่อให้ขอบมนขึ้น

        # สร้าง indicator (ตัวเลื่อน) แบบขอบมน
        indicator_size = 14
        x_on = switch_width - indicator_size - 5
        x_off = 5

        # ใช้ Label แทน Canvas
        indicator = tk.Label(
            switch_frame,
            bg="white",
            bd=1,
            relief=tk.RAISED,  # ใช้ relief=RAISED เพื่อให้มีเงา
        )
        indicator.place(
            x=x_on if variable.get() else x_off,
            y=(switch_height - indicator_size) // 2,
            width=indicator_size,
            height=indicator_size,
        )

        # บันทึก reference
        self.indicators = getattr(self, "indicators", {})
        indicator_id = len(self.indicators)
        self.indicators[indicator_id] = {
            "indicator": indicator,
            "bg": switch_bg,
            "variable": variable,
            "x_on": x_on,
            "x_off": x_off,
            "always_on": always_on,
        }

        # เพิ่ม bindings (ถ้าไม่ใช่ always_on)
        if not always_on:
            for widget in [switch_bg, indicator, label]:
                widget.bind("<Button-1>", lambda e, i=indicator_id: self.toggle_switch(i))
        else:
            # Make cursor normal for always-on switches (not clickable)
            label.config(cursor="arrow")

        return container

    def toggle_switch_state(self, variable):
        """Toggle สถานะของ variable โดยตรง และอัพเดท UI แล้วบันทึกทันที"""
        # Check if this is an always_on switch (TUI Auto Show)
        for indicator_id, data in self.indicators.items():
            if data["variable"] == variable and data.get("always_on", False):
                # Don't toggle if it's always_on
                return

        # Toggle ค่า variable
        new_state = not variable.get()
        variable.set(new_state)

        # แสดงค่าใหม่
        print(f"Variable toggled to: {new_state}")

        # Check for changes and update Apply button
        self.check_for_changes()

        # ค้นหา indicator ที่เกี่ยวข้องกับ variable นี้
        for indicator_id, data in self.indicators.items():
            if data["variable"] == variable:
                # อัพเดท UI ของ switch
                self.update_switch_ui(indicator_id, new_state)
                break

        # บันทึกการเปลี่ยนแปลงทันที (ไม่ต้องรอกด Apply)
        try:
            self.apply_settings(save_to_file=True)  # บันทึกลงไฟล์เมื่อ toggle เปลี่ยน
            print(f"Settings applied immediately for toggle change")
        except Exception as e:
            print(f"Error applying settings immediately: {e}")

    def toggle_switch(self, indicator_id):
        """Toggle สถานะของ switch และอัพเดท UI"""
        if indicator_id not in self.indicators:
            return

        # ดึงข้อมูล
        indicator_data = self.indicators[indicator_id]

        # Check if this is an always_on switch
        if indicator_data.get("always_on", False):
            # Don't toggle if it's always_on
            return

        indicator = indicator_data["indicator"]  # เปลี่ยนจาก ["canvas"] เป็น ["indicator"]
        bg = indicator_data["bg"]
        variable = indicator_data["variable"]

        # ตรวจสอบค่าปัจจุบัน
        current_value = variable.get()

        # Toggle ค่า variable
        variable.set(not current_value)

        # อัพเดท UI
        self.update_switch_ui(indicator_id, not current_value)

        # Check for changes and update Apply button
        self.check_for_changes()

    def update_switch_ui(self, indicator_id, is_on):
        """อัพเดท UI ของ switch ตามสถานะใหม่"""
        if indicator_id not in self.indicators:
            return

        indicator_data = self.indicators[indicator_id]
        indicator = indicator_data["indicator"]
        bg = indicator_data["bg"]
        x_on = indicator_data.get("x_on", 22)
        x_off = indicator_data.get("x_off", 4)
        always_on = indicator_data.get("always_on", False)

        if is_on:  # เปิด - CYBERPUNK
            indicator.place(x=x_on)
            if always_on:
                bg.config(bg="#008B8B")  # Dark cyan for always-on switches (CYBERPUNK)
            else:
                bg.config(bg=appearance_manager.get_theme_color("accent", "#00FFFF"))  # Cyan (CYBERPUNK)
        else:  # ปิด - CYBERPUNK
            indicator.place(x=x_off)
            bg.config(bg=appearance_manager.get_theme_color("button_inactive_bg", "#2a2a3e"))  # Dark blue-gray (CYBERPUNK)

    def apply_settings(self, settings_dict=None, save_to_file=True):
        """Apply settings with validation and show temporary message"""
        try:
            # กรณีกดปุ่ม Apply จาก settings UI
            if settings_dict is None:
                try:
                    # ดึงค่าจาก toggle switches เฉพาะที่ยังคงมี UI
                    enable_wasd_auto_hide = bool(self.auto_hide_var.get())
                    enable_cpu_monitoring = bool(
                        self.cpu_monitoring_var.get()
                    )  # CPU Monitoring
                    enable_tui_auto_show = bool(self.tui_auto_show_var.get())

                    # บันทึกค่าลง settings เฉพาะที่มี UI (ไม่บันทึกไฟล์ทันทีเพื่อป้องกัน duplicate save)
                    self.settings.set("enable_wasd_auto_hide", enable_wasd_auto_hide, save_immediately=False)
                    self.settings.set("enable_cpu_monitoring", enable_cpu_monitoring, save_immediately=False)
                    self.settings.set("enable_tui_auto_show", enable_tui_auto_show, save_immediately=False)
                    self.settings.set("enable_battle_chat_mode", self.battle_chat_mode_var.get(), save_immediately=False)  # ⚔️ Battle Chat Mode

                    # ตั้งค่า Dalamud เป็น True เสมอ (ไม่มี UI toggle)
                    self.settings.set("dalamud_enabled", True, save_immediately=False)

                    # บันทึกลงไฟล์ทันที (เฉพาะเมื่อ save_to_file=True) - บันทึกครั้งเดียวสำหรับทุกการเปลี่ยนแปลง
                    if save_to_file:
                        self.settings.save_settings()
                        print(f"Settings saved to file: WASD={enable_wasd_auto_hide}, CPU={enable_cpu_monitoring}, TUI={enable_tui_auto_show}")

                    # สร้าง dict สำหรับส่งต่อให้ callback (เฉพาะ settings ที่มี)
                    settings_dict = {
                        "enable_wasd_auto_hide": enable_wasd_auto_hide,
                        "enable_cpu_monitoring": enable_cpu_monitoring,
                        "enable_tui_auto_show": enable_tui_auto_show,
                        "dalamud_enabled": True  # เปิดเสมอ
                    }

                    # เรียก callback เพื่ออัพเดต UI อื่นๆ
                    if self.apply_settings_callback:
                        self.apply_settings_callback(settings_dict)
                        logging.info("Settings applied successfully")

                    # เปลี่ยนข้อความปุ่ม Apply ชั่วคราว
                    self.apply_button.config(
                        text="✓ APPLIED",
                        bg=self.apply_colors["applied"]["bg"],
                        fg=self.apply_colors["applied"]["fg"],
                        state=tk.DISABLED
                    )

                    # Reset initial values and has_changes flag
                    self.initial_values = {
                        "auto_hide": self.auto_hide_var.get(),
                        "cpu_monitoring": self.cpu_monitoring_var.get(),
                        "tui_auto_show": self.tui_auto_show_var.get()
                    }
                    self.has_changes = False

                    # แสดงข้อความ success
                    self.status_label.config(text="Settings applied successfully!")

                    # รีเซ็ตกลับหลังจาก 2 วินาที
                    self.settings_window.after(
                        2000,
                        lambda: self.update_apply_button_state(False)
                    )
                    self.settings_window.after(
                        2000, lambda: self.status_label.config(text="")
                    )

                    # อัพเดต toggle switch UI อีกครั้งเพื่อความมั่นใจ
                    for indicator_id, data in self.indicators.items():
                        variable = data["variable"]
                        self.update_switch_ui(indicator_id, variable.get())

                    # พิมพ์ข้อมูลตัวแปรเพื่อการตรวจสอบ
                    print(f"Applied settings:")
                    print(f"- WASD Auto Hide: {enable_wasd_auto_hide}")
                    print(f"- CPU Monitoring: {enable_cpu_monitoring}")
                    print(f"- TUI Auto Show: {enable_tui_auto_show}")

                    return True, None

                except ValueError as e:
                    self.status_label.config(text=f"Error: {str(e)}", fg="#FF5252")
                    self.settings_window.after(
                        3000, lambda: self.status_label.config(text="", fg="#4CAF50")
                    )
                    raise ValueError(f"Invalid input value: {str(e)}")

            # กรณีเรียกจาก advance settings (คงเดิม)
            else:
                logging.info("Applying advanced settings")
                # อัพเดทค่าลง settings
                for key, value in settings_dict.items():
                    self.settings.set(key, value)

                # บันทึกไฟล์
                self.settings.save_settings()

                if self.apply_settings_callback:
                    self.apply_settings_callback(settings_dict)

                return True, None

        except Exception as e:
            error_msg = f"Error applying settings: {str(e)}"
            logging.error(error_msg)

            # แสดงข้อความ error
            self.status_label.config(text=error_msg, fg="#FF5252")
            self.settings_window.after(
                3000, lambda: self.status_label.config(text="", fg="#4CAF50")
            )

            return False, error_msg

    def check_for_changes(self):
        """Check if any settings have changed from initial values"""
        current_values = {
            "auto_hide": self.auto_hide_var.get(),
            "cpu_monitoring": self.cpu_monitoring_var.get(),
            "tui_auto_show": self.tui_auto_show_var.get(),
            "battle_chat_mode": self.battle_chat_mode_var.get(),  # ⚔️ Battle Chat Mode
        }

        # Check if any value has changed
        self.has_changes = False
        for key in self.initial_values:
            if current_values[key] != self.initial_values[key]:
                self.has_changes = True
                break

        # Update Apply button state
        self.update_apply_button_state(self.has_changes)

    def update_apply_button_state(self, has_changes):
        """Update Apply button appearance based on whether there are changes"""
        # Remove old hover bindings
        if hasattr(self, 'apply_button_hover_enter'):
            self.apply_button.unbind("<Enter>")
        if hasattr(self, 'apply_button_hover_leave'):
            self.apply_button.unbind("<Leave>")

        if has_changes:
            # Active state - theme accent color
            self.apply_button.config(
                bg=self.apply_colors["active"]["bg"],
                fg=self.apply_colors["active"]["fg"],
                cursor="hand2",
                state=tk.NORMAL,
                text="APPLY"
            )
            # Add hover effects
            self.apply_button_hover_enter = lambda e: self.apply_button.config(
                bg=self.apply_colors["hover"]["bg"]
            )
            self.apply_button_hover_leave = lambda e: self.apply_button.config(
                bg=self.apply_colors["active"]["bg"]
            )
            self.apply_button.bind("<Enter>", self.apply_button_hover_enter)
            self.apply_button.bind("<Leave>", self.apply_button_hover_leave)
        else:
            # Inactive state - dark grey
            self.apply_button.config(
                bg=self.apply_colors["inactive"]["bg"],
                fg=self.apply_colors["inactive"]["fg"],
                cursor="arrow",
                state=tk.DISABLED,
                text="APPLY"
            )

    def reset_apply_button(self):
        """Reset the apply button text and status label"""
        self.update_apply_button_state(False)
        self.status_label.config(text="")

    def start_move_settings(self, event):
        self.settings_x = event.x
        self.settings_y = event.y

    def stop_move_settings(self, event):
        self.settings_x = None
        self.settings_y = None

    def do_move_settings(self, event):
        deltax = event.x - self.settings_x
        deltay = event.y - self.settings_y
        x = self.settings_window.winfo_x() + deltax
        y = self.settings_window.winfo_y() + deltay
        self.settings_window.geometry(f"+{x}+{y}")

        if (
            self.hotkey_ui
            and self.hotkey_ui.hotkey_window
            and self.hotkey_ui.hotkey_window.winfo_exists()
        ):
            hotkey_window = self.hotkey_ui.hotkey_window
            hotkey_window.update_idletasks()
            settings_height = self.settings_window.winfo_height()
            hotkey_x = x - hotkey_window.winfo_width() - 5
            hotkey_y = y + settings_height - hotkey_window.winfo_height()
            hotkey_window.geometry(f"+{hotkey_x}+{hotkey_y}")

    def open_advance_ui(self):
        # สร้าง advance_ui ใหม่ถ้ายังไม่มีหรือถูกปิดไป
        if (
            self.advance_ui is None
            or not hasattr(self.advance_ui, "advance_window")
            or not self.advance_ui.advance_window.winfo_exists()
        ):
            self.advance_ui = AdvanceUI(
                self.settings_window, self.settings, self.apply_settings_callback
            )

        # เปิดหน้าต่าง advance_ui
        self.advance_ui.open()
