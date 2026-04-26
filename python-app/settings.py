import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import logging
from translator_factory import TranslatorFactory
from appearance import appearance_manager
# advance_ui import removed 2026-04-25 — AdvanceUI class was never instantiated (OCR-era).
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
        "gemini-3.1-flash-lite-preview": {
            "display_name": "gemini-3.1-flash-lite-preview",
            "type": "gemini",
        },
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
            # line_spacing + text_transparency removed 2026-04-25 (orphan keys, never read)
            "width": 960,
            "height": 240,
            "enable_previous_dialog": True,  # เปิดใช้งาน Previous Dialog ด้วย right-click
            "enable_wasd_auto_hide": True,
            "enable_tui_auto_show": True,  # เปิดใช้งาน TUI auto-show เมื่อพบข้อความ text hook
            "enable_ui_toggle": True,  # อาจไม่ใช้ แต่คงไว้
            # enable_auto_area_switch + enable_click_translate removed 2026-04-25 (OCR-era dead features)
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
            # tui_sizes removed 2026-04-25 (orphan key, never read — TUI hardcodes sizes)
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
            # bg_swatch_mode + bg_swatch_transparency removed 2026-04-25 (orphan, OCR-era color picker)
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
            # buffer_settings removed 2026-04-25 (orphan key, never read — no buffering logic uses it)
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
            "cpu_limit": 80,  # ค่า default CPU limit (legacy field, unused)
            # CPU Monitoring Settings (Smart Performance) removed 2026-04-25
            # — was OCR-era throttling, no benefit under Dalamud pipe-push architecture.
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
            "logs_ui", {"width": 455, "height": 935, "font_size": 18, "font_family": "Anuphan", "visible": True}
        )

    def set_logs_settings(
        self, width=None, height=None, font_size=None, font_family=None, visible=None, x=None, y=None,
        transparency_mode=None, transparency_value=None, logs_reverse_mode=None
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
            # Legacy A/B/C/D mode — kept for backwards-compat with old Tkinter UI
            self.settings["logs_ui"]["transparency_mode"] = transparency_mode
        if transparency_value is not None:
            # New 10-100 slider value used by PyQt6 logs UI (v1.7.9+)
            self.settings["logs_ui"]["transparency_value"] = int(transparency_value)
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

        # Validate model — fallback to default if saved model no longer exists
        saved_model = params.get("model", "")
        if saved_model and saved_model not in self.VALID_MODELS:
            fallback = self.DEFAULT_API_PARAMETERS["model"]
            logging.warning(
                f"Saved model '{saved_model}' not in VALID_MODELS, falling back to '{fallback}'"
            )
            params["model"] = fallback
            params["displayed_model"] = fallback

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


# SettingsUI Tkinter class removed 2026-04-25.
# Was the legacy Tkinter settings UI — never instantiated in current PyQt6-based app.
# Active settings UI is pyqt_ui/settings_panel.SettingsPanel (created in MBB.create_settings_ui).
# All cpu_monitoring_var, click_translate_var, etc. references inside SettingsUI were dead.
