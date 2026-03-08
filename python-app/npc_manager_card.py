import time
import tkinter as tk
from tkinter import ttk, messagebox, font
import json
import os
import sys
import shutil
from datetime import datetime
from npc_file_utils import get_npc_file_path
from npc_file_utils import get_game_info_from_npc_file
from asset_manager import AssetManager


# Removed PyQt5 and swap_data imports - already available in main MBB

# Card colors
CARD_NORMAL_BG = "#1a1a1a"
CARD_HOVER_BG = "#222222"  # พื้นหลังเมื่อ hover (สว่างขึ้นเล็กน้อย)
CARD_NORMAL_BORDER = "#2a2a2a"
CARD_HOVER_BORDER = "#007AFF"  # accent blue border เมื่อ hover


# ลองนำเข้า logging manager หากมี
try:
    from loggings import LoggingManager
except ImportError:
    # สร้าง mock class สำหรับ logging ถ้าไม่พบไฟล์
    class LoggingManager:
        def __init__(self, parent=None):
            self.parent = parent

        def log_info(self, message):
            print(f"INFO: {message}")

        def log_error(self, message):
            print(f"ERROR: {message}")

        def log_npc_manager(self, message):
            print(f"NPC MANAGER: {message}")


_topmost_state = False  # ค่าเริ่มต้นเป็น False (unpin) ให้แสดงตามปกติ


class CardView:
    """คลาสสำหรับจัดการ UI ของแต่ละการ์ด"""

    def __init__(
        self,
        parent,
        data,
        section_type,
        font_config,
        all_roles_data=None,
        navigate_to_role_callback=None,
        on_edit_callback=None,
        on_delete_callback=None,
        detail_mode=False,
        copy_name="",  # เพิ่มพารามิเตอร์ที่มีค่าเริ่มต้น
        copy_callback=None,  # เพิ่มพารามิเตอร์ที่มีค่าเริ่มต้น
    ):
        """คลาส CardView สำหรับแสดงข้อมูลของแต่ละรายการในรูปแบบการ์ด"""
        self.parent = parent
        self.data = data
        self.section_type = section_type
        self.font_config = font_config
        self.all_roles_data = all_roles_data
        self.navigate_to_role_callback = navigate_to_role_callback
        self.on_edit_callback = on_edit_callback
        self.on_delete_callback = on_delete_callback
        self.detail_mode = detail_mode
        self.copy_name = copy_name
        self.copy_callback = copy_callback

        # สร้าง frame สำหรับการ์ด
        self.card_frame = tk.Frame(
            parent,
            bg=CARD_NORMAL_BG,
            highlightbackground=CARD_NORMAL_BORDER,
            highlightthickness=1,
        )

        # ใช้ grid แทน pack สำหรับ frame หลักของการ์ดด้วย
        self.card_frame.grid_rowconfigure(1, weight=1)
        self.card_frame.grid_columnconfigure(0, weight=1)

        # สร้าง UI สำหรับการ์ด
        self._create_card_ui()

        # hover effect — border highlight + bg lighten (detail_mode เท่านั้น)
        self._setup_card_hover()

    def _create_card_ui(self):
        """สร้าง UI สำหรับการ์ด (ย้ายปุ่ม Role Link ลงล่าง, ตัดคำชื่อ)"""
        # ดึงค่า font (เหมือนเดิม)
        font_family = self.font_config.get("family", "Arial")
        font_lg_bold = (font_family, self.font_config.get("large_bold", 21), "bold")
        font_md_bold = (font_family, self.font_config.get("medium_bold", 18), "bold")
        font_md = (font_family, self.font_config.get("medium", 16))
        font_sm_bold = (font_family, self.font_config.get("small_bold", 15), "bold")
        font_sm = (font_family, self.font_config.get("small", 15))
        font_xs_bold = (font_family, self.font_config.get("xsmall_bold", 13), "bold")
        font_xs = (font_family, self.font_config.get("xsmall", 13))

        # ปรับขนาด wraplength ตาม detail_mode
        wraplength = 320 if self.detail_mode else 350

        # --- ใช้ grid สำหรับ frame หลักของการ์ด ---
        self.card_frame.grid_rowconfigure(1, weight=1)  # ให้ content ขยายแนวตั้ง
        self.card_frame.grid_columnconfigure(
            0, weight=1
        )  # ให้ content/button ขยายแนวนอน

        # --- Frame บนสุด (Title, Gender Tag) ---
        # ไม่ต้องมีปุ่ม Role Link ที่นี่แล้ว
        top_frame = tk.Frame(self.card_frame, bg="#1a1a1a")
        top_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 0))
        top_frame.grid_columnconfigure(0, weight=1)  # ให้ชื่อขยายได้

        # --- Frame เนื้อหาตรงกลาง ---
        self.content_frame = tk.Frame(self.card_frame, bg="#1a1a1a")
        self.content_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        self.content_frame.grid_columnconfigure(0, weight=1)

        # --- Frame ปุ่มด้านล่าง ---
        button_frame = tk.Frame(self.card_frame, bg="#1a1a1a")
        button_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(5, 10))
        # กำหนดคอลัมน์สำหรับปุ่ม: Edit ซ้ายสุด, Role กลาง (ถ้ามี), Delete ขวาสุด
        button_frame.grid_columnconfigure(0, weight=1)  # Edit
        button_frame.grid_columnconfigure(1, weight=0)  # Role Link (ไม่ขยาย)
        button_frame.grid_columnconfigure(2, weight=1)  # Delete

        # สร้าง Widgets เริ่มต้นเป็น None
        title = None
        gender_tag = None
        role_label = None
        role_value = None
        rel_label = None
        rel_value = None
        desc_label = None
        desc_value = None
        separator = None
        content_label = None
        self.role_link_button = None  # ยังคงประกาศไว้

        # --- แสดง Title และ Gender Tag (ใน top_frame) ---
        if self.section_type == "main_characters":
            name = self.data.get("firstName", "")
            if self.data.get("lastName"):
                name += f" {self.data.get('lastName')}"
            # *** เพิ่ม wraplength และ justify ให้ title ***
            title = tk.Label(
                top_frame,
                text=name,
                font=font_lg_bold,
                bg="#1a1a1a",
                fg="#FFFFFF",
                anchor="w",
                wraplength=wraplength,  # ใช้ค่า wraplength ที่ปรับตาม detail_mode
                justify="left",
            )
            title.grid(row=0, column=0, sticky="ew")  # ใช้ grid ใน top_frame

            gender = self.data.get("gender", "")
            gender_bg_color = "#FF69B4" if gender == "Female" else "#007AFF"
            gender_tag = tk.Label(
                top_frame,
                text=gender,
                font=font_xs,
                bg=gender_bg_color,
                fg="#FFFFFF",
                padx=10,
                pady=4,
            )
            gender_tag.grid(row=1, column=0, sticky="w", pady=(5, 0))  # วางใต้ชื่อ

        elif self.section_type == "npcs":
            # *** เพิ่ม wraplength และ justify ให้ title ***
            title = tk.Label(
                top_frame,
                text=self.data.get("name", ""),
                font=font_lg_bold,
                bg="#1a1a1a",
                fg="#FFFFFF",
                anchor="w",
                wraplength=wraplength,  # ใช้ค่า wraplength ที่ปรับตาม detail_mode
                justify="left",
            )
            title.grid(row=0, column=0, sticky="ew")

        elif self.section_type in ["lore", "character_roles", "word_fixes"]:
            # *** เพิ่ม wraplength และ justify ให้ title ***
            title = tk.Label(
                top_frame,
                text=self.data.get("key", ""),
                font=font_lg_bold,
                bg="#1a1a1a",
                fg="#FFFFFF",
                anchor="w",
                wraplength=wraplength,  # ใช้ค่า wraplength ที่ปรับตาม detail_mode
                justify="left",
            )
            title.grid(row=0, column=0, sticky="ew")

        # --- แสดงข้อมูลส่วนเนื้อหา (ใน self.content_frame) ---
        if self.section_type == "main_characters":
            role_label = tk.Label(
                self.content_frame, text="Role:", font=font_md, bg="#1a1a1a", fg="#888888"
            )
            role_label.grid(row=0, column=0, sticky="w", pady=(5, 0))
            role_value = tk.Label(
                self.content_frame,
                text=self.data.get("role", ""),
                font=font_md,
                bg="#1a1a1a",
                fg="#FFFFFF",
                wraplength=wraplength,  # ใช้ค่า wraplength ที่ปรับตาม detail_mode
                justify="left",
            )
            role_value.grid(row=1, column=0, sticky="w")
            rel_label = tk.Label(
                self.content_frame,
                text="Relationship:",
                font=font_md,
                bg="#1a1a1a",
                fg="#888888",
            )
            rel_label.grid(row=2, column=0, sticky="w", pady=(10, 0))
            rel_value = tk.Label(
                self.content_frame,
                text=self.data.get("relationship", ""),
                font=font_md,
                bg="#1a1a1a",
                fg="#FFFFFF",
                wraplength=wraplength,  # ใช้ค่า wraplength ที่ปรับตาม detail_mode
                justify="left",
            )
            rel_value.grid(row=3, column=0, sticky="w")
        elif self.section_type == "npcs":
            role_label = tk.Label(
                self.content_frame, text="Role:", font=font_md, bg="#1a1a1a", fg="#888888"
            )
            role_label.grid(row=0, column=0, sticky="w", pady=(5, 0))
            role_value = tk.Label(
                self.content_frame,
                text=self.data.get("role", ""),
                font=font_md,
                bg="#1a1a1a",
                fg="#FFFFFF",
                wraplength=wraplength,  # ใช้ค่า wraplength ที่ปรับตาม detail_mode
                justify="left",
            )
            role_value.grid(row=1, column=0, sticky="w")
            desc_label = tk.Label(
                self.content_frame,
                text="Description:",
                font=font_md,
                bg="#1a1a1a",
                fg="#888888",
            )
            desc_label.grid(row=2, column=0, sticky="w", pady=(10, 0))
            desc_value = tk.Label(
                self.content_frame,
                text=self.data.get("description", ""),
                font=font_md,
                bg="#1a1a1a",
                fg="#FFFFFF",
                wraplength=350,
                justify="left",
            )
            desc_value.grid(row=3, column=0, sticky="w")
        elif self.section_type in ["lore", "character_roles", "word_fixes"]:
            separator = tk.Frame(self.content_frame, height=1, bg="#2a2a2a")
            separator.grid(
                row=0, column=0, sticky="ew", pady=5
            )  # ลด pady ของ separator
            content_label = tk.Label(
                self.content_frame,
                text=self.data.get("value", ""),
                font=font_md,
                bg="#1a1a1a",
                fg="#FFFFFF",
                wraplength=wraplength,  # ใช้ค่า wraplength ที่ปรับตาม detail_mode
                justify="left",
            )
            content_label.grid(row=1, column=0, sticky="w")

        # --- ปุ่มด้านล่าง (ใน button_frame) ---
        # ปุ่ม Edit (อยู่ column 0)
        edit_btn = tk.Button(
            button_frame,
            text="Edit",
            font=(font_xs if self.detail_mode else font_sm),
            bg="#222222",
            fg="#FFFFFF",
            bd=0,
            relief="flat",
            padx=8 if self.detail_mode else 15,
            pady=2 if self.detail_mode else 5,
            command=self._on_edit_click,
        )
        edit_btn.grid(row=0, column=0, sticky="w", padx=(0, 5))

        # *** เพิ่มปุ่ม Copy (ก่อนปุ่ม Role Link) ***
        if self.copy_name and self.copy_callback:
            copy_btn = tk.Button(
                button_frame,
                text="Copy",
                font=(font_xs if self.detail_mode else font_sm),
                bg="#222222",
                fg="#FFFFFF",
                bd=0,
                relief="flat",
                padx=8 if self.detail_mode else 15,
                pady=2 if self.detail_mode else 5,
                command=lambda: (
                    self.copy_callback(self.copy_name) if self.copy_callback else None
                ),
            )
            # วางไว้ก่อนปุ่ม Role Link (ถ้ามี) หรือ Delete
            if self.section_type == "main_characters":
                copy_btn.grid(row=0, column=1, sticky="w", padx=5)
            else:
                copy_btn.grid(row=0, column=1, sticky="w", padx=5)

            # Hover effects for Copy button
            copy_btn.bind(
                "<Enter>",
                lambda e, b=copy_btn, c="#2a2a2a": (
                    b.configure(bg=c) if b.winfo_exists() else None
                ),
            )
            copy_btn.bind(
                "<Leave>",
                lambda e, b=copy_btn: (
                    b.configure(bg="#222222") if b.winfo_exists() else None
                ),
            )

        # *** ปุ่ม Role Link (ย้ายมานี่, อยู่ column 2 แทน 1, เฉพาะ main_characters) ***
        if self.section_type == "main_characters":
            char_name = self.data.get("firstName")
            has_role_entry = False
            if char_name and self.all_roles_data:
                for role_char_name in self.all_roles_data.keys():
                    if role_char_name.lower() == char_name.lower():
                        has_role_entry = True
                        break

            role_button_text = "Edit Role" if has_role_entry else "Add Role"
            role_button_color = "#007AFF" if has_role_entry else "#FF9500"
            role_button_command = self._edit_role if has_role_entry else self._add_role

            self.role_link_button = tk.Button(
                button_frame,
                text=role_button_text,
                font=(font_xs if self.detail_mode else font_sm),
                bg=role_button_color,
                fg="white",
                bd=0,
                relief="flat",
                padx=8 if self.detail_mode else 15,
                pady=2 if self.detail_mode else 5,
                command=role_button_command,
            )
            # *** วางปุ่ม Role Link ไว้ column 2 แทน ***
            self.role_link_button.grid(row=0, column=2, sticky="ew", padx=5)

            # Hover effect
            hover_bg = "#0A84FF" if has_role_entry else "#FFA500"
            self.role_link_button.bind(
                "<Enter>",
                lambda e, hbg=hover_bg, btn=self.role_link_button: (
                    btn.configure(bg=hbg) if btn.winfo_exists() else None
                ),
            )
            self.role_link_button.bind(
                "<Leave>",
                lambda e, nbg=role_button_color, btn=self.role_link_button: (
                    btn.configure(bg=nbg) if btn.winfo_exists() else None
                ),
            )

        # ปุ่ม Delete (อยู่ column 2 หรือ 3 ขึ้นอยู่กับมีปุ่ม Role Link หรือไม่)
        delete_column = 3 if self.section_type == "main_characters" else 2
        delete_btn = tk.Button(
            button_frame,
            text="Delete",
            font=(font_xs if self.detail_mode else font_sm),
            bg="#222222",
            fg="#FF3B30",
            bd=0,
            relief="flat",
            padx=8 if self.detail_mode else 15,
            pady=2 if self.detail_mode else 5,
            command=self._on_delete_click,
        )
        delete_btn.grid(row=0, column=delete_column, sticky="e", padx=(5, 0))

        # Hover effects for Edit/Delete buttons
        for btn, hover_color in [(edit_btn, "#2a2a2a"), (delete_btn, "#2a2a2a")]:
            btn.bind(
                "<Enter>",
                lambda e, b=btn, c=hover_color: (
                    b.configure(bg=c) if b.winfo_exists() else None
                ),
            )
            btn.bind(
                "<Leave>",
                lambda e, b=btn: (
                    b.configure(bg="#222222") if b.winfo_exists() else None
                ),
            )

        # Event คลิกการ์ด (เหมือนเดิม)
        clickable_widgets = [self.card_frame, top_frame, self.content_frame]
        if title:
            clickable_widgets.append(title)
        if gender_tag:
            clickable_widgets.append(gender_tag)
        if role_label:
            clickable_widgets.append(role_label)
        if role_value:
            clickable_widgets.append(role_value)
        if rel_label:
            clickable_widgets.append(rel_label)
        if rel_value:
            clickable_widgets.append(rel_value)
        if desc_label:
            clickable_widgets.append(desc_label)
        if desc_value:
            clickable_widgets.append(desc_value)
        if separator:
            clickable_widgets.append(separator)
        if content_label:
            clickable_widgets.append(content_label)

        for widget in clickable_widgets:
            if (
                widget
                and isinstance(widget, (tk.Frame, tk.Label))
                and widget.winfo_exists()
            ):
                # ผูกกับ _on_edit_click เฉพาะ Frame และ Label (ไม่ผูกกับปุ่ม)
                widget.bind(
                    "<Button-1>", lambda e, d=self.data: self._handle_card_click(e, d)
                )

    def _handle_card_click(self, event, data):
        """จัดการเมื่อคลิกส่วนต่างๆ ของการ์ด (ที่ไม่ใช่ปุ่ม)"""
        # ตรวจสอบว่า widget ที่คลิกไม่ใช่ปุ่ม
        if event.widget.winfo_class() != "Button":
            # ถ้าต้องการให้คลิกแล้ว View:
            # self._on_view_click(data) # ต้องสร้างเมธอดนี้ หรือเรียก _show_card_detail โดยตรง
            # ถ้าต้องการให้คลิกแล้ว Edit:
            if self.on_edit_callback:
                self.on_edit_callback(data)

    def _edit_role(self):
        """เรียก Callback เพื่อนำทางไปยังหน้า Roles และค้นหาตัวละคร"""
        if self.navigate_to_role_callback and self.section_type == "main_characters":
            char_name = self.data.get("firstName")
            if char_name:
                # ส่งชื่อตัวละคร และ mode 'edit'
                self.navigate_to_role_callback(character_name=char_name, mode="edit")
            else:
                print("Warning: Could not get firstName for role navigation (edit).")

    def _add_role(self):
        """เรียก Callback เพื่อนำทางไปยังหน้า Roles และเตรียมเพิ่ม Role ใหม่"""
        if self.navigate_to_role_callback and self.section_type == "main_characters":
            char_name = self.data.get("firstName")
            if char_name:
                # ส่งชื่อตัวละคร และ mode 'add'
                self.navigate_to_role_callback(character_name=char_name, mode="add")
            else:
                print("Warning: Could not get firstName for role navigation (add).")

    def _on_edit_click(self, event=None):
        """จัดการเมื่อคลิกที่การ์ดหรือปุ่มแก้ไข"""
        if self.on_edit_callback:
            self.on_edit_callback(self.data)

    def _on_delete_click(self):
        """จัดการเมื่อคลิกปุ่มลบ"""
        if self.on_delete_callback:
            self.on_delete_callback(self.data)

    def update_data(self, new_data):
        """อัพเดทข้อมูลในการ์ด"""
        self.data = new_data
        # ล้างและสร้าง UI ใหม่
        for widget in self.card_frame.winfo_children():
            widget.destroy()
        self._create_card_ui()

    def get_frame(self):
        """ส่งคืน frame ของการ์ด"""
        return self.card_frame

    def _setup_card_hover(self):
        """ตั้งค่า hover effect สำหรับ detail_mode — border highlight + bg lighten"""
        if not self.detail_mode:
            return

        self._hover_active = False
        self._all_bg_widgets = []

        # รวบรวม widgets ทั้งหมดที่มี bg ต้องเปลี่ยนเมื่อ hover
        self._collect_bg_widgets(self.card_frame)

        # Bind Enter/Leave บน card_frame และ children ทั้งหมด
        self._bind_hover_recursive(self.card_frame)

    def _collect_bg_widgets(self, parent):
        """รวบรวม widgets ที่ใช้ bg สีเดียวกับการ์ด"""
        try:
            bg = str(parent.cget("bg")).lower() if hasattr(parent, "cget") else ""
            if bg == CARD_NORMAL_BG:
                self._all_bg_widgets.append(parent)
            for child in parent.winfo_children():
                self._collect_bg_widgets(child)
        except Exception:
            pass

    def _bind_hover_recursive(self, widget):
        """Bind hover events บน widget และ children ทั้งหมด"""
        try:
            widget.bind("<Enter>", self._on_card_hover_enter, add="+")
            widget.bind("<Leave>", self._on_card_hover_leave, add="+")
            for child in widget.winfo_children():
                self._bind_hover_recursive(child)
        except Exception:
            pass

    def _on_card_hover_enter(self, event):
        """เมื่อ mouse เข้าพื้นที่การ์ด — เปลี่ยน border + bg"""
        if self._hover_active:
            return
        self._hover_active = True
        try:
            self.card_frame.configure(
                highlightbackground=CARD_HOVER_BORDER,
                highlightthickness=2,
                cursor="hand2",
            )
            for w in self._all_bg_widgets:
                try:
                    w.configure(bg=CARD_HOVER_BG)
                except Exception:
                    pass
        except Exception:
            pass

    def _on_card_hover_leave(self, event):
        """เมื่อ mouse ออกจากการ์ด — คืนค่าเดิม"""
        if not self._hover_active:
            return
        # ตรวจสอบว่า mouse ออกจาก card_frame จริงๆ
        try:
            x, y = self.card_frame.winfo_pointerxy()
            widget = self.card_frame.winfo_containing(x, y)
            if widget is not None and self._is_child_of(widget, self.card_frame):
                return  # ยังอยู่ใน card
        except Exception:
            pass

        self._hover_active = False
        try:
            self.card_frame.configure(
                highlightbackground=CARD_NORMAL_BORDER,
                highlightthickness=1,
                cursor="",
            )
            for w in self._all_bg_widgets:
                try:
                    w.configure(bg=CARD_NORMAL_BG)
                except Exception:
                    pass
        except Exception:
            pass

    def _trigger_edit(self):
        """เรียก callback เพื่อเปิดฟอร์มแก้ไข"""
        try:
            if self.on_edit_callback:
                self.on_edit_callback(self.data)
        except Exception as e:
            pass

    def _is_child_of(self, widget, parent):
        """ตรวจสอบว่า widget เป็น child ของ parent หรือไม่"""
        try:
            current = widget
            while current:
                if current == parent:
                    return True
                current = current.winfo_parent()
                if current:
                    try:
                        current = parent.nametowidget(current)
                    except:
                        break
            return False
        except:
            return False

    def destroy(self):
        """ทำลายการ์ด"""
        self.card_frame.destroy()


class NPCManagerCard:
    """คลาสหลักสำหรับจัดการ NPC แบบ Card View
    Version: 2.0
    """

    def __init__(
        self,
        parent,
        reload_callback=None,
        logging_manager=None,
        stop_translation_callback=None,
        parent_app=None,  # เพิ่ม parent_app สำหรับเข้าถึง translator
    ):
        self.parent = parent
        self.reload_callback = reload_callback
        self.logging_manager = logging_manager or LoggingManager(None)
        self.stop_translation_callback = stop_translation_callback
        self.on_close_callback = None
        self.parent_app = parent_app  # เก็บ reference ไปยัง main app

        # 🎯 เพิ่ม: Callback สำหรับหยุดการแปลเมื่อเปิด NPC Manager
        self.stop_translation_callback = stop_translation_callback

        # เพิ่ม info เกี่ยวกับเกมจากไฟล์ NPC
        self.current_game_info = get_game_info_from_npc_file()

        # กำหนดค่าเริ่มต้น - *** ลดขนาดฟอนต์เป็น 80% (จาก 24 เป็น 19) ***
        # ใช้ Anuphan เป็นฟอนต์หลัก (รองรับภาษาไทย, bundled ใน fonts/)
        # fallback เป็น Segoe UI ถ้า Anuphan ไม่พร้อมใช้งาน
        self.font = "Anuphan"
        try:
            test_font = font.Font(root=self.parent, family="Anuphan", size=12)
            if test_font.actual()["family"].lower() != "anuphan":
                self.font = "Segoe UI"
        except Exception:
            self.font = "Segoe UI"
        self.font_size = 19  # ลดจาก 24 เป็น 19 (80%)
        # ขนาดฟอนต์สำหรับส่วนประกอบย่อยต่างๆ (คำนวณจาก 19)
        self.font_size_large_bold = 17  # ลดจาก 21 เป็น 17
        self.font_size_medium_bold = 14  # ลดจาก 18 เป็น 14
        self.font_size_medium = 13  # ลดจาก 16 เป็น 13
        self.font_size_small_bold = 12  # ลดจาก 15 เป็น 12
        self.font_size_small = 12  # ลดจาก 15 เป็น 12
        self.font_size_xsmall_bold = 10  # ลดจาก 13 เป็น 10
        self.font_size_xsmall = 10  # ลดจาก 13 เป็น 10

        self.data = {}
        self.data_cache = {}
        
        # คำอธิบายสำหรับแต่ละแท็บ
        self.section_descriptions = {
            "main_characters": "📝 ตัวละครหลัก - ระบุเพศ บทบาท ความสัมพันธ์ เพื่ออรรถรสการแปลสูงสุด",
            "npcs": "👥 NPC ทั่วไป - จัดการตัวละครรองและ NPC ในเกม", 
            "lore": "📚 คำศัพท์เฉพาะ - คำศัพท์ สถานที่ ไอเทม ที่มีชื่อเฉพาะในเกม",
            "character_roles": "🎭 สไตล์การพูด - กำหนดบุคลิกและรูปแบบการพูดของตัวละคร",
            "word_fixes": "🔧 แก้คำผิด - แก้ไขคำที่แปลผิดบ่อยๆ หรือต้องการกำหนดเอง"
        }

        # ✅ เพิ่มตัวแปรสำหรับการบันทึกสถานะ (State Preservation)
        self.saved_state = {
            "search_term": "",  # คำค้นหาที่บันทึกไว้
            "current_section": None,  # section ปัจจุบันที่บันทึกไว้
            "scroll_position": 0,  # ตำแหน่ง scroll ที่บันทึกไว้
            "window_geometry": None,  # ขนาดและตำแหน่งหน้าต่าง
        }

        # Game info
        # เรียกใช้ฟังก์ชันเพื่ออ่านข้อมูลจาก npc.json โดยตรง
        self.current_game_info = get_game_info_from_npc_file()

        # เพิ่มการตรวจสอบเผื่อในกรณีที่ไฟล์ npc.json ไม่มีข้อมูล _game_info
        if not self.current_game_info:
            self.logging_manager.log_warning(
                "No _game_info found in NPC file for NPCManagerCard, using default."
            )
            self.current_game_info = {
                "name": "N/A",
                "code": "default",
                "description": "No game info found in NPC.json",
            }

        # 🔧 เพิ่มระบบจัดการ timer และ focus แบบครอบคลุม
        self._all_timers = []  # เก็บ timer ID ทั้งหมด
        self._active_bindings = []  # เก็บ event bindings ที่ active
        self._is_destroyed = False  # flag ตรวจสอบว่า instance ถูก destroy แล้ว

        # ✅ เพิ่มตัวแปรสำหรับ Health Monitoring
        self._health_check_timer = None
        self._last_interaction_time = time.time()
        self._interaction_count = 0
        self._last_focus_time = 0  # สำหรับ focus cooldown

        self.current_section = None
        self.tree_items = {}
        self.is_topmost = True  # เริ่มต้นด้วย pin mode เพื่อป้องกันการทับ
        self._search_cache = {}
        self._search_delay = None
        self._lazy_load_complete = False
        self._focus_after_id = None
        self.current_detail_widget = None  # Track widget in detail_content_frame
        self.current_edit_data = None  # Track data being edited

        # สร้างหน้าต่าง
        self.window = tk.Toplevel(parent)
        self.window.title("NPC Manager")
        self.window.protocol("WM_DELETE_WINDOW", self.hide_window)

        # *** ปรับขนาดหน้าต่างเริ่มต้น (ลดเป็น 80% แล้วเพิ่มความสูง 100px) ***
        default_width = 940
        default_height = 820

        # คำนวณตำแหน่งเริ่มต้น (ทางขวาของ MBB main window)
        x, y = 0, 0
        try:
            if parent_app and hasattr(parent_app, "_get_mbb_geometry"):
                mx, my, mw, mh = parent_app._get_mbb_geometry()
                x = mx + mw + 10
                y = my
            else:
                screen_width = parent.winfo_screenwidth()
                screen_height = parent.winfo_screenheight()
                x = (screen_width - default_width) // 2
                y = (screen_height - default_height) // 2
        except Exception:
            pass

        # ตั้งค่าขนาดและตำแหน่ง
        self.window.withdraw()
        self.window.geometry(f"{default_width}x{default_height}+{x}+{y}")
        # *** ปรับ minsize ให้เล็กลงอีก (ลดเป็น 80%) ***
        self.window.minsize(456, 416)  # ลดจาก 570x520 เป็น 456x416

        # แก้ไขเพื่อให้แสดงในแถบงาน taskbar ได้
        # การใช้ overrideredirect(True) อาจทำให้การจัดการ focus ยากขึ้น
        # ลองทดสอบกับ False ถ้ายังเจอปัญหา focus แปลกๆ
        self.window.overrideredirect(True)
        # Only set transient when parent is visible (withdrawn parent causes display issues)
        try:
            if parent.winfo_viewable():
                self.window.transient(parent)
        except Exception:
            pass  # Skip transient if parent state can't be determined

        # กำหนดสไตล์ (เหมือนเดิม)
        self.style = {
            "bg_primary": "#141414",
            "bg_secondary": "#1a1a1a",
            "bg_tertiary": "#222222",
            "accent": "#007AFF",
            "accent_hover": "#0A84FF",
            "text_primary": "#e0e0e0",
            "text_secondary": "#888888",
            "error": "#cc4444",
            "success": "#4CAF50",
            "warning": "#FF9500",
            "info": "#3498DB",
        }

        # โหลดข้อมูล (lazy loading) (เหมือนเดิม)
        self.load_data()

        self.search_results = {
            "main_characters": 0,
            "npcs": 0,
            "lore": 0,
            "character_roles": 0,
            "word_fixes": 0,
        }

        # สร้าง UI (เหมือนเดิม)
        self._create_main_ui()

        # อัพเดทสถานะ Topmost เริ่มต้น (เหมือนเดิม)
        global _topmost_state
        self.is_topmost = _topmost_state
        self._ensure_topmost()

        # ✅ เริ่มระบบ Health Monitoring
        self._start_health_monitoring()

    def _create_main_ui(self):
        """สร้าง UI หลักของโปรแกรม (ปรับสัดส่วน Layout และ Resize Icon)"""
        # ตั้งค่าสีพื้นหลังหลัก (เหมือนเดิม)
        self.window.configure(bg=self.style["bg_primary"])

        # สร้างแถบหัวเรื่อง (จะผูก event ลากในนั้น)
        self._create_title_bar()

        # สร้างกล่องค้นหาและปุ่มควบคุม (เหมือนเดิม)
        self._create_toolbar()

        # ⭐ เพิ่มส่วนคำอธิบายแท็บ
        self._create_info_panel()

        # จัดวาง container หลัก (เหมือนเดิม)
        self.main_container = tk.Frame(self.window, bg=self.style["bg_primary"])
        self.main_container.pack(fill="both", expand=True, padx=10, pady=5)

        # --- ปรับสัดส่วน Frame ซ้ายและขวา (ลดขนาดเป็น 80%) ---
        right_frame_width = 440  # ลดจาก 550 เป็น 440 (80%) (เพิ่ม 37.5%)
        self.right_container = tk.Frame(
            self.main_container, bg=self.style["bg_primary"], width=right_frame_width
        )
        self.right_container.pack(side="right", fill="y", expand=False, padx=(5, 0))
        self.right_container.pack_propagate(False)

        # สร้างหน้าต่างด้านซ้ายสำหรับแสดงรายการ (ใช้พื้นที่ที่เหลือ) (เหมือนเดิม)
        self.left_container = tk.Frame(self.main_container, bg=self.style["bg_primary"])
        self.left_container.pack(side="left", fill="both", expand=True, padx=(0, 5))

        # สร้างพื้นที่แสดงรายการ (list) ใน left_container (เหมือนเดิม)
        self._create_card_container()  # This creates the Treeview and its Scrollbar

        # สร้างพื้นที่แสดงรายละเอียด ใน right_container (เหมือนเดิม)
        self._create_detail_panel()

        # สร้างแถบสถานะ (เหมือนเดิม)
        self._create_status_bar()

        # มุมโค้ง (ใช้ after เพื่อรอ window geometry update)
        self.window.after(100, self._apply_rounded_corners)
        # --- จบการลบ ---

    def _create_title_bar(self):
        """สร้างแถบหัวเรื่อง — แยกเป็น 2 แถว: header + section tabs"""
        bg = self.style["bg_primary"]

        # ====== ROW 1: Header — Title (left) + Pin/Close (right) ======
        self.title_bar = tk.Frame(self.window, bg=bg, height=44, cursor="fleur")
        self.title_bar.pack(fill="x", side="top", padx=8, pady=(8, 0))
        self.title_bar.pack_propagate(False)
        self.title_bar.bind("<Button-1>", self._start_move)
        self.title_bar.bind("<B1-Motion>", self._do_move)

        # -- Title text (left) --
        title_text_frame = tk.Frame(self.title_bar, bg=bg)
        title_text_frame.pack(side="left", padx=(8, 0))
        for w in [title_text_frame]:
            w.bind("<Button-1>", self._start_move)
            w.bind("<B1-Motion>", self._do_move)

        self.title_label = tk.Label(
            title_text_frame, text="NPC Manager", bg=bg,
            fg=self.style["text_primary"],
            font=(self.font, self.font_size_large_bold),
            cursor="fleur",
        )
        self.title_label.pack(side="left")
        self.title_label.bind("<Button-1>", self._start_move)
        self.title_label.bind("<B1-Motion>", self._do_move)

        self.title_sub_label = tk.Label(
            title_text_frame, text="ฐานข้อมูลตัวละคร", bg=bg,
            fg=self.style["text_secondary"],
            font=(self.font, self.font_size_xsmall),
            cursor="fleur",
        )
        self.title_sub_label.pack(side="left", padx=(10, 0), pady=(4, 0))
        self.title_sub_label.bind("<Button-1>", self._start_move)
        self.title_sub_label.bind("<B1-Motion>", self._do_move)

        # -- Controls (right): Close > Pin --
        controls_frame = tk.Frame(self.title_bar, bg=bg)
        controls_frame.pack(side="right", padx=(0, 4))

        pin_btn_size = 24
        self.close_button = tk.Button(
            controls_frame, text="×", font=(self.font, 14, "bold"),
            width=3, bg=bg, fg="#AAAAAA", bd=0, relief="flat",
            pady=2, cursor="hand2", command=self.hide_window,
        )
        self.close_button.pack(side="right", padx=(0, 2))
        self.close_button.bind(
            "<Enter>", lambda e: (
                self.close_button.config(bg="#FF3B30", fg="white")
                if self.close_button.winfo_exists() else None),
        )
        self.close_button.bind(
            "<Leave>", lambda e: (
                self.close_button.config(bg=bg, fg="#AAAAAA")
                if self.close_button.winfo_exists() else None),
        )

        self.pin_button = tk.Canvas(
            controls_frame, width=pin_btn_size, height=pin_btn_size,
            bg=bg, highlightthickness=0, cursor="hand2",
        )
        self.pin_button.pack(side="right", padx=(0, 6))
        try:
            self.pin_image = self._load_icon("pin.png", pin_btn_size)
            self.unpin_image = self._load_icon("unpin.png", pin_btn_size)
            if self.pin_image and self.unpin_image:
                self.pin_icon = self.pin_button.create_image(
                    pin_btn_size // 2, pin_btn_size // 2,
                    image=(self.pin_image if self.is_topmost else self.unpin_image),
                )
            else:
                raise ValueError("Pin/Unpin icons not loaded")
        except Exception as e:
            self.logging_manager.log_error(f"Error loading pin icons: {e}")
            self.pin_icon = self.pin_button.create_oval(
                2, 2, pin_btn_size - 2, pin_btn_size - 2,
                fill=("#FF9500" if self.is_topmost else "#AAAAAA"), outline="",
            )
        self.pin_button.bind("<Button-1>", lambda e: self._toggle_topmost())
        self.pin_button.bind(
            "<Enter>", lambda e: (
                self._highlight_button(self.pin_button)
                if self.pin_button.winfo_exists() else None),
        )
        self.pin_button.bind(
            "<Leave>", lambda e: (
                self._unhighlight_button(self.pin_button)
                if self.pin_button.winfo_exists() else None),
        )

        # ====== Divider ======
        tk.Frame(self.window, bg=self.style["bg_tertiary"], height=1).pack(
            fill="x", padx=16, pady=(4, 0))

        # ====== ROW 2: Section tabs — centered, full width ======
        self.sections_frame = tk.Frame(self.window, bg=bg)
        self.sections_frame.pack(fill="x", side="top", padx=12, pady=(6, 2))
        self._create_section_buttons()

    def _apply_rounded_corners(self):
        """ใช้ Win32 API สร้างมุมโค้งให้หน้าต่าง"""
        try:
            import ctypes
            from ctypes import wintypes
            hwnd = ctypes.windll.user32.GetParent(self.window.winfo_id())
            w = self.window.winfo_width()
            h = self.window.winfo_height()
            radius = 16
            rgn = ctypes.windll.gdi32.CreateRoundRectRgn(
                0, 0, w + 1, h + 1, radius, radius)
            ctypes.windll.user32.SetWindowRgn(hwnd, rgn, True)
        except Exception as e:
            self.logging_manager.log_error(f"Rounded corners error: {e}")

    def _start_resize(self, event):
        """เริ่มการปรับขนาดหน้าต่าง"""

        # บันทึกตำแหน่งเริ่มต้นของเมาส์ และขนาดหน้าต่างปัจจุบัน

        self._resize_start_x = event.x_root

        self._resize_start_y = event.y_root

        self._resize_start_width = self.window.winfo_width()

        self._resize_start_height = self.window.winfo_height()

        self.logging_manager.log_info("Start resizing window...")

    def _do_resize(self, event):
        """ดำเนินการปรับขนาดหน้าต่างตามการลากเมาส์"""

        try:

            # คำนวณขนาดใหม่จากตำแหน่งเมาส์ที่เปลี่ยนไป

            delta_x = event.x_root - self._resize_start_x

            delta_y = event.y_root - self._resize_start_y

            new_width = self._resize_start_width + delta_x

            new_height = self._resize_start_height + delta_y

            # ตรวจสอบขนาดขั้นต่ำ

            min_w, min_h = self.window.minsize()

            new_width = max(min_w, new_width)

            new_height = max(min_h, new_height)

            # กำหนดขนาดใหม่ให้หน้าต่าง
            self.window.geometry(f"{new_width}x{new_height}")

            # อัพเดตมุมโค้งตามขนาดใหม่
            self._apply_rounded_corners()

        except Exception as e:

            self.logging_manager.log_error(f"Error during resize: {e}")

    def _load_icon(self, icon_name, size):
        """โหลดไอคอนและปรับขนาด


        Args:

            icon_name: ชื่อไฟล์ไอคอน

            size: ขนาดที่ต้องการ


        Returns:

            PhotoImage: ไอคอนที่พร้อมใช้งาน

        """

        try:
            # โหลดและปรับขนาดไอคอน (ใช้ AssetManager ที่มี resource_path() built-in)
            return AssetManager.load_icon(icon_name, (size, size))

        except ImportError:
            # กรณีไม่มี PIL ให้ใช้ PhotoImage ธรรมดา
            try:
                from resource_utils import resource_path
                return tk.PhotoImage(file=resource_path(f"assets/{icon_name}"))
            except Exception as e:
                self.logging_manager.log_error(f"Error loading icon with Tkinter: {e}")
                return None

        except Exception as e:

            self.logging_manager.log_error(f"Error loading icon: {e}")

            return None

    def _highlight_button(self, button):
        """ไฮไลท์ปุ่มเมื่อ hover


        Args:

            button: ปุ่มที่ต้องการไฮไลท์

        """

        button.configure(bg="#333333")

    def _unhighlight_button(self, button):
        """ยกเลิกไฮไลท์ปุ่มเมื่อเมาส์ออก


        Args:

            button: ปุ่มที่ต้องการยกเลิกไฮไลท์

        """

        button.configure(bg=self.style["bg_primary"])

    def _toggle_topmost(self):
        """สลับสถานะการอยู่บนสุดของหน้าต่าง"""

        try:

            # สลับสถานะ

            self.is_topmost = not self.is_topmost

            # บันทึกค่าลงในตัวแปรกลาง

            global _topmost_state

            _topmost_state = self.is_topmost

            # ตั้งค่า topmost ของหน้าต่าง

            self.window.attributes("-topmost", self.is_topmost)

            # เปลี่ยนไอคอนตามสถานะ

            if hasattr(self, "pin_image") and hasattr(self, "unpin_image"):

                if self.is_topmost:

                    # แสดงไอคอนปักหมุด (สถานะปักหมุดแล้ว)

                    self.pin_button.itemconfig(self.pin_icon, image=self.pin_image)

                    self._update_status("ปักหมุดหน้าต่างเรียบร้อย")

                else:

                    # แสดงไอคอนยกเลิกปักหมุด (สถานะปกติ)

                    self.pin_button.itemconfig(self.pin_icon, image=self.unpin_image)

                    self._update_status("ยกเลิกการปักหมุดหน้าต่าง")

            else:

                # กรณีไม่มีไอคอน เปลี่ยนสีแทน

                if self.is_topmost:

                    self.pin_button.itemconfig(self.pin_icon, fill="#FF9500")

                    self._update_status("ปักหมุดหน้าต่างเรียบร้อย")

                else:

                    self.pin_button.itemconfig(self.pin_icon, fill="#AAAAAA")

                    self._update_status("ยกเลิกการปักหมุดหน้าต่าง")

        except Exception as e:

            self.logging_manager.log_error(f"Error toggling topmost: {e}")

    def _ensure_topmost(self):
        """ตรวจสอบและตั้งค่าให้หน้าต่างอยู่บนสุดเสมอ"""

        try:

            # ตรวจสอบหน้าต่างมีอยู่จริงและกำลังแสดงอยู่

            if (
                hasattr(self, "window")
                and self.window.winfo_exists()
                and self.window.state() != "withdrawn"
            ):

                # อ่านค่าสถานะปักหมุดจากตัวแปรกลาง

                global _topmost_state

                self.is_topmost = _topmost_state

                # บังคับให้หน้าต่างอยู่บนสุดเสมอถ้าสถานะเป็น True

                if self.is_topmost:

                    self.window.attributes("-topmost", True)

                    # ตั้งเวลาให้ตรวจสอบซ้ำอีกครั้งหลังจากแสดงหน้าต่าง (50ms)

                    self._safe_after(50, self._confirm_topmost)

                # อัพเดทไอคอนปักหมุดตามสถานะ

                if hasattr(self, "pin_icon"):

                    if self.is_topmost:

                        if hasattr(self, "pin_image"):

                            self.pin_button.itemconfig(
                                self.pin_icon, image=self.pin_image
                            )

                        else:

                            self.pin_button.itemconfig(self.pin_icon, fill="#FF9500")

                    else:

                        if hasattr(self, "unpin_image"):

                            self.pin_button.itemconfig(
                                self.pin_icon, image=self.unpin_image
                            )

                        else:

                            self.pin_button.itemconfig(self.pin_icon, fill="#AAAAAA")

        except Exception as e:

            self.logging_manager.log_error(f"Error in ensure_topmost: {e}")

    def _confirm_topmost(self):
        """ตรวจสอบซ้ำว่าหน้าต่างอยู่บนสุดจริงๆ"""

        try:

            if (
                self.is_topmost
                and hasattr(self, "window")
                and self.window.winfo_exists()
            ):

                # บังคับให้หน้าต่างอยู่บนสุดเสมออีกครั้ง

                self.window.attributes("-topmost", True)

                # บังคับให้หน้าต่างได้รับโฟกัส (ใช้ safe method)

                self._safe_focus_force()

        except Exception as e:

            self.logging_manager.log_error(f"Error in confirm_topmost: {e}")

    def _create_section_buttons(self):
        """สร้างปุ่มเลือก section (ปรับขนาดฟอนต์)"""

        sections = [
            ("MAIN", "main_characters"),
            ("NPCS", "npcs"),
            ("LORE", "lore"),
            ("ROLES", "character_roles"),
            ("แก้คำผิด(auto)", "word_fixes"),
        ]

        # สร้าง frame ใส่ปุ่ม (เหมือนเดิม)

        buttons_container = tk.Frame(self.sections_frame, bg=self.style["bg_primary"])

        buttons_container.pack(expand=True)

        # เก็บปุ่มไว้ในพจนานุกรม (เหมือนเดิม)

        self.section_buttons = {}

        self.section_indicators = {}

        # สร้างปุ่มแต่ละส่วน

        for text, section in sections:

            button_frame = tk.Frame(
                buttons_container, bg=self.style["bg_primary"], padx=4  # เพิ่ม padx
            )

            button_frame.pack(side="left")

            # สร้าง Frame สำหรับใส่ปุ่มและตัวบ่งชี้ (เหมือนเดิม)

            inner_frame = tk.Frame(button_frame, bg=self.style["bg_primary"])

            inner_frame.pack(fill="both", expand=True)

            btn = tk.Button(
                inner_frame,
                text=text,
                # *** ปรับขนาดฟอนต์ ***
                font=(self.font, self.font_size_medium),  # ใช้ขนาดกลาง
                bg=self.style["bg_tertiary"],
                fg=self.style["text_primary"],
                bd=0,
                highlightthickness=0,
                relief="flat",
                padx=16,
                pady=6,
                command=lambda s=section: self.show_section(s),
            )

            btn.pack(fill="both", expand=True)

            # สร้างตัวบ่งชี้แบบใหม่ที่เด่นชัดมากขึ้น

            indicator = tk.Label(
                inner_frame,
                text="0",
                # *** ปรับขนาดฟอนต์ ***
                font=(self.font, self.font_size_xsmall_bold),  # ขนาดเล็ก หนา
                bg="#FFD700",  # เปลี่ยนเป็นสีเหลืองทองเหมือนตัวอักษรค้นหา
                fg="#000000",  # เปลี่ยนสีตัวอักษรเป็นสีดำเพื่อให้เห็นชัดบนพื้นสีทอง
                padx=6,  # เพิ่ม padding
                pady=2,  # เพิ่ม padding
                relief="flat",
                bd=0,
                highlightthickness=0,
            )

            # ตำแหน่ง indicator (เหมือนเดิม แต่ปรับ y เล็กน้อย)

            indicator.place(relx=1.0, rely=0, anchor="ne", x=-4, y=4)

            indicator.pack_forget()  # ซ่อนตัวบ่งชี้เริ่มต้น

            # เพิ่ม hover effects (เหมือนเดิม)

            btn.bind("<Enter>", lambda e, b=btn: self._on_section_button_hover(b))

            btn.bind("<Leave>", lambda e, b=btn: self._on_section_button_leave(b))

            # เก็บปุ่มและตัวบ่งชี้ไว้ในพจนานุกรม (เหมือนเดิม)

            self.section_buttons[section] = btn

            self.section_indicators[section] = indicator

    def _update_section_description(self, section):
        """อัพเดตคำอธิบายตามแท็บที่เลือก"""
        if hasattr(self, "section_description_label"):
            description = self.section_descriptions.get(
                section, 
                "เลือกแท็บเพื่อดูคำอธิบาย"
            )
            self.section_description_label.configure(text=description)

    def _create_toolbar(self):
        """สร้างแถบเครื่องมือและกล่องค้นหา"""

        # Divider ระหว่าง tabs กับ toolbar
        tk.Frame(self.window, bg=self.style["bg_tertiary"], height=1).pack(
            fill="x", padx=16, pady=(2, 0))

        self.toolbar = tk.Frame(
            self.window, bg=self.style["bg_primary"],
            height=40, cursor="fleur",
        )
        self.toolbar.pack(fill="x", side="top", padx=12, pady=(6, 4))

        # เพิ่ม binding การลากหน้าต่างกับ toolbar
        self.toolbar.bind("<Button-1>", self._start_move)
        self.toolbar.bind("<B1-Motion>", self._do_move)

        # สร้างกล่องค้นหา (ด้านซ้าย) (เหมือนเดิม)
        search_frame = tk.Frame(self.toolbar, bg=self.style["bg_primary"])
        search_frame.pack(side="left", fill="y", padx=(0, 10))  # เพิ่ม padx ขวา

        # ทำให้ search_frame ไม่รับ event ลากหน้าต่าง
        def _stop_propagation(event):
            return "break"

        search_frame.bind("<Button-1>", _stop_propagation)
        search_frame.bind("<B1-Motion>", _stop_propagation)

        # สร้างกล่องค้นหาแบบมีขอบมน (เหมือนเดิม)
        search_container = tk.Frame(
            search_frame,
            bg=self.style["bg_tertiary"],
            height=32,  # ลดจาก 40 เป็น 32
            padx=10,  # ลดจาก 12 เป็น 10
            pady=4,  # ลดจาก 6 เป็น 4
        )
        search_container.pack(fill="x", expand=True)

        # ไอคอนค้นหา
        search_icon = tk.Label(
            search_container,
            text="🔍",
            bg=self.style["bg_tertiary"],
            fg=self.style["text_secondary"],
            # *** ปรับขนาดฟอนต์ ***
            font=(self.font, self.font_size_medium),  # ใช้ขนาดกลาง
        )
        search_icon.pack(side="left", padx=(0, 8))  # เพิ่ม padx ขวา

        # ช่องค้นหา (เหมือนเดิม)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self._on_search_change)

        self.search_entry = tk.Entry(
            search_container,
            textvariable=self.search_var,
            bg=self.style["bg_tertiary"],
            fg="#FFD700",  # เปลี่ยนสีข้อความเป็นสีเหลืองทอง (Gold)
            insertbackground="#FFD700",  # เปลี่ยนสี cursor เป็นสีเหลืองทองเช่นกัน
            # *** ปรับขนาดฟอนต์ ***
            font=(self.font, self.font_size_medium),  # ใช้ขนาดกลาง
            relief="flat",
            bd=0,
            highlightthickness=0,
            width=20,  # ลดขนาดความกว้างจาก 30 เป็น 20
        )
        self.search_entry.pack(
            side="left", fill="both", expand=True, padx=0
        )  # ใช้ fill="both"

        # ปุ่มล้างการค้นหา
        self.clear_search_btn = tk.Button(
            search_container,
            text="✕",
            bg=self.style["bg_tertiary"],
            fg=self.style["text_secondary"],
            # *** ปรับขนาดฟอนต์ ***
            font=(self.font, self.font_size_small),  # ใช้ขนาดเล็ก
            bd=0,
            highlightthickness=0,
            command=self._clear_search,
        )
        self.clear_search_btn.pack(side="left", padx=(8, 0))  # เพิ่ม padx ซ้าย
        self.clear_search_btn.pack_forget()  # ซ่อนไว้ก่อน

        # สร้างปุ่มด้านขวา (เหมือนเดิม - อาจจะใส่ปุ่ม Save หรือ Add ตรงนี้แทน panel ขวาในอนาคต)
        # สร้าง container สำหรับปุ่มและ warning
        self.button_container = tk.Frame(self.toolbar, bg=self.style["bg_primary"])
        self.button_container.pack(side="right", fill="y")

        button_frame = tk.Frame(self.button_container, bg=self.style["bg_primary"])
        button_frame.pack(side="top", fill="x")

        # ทำให้ button_frame ไม่รับ event ลากหน้าต่าง
        button_frame.bind("<Button-1>", _stop_propagation)
        button_frame.bind("<B1-Motion>", _stop_propagation)

        # เพิ่มปุ่ม More แบบ dropdown
        self.more_btn = tk.Button(
            button_frame,
            text="More ▼",
            font=(self.font, self.font_size_small),
            bg="#222222",  # สีเทาเข้มของ UI
            fg="white",
            bd=0,
            relief="flat",
            padx=8,
            pady=3,
            command=self._show_more_menu,
            cursor="hand2",
        )
        self.more_btn.pack(side="right", padx=(2, 0))

        # เพิ่ม hover effect สำหรับปุ่ม More
        self.more_btn.bind(
            "<Enter>",
            lambda e: (
                self.more_btn.configure(bg="#2a2a2a")
                if self.more_btn.winfo_exists()
                else None
            ),
        )
        self.more_btn.bind(
            "<Leave>",
            lambda e: (
                self.more_btn.configure(bg="#222222")
                if self.more_btn.winfo_exists()
                else None
            ),
        )

        # สร้าง dropdown menu (ซ่อนไว้เริ่มต้น)
        self.more_menu = None

    def _create_card_container(self):
        """สร้างพื้นที่สำหรับแสดงรายการข้อมูลโดยใช้ ttk.Treeview (ปรับขนาดฟอนต์)"""

        # สร้าง frame หลักสำหรับใส่รายการ (เหมือนเดิม)

        self.card_container_frame = tk.Frame(
            self.left_container, bg=self.style["bg_primary"]
        )

        self.card_container_frame.pack(fill="both", expand=True)

        # สร้าง frame สำหรับ Treeview และ Scrollbar (เหมือนเดิม)

        list_frame = tk.Frame(self.card_container_frame, bg=self.style["bg_primary"])

        list_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # กำหนดสไตล์ให้ Treeview และ Scrollbar (ปรับสีให้เข้ากับธีม)
        style = ttk.Style()
        style.theme_use("clam")  # ต้องตั้ง theme ก่อน

        # กำหนดสไตล์ Scrollbar แบบ Dark Flat
        style.configure(
            "Vertical.TScrollbar",
            background="#2a2a2a",  # สีปุ่ม scroll
            troughcolor="#222222",  # พื้นหลัง trough
            bordercolor="#222222",  # สีขอบ
            arrowcolor="#222222",  # ซ่อนลูกศร (ใช้สีเดียวกับพื้น)
            darkcolor="#2a2a2a",  # สีเงา (ทำให้เท่ากับ background เพื่อไม่มีขยัก)
            lightcolor="#2a2a2a",  # สีไฮไลท์ (ทำให้เท่ากับ background เพื่อไม่มีขยัก)
            borderwidth=2,  # ขอบ
            relief="flat",
            arrowsize=6,  # ลูกศร
        )

        # กำหนดสีเมื่อ hover และกด (สว่างขึ้น 30%)
        style.map(
            "Vertical.TScrollbar",
            background=[
                ("active", "#9C9C9C"),  # สีเทาสว่างขึ้น 30% เมื่อ hover
                ("pressed", "#7D7D7D"),  # สีเมื่อกดค้าง
            ],
            darkcolor=[
                ("active", "#6D6D6D"),  # ปรับสีเงาให้เท่ากันเพื่อความเรียบ
                ("pressed", "#7D7D7D"),
            ],
            lightcolor=[
                ("active", "#6D6D6D"),  # ปรับสีไฮไลท์ให้เท่ากันเพื่อความเรียบ
                ("pressed", "#7D7D7D"),
            ],
        )

        # สร้าง Scrollbar
        tree_scrollbar = ttk.Scrollbar(list_frame, orient="vertical")
        tree_scrollbar.pack(side="right", fill="y")

        # กำหนดสไตล์ Treeview

        # *** ปรับขนาดฟอนต์ และ rowheight ***

        style.configure(
            "Treeview",
            background=self.style["bg_primary"],
            foreground=self.style["text_primary"],
            fieldbackground=self.style["bg_primary"],
            rowheight=int(self.font_size * 1.8),  # ปรับความสูงแถวตามขนาดฟอนต์
            font=(self.font, self.font_size_medium),
        )  # ปรับ font size ของ item

        style.map("Treeview", background=[("selected", self.style["accent"])])

        # *** ปรับขนาดฟอนต์ และ padding ของ Header ***

        style.configure(
            "Treeview.Heading",
            background="#000000",  # สีดำสำหรับ header
            foreground=self.style["text_primary"],  # ข้อความสีขาว
            font=(self.font, self.font_size_small, "bold"),  # ฟอนต์ตัวหนา
            borderwidth=0,  # ลบเส้นขอบ
            relief="flat",  # ไม่มีเอฟเฟกต์ขอบ
            padding=(15, 8),
        )  # เพิ่ม padding ให้ header
        
        # ลบ hover effect ของ header
        style.map("Treeview.Heading",
            background=[('active', '#000000')],  # คงสีดำเมื่อ hover
            foreground=[('active', self.style["text_primary"])],  # คงสีข้อความเมื่อ hover
        )

        style.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])

        # สร้าง Treeview (เหมือนเดิม)

        self.tree = ttk.Treeview(
            list_frame,
            columns=("Name", "Type"),
            show="headings",
            yscrollcommand=tree_scrollbar.set,
            selectmode="browse",
        )

        tree_scrollbar.config(command=self.tree.yview)

        # กำหนดหัวข้อคอลัมน์ (เหมือนเดิม)

        self.tree.heading("Name", text="NAME", anchor="w")

        self.tree.heading("Type", text="TYPE", anchor="w")

        # กำหนดความกว้างคอลัมน์ (ปรับสัดส่วนได้ - อาจต้องปรับค่า width เริ่มต้น)

        self.tree.column(
            "Name",
            width=280,
            minwidth=100,  # กำหนดความกว้างขั้นต่ำ
            stretch=tk.YES,  # อนุญาตให้ปรับขนาด
            anchor="w",  # ⭐ ลดจาก 400 เป็น 280 (ลด 30%)
        )  # เพิ่ม width เริ่มต้น

        self.tree.column(
            "Type", 
            width=200, 
            minwidth=80,  # กำหนดความกว้างขั้นต่ำ
            stretch=tk.YES,  # เปลี่ยนให้ปรับขนาดได้
            anchor="w"
        )  # เพิ่ม width เริ่มต้น

        self.tree.pack(side="left", fill="both", expand=True)

        # --- ผูก Event --- (เหมือนเดิม)

        self.tree.bind("<<TreeviewSelect>>", self._on_treeview_select)

        self.tree.bind("<Double-1>", self._on_treeview_double_click)

        # frame สำหรับแสดงรายละเอียด (เหมือนเดิม)

        self.card_detail_frame = tk.Frame(
            self.card_container_frame, bg=self.style["bg_primary"]
        )

        # เก็บรายการ Treeview items (เหมือนเดิม)

        self.tree_items = {}

    def _populate_treeview(self, items):
        """เพิ่มข้อมูลลงใน Treeview แบบแบ่งชุดเพื่อป้องกัน UI ค้าง"""
        # ล้างข้อมูลเก่าใน Treeview - ใช้วิธีที่มีประสิทธิภาพดีกว่า
        try:
            children = self.tree.get_children()
            if children:
                # ลบทั้งหมดในครั้งเดียวแทนการลูปทีละตัว
                self.tree.delete(*children)
            self.tree_items.clear()
        except tk.TclError as e:
            self.logging_manager.log_error(f"Error clearing treeview: {e}")
            self.tree_items = {}

        # เพิ่มรายการแบบแบ่งชุด - ลด batch size เพื่อป้องกัน freeze
        BATCH_SIZE = 25  # ลดจาก 50 เป็น 25 เพื่อ responsive มากขึ้น

        def add_batch(start_idx=0):
            # ตรวจสอบว่ายังมีรายการเหลืออยู่หรือไม่
            if start_idx >= len(items):
                # เสร็จสิ้นการเพิ่มรายการทั้งหมด - ใช้ after_idle แทน
                self.window.after_idle(lambda: None)  # เพิ่มจาก update_idletasks()
                return

            # กำหนดขอบเขตรายการในชุดปัจจุบัน
            end_idx = min(start_idx + BATCH_SIZE, len(items))
            batch_items = items[start_idx:end_idx]

            # เพิ่มรายการในชุดปัจจุบัน
            for item_data in batch_items:
                name = ""
                item_type = ""

                # กำหนดชื่อและประเภทตาม section
                if self.current_section == "main_characters":
                    name = item_data.get("firstName", "")
                    if item_data.get("lastName"):
                        name += f" {item_data.get('lastName')}"
                    item_type = item_data.get("gender", "")
                elif self.current_section == "npcs":
                    name = item_data.get("name", "")
                    item_type = item_data.get("role", "")
                elif self.current_section in ["lore", "character_roles", "word_fixes"]:
                    name = item_data.get("key", "")

                    if self.current_section == "lore":
                        item_type = "Lore"
                    elif self.current_section == "character_roles":
                        item_type = "Role"
                    else:
                        item_type = "Fix"
                else:
                    continue  # ข้าม section ที่ไม่รู้จัก

                # เพิ่มแถวลงใน Treeview และเก็บข้อมูล
                iid = self.tree.insert("", "end", text=name, values=(name, item_type))
                self.tree_items[iid] = item_data  # เก็บข้อมูลเต็มๆ ไว้

            # ตั้งเวลาเพิ่มชุดถัดไป - เพิ่มเวลาเล็กน้อยเพื่อให้ UI responsive
            self.window.after(5, lambda: add_batch(end_idx))  # เพิ่มจาก 1ms เป็น 5ms

        # เริ่มเพิ่มรายการชุดแรก (ถ้ามีรายการ)
        if items:
            add_batch()

    def _create_cards_for_section(self, search_term=None):
        """กรองข้อมูลและแสดงผลใน Treeview"""
        # แสดงสถานะว่ากำลังโหลดข้อมูล
        self._update_status(f"กำลังโหลดข้อมูล...")

        # เพิ่ม: อัพเดต UI ก่อนเริ่มงานหนัก
        self.window.update_idletasks()

        # ตรวจสอบข้อมูลพื้นฐาน
        if not self.current_section or self.current_section not in self.data:
            self._populate_treeview([])  # แสดง Treeview ว่างๆ
            self._update_status("ไม่มีข้อมูลสำหรับส่วนนี้")
            self.item_count_text.configure(text="0 รายการ")
            return

        section_data = self.data[self.current_section]
        filtered_items = []
        cache_key = f"{self.current_section}__{search_term or 'all'}"

        # ตรวจสอบแคช
        if hasattr(self, "_search_cache") and cache_key in self._search_cache:
            filtered_items = self._search_cache[cache_key]
        else:
            # กรองข้อมูล
            if isinstance(section_data, list):
                for item in section_data:
                    if not search_term or any(
                        search_term in str(v).lower() for v in item.values()
                    ):
                        filtered_items.append(item)
            elif isinstance(section_data, dict):
                for key, value in section_data.items():
                    if (
                        not search_term
                        or search_term in key.lower()
                        or search_term in str(value).lower()
                    ):
                        filtered_items.append({"key": key, "value": value})

            # บันทึกลงแคช
            if not hasattr(self, "_search_cache"):
                self._search_cache = {}
            self._search_cache[cache_key] = filtered_items

        # เรียงลำดับ
        try:
            if self.current_section in ["main_characters", "npcs"]:
                key_field = (
                    "firstName" if self.current_section == "main_characters" else "name"
                )
                filtered_items.sort(key=lambda x: x.get(key_field, "").lower())
            elif self.current_section in ["lore", "character_roles", "word_fixes"]:
                filtered_items.sort(key=lambda x: x.get("key", "").lower())
        except Exception as e:
            self.logging_manager.log_error(f"Error sorting items: {e}")

        # เพิ่ม: อัพเดต UI ก่อนเพิ่มรายการ
        self.window.update_idletasks()

        # เรียก _populate_treeview (ที่ปรับปรุงแล้ว)
        self._populate_treeview(filtered_items)

        # อัพเดทสถานะและจำนวนรายการ
        total_matches = len(filtered_items)
        section_title = self.current_section.replace("_", " ").title()
        if total_matches == 0:
            status_msg = (
                f"ไม่พบรายการสำหรับ '{search_term}'"
                if search_term
                else f"ไม่มีรายการใน {section_title}"
            )
            self._update_status(status_msg)
        else:
            status_msg = (
                f"พบ {total_matches} รายการสำหรับ '{search_term}' ใน {section_title}"
                if search_term
                else f"กำลังแสดง {total_matches} รายการใน {section_title}"
            )
            self._update_status(status_msg)

        self.item_count_text.configure(text=f"{total_matches} รายการ")

        # เพิ่ม: อัพเดต UI หลังจากเสร็จสิ้น
        self.window.update_idletasks()

    def _on_treeview_select(self, event):
        """จัดการเมื่อมีการเลือกรายการใน Treeview"""
        # เคลียร์ focus timer ก่อนทุกครั้ง
        if hasattr(self, "_focus_after_id") and self._focus_after_id:
            try:
                self._safe_after_cancel(self._focus_after_id)
            except:
                pass
            self._focus_after_id = None

        selected_item_ids = self.tree.selection()  # อาจมีหลายรายการถ้า selectmode เปลี่ยน

        if not selected_item_ids:
            self._hide_detail_form()  # ซ่อน panel ถ้าไม่มีอะไรถูกเลือก
            return

        selected_iid = selected_item_ids[0]  # เอาเฉพาะรายการแรกที่เลือก

        if selected_iid in self.tree_items:
            item_data = self.tree_items[selected_iid]

            # เพิ่ม: ตรวจสอบข้อมูลล่าสุดจาก self.data
            fresh_data = None

            # ดึงข้อมูลล่าสุดตามประเภทของ section
            if self.current_section in ["main_characters", "npcs"]:
                id_field = (
                    "firstName" if self.current_section == "main_characters" else "name"
                )
                id_value = item_data.get(id_field)

                if id_value:
                    for item in self.data.get(self.current_section, []):
                        if item.get(id_field) == id_value:
                            fresh_data = item
                            break
            elif self.current_section in ["lore", "character_roles", "word_fixes"]:
                key = item_data.get("key")
                if key and key in self.data.get(self.current_section, {}):
                    value = self.data[self.current_section][key]
                    fresh_data = {"key": key, "value": value}

            # ใช้ข้อมูลล่าสุด (ถ้ามี) หรือใช้ข้อมูลจาก tree_items
            data_to_show = fresh_data if fresh_data else item_data

            # อัพเดต tree_items ด้วยข้อมูลล่าสุด (ถ้ามี)
            if fresh_data:
                self.tree_items[selected_iid] = fresh_data

            # ⭐ แก้ไข: ให้ทุกแท็บแสดงในโหมด "ดู" ก่อน ไม่เข้าสู่โหมดแก้ไขทันที
            self._show_card_detail(data_to_show)  # ใช้ _show_card_detail สำหรับทุกแท็บ

            # ⭐ อัปเดตปุ่มตามสถานะการเลือก
            self._update_button_for_selection(selected_item_ids)
        else:
            self.logging_manager.log_error(
                f"Selected item data not found for iid: {selected_iid}"
            )
            self._hide_detail_form()

    def _update_button_for_selection(self, selected_items):
        """อัปเดตปุ่มตามสถานะการเลือกรายการ"""
        try:
            if (
                not hasattr(self, "save_edit_btn")
                or not self.save_edit_btn.winfo_exists()
            ):
                return

            # ถ้าไม่ได้อยู่ในโหมดแก้ไข และมีการเลือกรายการ
            if (
                not hasattr(self, "current_edit_data") or not self.current_edit_data
            ) and selected_items:
                # แสดงปุ่ม EDIT
                if self.save_edit_btn.cget("text") != "EDIT":
                    self.save_edit_btn.configure(
                        text="EDIT", command=self._edit_selected_item
                    )
            elif not selected_items:
                # ไม่มีการเลือกรายการ - แสดงปุ่ม ADD ENTRY
                if self.save_edit_btn.cget("text") != "ADD ENTRY":
                    self.save_edit_btn.configure(
                        text="ADD ENTRY", command=self._quick_add_new_entry
                    )

        except Exception as e:
            self.logging_manager.log_error(f"Error updating button for selection: {e}")

    def _on_treeview_double_click(self, event):
        """จัดการเมื่อมีการดับเบิลคลิกรายการใน Treeview (ทำเหมือนกด Edit)"""

        selected_item_ids = self.tree.selection()

        if not selected_item_ids:

            return

        selected_iid = selected_item_ids[0]

        if selected_iid in self.tree_items:

            item_data = self.tree_items[selected_iid]

            self._on_card_edit(item_data)  # เรียกฟังก์ชันแก้ไข

        else:

            self.logging_manager.log_error(
                f"Double-clicked item data not found for iid: {selected_iid}"
            )

    def _create_list_header(self):
        """สร้างส่วนหัวของรายการแสดงผล"""

        header_frame = tk.Frame(
            self.list_container, bg=self.style["bg_tertiary"], height=30
        )

        header_frame.pack(fill="x", pady=(0, 5))

        # ทำให้ความสูงคงที่

        header_frame.pack_propagate(False)

        # สร้างฟิลด์สำหรับแต่ละส่วน

        columns = [("NAME", 3), ("TYPE", 1), ("ACTIONS", 1)]  # ส่วนชื่อใช่พื้นที่มากกว่า

        for i, (column, weight) in enumerate(columns):

            col_frame = tk.Frame(header_frame, bg=self.style["bg_tertiary"])

            col_frame.pack(side="left", fill="both", expand=True, padx=5)

            if column == "ACTIONS":

                col_frame.pack(
                    side="right", fill="both", expand=False, padx=5, ipadx=20
                )

            label = tk.Label(
                col_frame,
                text=column,
                font=(self.font, 10, "bold"),
                bg=self.style["bg_tertiary"],
                fg=self.style["text_secondary"],
                anchor="w",
            )

            label.pack(side="left", padx=5)

    def _create_detail_panel(self):
        """สร้างพื้นที่แสดงรายละเอียดด้านขวา (ปรับปรุง Layout ด้วย Grid)"""
        self.detail_panel = tk.Frame(
            self.right_container,
            bg=self.style["bg_secondary"],
            highlightbackground=self.style["bg_tertiary"],
            highlightthickness=1,
        )
        self.detail_panel.pack(fill="both", expand=True)

        # กำหนด layout แบบ grid สำหรับ detail_panel
        self.detail_panel.grid_rowconfigure(1, weight=1)  # แถว content ขยายได้
        self.detail_panel.grid_columnconfigure(0, weight=1)  # คอลัมน์ขยายได้

        # --- Title Container (ใช้ grid แถว 0) ---
        title_container = tk.Frame(self.detail_panel, bg=self.style["bg_secondary"])
        title_container.grid(row=0, column=0, sticky="ew", pady=(20, 10))
        self.detail_title = tk.Label(
            title_container,
            text="DETAILS",
            font=(self.font, self.font_size_large_bold),
            bg=self.style["bg_secondary"],
            fg=self.style["text_primary"],
        )
        self.detail_title.pack()  # Pack ภายใน title_container

        # --- Content Frame (ใช้ grid แถว 1 - พื้นที่หลัก) ---
        # Frame นี้จะใช้บรรจุ CardView หรือ detail_form_frame
        self.detail_content_frame = tk.Frame(
            self.detail_panel, bg=self.style["bg_secondary"]
        )
        self.detail_content_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        self.detail_content_frame.grid_rowconfigure(
            0, weight=1
        )  # Allow content (Card or Form) to expand vertically
        self.detail_content_frame.grid_columnconfigure(
            0, weight=1
        )  # Allow content to expand horizontally

        # --- Button Container (ใช้ grid แถว 2) ---
        self.button_container = tk.Frame(
            self.detail_panel, bg=self.style["bg_secondary"]
        )
        self.button_container.grid(row=2, column=0, sticky="ew", pady=(10, 20), padx=20)

        # สร้างปุ่ม (แต่ยังไม่ pack/grid) - จะถูกจัดการโดย _show_..., _on_card_edit, _hide_detail_form
        self.save_edit_btn = tk.Button(
            self.button_container,
            text="ADD ENTRY",  # Default text
            bg=self.style["accent"],
            fg="white",
            font=(self.font, self.font_size_small),  # 🎨 เปลี่ยนจาก medium เป็น small
            bd=0,
            relief="flat",
            highlightthickness=0,
            padx=8,  # 🎨 ลดจาก 6 เป็น 8 (เพิ่มขึ้นเล็กน้อยเพื่อให้สมดุล)
            pady=4,  # 🎨 ลดจาก 6 เป็น 4 (เล็กลง)
            command=self._quick_add_new_entry,  # Default command
        )
        # ผูก hover effect (ทำครั้งเดียวตอนสร้าง)
        self.save_edit_btn.bind(
            "<Enter>",
            lambda e, btn=self.save_edit_btn: btn.configure(
                bg=self.style["accent_hover"]
            ),
        )
        self.save_edit_btn.bind(
            "<Leave>",
            lambda e, btn=self.save_edit_btn: btn.configure(bg=self.style["accent"]),
        )

        # สร้าง frame สำหรับฟอร์ม (แต่ยังไม่ pack/grid)
        # ฟอร์มจริงๆ จะถูกสร้างใน _create_detail_form_for_section และแสดงผลตามต้องการ
        self.detail_form_frame = tk.Frame(
            self.detail_content_frame, bg=self.style["bg_secondary"]
        )
        self.detail_form_elements = {}
        self.current_detail_widget = (
            None  # Track what is currently shown in content frame
        )

    def _clear_detail_content_frame(self):
        """ล้าง widget ทั้งหมดใน detail_content_frame โดยใช้ระบบจัดการใหม่"""

        # 🔧 ใช้ระบบจัดการ timer และ focus ใหม่
        # ยกเลิก pending timers ทั้งหมดที่อาจทำให้ freeze
        timer_cancelled = False
        if hasattr(self, "_focus_after_id") and self._focus_after_id:
            self._safe_after_cancel(self._focus_after_id)
            self._focus_after_id = None
            timer_cancelled = True

        # Force release focus และ grab ก่อนล้าง widgets
        self._force_ui_unlock()

        # Clear form elements อย่างปลอดภัย
        if hasattr(self, "detail_form_elements") and self.detail_form_elements:
            elements_to_clear = list(self.detail_form_elements.items())
            self.detail_form_elements.clear()  # Clear reference ก่อน

            for field_name, widget_var in elements_to_clear:
                try:
                    # ตรวจสอบว่า widget ยังอยู่และไม่ถูก focus อยู่
                    if (
                        hasattr(widget_var, "winfo_exists")
                        and widget_var.winfo_exists()
                    ):
                        # ถ้า widget นี้กำลังถูก focus อยู่ ให้ย้าย focus ออกก่อน
                        try:
                            if widget_var == widget_var.focus_get():
                                self.window.after_idle(lambda: self.window.focus_set())
                        except tk.TclError:
                            pass  # widget ไม่มีอยู่แล้ว

                        # Destroy widget โดยตรง (events จะถูกลบอัตโนมัติ)
                        widget_var.destroy()

                except Exception as e:
                    self.logging_manager.log_warning(
                        f"Error clearing widget {field_name}: {e}"
                    )

        # 🎯 ขั้นตอนที่ 4: Reset state variables อย่างสมบูรณ์
        self.current_detail_widget = None
        # ⭐ เอาออก: ไม่ควรรีเซ็ต current_edit_data ที่นี่ เพราะอาจทำให้โหมดแก้ไขหายไป
        # if hasattr(self, "current_edit_data"):
        #     self.current_edit_data = None
        # if hasattr(self, "has_actual_changes"):
        #     self.has_actual_changes = False

        # 🎯 ขั้นตอนที่ 5: ตรวจสอบและจัดการ detail_content_frame
        if not (
            hasattr(self, "detail_content_frame")
            and self.detail_content_frame.winfo_exists()
        ):
            self.logging_manager.log_warning(
                "detail_content_frame missing, recreating..."
            )
            if hasattr(self, "detail_panel") and self.detail_panel.winfo_exists():
                self.detail_content_frame = tk.Frame(
                    self.detail_panel, bg=self.style["bg_secondary"]
                )
                self.detail_content_frame.grid(
                    row=1, column=0, sticky="nsew", padx=10, pady=5
                )
                self.detail_content_frame.grid_rowconfigure(0, weight=1)
                self.detail_content_frame.grid_columnconfigure(0, weight=1)
            else:
                return

        # 🎯 ขั้นตอนที่ 6: ล้าง remaining widgets อย่างระมัดระวัง
        try:
            children_list = list(self.detail_content_frame.winfo_children())
            for widget in children_list:
                try:
                    if widget.winfo_exists():
                        # ตรวจสอบว่าไม่ใช่ widget ที่กำลัง focus อยู่
                        try:
                            if widget == widget.focus_get():
                                self.window.after_idle(lambda: self.window.focus_set())
                        except (tk.TclError, AttributeError):
                            pass  # widget ไม่มีอยู่แล้ว หรือไม่มี focus
                        widget.destroy()
                except Exception as e:
                    self.logging_manager.log_warning(
                        f"Error destroying remaining widget: {e}"
                    )
        except Exception as e:
            self.logging_manager.log_error(f"Error clearing content frame: {e}")

        # 🎯 ขั้นตอนที่ 7: Clear reference เพื่อป้องกัน "bad window path name"
        if hasattr(self, "detail_form_frame"):
            self.detail_form_frame = None
            self.logging_manager.log_info("Cleared detail_form_frame reference")

        # 🎯 ขั้นตอนที่ 8: Ensure window is responsive
        try:
            # Force UI update แบบปลอดภัย - ใช้ after_idle แทน update()
            self.window.update_idletasks()
            # self.window.update()  # ปิดการใช้ update() เพื่อป้องกัน UI freeze

            # เปิดใช้งาน window interaction
            self.window.config(cursor="")

            if timer_cancelled:
                self.logging_manager.log_info(
                    "Content frame cleared successfully with timer cancelled"
                )
            else:
                self.logging_manager.log_info("Content frame cleared successfully")

        except Exception as e:
            self.logging_manager.log_warning(
                f"Error ensuring window responsiveness: {e}"
            )

    def _create_status_bar(self):
        """สร้างแถบสถานะด้านล่าง และ Resize Grip"""

        # สร้าง frame สำหรับแถบสถานะ
        self.status_bar = tk.Frame(self.window, bg=self.style["bg_tertiary"], height=35)
        self.status_bar.pack(side="bottom", fill="x")
        self.status_bar.pack_propagate(False)

        # ข้อความสถานะด้านซ้าย (เหมือนเดิม)
        self.status_text = tk.Label(
            self.status_bar,
            text="Ready",
            bg=self.style["bg_tertiary"],
            fg=self.style["text_secondary"],
            font=(self.font, self.font_size_small),
        )
        self.status_text.pack(side="left", padx=15)

        # --- สร้าง Resize Grip ---
        resize_icon_size = 20  # ขนาดไอคอน
        try:
            from PIL import Image, ImageTk

            self.resize_icon_image = AssetManager.load_icon(
                "resize.png", (resize_icon_size, resize_icon_size)
            )

            if not self.resize_icon_image:
                raise ValueError("Failed to load resize.png")

            # สร้าง Label สำหรับแสดงไอคอนและรับ Event
            self.resize_grip = tk.Label(
                self.window,
                image=self.resize_icon_image,
                # --- [จุดแก้ไข] ---
                # เปลี่ยนสีพื้นหลังให้ตรงกับสีของ status_bar
                bg=self.style["bg_tertiary"],
                cursor="sizing",
            )
            # ใช้ place วางที่มุมขวาล่างของ self.window
            self.resize_grip.place(relx=1.0, rely=1.0, anchor="se")

            # ผูก Event การลากเพื่อปรับขนาด
            self.resize_grip.bind("<Button-1>", self._start_resize)
            self.resize_grip.bind("<B1-Motion>", self._do_resize)

            # ทำให้ resize_grip อยู่เหนือ status_bar
            self.resize_grip.lift(self.status_bar)

        except Exception as e:
            self.logging_manager.log_error(f"Could not create resize grip: {e}")
            self.resize_grip = None

        # --- จำนวนรายการด้านขวา (Pack ก่อน Resize Grip) ---
        self.item_count_text = tk.Label(
            self.status_bar,
            text="0 items",
            bg=self.style["bg_tertiary"],
            fg=self.style["text_secondary"],
            font=(self.font, self.font_size_small),
        )
        # Pack ชิดขวา และเพิ่ม padding ให้มีที่ว่างสำหรับ resize grip
        self.item_count_text.pack(side="right", padx=30)

    def _get_npc_file_path(self):
        """
        Returns the standardized path to the NPC data file using the central utility.
        """
        return get_npc_file_path()

    def _get_backup_dir(self):
        """คืนค่าพาธโฟลเดอร์ backup ที่อยู่ข้าง npc.json"""
        npc_file_path = self._get_npc_file_path()
        return os.path.join(os.path.dirname(npc_file_path), "backups")

    def _create_backup(self):
        """สร้างไฟล์สำรอง npc.json พร้อม rotation (เก็บสูงสุด 10 ไฟล์)

        Returns:
            bool: True หากสร้างสำเร็จ
        """
        MAX_BACKUPS = 10
        try:
            npc_file_path = self._get_npc_file_path()
            if not os.path.exists(npc_file_path):
                self.logging_manager.log_info("ไม่พบไฟล์ NPC สำหรับการสำรอง")
                return False

            backup_dir = self._get_backup_dir()
            os.makedirs(backup_dir, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = os.path.join(backup_dir, f"NPC_{timestamp}.json")

            shutil.copy2(npc_file_path, backup_filename)
            self.logging_manager.log_info(f"Backup created: {backup_filename}")

            # Rotation — ลบไฟล์เก่าเกิน MAX_BACKUPS
            self._rotate_backups(backup_dir, MAX_BACKUPS)

            return True
        except Exception as e:
            self.logging_manager.log_error(f"Backup failed: {e}")
            return False

    def _rotate_backups(self, backup_dir, max_keep):
        """ลบ backup เก่าที่เกินจำนวน max_keep (เรียงตามวันที่สร้าง)"""
        try:
            backup_files = sorted(
                [
                    os.path.join(backup_dir, f)
                    for f in os.listdir(backup_dir)
                    if f.startswith("NPC_") and f.endswith(".json")
                ],
                key=os.path.getmtime,
            )
            # ลบไฟล์เก่าสุดจนเหลือ max_keep
            while len(backup_files) > max_keep:
                oldest = backup_files.pop(0)
                os.remove(oldest)
                self.logging_manager.log_info(f"Rotated old backup: {os.path.basename(oldest)}")
        except Exception as e:
            self.logging_manager.log_error(f"Backup rotation error: {e}")

    def load_data(self, section=None):
        """โหลดข้อมูลจาก NPC.json แบบเลือกโหลดเฉพาะส่วน


        Args:

            section (str, optional): section ที่ต้องการโหลด ถ้าไม่ระบุจะโหลดทั้งหมด

        """

        try:

            # ตรวจสอบว่ามีข้อมูลในแคชหรือไม่

            if hasattr(self, "data_cache") and self.data_cache and not section:

                self.data = self.data_cache

                self.has_unsaved_changes = False

                return True

            with open(self._get_npc_file_path(), "r", encoding="utf-8") as file:

                if section:

                    # อ่านเฉพาะหัวข้อที่สนใจเพื่อลดปริมาณข้อมูล

                    full_data = json.load(file)

                    if section in full_data:

                        # อัพเดทแค่ส่วนที่ต้องการ

                        if not hasattr(self, "data") or not self.data:

                            self.data = {
                                key: (
                                    []
                                    if isinstance(full_data.get(key, []), list)
                                    else {}
                                )
                                for key in full_data.keys()
                            }

                        self.data[section] = full_data[section]

                    else:

                        return False

                else:

                    # อ่านข้อมูลทั้งหมด

                    full_data = json.load(file)

                    self.data = full_data

                    # เก็บข้อมูลในแคช

                    self.data_cache = full_data.copy()

                # สรุปข้อมูลที่โหลด

                summary = {
                    "main_characters": len(self.data.get("main_characters", [])),
                    "npcs": len(self.data.get("npcs", [])),
                    "lore": len(self.data.get("lore", {})),
                    "character_roles": len(self.data.get("character_roles", {})),
                    "word_fixes": len(self.data.get("word_fixes", {})),
                }

                self.logging_manager.log_info("NPC Data Summary:")

                for category, count in summary.items():

                    self.logging_manager.log_info(f"- {category}: {count} entries")

                self.has_unsaved_changes = False

                return True

        except FileNotFoundError:

            self.logging_manager.log_error("ไม่พบไฟล์ NPC.json หรือไฟล์ที่คล้ายกัน")

            messagebox.showerror("Error", "ไม่พบไฟล์ NPC ใดๆ!")

            self.data = {
                "main_characters": [],
                "npcs": [],
                "lore": {},
                "character_roles": {},
                "word_fixes": {},
            }

            return False

        except json.JSONDecodeError:

            self.logging_manager.log_error("Error: Invalid JSON in NPC.json")

            messagebox.showerror("Error", "Invalid JSON in NPC.json!")

            self.data = {
                "main_characters": [],
                "npcs": [],
                "lore": {},
                "character_roles": {},
                "word_fixes": {},
            }

            return False

    def _search_in_background(self, search_term):
        """ค้นหาข้อมูล NPC — ทำใน main thread (ข้อมูล ~600 entries ทำได้เร็วพอ
        และหลีกเลี่ยงปัญหา 'main thread is not in main loop' จาก Tkinter)

        Args:
            search_term (str): คำที่ต้องการค้นหา
        """
        try:
            # รีเซ็ตผลการค้นหาทุก section ให้เป็น 0
            for section in self.search_results:
                self.search_results[section] = 0

            # ล้างแคชการค้นหาเดิม
            if hasattr(self, "_search_cache"):
                self._search_cache = {}

            # ถ้ามีคำค้นหา ค้นหาทุก section
            if search_term:
                for section in self.data:
                    if section not in self.search_results:
                        continue

                    section_data = self.data[section]

                    # กรณีเป็นรายการ (main_characters, npcs)
                    if isinstance(section_data, list):
                        for item in section_data:
                            for key, value in item.items():
                                if search_term in str(value).lower():
                                    self.search_results[section] += 1
                                    break

                    # กรณีเป็นพจนานุกรม (lore, character_roles, word_fixes)
                    elif isinstance(section_data, dict):
                        for key, value in section_data.items():
                            if (
                                search_term in key.lower()
                                or search_term in str(value).lower()
                            ):
                                self.search_results[section] += 1

            # อัพเดท UI ทันที (อยู่ main thread อยู่แล้ว)
            if not self._is_destroyed:
                self._update_after_search(search_term)

        except Exception as e:
            self.logging_manager.log_error(f"Error in search: {e}")
            if not self._is_destroyed:
                self._update_status(f"เกิดข้อผิดพลาดในการค้นหา: {e}")

    def _update_after_search(self, search_term):
        """อัพเดท UI หลังจากค้นหาเสร็จ"""

        # อัพเดทตัวบ่งชี้ผลการค้นหา

        self._update_search_indicators()

        # ล้างการ์ดเดิม

        self._clear_cards()

        # สร้างการ์ดใหม่ตามคำค้นหาสำหรับ section ปัจจุบันเท่านั้น

        if self.current_section:

            self._create_cards_for_section(search_term)

        # อัพเดทสถานะ

        total_found = sum(self.search_results.values())

        if search_term:

            if total_found > 0:

                section_count = sum(
                    1 for count in self.search_results.values() if count > 0
                )

                current_section_count = self.search_results.get(self.current_section, 0)

                self.item_count_text.configure(
                    text=f"{current_section_count} จาก {total_found} รายการ"
                )

                if section_count > 1:

                    self._update_status(
                        f"พบ {total_found} รายการใน {section_count} หมวดหมู่"
                    )

                else:

                    self._update_status(f"พบ {total_found} รายการ")

            else:

                self.item_count_text.configure(text="0 รายการ")

                self._update_status(f"ไม่พบ '{search_term}'")

        else:

            item_count = self._get_section_item_count()

            self.item_count_text.configure(text=f"{item_count} รายการ")

            section_title = self.current_section.replace("_", " ").title()

            self._update_status(f"กำลังดู {section_title}")

        # ✅ บันทึกสถานะหลังจากการค้นหาเสร็จ
        self._save_current_state()

    def save_changes(self):
        """บันทึกการเปลี่ยนแปลงลง NPC.json (auto-backup ก่อนเขียนทับ)"""
        try:
            self._update_status("กำลังบันทึกข้อมูล...")

            # ตรวจสอบข้อมูลก่อนบันทึก
            if not self._validate_data():
                self._update_status("ไม่สามารถบันทึกข้อมูลได้ ข้อมูลไม่ถูกต้อง")
                return False

            # สำรองไฟล์เดิมก่อนเขียนทับ
            self._create_backup()

            # ดึง Path ของไฟล์ NPC ที่จะบันทึก
            npc_file_to_save = self._get_npc_file_path()

            # บันทึกข้อมูล
            with open(npc_file_to_save, "w", encoding="utf-8") as file:
                json.dump(self.data, file, indent=4, ensure_ascii=False)

            # รีเซ็ตสถานะและอัปเดตแคช
            self.has_unsaved_changes = False
            self.data_cache = self.data.copy()
            self._search_cache = {}

            # อัปเดต UI
            success_message = (
                f"บันทึกไปยัง {os.path.basename(npc_file_to_save)} เรียบร้อยแล้ว"
            )
            self._update_status(success_message)
            self.flash_success_message("บันทึกข้อมูลสำเร็จ!")
            if self.reload_callback:
                self.logging_manager.log_info("กำลังรีโหลดข้อมูล NPC...")
                self.reload_callback()

            return True

        except Exception as e:
            self._handle_save_error(e)
            return False


    def _show_more_menu(self):
        """แสดงเมนู dropdown สำหรับปุ่ม More"""
        # ถ้ามีเมนูอยู่แล้ว ให้ซ่อนก่อน
        if self.more_menu and self.more_menu.winfo_exists():
            self.more_menu.destroy()
            self.more_menu = None
            return

        # สร้างเมนู dropdown
        self.more_menu = tk.Toplevel(self.window)
        self.more_menu.wm_overrideredirect(True)  # ไม่มี title bar
        self.more_menu.configure(bg="#222222", relief="solid", bd=1)

        # กำหนดตำแหน่งเมนูให้อยู่ใต้ปุ่ม More
        x = self.more_btn.winfo_rootx()
        y = self.more_btn.winfo_rooty() + self.more_btn.winfo_height()
        self.more_menu.geometry(f"150x76+{x}+{y}")

        # --- ปุ่ม Backup ---
        backup_btn = tk.Button(
            self.more_menu,
            text="💾 สำรองข้อมูล",
            font=(self.font, self.font_size_small),
            bg="#222222",
            fg="white",
            bd=0,
            relief="flat",
            anchor="w",
            padx=10,
            pady=5,
            command=self._backup_action_from_menu,
            cursor="hand2",
        )
        backup_btn.pack(fill="x", padx=2, pady=(2, 0))
        backup_btn.bind("<Enter>", lambda e: backup_btn.configure(bg="#2a2a2a"))
        backup_btn.bind("<Leave>", lambda e: backup_btn.configure(bg="#222222"))

        # --- ปุ่ม Reset UI ---
        reset_btn = tk.Button(
            self.more_menu,
            text="⟳ รีเซ็ต UI",
            font=(self.font, self.font_size_small),
            bg="#222222",
            fg="white",
            bd=0,
            relief="flat",
            anchor="w",
            padx=10,
            pady=5,
            command=self._reset_ui_from_menu,
            cursor="hand2",
        )
        reset_btn.pack(fill="x", padx=2, pady=(0, 2))
        reset_btn.bind("<Enter>", lambda e: reset_btn.configure(bg="#2a2a2a"))
        reset_btn.bind("<Leave>", lambda e: reset_btn.configure(bg="#222222"))

        # ปิดเมนูเมื่อคลิกข้างนอก
        self.more_menu.bind("<FocusOut>", lambda e: self._hide_more_menu())
        self.more_menu.focus_set()

        # ปิดเมนูเมื่อคลิกที่อื่น
        def on_click_outside(event):
            if event.widget != self.more_menu:
                self._hide_more_menu()

        self.window.bind("<Button-1>", on_click_outside, add="+")

    def _hide_more_menu(self):
        """ซ่อนเมนู dropdown"""
        if self.more_menu and self.more_menu.winfo_exists():
            self.more_menu.destroy()
            self.more_menu = None

    def _backup_action_from_menu(self):
        """การกระทำสำรองจากเมนู dropdown"""
        self._hide_more_menu()
        self._manual_backup_action()

    def _reset_ui_from_menu(self):
        """รีเซ็ต UI จากเมนู dropdown"""
        self._hide_more_menu()
        self.reset_ui_state()

    def _manual_backup_action(self):
        """การกระทำเมื่อกดปุ่มสำรองแมนนวล"""
        try:
            self._update_status("กำลังสร้างไฟล์สำรอง...")

            if self._create_backup():
                self.flash_success_message("สร้างไฟล์สำรองสำเร็จ!")
                self._update_status("สร้างไฟล์สำรองเรียบร้อยแล้ว")
            else:
                self._update_status("ไม่สามารถสร้างไฟล์สำรองได้")

        except Exception as e:
            self.logging_manager.log_error(f"เกิดข้อผิดพลาดในการสำรองแมนนวล: {e}")
            self._update_status("เกิดข้อผิดพลาดในการสำรอง")

    def _validate_data(self):
        """ตรวจสอบความถูกต้องของข้อมูลก่อนบันทึก"""

        required_sections = [
            "main_characters",
            "npcs",
            "lore",
            "character_roles",
            "word_fixes",
        ]

        for section in required_sections:

            if section not in self.data:

                messagebox.showerror(
                    "Validation Error", f"Missing required section: {section}"
                )

                return False

            # ตรวจสอบประเภทข้อมูล

            if section in ["main_characters", "npcs"]:

                if not isinstance(self.data[section], list):

                    messagebox.showerror(
                        "Validation Error", f"Section {section} must be a list"
                    )

                    return False

            else:

                if not isinstance(self.data[section], dict):

                    messagebox.showerror(
                        "Validation Error", f"Section {section} must be a dictionary"
                    )

                    return False

        return True

    def _handle_save_error(self, error):
        """จัดการข้อผิดพลาดจากการบันทึก"""

        error_msg = f"Failed to save changes: {str(error)}"

        self.logging_manager.log_error(error_msg)

        messagebox.showerror("Save Error", error_msg)

    def show_section(self, section):
        """แสดงและตั้งค่าส่วนที่เลือก พร้อมใช้ระบบจัดการใหม่"""
        # 🔧 ใช้ระบบจัดการใหม่แทนการจัดการแยกส่วน
        self._comprehensive_cleanup()

        # 🎯 เพิ่ม logging
        self.logging_manager.log_info(f"Switching to section: {section}")

        self.current_section = section

        # ⭐ อัพเดทคำอธิบายแท็บ
        self._update_section_description(section)

        # อัพเดทปุ่ม section (เหมือนเดิม)
        for section_id, btn in self.section_buttons.items():
            if section_id == self.current_section:
                btn.configure(bg=self.style["accent"], fg=self.style["text_primary"])
            else:
                btn.configure(
                    bg=self.style["bg_tertiary"], fg=self.style["text_primary"]
                )

        # เพิ่ม: อัปเดต UI ก่อนดำเนินการต่อ
        self.window.update_idletasks()

        # อัพเดทตัวบ่งชี้ผลการค้นหา (เนื่องจาก section ปัจจุบันเปลี่ยน)
        self._update_search_indicators()

        # ล้างการ์ดเดิม
        self._clear_cards()

        # ดึงคำค้นหาปัจจุบัน (ถ้ามี)
        search_term = self.search_var.get().lower() if self.search_var.get() else None

        # สร้างการ์ดใหม่
        self._create_cards_for_section(search_term)

        # 🎯 เพิ่ม logging สำหรับ debug
        treeview_count = len(self.tree.get_children()) if hasattr(self, "tree") else 0
        self.logging_manager.log_info(
            f"Section {section} loaded with {treeview_count} items in treeview"
        )

        # อัพเดทหัวเรื่อและสถานะ
        section_title = section.replace("_", " ").title()
        self.detail_title.configure(text=f"{section_title} Details")

        # ล้างพื้นที่ detail content ก่อนสร้างฟอร์มใหม่ (ป้องกัน pack/grid conflict)
        self._clear_detail_content_frame()

        # สร้างฟอร์มรายละเอียดสำหรับส่วนที่เลือก
        self._create_detail_form_for_section()

        # ⭐ อัปเดตปุ่มให้เหมาะสมกับ section ใหม่
        self._reset_button_for_new_section()

        # อัพเดทสถานะ
        if search_term:
            total_found = sum(self.search_results.values())
            current_section_count = self.search_results.get(self.current_section, 0)
            self.item_count_text.configure(
                text=f"{current_section_count} จาก {total_found} รายการ"
            )
        else:
            item_count = self._get_section_item_count()
            self.item_count_text.configure(text=f"{item_count} รายการ")

        self._update_status(f"กำลังดู {section_title}")

        # เพิ่ม: อัปเดต UI เมื่อเสร็จสิ้น
        self.window.update_idletasks()

        # ✅ บันทึกสถานะหลังจากเปลี่ยน section
        self._save_current_state()

    def _reset_button_for_new_section(self):
        """รีเซ็ตปุ่มเมื่อเปลี่ยน section ใหม่"""
        try:
            if (
                not hasattr(self, "save_edit_btn")
                or not self.save_edit_btn.winfo_exists()
            ):
                return

            # รีเซ็ต current_edit_data
            self.current_edit_data = None

            # ตั้งค่าปุ่มเป็น ADD ENTRY เสมอเมื่อเปลี่ยน section
            self.save_edit_btn.configure(
                text="ADD ENTRY", command=self._quick_add_new_entry
            )

            # แสดงปุ่มถ้ายังไม่ได้แสดง
            if not self.save_edit_btn.winfo_ismapped():
                self.save_edit_btn.pack(fill="x")

        except Exception as e:
            self.logging_manager.log_error(
                f"Error resetting button for new section: {e}"
            )

    def reset_ui_state(self):
        """รีเซ็ตสถานะ UI ทั้งหมดและรีเฟรชข้อมูลเพื่อแก้ไขปัญหา focus และการแสดงผล"""
        try:
            # 🔧 ใช้ระบบจัดการใหม่แทนการจัดการแยกส่วน
            self._comprehensive_cleanup()
            self._force_ui_unlock()

            # รีโหลดข้อมูลจากไฟล์เพื่อให้แน่ใจว่าได้ข้อมูลล่าสุด
            self.load_data()

            # ⭐ รีเฟรชหน้าจอปัจจุบัน
            if hasattr(self, "current_section") and self.current_section:
                # ล้างแคชการค้นหา
                if hasattr(self, "_search_cache"):
                    self._search_cache.clear()

                # ล้างการเลือกใน Treeview
                if hasattr(self, "tree") and self.tree.winfo_exists():
                    selection = self.tree.selection()
                    if selection:
                        self.tree.selection_remove(selection)

                # รีเฟรชการแสดงผล
                self._clear_cards()
                search_term = (
                    self.search_var.get().lower() if self.search_var.get() else None
                )
                self._create_cards_for_section(search_term)

                # รีเซ็ต panel ขวา
                self._hide_detail_form()

            # อัปเดต idletasks เพื่อให้แน่ใจว่า UI ได้รับการอัปเดต
            self.window.update_idletasks()

            # แสดงข้อความให้ผู้ใช้ทราบ
            self._update_status("รีเฟรชข้อมูลและรีเซ็ตสถานะ UI เรียบร้อย")
            self.logging_manager.log_info("UI state has been reset and data refreshed")

            return True
        except Exception as e:
            self.logging_manager.log_error(
                f"Error resetting UI state and refreshing data: {e}"
            )
            self._update_status("เกิดข้อผิดพลาดในการรีเฟรช กรุณาลองใหม่")
            return False

    def _on_section_button_hover(self, button):
        """จัดการ hover effect สำหรับปุ่ม section"""

        is_selected = button == self.section_buttons.get(self.current_section)

        if is_selected:

            button.configure(bg=self.style["accent_hover"])

        else:

            button.configure(bg="#2a2a2a")

    def _on_section_button_leave(self, button):
        """จัดการ leave effect สำหรับปุ่ม section"""

        is_selected = button == self.section_buttons.get(self.current_section)

        if is_selected:

            button.configure(bg=self.style["accent"], fg=self.style["text_primary"])

        else:

            button.configure(
                bg=self.style["bg_tertiary"], fg=self.style["text_primary"]
            )

    def _start_move(self, event):
        """เริ่มการลากหน้าต่าง"""

        self.x = event.x

        self.y = event.y

    def _do_move(self, event):
        """ดำเนินการลากหน้าต่าง"""

        try:

            deltax = event.x - self.x

            deltay = event.y - self.y

            x = self.window.winfo_x() + deltax

            y = self.window.winfo_y() + deltay

            self.window.geometry(f"+{x}+{y}")

        except Exception as e:

            self.logging_manager.log_error(f"Move error: {e}")

    def _on_list_frame_configure(self, event):
        """จัดการเมื่อ frame ของรายการมีการเปลี่ยนแปลงขนาด"""

        # อัพเดทขนาด scrollable area

        self.list_canvas.configure(scrollregion=self.list_canvas.bbox("all"))

    def _on_list_canvas_configure(self, event):
        """จัดการเมื่อ canvas มีการเปลี่ยนแปลงขนาด"""

        # อัพเดทความกว้างของ frame ภายใน canvas

        width = event.width

        self.list_canvas.itemconfig(self.list_window, width=width)

    def _on_mousewheel_list(self, event):
        """จัดการการเลื่อนเมาส์สำหรับลิสต์"""

        self.list_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_search_change(self, *args):
        """จัดการเมื่อมีการเปลี่ยนแปลงในช่องค้นหา"""

        search_term = self.search_var.get().lower()

        # แสดง/ซ่อนปุ่มล้างการค้นหา

        if search_term:

            self.clear_search_btn.pack(side="left", padx=(5, 0))

        else:

            self.clear_search_btn.pack_forget()

        # แสดงสถานะว่ากำลังค้นหา เพื่อให้ผู้ใช้ทราบว่าระบบกำลังทำงาน

        if search_term:

            self._update_status(f"กำลังค้นหา '{search_term}'...")

        # ดีเลย์การค้นหาเล็กน้อยเพื่อลดการค้นหาซ้ำซ้อนเมื่อผู้ใช้พิมพ์ต่อเนื่อง

        if hasattr(self, "_search_delay") and self._search_delay:

            self._safe_after_cancel(self._search_delay)

        # ตั้งเวลาเล็กน้อยก่อนเริ่มค้นหาจริง - เพิ่มจาก 300ms เป็น 500ms
        # เพื่อลดการ search บ่อยเกินไปและให้ผู้ใช้พิมพ์เสร็จก่อน
        
        # ปรับเวลา debounce ตามความยาวของคำค้นหา
        debounce_time = 500 if len(search_term) <= 2 else 300  # คำสั้นรอนานกว่า
        
        self._search_delay = self._safe_after(
            debounce_time, lambda: self._search_in_background(search_term)
        )

    def _update_search_indicators(self):
        """อัพเดทตัวบ่งชี้ผลการค้นหาสำหรับแต่ละ section"""

        for section, count in self.search_results.items():

            if section in self.section_indicators:

                indicator = self.section_indicators[section]

                # แสดงตัวบ่งชี้เฉพาะเมื่อพบผลลัพธ์ และ ไม่ใช่ section ปัจจุบัน

                if count > 0 and section != self.current_section:

                    # อัพเดทข้อความให้แสดงจำนวนผลลัพธ์
                    indicator.configure(text=str(count))

                    # แสดงตัวบ่งชี้
                    if indicator.winfo_manager() == "":  # ถ้ายังไม่ได้แสดง
                        # เพิ่มค่า z-index โดยใช้ lift() เพื่อให้อยู่ด้านหน้าของแท็บ
                        indicator.place(relx=1.0, rely=0, anchor="ne", x=-2, y=2)
                        indicator.lift()  # ยก indicator ให้อยู่บนสุด
                else:
                    # ซ่อนตัวบ่งชี้
                    indicator.place_forget()

    def _clear_search(self):
        """ล้างการค้นหา"""

        self.search_var.set("")

        self.clear_search_btn.pack_forget()

        # รีเซ็ตผลการค้นหา

        for section in self.search_results:

            self.search_results[section] = 0

        # อัพเดทตัวบ่งชี้

        self._update_search_indicators()

    def refresh_current_view(self):
        """รีเฟรชการแสดงผลข้อมูลในหน้าปัจจุบัน"""
        try:
            if not hasattr(self, "current_section") or not self.current_section:
                self.logging_manager.log_warning("No current section to refresh")
                return False

            # ล้างแคชการค้นหา
            if hasattr(self, "_search_cache"):
                self._search_cache.clear()

            # ล้างการเลือกปัจจุบัน
            if hasattr(self, "tree") and self.tree.winfo_exists():
                selection = self.tree.selection()
                if selection:
                    self.tree.selection_remove(selection)

            # รีเฟรชการแสดงผล
            search_term = (
                self.search_var.get().lower() if self.search_var.get() else None
            )
            self._create_cards_for_section(search_term)

            # รีเซ็ต panel ขวาถ้าอยู่ในโหมดแก้ไข
            if hasattr(self, "current_edit_data") and self.current_edit_data:
                self._hide_detail_form()

            self._update_status(
                f"รีเฟรชข้อมูล {self.current_section.replace('_', ' ').title()} เรียบร้อย"
            )
            return True

        except Exception as e:
            self.logging_manager.log_error(f"Error refreshing current view: {e}")
            return False

    def _update_status(self, message):
        """อัพเดทข้อความสถานะ"""
        self.status_text.configure(text=message)

    def _clear_cards(self):
        """ล้างรายการทั้งหมดใน Treeview และซ่อน panel รายละเอียด"""

        # ล้าง Treeview

        if hasattr(self, "tree"):

            children = self.tree.get_children()
            if children:
                # ลบทั้งหมดในครั้งเดียว - แก้ไขให้มีประสิทธิภาพ
                self.tree.delete(*children)

        # เคลียร์ข้อมูลที่เก็บไว้สำหรับ Treeview

        if hasattr(self, "tree_items"):

            self.tree_items.clear()

        # ⭐ รีเซ็ตปุ่มเมื่อล้างรายการ
        if hasattr(self, "save_edit_btn") and self.save_edit_btn.winfo_exists():
            self.save_edit_btn.configure(
                text="ADD ENTRY", command=self._quick_add_new_entry
            )

        # ล้างการ์ดรายละเอียด (Panel ขวา)

        if hasattr(self, "card_detail_frame"):

            for widget in self.card_detail_frame.winfo_children():

                widget.destroy()

            # ซ่อน panel รายละเอียด

            self.card_detail_frame.pack_forget()

        # รีเซ็ตการ์ดที่แสดงรายละเอียดปัจจุบัน

        if hasattr(self, "current_detail_card"):

            self.current_detail_card = None

    def _create_list_item(self, item_data, index):
        """สร้างรายการในลิสต์จากข้อมูลที่กำหนด


        Args:

            item_data: ข้อมูลของรายการ

            index: ลำดับของรายการ (สำหรับสีสลับ)

        """

        # กำหนดสีพื้นหลังสลับกันระหว่างแถวคู่และแถวคี่

        bg_color = (
            self.style["bg_primary"] if index % 2 == 0 else self.style["bg_secondary"]
        )

        # สร้าง frame สำหรับรายการ

        item_frame = tk.Frame(
            self.list_frame,
            bg=bg_color,
            padx=5,
            pady=8,
            highlightbackground=self.style["bg_tertiary"],
            highlightthickness=1,
        )

        item_frame.pack(fill="x", pady=1)

        # กำหนดชื่อที่จะแสดง

        if self.current_section == "main_characters":

            name = item_data.get("firstName", "")

            if item_data.get("lastName"):

                name += f" {item_data.get('lastName')}"

            item_type = item_data.get("gender", "")

        elif self.current_section == "npcs":

            name = item_data.get("name", "")

            item_type = item_data.get("role", "")

        elif self.current_section in ["lore", "character_roles", "word_fixes"]:

            name = item_data.get("key", "")

            value = item_data.get("value", "")

            # กำหนดประเภทตามส่วน

            if self.current_section == "lore":

                item_type = "Lore"

            elif self.current_section == "character_roles":

                item_type = "Role"

            else:

                item_type = "Fix"

        # สร้างส่วนแสดงชื่อ

        name_frame = tk.Frame(item_frame, bg=bg_color)

        name_frame.pack(side="left", fill="both", expand=True, padx=5)

        name_label = tk.Label(
            name_frame,
            text=name,
            font=(self.font, 11, "bold"),
            bg=bg_color,
            fg=self.style["text_primary"],
            anchor="w",
        )

        name_label.pack(side="left", anchor="w")

        # สร้างส่วนแสดงประเภท

        type_frame = tk.Frame(item_frame, bg=bg_color)

        type_frame.pack(side="left", fill="y", padx=5)

        type_label = tk.Label(
            type_frame,
            text=item_type,
            font=(self.font, 10),
            bg=bg_color,
            fg=self.style["text_secondary"],
            anchor="w",
        )

        type_label.pack(side="left", anchor="w")

        # สร้างส่วนปุ่มการทำงาน

        action_frame = tk.Frame(item_frame, bg=bg_color)

        action_frame.pack(side="right", fill="y", padx=5)

        view_btn = tk.Button(
            action_frame,
            text="View",
            font=(self.font, 10),
            bg=self.style["accent"],
            fg="white",
            bd=0,
            padx=8,
            pady=2,
            command=lambda d=item_data: self._show_card_detail(d),
        )

        view_btn.pack(side="right", padx=2)

        edit_btn = tk.Button(
            action_frame,
            text="Edit",
            font=(self.font, 10),
            bg=self.style["bg_tertiary"],
            fg=self.style["text_primary"],
            bd=0,
            padx=8,
            pady=2,
            command=lambda d=item_data: self._on_card_edit(d),
        )

        edit_btn.pack(side="right", padx=2)

        # เพิ่ม hover effects - แก้ไขส่วนนี้

        # กำหนดค่าสีสำหรับปุ่ม View

        view_hover_color = self.style["accent_hover"]

        view_normal_color = self.style["accent"]

        # กำหนดค่าสีสำหรับปุ่ม Edit

        edit_hover_color = "#2a2a2a"

        edit_normal_color = self.style["bg_tertiary"]

        # ผูกเหตุการณ์ Enter และ Leave สำหรับปุ่ม View

        view_btn.bind(
            "<Enter>", lambda e, btn=view_btn: btn.configure(bg=view_hover_color)
        )

        view_btn.bind(
            "<Leave>", lambda e, btn=view_btn: btn.configure(bg=view_normal_color)
        )

        # ผูกเหตุการณ์ Enter และ Leave สำหรับปุ่ม Edit

        edit_btn.bind(
            "<Enter>", lambda e, btn=edit_btn: btn.configure(bg=edit_hover_color)
        )

        edit_btn.bind(
            "<Leave>", lambda e, btn=edit_btn: btn.configure(bg=edit_normal_color)
        )

        # เพิ่ม event สำหรับคลิกที่รายการ

        item_frame.bind("<Button-1>", lambda e, d=item_data: self._show_card_detail(d))

        name_label.bind("<Button-1>", lambda e, d=item_data: self._show_card_detail(d))

        type_label.bind("<Button-1>", lambda e, d=item_data: self._show_card_detail(d))

        # เพิ่มรายการเข้าไปในลิสต์

        self.list_items.append((item_frame, item_data))

    def _show_card_detail(self, data, is_preview=False):
        """แสดงรายละเอียดการ์ดใน Panel ด้านขวา - รองรับโหมด preview สำหรับตัวละครใหม่"""
        try:
            # ส่วนที่มีการยกเลิก focus timer
            if hasattr(self, "_focus_after_id") and self._focus_after_id:
                try:
                    self._safe_after_cancel(self._focus_after_id)
                except:
                    pass
                self._focus_after_id = None

            # บันทึกสถานะสำหรับการ monitor ปัญหา (ถ้ามี)
            if hasattr(self.window, "last_ui_action"):
                self.window.last_ui_action = "show_card_detail"
            if hasattr(self.window, "last_ui_timestamp"):
                self.window.last_ui_timestamp = time.time()

            # ⭐ แก้ไขปัญหา: ตรวจสอบว่าอยู่ในโหมดแก้ไขหรือไม่ก่อนรีเซ็ต current_edit_data
            # หากไม่ได้อยู่ในโหมดแก้ไข หรือ ข้อมูลที่จะแสดงไม่ใช่ข้อมูลที่กำลังแก้ไข
            is_currently_editing = (
                hasattr(self, "current_edit_data")
                and self.current_edit_data is not None
            )

            # ถ้าไม่ได้อยู่ในโหมดแก้ไข หรือ data ที่ส่งมาต่างจาก current_edit_data
            if not is_currently_editing or data != self.current_edit_data:
                # เฉพาะเมื่อไม่ได้อยู่ในโหมดแก้ไข หรือกำลังจะแสดงข้อมูลคนอื่น
                if not is_currently_editing:
                    self.current_edit_data = None  # รีเซ็ตเฉพาะเมื่อไม่ได้อยู่ในโหมดแก้ไข
                    self.has_actual_changes = False  # รีเซ็ต change tracking

            self._clear_detail_content_frame()  # ล้างพื้นที่ content

            # อัพเดท Title หลักของ Panel - รองรับโหมด preview
            if is_preview:
                section_title = "Character Preview"
                self.detail_title.configure(text=section_title)
            else:
                section_title = self.current_section.replace("_", " ").title()
                self.detail_title.configure(text=f"{section_title} Details")

            # --- จัดเตรียมชื่อที่จะ copy ---
            copy_name = ""
            if self.current_section == "main_characters":
                copy_name = data.get("firstName", "")
                if data.get("lastName"):
                    copy_name += f" {data.get('lastName')}"
            elif self.current_section == "npcs":
                copy_name = data.get("name", "")
            elif self.current_section in ["lore", "character_roles", "word_fixes"]:
                copy_name = data.get("key", "")
            # -----------------------------------

            # สร้าง CardView instance โดยมี detail_content_frame เป็น parent
            font_config_to_pass = {
                "family": self.font,
                "large_bold": self.font_size_large_bold,
                "medium_bold": self.font_size_medium_bold,
                "medium": self.font_size_medium,
                "small_bold": self.font_size_small_bold,
                "small": self.font_size_small,
                "xsmall_bold": self.font_size_xsmall_bold,
                "xsmall": self.font_size_xsmall,
            }

            # ตรวจสอบว่า CardView รองรับพารามิเตอร์ copy_name และ copy_callback หรือไม่
            cardview_args = {
                "parent": self.detail_content_frame,
                "data": data,
                "section_type": self.current_section,
                "font_config": font_config_to_pass,
                "all_roles_data": self.data.get("character_roles", {}),
                "navigate_to_role_callback": self._navigate_and_prepare_role,
                "on_edit_callback": self._on_card_edit,
                "on_delete_callback": self._on_card_delete,
                "detail_mode": True,
            }

            # เพิ่มพารามิเตอร์ copy_name และ copy_callback เฉพาะเมื่อเรามีเมธอด _copy_to_search
            if hasattr(self, "_copy_to_search") and callable(self._copy_to_search):
                cardview_args["copy_name"] = copy_name
                cardview_args["copy_callback"] = self._copy_to_search

            # word_fixes ใช้ layout พิเศษ (จัดกลาง, แสดง ก่อน/หลัง)
            if self.current_section == "word_fixes" and not is_preview:
                self._create_word_fixes_detail_view(data)
            else:
                # สร้าง CardView ด้วยพารามิเตอร์ที่เหมาะสม
                card = CardView(**cardview_args)
                card_frame = card.get_frame()
                card_frame.grid(row=0, column=0, sticky="nsew")
                self.current_detail_widget = card_frame

            # ⭐ แสดงปุ่ม "EDIT" สำหรับการแก้ไขข้อมูล
            if hasattr(self, "save_edit_btn") and self.save_edit_btn.winfo_exists():
                self.save_edit_btn.configure(
                    text="EDIT", command=lambda: self._on_card_edit(data)
                )
                if not self.save_edit_btn.winfo_ismapped():
                    self.save_edit_btn.pack(fill="x")

            self.window.update_idletasks()

        except Exception as e:
            self.logging_manager.log_error(f"Error showing card detail: {e}")
            import traceback

            self.logging_manager.log_error(traceback.format_exc())

    def _check_ui_responsiveness(self):
        """ตรวจสอบว่า UI ยังตอบสนองปกติหรือไม่"""
        try:
            # เช็คว่ามีการโต้ตอบล่าสุดนานเกินไปหรือไม่
            if hasattr(self.window, "last_ui_timestamp"):
                time_diff = time.time() - self.window.last_ui_timestamp
                if time_diff > 5:  # 5 วินาที
                    self.logging_manager.log_warning(
                        f"UI may be unresponsive. Last action: {getattr(self.window, 'last_ui_action', 'unknown')}"
                    )

                    # ถ้าไม่มีการโต้ตอบนานเกิน 5 วินาที ลองรีเซ็ต UI
                    should_reset = False

                    # ตรวจสอบว่า entry widgets ตอบสนองหรือไม่
                    for field, widget in self.detail_form_elements.items():
                        if isinstance(widget, tk.Entry) or isinstance(widget, tk.Text):
                            try:
                                # ทดสอบโดยเรียกเมธอดพื้นฐาน
                                if not widget.winfo_viewable():
                                    should_reset = True
                                    break
                            except:
                                should_reset = True
                                break

                    if should_reset:
                        self.logging_manager.log_warning(
                            "Auto-resetting UI due to potential unresponsiveness"
                        )
                        self.reset_ui_state()

            # ตั้งเวลาตรวจสอบอีกครั้ง
            self._safe_after(5000, self._check_ui_responsiveness)  # ตรวจสอบทุก 5 วินาที
        except Exception as e:
            self.logging_manager.log_error(f"Error checking UI responsiveness: {e}")

    def _copy_to_search(self, name):
        """คัดลอกชื่อไปยังช่องค้นหาอัตโนมัติ"""
        try:
            if name and hasattr(self, "search_var"):
                # กำหนดค่าให้กับ search_var ซึ่งจะทริกเกอร์การค้นหาโดยอัตโนมัติ
                self.search_var.set(name)

                # Focus ไปที่ช่องค้นหา
                if hasattr(self, "search_entry") and self.search_entry.winfo_exists():
                    self.search_entry.focus_set()
                    self.search_entry.select_range(0, tk.END)  # เลือกข้อความทั้งหมด

                # แสดงข้อความยืนยัน
                self.flash_message(f"คัดลอก '{name}' ไปยังการค้นหาแล้ว", "info")

        except Exception as e:
            self.logging_manager.log_error(f"Error copying to search: {e}")

    def _add_list_items_in_batches(self, items, batch_size=30, start_idx=0):
        """เพิ่มรายการทีละชุดเพื่อไม่ให้ UI ค้าง


        Args:

            items: รายการข้อมูลสำหรับสร้างลิสต์

            batch_size: จำนวนรายการที่สร้างต่อรอบ

            start_idx: ตำแหน่งเริ่มต้น

        """

        if start_idx >= len(items):

            return

        end_idx = min(start_idx + batch_size, len(items))

        # สร้างรายการในชุดนี้

        for i in range(start_idx, end_idx):

            item = items[i]

            self._create_list_item(item, i)

        # กำหนดการเรียกใช้ฟังก์ชันถัดไป

        self._safe_after(
            10,
            lambda: self._add_list_items_in_batches(items, batch_size, end_idx),
        )

    def _add_cards_in_batches(self, items, cards_per_row, batch_size=10, start_idx=0):
        """เพิ่มการ์ดทีละชุดเพื่อไม่ให้ UI ค้าง


        Args:

            items: รายการข้อมูลสำหรับสร้างการ์ด

            cards_per_row: จำนวนการ์ดต่อแถว

            batch_size: จำนวนการ์ดที่สร้างต่อรอบ

            start_idx: ตำแหน่งเริ่มต้น

        """

        if start_idx >= len(items):

            # ตั้งค่า weight สำหรับการปรับขนาดอัตโนมัติ

            rows_needed = max(1, (len(items) + cards_per_row - 1) // cards_per_row)

            for i in range(rows_needed):

                self.card_frame.rowconfigure(i, weight=1)

            for i in range(cards_per_row):

                self.card_frame.columnconfigure(i, weight=1)

            return

        end_idx = min(start_idx + batch_size, len(items))

        # ตำแหน่งการ์ดปัจจุบัน

        current_row = start_idx // cards_per_row

        current_col = start_idx % cards_per_row

        # สร้างการ์ดในชุดนี้

        for i in range(start_idx, end_idx):

            item = items[i]

            # สร้างการ์ด

            card = CardView(
                self.card_frame,
                item,
                self.current_section,
                on_edit_callback=self._on_card_edit,
                on_delete_callback=self._on_card_delete,
                detail_mode=True,  # เพิ่ม parameter ใหม่สำหรับระบุว่าเป็น detail panel หรือไม่
            )

            # จัดตำแหน่งการ์ด

            card.get_frame().grid(
                row=current_row, column=current_col, padx=10, pady=10, sticky="nsew"
            )

            # อัพเดทตำแหน่งการ์ดถัดไป

            current_col += 1

            if current_col >= cards_per_row:

                current_col = 0

                current_row += 1

            # เพิ่มการ์ดลงในรายการ

            self.cards.append(card)

        # กำหนดการเรียกใช้ฟังก์ชันถัดไป

        self._safe_after(
            10,
            lambda: self._add_cards_in_batches(
                items, cards_per_row, batch_size, end_idx
            ),
        )

    def _get_section_item_count(self, search_term=None):
        """นับจำนวนรายการในส่วนที่เลือก"""

        if not self.current_section or self.current_section not in self.data:

            return 0

        section_data = self.data[self.current_section]

        if not search_term:

            # นับทั้งหมด

            if isinstance(section_data, list):

                return len(section_data)

            elif isinstance(section_data, dict):

                return len(section_data)

            return 0

        else:

            # นับเฉพาะที่ตรงกับคำค้นหา

            count = 0

            if isinstance(section_data, list):

                for item in section_data:

                    for key, value in item.items():

                        if search_term in str(value).lower():

                            count += 1

                            break

            elif isinstance(section_data, dict):

                for key, value in section_data.items():

                    if search_term in key.lower() or search_term in str(value).lower():

                        count += 1

            return count

    def _create_detail_form_for_section(self):
        """สร้างฟอร์มรายละเอียดสำหรับส่วนที่เลือก (ปรับขนาดฟอนต์)"""

        # 🎯 แก้ไขปัญหา widget lifecycle - ตรวจสอบและสร้างใหม่หากจำเป็น
        # ตรวจสอบว่า detail_form_frame ยังมีอยู่และใช้งานได้หรือไม่
        form_frame_exists = (
            hasattr(self, "detail_form_frame") and self.detail_form_frame is not None
        )

        # ตรวจสอบเพิ่มเติมว่า widget path ยังใช้งานได้หรือไม่
        if form_frame_exists:
            try:
                # ทดสอบเข้าถึง widget - หากผิดพลาดแสดงว่าถูกทำลายแล้ว
                self.detail_form_frame.winfo_exists()
                # ล้างฟอร์มเดิมหาก widget ยังมีอยู่
                for widget in self.detail_form_frame.winfo_children():
                    widget.destroy()
            except (AttributeError, tk.TclError) as e:
                # Widget ถูกทำลายไปแล้ว - ต้องสร้างใหม่
                if hasattr(self, "logging_manager"):
                    self.logging_manager.log_warning(
                        f"detail_form_frame destroyed, recreating: {e}"
                    )
                form_frame_exists = False

        # สร้าง detail_form_frame ใหม่หากไม่มีหรือถูกทำลายไปแล้ว
        if not form_frame_exists:
            if (
                hasattr(self, "detail_content_frame")
                and self.detail_content_frame.winfo_exists()
            ):
                self.detail_form_frame = tk.Frame(
                    self.detail_content_frame, bg=self.style["bg_secondary"]
                )
                if hasattr(self, "logging_manager"):
                    self.logging_manager.log_info("Created new detail_form_frame")
            else:
                # ไม่สามารถสร้าง detail_form_frame ได้ - ออกจากฟังก์ชัน
                if hasattr(self, "logging_manager"):
                    self.logging_manager.log_error(
                        "Cannot create detail_form_frame: detail_content_frame missing"
                    )
                return

        # Reset form elements dictionary
        self.detail_form_elements = {}

        # ถ้าไม่มีส่วนที่เลือก
        if not self.current_section:
            return

        # กำหนดฟิลด์ตามส่วนที่เลือก (เหมือนเดิม)
        if self.current_section == "main_characters":
            # 🎨 ปรับปรุง: ใช้ layout พิเศษสำหรับ main_characters เพื่อประหยัดพื้นที่
            self._create_main_characters_compact_layout()
            return
        elif self.current_section == "npcs":
            fields = ["name", "role", "description"]
        elif self.current_section == "lore":
            fields = ["term", "description"]
        elif self.current_section == "character_roles":
            self._create_roles_layout()
            return
        elif self.current_section == "word_fixes":
            # ⭐ สำหรับ word_fixes ใช้ layout พิเศษแบบ 2 ฝั่ง
            self._create_word_fixes_layout()
            return  # ออกจากฟังก์ชันเพราะใช้ layout พิเศษ
        else:
            return

        # สร้างฟิลด์ในฟอร์มแบบปกติ (สำหรับแท็บอื่นๆ)
        for field in fields:
            field_frame = tk.Frame(
                self.detail_form_frame,
                bg=self.style["bg_secondary"],
                pady=4,
            )
            field_frame.pack(fill="x", pady=4)

            # ป้ายชื่อฟิลด์
            label = tk.Label(
                field_frame,
                text=field.replace("_", " ").capitalize() + ":",
                font=(self.font, self.font_size_medium),
                bg=self.style["bg_secondary"],
                fg=self.style["text_secondary"],
            )
            label.pack(anchor="w")

            # สร้างฟิลด์ input ตามประเภท
            if field in ["description", "style"]:
                # กล่องข้อความหลายบรรทัด - ไม่เปลี่ยนแปลง
                entry_container = tk.Frame(
                    field_frame,
                    bg=self.style["bg_primary"],
                    highlightthickness=1,
                    highlightbackground=self.style["bg_tertiary"],
                    highlightcolor=self.style["accent"],
                )
                entry_container.pack(fill="x", pady=(2, 0))

                entry = tk.Text(
                    entry_container,
                    height=8,
                    width=40,
                    bg=self.style["bg_primary"],
                    fg=self.style["text_primary"],
                    insertbackground=self.style["text_primary"],
                    font=(self.font, self.font_size_medium),
                    bd=0,
                    relief="flat",
                    padx=10,
                    pady=6,
                    wrap=tk.WORD,
                )
                entry.pack(side="left", fill="both", expand=True)

                self.detail_form_elements[field] = entry

                # เพิ่ม scrollbar แบบ Dark Flat
                scrollbar = ttk.Scrollbar(
                    entry_container, orient="vertical", command=entry.yview
                )
                scrollbar.pack(side="right", fill="y")
                entry.config(yscrollcommand=scrollbar.set)

                # เพิ่ม focus effects - ⭐ เพิ่ม change tracking สำหรับ Text widgets
                entry.bind(
                    "<FocusIn>",
                    lambda e, w=entry_container, f=field: (
                        w.config(highlightbackground=self.style["accent"]),
                        (
                            setattr(self.window, "last_ui_timestamp", time.time())
                            if hasattr(self.window, "last_ui_timestamp")
                            else None
                        ),
                        (
                            setattr(self.window, "last_ui_action", f"focus_entry_{f}")
                            if hasattr(self.window, "last_ui_action")
                            else None
                        ),
                    ),
                )
                entry.bind(
                    "<FocusOut>",
                    lambda e, w=entry_container: w.config(
                        highlightbackground=self.style["bg_tertiary"]
                    ),
                )
                # เพิ่มการตรวจสอบการเปลี่ยนแปลงใน Text widget
                # 🔥 ลบระบบ unsaved changes - ไม่ต้องตรวจสอบการเปลี่ยนแปลง
                # entry.bind(
                #     "<KeyRelease>",
                #     lambda e, f=field: setattr(self, "has_actual_changes", True),
                # )

            else:
                # ฟิลด์ข้อความบรรทัดเดียว (Entry)
                entry_var = tk.StringVar()

                entry_container = tk.Frame(
                    field_frame,
                    bg=self.style["bg_primary"],
                    highlightthickness=1,
                    highlightbackground=self.style["bg_tertiary"],
                    highlightcolor=self.style["accent"],
                )
                entry_container.pack(fill="x", pady=(2, 0))

                entry = tk.Entry(
                    entry_container,
                    textvariable=entry_var,
                    bg=self.style["bg_primary"],
                    fg=self.style["text_primary"],
                    insertbackground=self.style["text_primary"],
                    font=(self.font, self.font_size_medium),
                    bd=0,
                    relief="flat",
                )
                entry.pack(fill="x", padx=10, pady=6)

                self.detail_form_elements[field] = entry_var

                # เพิ่ม focus effects
                entry.bind(
                    "<FocusIn>",
                    lambda e, w=entry_container, f=field: (
                        w.config(highlightbackground=self.style["accent"]),
                        (
                            setattr(self.window, "last_ui_timestamp", time.time())
                            if hasattr(self.window, "last_ui_timestamp")
                            else None
                        ),
                        (
                            setattr(self.window, "last_ui_action", f"focus_entry_{f}")
                            if hasattr(self.window, "last_ui_action")
                            else None
                        ),
                    ),
                )
                entry.bind(
                    "<FocusOut>",
                    lambda e, w=entry_container: w.config(
                        highlightbackground=self.style["bg_tertiary"]
                    ),
                )
                # เพิ่มการตรวจสอบการเปลี่ยนแปลงใน Entry widget
                entry_var.trace_add(
                    "write",
                    lambda *args, f=field: setattr(self, "has_actual_changes", True),
                )

        # Pack ฟอร์มหลังสร้างฟิลด์เสร็จแล้ว
        self.detail_form_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=10)

    def _create_main_characters_compact_layout(self):
        """สร้าง layout แบบ compact สำหรับ main_characters เพื่อประหยัดพื้นที่"""

        # 🎯 ตรวจสอบและสร้าง detail_form_frame ถ้าจำเป็น (เหมือน _create_detail_form_for_section)
        form_frame_exists = (
            hasattr(self, "detail_form_frame") and self.detail_form_frame is not None
        )

        if form_frame_exists:
            try:
                self.detail_form_frame.winfo_exists()
                for widget in self.detail_form_frame.winfo_children():
                    widget.destroy()
            except (AttributeError, tk.TclError):
                form_frame_exists = False

        if not form_frame_exists:
            if (
                hasattr(self, "detail_content_frame")
                and self.detail_content_frame.winfo_exists()
            ):
                self.detail_form_frame = tk.Frame(
                    self.detail_content_frame, bg=self.style["bg_secondary"]
                )
                self.logging_manager.log_info(
                    "Created new detail_form_frame for compact layout"
                )
            else:
                self.logging_manager.log_error(
                    "Cannot create detail_form_frame: detail_content_frame missing"
                )
                return

        # Reset form elements dictionary
        self.detail_form_elements = {}

        # 🎨 สร้าง Name Row (firstName + lastName ในแถวเดียวกัน)
        name_row_frame = tk.Frame(
            self.detail_form_frame,
            bg=self.style["bg_secondary"],
            pady=4,
        )
        name_row_frame.pack(fill="x", pady=4)

        # Label สำหรับ Name
        name_label = tk.Label(
            name_row_frame,
            text="Name:",
            font=(self.font, self.font_size_medium),
            bg=self.style["bg_secondary"],
            fg=self.style["text_secondary"],
        )
        name_label.pack(anchor="w")

        # Container สำหรับ firstName และ lastName
        name_inputs_container = tk.Frame(name_row_frame, bg=self.style["bg_secondary"])
        name_inputs_container.pack(fill="x", pady=(2, 0))

        # firstName (กว้าง 70%)
        firstname_container = tk.Frame(
            name_inputs_container,
            bg=self.style["bg_primary"],
            highlightthickness=1,
            highlightbackground=self.style["bg_tertiary"],
            highlightcolor=self.style["accent"],
        )
        firstname_container.pack(side="left", fill="x", expand=True, padx=(0, 5))

        firstname_entry = tk.Entry(
            firstname_container,
            bg=self.style["bg_primary"],
            fg=self.style["text_primary"],
            insertbackground=self.style["text_primary"],
            font=(self.font, self.font_size_medium),
            bd=0,
            relief="flat",
        )
        firstname_entry.pack(fill="x", padx=8, pady=4)

        # Create StringVar for firstName
        firstname_var = tk.StringVar()
        firstname_entry.config(textvariable=firstname_var)
        self.detail_form_elements["firstName"] = firstname_var

        # lastName (กว้าง 30% แต่จำกัดความกว้างสูงสุด)
        lastname_container = tk.Frame(
            name_inputs_container,
            bg=self.style["bg_primary"],
            highlightthickness=1,
            highlightbackground=self.style["bg_tertiary"],
            highlightcolor=self.style["accent"],
            width=100,  # จำกัดความกว้าง
        )
        lastname_container.pack(side="right", fill="y", padx=(5, 0))
        lastname_container.pack_propagate(False)  # ไม่ให้ขยายตาม content

        lastname_entry = tk.Entry(
            lastname_container,
            bg=self.style["bg_primary"],
            fg=self.style["text_primary"],
            insertbackground=self.style["text_primary"],
            font=(self.font, self.font_size_small),  # ใช้ฟอนต์เล็กลง
            bd=0,
            relief="flat",
            width=10,  # จำกัดที่ 10 ตัวอักษร
        )
        lastname_entry.pack(fill="both", expand=True, padx=6, pady=4)

        # Create StringVar for lastName
        lastname_var = tk.StringVar()
        lastname_entry.config(textvariable=lastname_var)
        self.detail_form_elements["lastName"] = lastname_var

        # Placeholder text for lastName
        lastname_entry.insert(0, "Surname")
        lastname_entry.config(fg=self.style["text_secondary"])

        # Focus effects สำหรับ firstName
        firstname_entry.bind(
            "<FocusIn>",
            lambda e: firstname_container.config(
                highlightbackground=self.style["accent"]
            ),
        )
        firstname_entry.bind(
            "<FocusOut>",
            lambda e: firstname_container.config(
                highlightbackground=self.style["bg_tertiary"]
            ),
        )
        firstname_entry.bind(
            "<KeyRelease>", lambda e: setattr(self, "has_actual_changes", True)
        )

        # Focus effects สำหรับ lastName
        def on_lastname_focus_in(e):
            lastname_container.config(highlightbackground=self.style["accent"])
            if lastname_entry.get() == "Surname":
                lastname_entry.delete(0, tk.END)
                lastname_entry.config(fg=self.style["text_primary"])

        def on_lastname_focus_out(e):
            lastname_container.config(highlightbackground=self.style["bg_tertiary"])
            if not lastname_entry.get().strip():
                lastname_entry.insert(0, "Surname")
                lastname_entry.config(fg=self.style["text_secondary"])

        lastname_entry.bind("<FocusIn>", on_lastname_focus_in)
        lastname_entry.bind("<FocusOut>", on_lastname_focus_out)
        lastname_entry.bind(
            "<KeyRelease>", lambda e: setattr(self, "has_actual_changes", True)
        )

        # 🎨 Gender Row (ปุ่ม compact)
        gender_frame = tk.Frame(
            self.detail_form_frame,
            bg=self.style["bg_secondary"],
            pady=2,  # ลด padding
        )
        gender_frame.pack(fill="x", pady=2)

        gender_label = tk.Label(
            gender_frame,
            text="Gender:",
            font=(self.font, self.font_size_medium),
            bg=self.style["bg_secondary"],
            fg=self.style["text_secondary"],
        )
        gender_label.pack(anchor="w")

        # Container สำหรับปุ่ม gender (compact)
        gender_container = tk.Frame(gender_frame, bg=self.style["bg_secondary"])
        gender_container.pack(fill="x", pady=(2, 0))

        # สร้าง StringVar สำหรับ gender
        gender_var = tk.StringVar(value="Female")  # ค่าเริ่มต้น
        self.detail_form_elements["gender"] = gender_var

        # สร้างปุ่ม gender แบบ compact
        self.gender_buttons = {}
        gender_options = ["Male", "Female", "Neutral"]

        for i, gender in enumerate(gender_options):
            color = (
                "#007AFF"
                if gender == "Male"
                else "#FF69B4" if gender == "Female" else "#34C759"
            )

            btn = tk.Button(
                gender_container,
                text=gender,
                font=(self.font, self.font_size_small),  # ใช้ฟอนต์เล็กลง
                bg="#222222",
                fg=color,
                bd=0,
                relief="flat",
                padx=12,  # ลด padding
                pady=4,  # ลด padding
                command=lambda g=gender: self._set_gender(g),
            )
            btn.pack(side="left", padx=(0, 5))
            self.gender_buttons[gender] = btn

        # ตั้งค่าปุ่ม Female เป็น active เริ่มต้น
        self._set_gender("Female")

        # 🎨 Role และ Relationship แบบ compact
        compact_fields = [
            ("role", "Role:", "Adventure"),
            ("relationship", "Relationship:", "Neutral"),
        ]

        for field, label_text, default_value in compact_fields:
            field_frame = tk.Frame(
                self.detail_form_frame,
                bg=self.style["bg_secondary"],
                pady=2,  # ลด padding
            )
            field_frame.pack(fill="x", pady=2)

            # ป้ายชื่อฟิลด์
            label = tk.Label(
                field_frame,
                text=label_text,
                font=(self.font, self.font_size_medium),
                bg=self.style["bg_secondary"],
                fg=self.style["text_secondary"],
            )
            label.pack(anchor="w")

            # สร้าง Entry field
            entry_container = tk.Frame(
                field_frame,
                bg=self.style["bg_primary"],
                highlightthickness=1,
                highlightbackground=self.style["bg_tertiary"],
                highlightcolor=self.style["accent"],
            )
            entry_container.pack(fill="x", pady=(2, 0))

            entry = tk.Entry(
                entry_container,
                bg=self.style["bg_primary"],
                fg=self.style["text_primary"],
                insertbackground=self.style["text_primary"],
                font=(self.font, self.font_size_medium),
                bd=0,
                relief="flat",
            )
            entry.pack(fill="x", padx=8, pady=4)

            # Create StringVar
            field_var = tk.StringVar(value=default_value)
            entry.config(textvariable=field_var)
            self.detail_form_elements[field] = field_var

            # Focus effects
            entry.bind(
                "<FocusIn>",
                lambda e, w=entry_container: w.config(
                    highlightbackground=self.style["accent"]
                ),
            )
            entry.bind(
                "<FocusOut>",
                lambda e, w=entry_container: w.config(
                    highlightbackground=self.style["bg_tertiary"]
                ),
            )
            entry.bind(
                "<KeyRelease>", lambda e: setattr(self, "has_actual_changes", True)
            )

        # Pack ฟอร์มหลังสร้างฟิลด์เสร็จแล้ว
        self.detail_form_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=10)

    def _create_roles_layout(self):
        """สร้าง layout สำหรับ ROLES tab — dropdown เลือกตัวละครจาก MAIN เท่านั้น"""

        # ตรวจสอบและสร้าง detail_form_frame
        form_frame_exists = (
            hasattr(self, "detail_form_frame") and self.detail_form_frame is not None
        )
        if form_frame_exists:
            try:
                self.detail_form_frame.winfo_exists()
                for widget in self.detail_form_frame.winfo_children():
                    widget.destroy()
            except (AttributeError, tk.TclError):
                form_frame_exists = False

        if not form_frame_exists:
            if hasattr(self, "detail_content_frame") and self.detail_content_frame.winfo_exists():
                self.detail_form_frame = tk.Frame(
                    self.detail_content_frame, bg=self.style["bg_secondary"]
                )
            else:
                return

        self.detail_form_elements = {}

        # ดึงชื่อจาก main_characters
        all_main_names = []
        for char in self.data.get("main_characters", []):
            name = char.get("firstName", "")
            if name:
                all_main_names.append(name)

        # ดึงชื่อที่มี roles แล้ว
        existing_roles = set(self.data.get("character_roles", {}).keys())

        # กรองเฉพาะที่ยังไม่มี roles (case-insensitive)
        existing_lower = {n.lower() for n in existing_roles}
        available_names = [n for n in all_main_names if n.lower() not in existing_lower]
        available_names.sort()

        # === Character field (Dropdown) ===
        char_frame = tk.Frame(self.detail_form_frame, bg=self.style["bg_secondary"], pady=4)
        char_frame.pack(fill="x", pady=4)

        char_label = tk.Label(
            char_frame, text="Character:",
            font=(self.font, self.font_size_medium),
            bg=self.style["bg_secondary"], fg=self.style["text_secondary"],
        )
        char_label.pack(anchor="w")

        char_var = tk.StringVar()
        self.detail_form_elements["character"] = char_var

        if available_names:
            # สร้าง ttk style สำหรับ Combobox dark theme
            combo_style = ttk.Style()
            combo_style.configure(
                "Dark.TCombobox",
                fieldbackground=self.style["bg_primary"],
                background=self.style["bg_tertiary"],
                foreground=self.style["text_primary"],
                arrowcolor=self.style["text_secondary"],
                selectbackground=self.style["accent"],
                selectforeground="white",
            )
            combo_style.map("Dark.TCombobox",
                fieldbackground=[("readonly", self.style["bg_primary"])],
                foreground=[("readonly", self.style["text_primary"])],
            )

            combo = ttk.Combobox(
                char_frame, textvariable=char_var,
                values=available_names, state="readonly",
                font=(self.font, self.font_size_medium),
                style="Dark.TCombobox",
            )
            combo.pack(fill="x", pady=(4, 0))
            # เลือกตัวแรกเป็นค่าเริ่มต้น
            combo.current(0)
        else:
            # ไม่มีตัวละครที่ยังไม่มี roles
            no_char_label = tk.Label(
                char_frame,
                text="✅ ตัวละครหลักทุกตัวมีน้ำเสียงแล้ว",
                font=(self.font, self.font_size_small),
                bg=self.style["bg_secondary"], fg=self.style["success"],
            )
            no_char_label.pack(anchor="w", pady=(4, 0))

            # ซ่อนปุ่ม ADD ENTRY
            if hasattr(self, "save_edit_btn") and self.save_edit_btn.winfo_exists():
                self.save_edit_btn.pack_forget()

            self.detail_form_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=10)
            return

        # === Style field (Text widget) ===
        style_frame = tk.Frame(self.detail_form_frame, bg=self.style["bg_secondary"], pady=4)
        style_frame.pack(fill="x", pady=4)

        style_label = tk.Label(
            style_frame, text="Style / น้ำเสียง:",
            font=(self.font, self.font_size_medium),
            bg=self.style["bg_secondary"], fg=self.style["text_secondary"],
        )
        style_label.pack(anchor="w")

        style_container = tk.Frame(
            style_frame, bg=self.style["bg_primary"],
            highlightthickness=1,
            highlightbackground=self.style["bg_tertiary"],
            highlightcolor=self.style["accent"],
        )
        style_container.pack(fill="x", pady=(4, 0))

        style_text = tk.Text(
            style_container, bg=self.style["bg_primary"],
            fg=self.style["text_primary"],
            insertbackground=self.style["text_primary"],
            font=(self.font, self.font_size_medium),
            bd=0, relief="flat", height=6, wrap="word",
        )
        style_text.pack(fill="x", padx=8, pady=4)
        self.detail_form_elements["style"] = style_text

        # Hint
        hint_label = tk.Label(
            style_frame,
            text="เช่น: พูดจาสุภาพ ใช้คำราชาศัพท์ / Speaks casually, uses slang",
            font=(self.font, self.font_size_xsmall),
            bg=self.style["bg_secondary"], fg=self.style["text_secondary"],
            wraplength=380,
        )
        hint_label.pack(anchor="w", pady=(2, 0))

        self.detail_form_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=10)

    def _set_gender(self, selected_gender):
        """ตั้งค่าเพศและอัปเดตปุ่ม - เวอร์ชันแก้ไข hover conflict"""
        try:
            # อัปเดต StringVar - เพิ่มการตรวจสอบ
            if (
                hasattr(self, "detail_form_elements")
                and "gender" in self.detail_form_elements
            ):
                self.detail_form_elements["gender"].set(selected_gender)

            # อัปเดตสีปุ่ม
            if hasattr(self, "gender_buttons"):
                for gender, btn in self.gender_buttons.items():
                    try:
                        if btn.winfo_exists():
                            color = (
                                "#007AFF"
                                if gender == "Male"
                                else "#FF69B4" if gender == "Female" else "#34C759"
                            )
                            if gender == selected_gender:
                                # ปุ่มที่เลือก: สีเข้มและหนา - ไม่มี hover
                                btn.configure(
                                    bg=color,
                                    fg="white",
                                    font=(self.font, self.font_size_small, "bold"),
                                )
                                # ลบ hover effects ชั่วคราว แล้วใส่ hover แบบ disabled
                                btn.unbind("<Enter>")
                                btn.unbind("<Leave>")
                                # ใส่ hover effects ที่ไม่ทำอะไร (เพื่อไม่ให้เปลี่ยนสี)
                                btn.bind("<Enter>", lambda e: None)
                                btn.bind("<Leave>", lambda e: None)
                            else:
                                # ปุ่มอื่น: สีจาง + hover effects ปกติ
                                btn.configure(
                                    bg="#222222",
                                    fg=color,
                                    font=(self.font, self.font_size_small),
                                )
                                # ลบ hover effects เก่า แล้วใส่ใหม่
                                btn.unbind("<Enter>")
                                btn.unbind("<Leave>")
                                # เพิ่ม hover effects ปกติ
                                btn.bind(
                                    "<Enter>",
                                    lambda e, b=btn: (
                                        b.configure(bg="#2a2a2a")
                                        if b.winfo_exists()
                                        else None
                                    ),
                                )
                                btn.bind(
                                    "<Leave>",
                                    lambda e, b=btn: (
                                        b.configure(bg="#222222")
                                        if b.winfo_exists()
                                        else None
                                    ),
                                )
                    except tk.TclError:
                        # Widget ถูกทำลายแล้ว - ข้ามไป
                        continue

            # 🔥 ลบระบบ unsaved changes - ไม่ต้องตรวจสอบการเปลี่ยนแปลง
            # if hasattr(self, "has_actual_changes"):
            #     self.has_actual_changes = True

        except Exception as e:
            # Log error ถ้ามี logging manager
            if hasattr(self, "logging_manager"):
                self.logging_manager.log_error(f"Error in _set_gender: {e}")

    def _create_word_fixes_layout(self):
        """สร้าง layout พิเศษสำหรับ word_fixes แบบ 2 ฝั่ง (คำผิด | คำถูก)"""

        # 🎯 ตรวจสอบและสร้าง detail_form_frame ถ้าจำเป็น
        form_frame_exists = (
            hasattr(self, "detail_form_frame") and self.detail_form_frame is not None
        )

        if form_frame_exists:
            try:
                self.detail_form_frame.winfo_exists()
                for widget in self.detail_form_frame.winfo_children():
                    widget.destroy()
            except (AttributeError, tk.TclError):
                form_frame_exists = False

        if not form_frame_exists:
            if (
                hasattr(self, "detail_content_frame")
                and self.detail_content_frame.winfo_exists()
            ):
                self.detail_form_frame = tk.Frame(
                    self.detail_content_frame, bg=self.style["bg_secondary"]
                )
            else:
                return

        # Reset form elements dictionary
        self.detail_form_elements = {}

        # สร้าง container หลักสำหรับ layout แนวตั้ง
        main_container = tk.Frame(self.detail_form_frame, bg=self.style["bg_secondary"])
        main_container.pack(fill="both", expand=True, padx=15, pady=10)

        # กำหนด grid weights สำหรับ 2 แถว (แนวตั้ง)
        main_container.grid_rowconfigure(0, weight=1)
        main_container.grid_rowconfigure(1, weight=1)
        main_container.grid_columnconfigure(0, weight=1)

        # === ด้านบน: ก่อนแก้ไข ===
        top_frame = tk.Frame(
            main_container, bg=self.style["bg_tertiary"], relief="solid", bd=1
        )
        top_frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=(0, 3))
        top_frame.grid_rowconfigure(1, weight=1)
        top_frame.grid_columnconfigure(0, weight=1)

        # หัวข้อด้านบน
        top_title = tk.Label(
            top_frame,
            text="ก่อนแก้ไข",
            font=(self.font, self.font_size_medium_bold),
            bg=self.style["bg_tertiary"],
            fg="#FF6B6B",
            anchor="center",
            pady=8,
        )
        top_title.grid(row=0, column=0, sticky="ew")

        # ช่องใส่ก่อนแก้ไข
        incorrect_var = tk.StringVar()
        incorrect_entry = tk.Entry(
            top_frame,
            textvariable=incorrect_var,
            font=(self.font, self.font_size_medium),
            bg=self.style["bg_secondary"],
            fg=self.style["text_primary"],
            relief="flat",
            bd=0,
            justify="center",
            insertbackground=self.style["text_primary"],
        )
        incorrect_entry.grid(row=1, column=0, sticky="ew", padx=8, pady=(5, 15))

        # === ด้านล่าง: หลังแก้ไข ===
        bottom_frame = tk.Frame(
            main_container, bg=self.style["bg_tertiary"], relief="solid", bd=1
        )
        bottom_frame.grid(row=1, column=0, sticky="nsew", padx=0, pady=(3, 0))
        bottom_frame.grid_rowconfigure(1, weight=1)
        bottom_frame.grid_columnconfigure(0, weight=1)

        # หัวข้อด้านล่าง
        bottom_title = tk.Label(
            bottom_frame,
            text="หลังแก้ไข",
            font=(self.font, self.font_size_medium_bold),
            bg=self.style["bg_tertiary"],
            fg="#4ECDC4",
            anchor="center",
            pady=8,
        )
        bottom_title.grid(row=0, column=0, sticky="ew")

        # ช่องใส่หลังแก้ไข
        correct_var = tk.StringVar()
        correct_entry = tk.Entry(
            bottom_frame,
            textvariable=correct_var,
            font=(self.font, self.font_size_medium),
            bg=self.style["bg_secondary"],
            fg=self.style["text_primary"],
            relief="flat",
            bd=0,
            justify="center",
            insertbackground=self.style["text_primary"],
        )
        correct_entry.grid(row=1, column=0, sticky="ew", padx=8, pady=(5, 15))

        # เก็บ StringVars ลงใน form elements
        self.detail_form_elements["incorrect"] = incorrect_var
        self.detail_form_elements["correct"] = correct_var

        # แสดง detail_form_frame (ใช้ grid ให้ตรงกับ detail_content_frame)
        self.detail_form_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=10)

    def _create_word_fixes_detail_view(self, data):
        """สร้าง detail view พิเศษสำหรับ word_fixes แบบแนวตั้ง (แสดงรายละเอียด)"""

        # สร้าง container หลักสำหรับ layout แนวตั้ง
        main_container = tk.Frame(
            self.detail_content_frame, bg=self.style["bg_secondary"]
        )
        main_container.pack(fill="both", expand=True, padx=5, pady=5)

        # กำหนด grid weights สำหรับ 2 แถว
        main_container.grid_rowconfigure(0, weight=1)
        main_container.grid_rowconfigure(1, weight=1)
        main_container.grid_columnconfigure(0, weight=1)

        # === ด้านบน: ก่อนแก้ไข ===
        top_frame = tk.Frame(
            main_container, bg=self.style["bg_tertiary"], relief="solid", bd=1
        )
        top_frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=(0, 3))

        # หัวข้อด้านบน
        top_title = tk.Label(
            top_frame,
            text="ก่อนแก้ไข",
            font=(self.font, self.font_size_medium),
            bg=self.style["bg_tertiary"],
            fg="#FF6B6B",  # สีแดงอ่อนสำหรับก่อนแก้ไข
            pady=8,
        )
        top_title.pack(fill="x", pady=(10, 5))

        # แสดงข้อความก่อนแก้ไข
        incorrect_label = tk.Label(
            top_frame,
            text=data.get("key", "???"),
            font=(self.font, self.font_size_large_bold),
            bg=self.style["bg_tertiary"],
            fg=self.style["text_primary"],
            wraplength=380,
            justify="center",
        )
        incorrect_label.pack(fill="x", padx=15, pady=(5, 15))

        # === ด้านล่าง: หลังแก้ไข ===
        bottom_frame = tk.Frame(
            main_container, bg=self.style["bg_tertiary"], relief="solid", bd=1
        )
        bottom_frame.grid(row=1, column=0, sticky="nsew", padx=0, pady=(3, 0))

        # หัวข้อด้านล่าง
        bottom_title = tk.Label(
            bottom_frame,
            text="หลังแก้ไข",
            font=(self.font, self.font_size_medium),
            bg=self.style["bg_tertiary"],
            fg="#4ECDC4",  # สีเขียวอ่อนสำหรับหลังแก้ไข
            pady=8,
        )
        bottom_title.pack(fill="x", pady=(10, 5))

        # แสดงข้อความหลังแก้ไข
        correct_label = tk.Label(
            bottom_frame,
            text=data.get("value", "???"),
            font=(self.font, self.font_size_large_bold),
            bg=self.style["bg_tertiary"],
            fg=self.style["text_primary"],
            wraplength=380,
            justify="center",
        )
        correct_label.pack(fill="x", padx=15, pady=(5, 15))

        # เก็บ reference เพื่อใช้งานในอนาคต
        self.current_detail_widget = main_container

    def _on_field_focus(self, field_name):
        """จัดการเมื่อผู้ใช้ focus ที่ field (optional method สำหรับ tracking)"""
        # เมธอดนี้สามารถใช้สำหรับ tracking การใช้งาน หรือ validation
        # ปัจจุบันไม่จำเป็นต้องทำอะไร แต่เตรียมไว้สำหรับการพัฒนาในอนาคต
        pass

    def _select_gender_tag(self, gender, var):
        """จัดการเมื่อมีการคลิกที่ปุ่ม tag เพศ"""
        try:
            # กำหนดค่าให้กับ StringVar
            var.set(gender)

            # 🔥 ลบระบบ unsaved changes - ไม่ต้องตรวจสอบการเปลี่ยนแปลง
            # if hasattr(self, "has_actual_changes"):
            #     self.has_actual_changes = True

            # อัปเดตสถานะของปุ่ม tag
            if hasattr(self, "gender_buttons"):
                # ปรับสถานะปุ่มทั้งหมด
                for g, btn in self.gender_buttons.items():
                    if btn.winfo_exists():
                        if g == gender:
                            # ปุ่มที่เลือก: สีเข้มและหนา
                            color = (
                                "#007AFF"
                                if g == "Male"
                                else "#FF69B4" if g == "Female" else "#34C759"
                            )
                            btn.configure(
                                bg=color,
                                fg="white",
                                font=(self.font, self.font_size_small, "bold"),
                            )
                        else:
                            # ปุ่มอื่น: สีจาง
                            color = (
                                "#007AFF"
                                if g == "Male"
                                else "#FF69B4" if g == "Female" else "#34C759"
                            )
                            btn.configure(
                                bg="#222222",
                                fg=color,
                                font=(self.font, self.font_size_small),
                            )
        except Exception as e:
            self.logging_manager.log_error(f"Error selecting gender tag: {e}")

    def _show_add_dialog(self):
        """แสดงฟอร์มสำหรับเพิ่มรายการใหม่ (ทำหน้าที่เป็นตัวกลางเรียกใช้งาน _clear_detail_form เท่านั้น)"""

        # ล้างฟอร์ม

        self._clear_detail_form()

        # อัพเดทหัวเรื่อง

        section_title = self.current_section.replace("_", " ").title()

        self.detail_title.configure(text=f"Add New {section_title}")

    def _clear_detail_form(self):
        """ล้างข้อมูลในฟอร์ม - รองรับ compact layout"""

        for field, var in self.detail_form_elements.items():
            if isinstance(var, tk.Text):
                var.delete("1.0", tk.END)
            else:
                # 🎨 จัดการ lastName พิเศษสำหรับ compact layout
                if field == "lastName" and self.current_section == "main_characters":
                    var.set("")  # เคลียร์ค่า
                    # หา entry widget เพื่อรีเซ็ต placeholder
                    try:
                        for widget in self.detail_form_frame.winfo_children():
                            if isinstance(widget, tk.Frame):
                                for subwidget in widget.winfo_children():
                                    if isinstance(subwidget, tk.Frame):
                                        for entry_widget in subwidget.winfo_children():
                                            if (
                                                isinstance(entry_widget, tk.Entry)
                                                and entry_widget.cget("width") == 10
                                            ):
                                                entry_widget.delete(0, tk.END)
                                                entry_widget.insert(0, "Surname")
                                                entry_widget.config(
                                                    fg=self.style["text_secondary"]
                                                )
                                                break
                    except:
                        pass  # ไม่เป็นไร ถ้าหา widget ไม่เจอ
                else:
                    var.set("")

    def _save_detail_edit(self):
        """บันทึกการแก้ไขรายละเอียดและบันทึกลงไฟล์ทันที (ไม่มีการถามยืนยัน)"""
        # ⭐ เพิ่มการตรวจสอบและ debug ข้อมูลที่ละเอียดขึ้น
        has_current_edit_data = hasattr(self, "current_edit_data")
        current_edit_value = getattr(self, "current_edit_data", "NOT_SET")

        if not has_current_edit_data or not self.current_edit_data:
            debug_msg = (
                f"Attempted to save edit with no current_edit_data. "
                f"has_attr={has_current_edit_data}, "
                f"value={current_edit_value}, "
                f"current_section={getattr(self, 'current_section', 'NOT_SET')}"
            )
            self.logging_manager.log_warning(debug_msg)

            # ลองตรวจสอบว่ามี form elements อยู่หรือไม่
            if hasattr(self, "detail_form_elements") and self.detail_form_elements:
                self.logging_manager.log_warning(
                    f"Form elements exist but current_edit_data is missing. "
                    f"Available fields: {list(self.detail_form_elements.keys())}"
                )

            self.flash_error_message("ไม่สามารถบันทึกได้: ไม่พบข้อมูลที่กำลังแก้ไข")
            return  # ไม่ได้อยู่ในโหมดแก้ไข

        # เก็บข้อมูลจากฟอร์ม
        updated_data_from_form = {}
        form_valid = True
        missing_fields = []
        for field, widget_var in self.detail_form_elements.items():
            value = ""
            if isinstance(widget_var, tk.Text):
                value = widget_var.get("1.0", tk.END).strip()
            elif isinstance(widget_var, tk.StringVar):
                value = widget_var.get().strip()
            else:
                self.logging_manager.log_warning(
                    f"Unknown widget type in form elements: {type(widget_var)}"
                )
                continue  # ข้าม widget ที่ไม่รู้จัก

            updated_data_from_form[field] = value

            # 🎨 จัดการ lastName placeholder สำหรับ main_characters
            if field == "lastName" and self.current_section == "main_characters":
                if value == "Surname" or not value.strip():
                    updated_data_from_form[field] = ""  # เก็บเป็นค่าว่าง

            # ตรวจสอบ field ที่จำเป็น (ตัวอย่าง: สำหรับ dict sections ต้องมี key)
            if self.current_section in ["lore", "character_roles", "word_fixes"]:
                key_field_map = {
                    "lore": "term",
                    "character_roles": "character",
                    "word_fixes": "incorrect",
                }
                if field == key_field_map.get(self.current_section) and not value:
                    missing_fields.append(field.capitalize())
                    form_valid = False
            elif self.current_section == "main_characters":
                if field == "firstName" and not value:
                    missing_fields.append(field.capitalize())
                    form_valid = False
            elif self.current_section == "npcs":
                if field == "name" and not value:
                    missing_fields.append(field.capitalize())
                    form_valid = False

        if not form_valid:
            messagebox.showwarning(
                "ข้อมูลไม่ครบถ้วน", f"กรุณากรอกข้อมูลในช่อง: {', '.join(missing_fields)}"
            )
            return

        # อัพเดทข้อมูลใน self.data
        update_success = self._update_data_item(updated_data_from_form)

        if update_success:
            # บันทึกการเปลี่ยนแปลงลงไฟล์ทันที
            save_success = self.save_changes()  # save_changes มีการ backup และเขียนไฟล์

            if save_success:
                # ======= เพิ่มส่วนนี้: อัพเดท Treeview และ tree_items =========
                # 1. หา Treeview item ที่กำลังแก้ไข
                selected_items = self.tree.selection()
                if selected_items:
                    selected_iid = selected_items[0]

                    # 2. อัพเดทข้อมูลใน tree_items ด้วยข้อมูลใหม่
                    if selected_iid in self.tree_items:
                        self.tree_items[selected_iid] = updated_data_from_form

                        # 3. อัพเดทการแสดงผลใน Treeview
                        name_value = ""
                        type_value = ""

                        if self.current_section == "main_characters":
                            name_value = updated_data_from_form.get("firstName", "")
                            if updated_data_from_form.get("lastName"):
                                name_value += (
                                    f" {updated_data_from_form.get('lastName')}"
                                )
                            type_value = updated_data_from_form.get("gender", "")
                        elif self.current_section == "npcs":
                            name_value = updated_data_from_form.get("name", "")
                            type_value = updated_data_from_form.get("role", "")
                        elif self.current_section in [
                            "lore",
                            "character_roles",
                            "word_fixes",
                        ]:
                            key_field_map = {
                                "lore": "term",
                                "character_roles": "character",
                                "word_fixes": "incorrect",
                            }
                            key_field = key_field_map.get(self.current_section)

                            if key_field and key_field in updated_data_from_form:
                                name_value = updated_data_from_form.get(key_field, "")

                            # กำหนดประเภทตาม section
                            if self.current_section == "lore":
                                type_value = "Lore"
                            elif self.current_section == "character_roles":
                                type_value = "Role"
                            else:
                                type_value = "Fix"

                        # อัพเดทค่าใน Treeview
                        self.tree.item(selected_iid, values=(name_value, type_value))
                        # ==========================================================
                    else:
                        # กรณีไม่พบ iid ใน tree_items (ควรไม่เกิดขึ้น แต่เผื่อกรณีผิดพลาด)
                        self.logging_manager.log_warning(
                            f"Selected item {selected_iid} not found in tree_items after edit"
                        )
                        # รีเฟรชทั้งหมดในกรณีนี้
                        search_term = (
                            self.search_var.get().lower()
                            if self.search_var.get()
                            else None
                        )
                        self._clear_cards()
                        self._create_cards_for_section(search_term)
                else:
                    # กรณีไม่มีรายการที่ถูกเลือก (ควรไม่เกิดขึ้น แต่เผื่อกรณีผิดพลาด)
                    self.logging_manager.log_warning(
                        "No item selected in Treeview after edit, refreshing all items"
                    )
                    # รีเฟรชทั้งหมดในกรณีนี้
                    search_term = (
                        self.search_var.get().lower() if self.search_var.get() else None
                    )
                    self._clear_cards()
                    self._create_cards_for_section(search_term)

                # แสดงข้อความสำเร็จ
                self.flash_success_message("อัพเดตแล้ว!")
                self._update_status("อัพเดตข้อมูลเรียบร้อย")

                # ⭐ เพิ่มการ reset state หลัง save สำเร็จ เพื่อป้องกัน UI ค้าง
                self.current_edit_data = None  # ล้างข้อมูล edit ที่ค้างอยู่
                self.has_actual_changes = False  # ⭐ รีเซ็ต change tracking

                # กลับไปหน้าเดิม (แสดงรายการ) แทนการติดอยู่ในหน้า edit form
                try:
                    # ⭐ รีเซ็ตปุ่มกลับเป็น ADD ENTRY
                    if (
                        hasattr(self, "save_edit_btn")
                        and self.save_edit_btn.winfo_exists()
                    ):
                        self.save_edit_btn.configure(
                            text="ADD ENTRY", command=self._quick_add_new_entry
                        )

                    # ล้างการเลือกใน Treeview เพื่อกลับสู่สถานะปกติ
                    if hasattr(self, "tree") and self.tree.winfo_exists():
                        selection = self.tree.selection()
                        if selection:
                            self.tree.selection_remove(selection)

                    # ⭐ เพิ่มการ refresh ข้อมูลหลังบันทึกเสร็จ
                    # ล้างแคชการค้นหาเพื่อให้ได้ข้อมูลล่าสุด
                    if hasattr(self, "_search_cache"):
                        self._search_cache.clear()

                    # รีเฟรชการแสดงผลใน Treeview
                    search_term = (
                        self.search_var.get().lower() if self.search_var.get() else None
                    )
                    self._create_cards_for_section(search_term)

                    self._hide_detail_form()  # รีเซ็ต panel ขวากลับสู่สถานะ add entry
                except Exception as e:
                    self.logging_manager.log_warning(
                        f"Error resetting detail form after save: {e}"
                    )
                    # Fallback: อย่างน้อยก็ clear form elements
                    if hasattr(self, "detail_form_elements"):
                        self.detail_form_elements.clear()
            else:
                # แสดงข้อความเตือนหากบันทึกไม่สำเร็จ
                self.flash_error_message("อัพเดตข้อมูลในโปรแกรมแล้ว แต่บันทึกลงไฟล์ไม่สำเร็จ")
                self._update_status("เกิดข้อผิดพลาดในการบันทึกลงไฟล์")
        else:
            # การอัพเดท self.data ล้มเหลว
            self._update_status("ไม่สามารถอัพเดตข้อมูลได้")

    def _update_data_item(self, updated_data_from_form):
        """อัพเดทข้อมูลในโครงสร้างข้อมูล (self.data)"""
        try:
            if not self.current_section or not self.current_edit_data:
                self.logging_manager.log_error(
                    "Cannot update: No current section or edit data."
                )
                return False

            # กรณีรายการ (List of Dicts)
            if self.current_section in ["main_characters", "npcs"]:
                id_field_original = (
                    "firstName" if self.current_section == "main_characters" else "name"
                )
                original_id = self.current_edit_data.get(id_field_original)

                if original_id is None:
                    self.logging_manager.log_error(
                        f"Original ID not found in current_edit_data for section {self.current_section}"
                    )
                    return False

                found_index = -1
                for i, item in enumerate(self.data[self.current_section]):
                    if item.get(id_field_original) == original_id:
                        found_index = i
                        break

                if found_index != -1:
                    self.data[self.current_section][found_index].update(
                        updated_data_from_form
                    )
                    # 🔥 ลบระบบ unsaved changes - บันทึกทันทีไม่ต้องแจ้งเตือน
                    # self.has_unsaved_changes = True
                    self.logging_manager.log_info(
                        f"Updated item at index {found_index} in {self.current_section}"
                    )
                    return True
                else:
                    self.logging_manager.log_error(
                        f"Could not find item with {id_field_original}='{original_id}' to update."
                    )
                    return False

            # กรณีพจนานุกรม (Dict)
            elif self.current_section in ["lore", "character_roles", "word_fixes"]:
                original_key = self.current_edit_data.get("key")  # Key เดิมที่กำลังแก้ไข

                form_key_field = None
                form_value_field = None
                if self.current_section == "lore":
                    form_key_field = "term"
                    form_value_field = "description"
                elif self.current_section == "character_roles":
                    form_key_field = "character"
                    form_value_field = "style"
                elif self.current_section == "word_fixes":
                    form_key_field = "incorrect"
                    form_value_field = "correct"

                new_key = updated_data_from_form.get(form_key_field)
                new_value = updated_data_from_form.get(form_value_field)

                if original_key is None or new_key is None or new_value is None:
                    self.logging_manager.log_error(
                        "Missing key/value data for dictionary update."
                    )
                    messagebox.showerror("Error", "Missing required field for update.")
                    return False

                # ตรวจสอบว่า key เดิมมีอยู่จริง
                if original_key not in self.data[self.current_section]:
                    self.logging_manager.log_error(
                        f"Original key '{original_key}' not found in {self.current_section} for update."
                    )
                    messagebox.showerror(
                        "Error",
                        f"Original entry '{original_key}' not found. Cannot update.",
                    )
                    return False

                # กรณี Key ไม่เปลี่ยน
                if original_key == new_key:
                    self.data[self.current_section][new_key] = new_value
                # กรณี Key เปลี่ยน
                else:
                    # ตรวจสอบว่า Key ใหม่ซ้ำหรือไม่
                    if new_key in self.data[self.current_section]:
                        messagebox.showerror(
                            "Error",
                            f"The key '{new_key}' already exists. Cannot rename.",
                        )
                        return False
                    # ลบ Key เดิม แล้วเพิ่ม Key ใหม่ (อาจทำให้ลำดับเปลี่ยน ถ้าสำคัญต้องจัดการเพิ่ม)
                    del self.data[self.current_section][original_key]
                    self.data[self.current_section][new_key] = new_value
                    self.logging_manager.log_info(
                        f"Renamed key '{original_key}' to '{new_key}' in {self.current_section}"
                    )

                # 🔥 ลบระบบ unsaved changes - บันทึกทันทีไม่ต้องแจ้งเตือน
                # self.has_unsaved_changes = True
                self.logging_manager.log_info(
                    f"Updated entry for key '{new_key}' in {self.current_section}"
                )
                return True

            else:
                self.logging_manager.log_error(
                    f"Update logic not defined for section: {self.current_section}"
                )
                return False

        except Exception as e:
            self.logging_manager.log_error(f"Update data item error: {e}")
            messagebox.showerror("Error", f"Failed to update data: {str(e)}")
            return False

    def _add_data_item(self, new_entry):
        """เพิ่มรายการใหม่ในโครงสร้างข้อมูล (ถ้า key ซ้ำ จะเขียนทับเลย)"""
        try:
            if not self.current_section:
                self.logging_manager.log_error(
                    "Cannot add item: No current section selected."
                )
                return False

            # กรณีรายการ (List of Dicts)
            if self.current_section in ["main_characters", "npcs"]:
                key_field = (
                    "firstName" if self.current_section == "main_characters" else "name"
                )
                new_key_value = new_entry.get(key_field)

                if not new_key_value:  # ตรวจสอบว่า key field ไม่ใช่ค่าว่าง
                    messagebox.showerror(
                        "ข้อมูลไม่ถูกต้อง", f"กรุณากรอกข้อมูลสำหรับ '{key_field}'"
                    )
                    return False

                existing_index = -1
                for i, item in enumerate(self.data[self.current_section]):
                    if item.get(key_field) == new_key_value:
                        existing_index = i
                        break

                if existing_index != -1:
                    # --- ลบส่วนที่ถามยืนยัน ---
                    # if messagebox.askyesno(...):
                    self.logging_manager.log_info(
                        f"Overwriting existing entry with {key_field}='{new_key_value}' in {self.current_section}"
                    )
                    self.data[self.current_section][existing_index] = new_entry
                    # 🔥 ลบระบบ unsaved changes - บันทึกทันทีไม่ต้องแจ้งเตือน
                    # self.has_unsaved_changes = True
                    return True
                    # else:
                    #    return False # User chose not to overwrite
                else:
                    # เพิ่มรายการใหม่
                    self.data[self.current_section].append(new_entry)
                    # 🔥 ลบระบบ unsaved changes - บันทึกทันทีไม่ต้องแจ้งเตือน
                    # self.has_unsaved_changes = True
                    self.logging_manager.log_info(
                        f"Added new entry with {key_field}='{new_key_value}' to {self.current_section}"
                    )
                    return True

            # กรณีพจนานุกรม (Dict)
            elif self.current_section in ["lore", "character_roles", "word_fixes"]:
                key = None
                value = None
                key_field_name = ""  # สำหรับแสดงใน log/error

                if self.current_section == "lore":
                    key_field_name = "term"
                    key = new_entry.get(key_field_name)
                    value = new_entry.get("description")
                elif self.current_section == "character_roles":
                    key_field_name = "character"
                    key = new_entry.get(key_field_name)
                    value = new_entry.get("style")
                elif self.current_section == "word_fixes":
                    key_field_name = "incorrect"
                    key = new_entry.get(key_field_name)
                    value = new_entry.get("correct")

                if not key:  # ตรวจสอบว่า key ไม่ใช่ค่าว่าง
                    messagebox.showerror(
                        "ข้อมูลไม่ถูกต้อง", f"กรุณากรอกข้อมูลสำหรับ '{key_field_name}'"
                    )
                    return False

                if value is not None:  # Value สามารถเป็นสตริงว่างได้
                    # ตรวจสอบว่ามีรายการซ้ำหรือไม่
                    if key in self.data[self.current_section]:
                        # --- ลบส่วนที่ถามยืนยัน ---
                        # if messagebox.askyesno(...):
                        self.logging_manager.log_info(
                            f"Overwriting existing entry for key='{key}' in {self.current_section}"
                        )
                        self.data[self.current_section][key] = value
                        # 🔥 ลบระบบ unsaved changes - บันทึกทันทีไม่ต้องแจ้งเตือน
                        # self.has_unsaved_changes = True
                        return True
                        # else:
                        #    return False # User chose not to overwrite
                    else:
                        # เพิ่มรายการใหม่
                        self.data[self.current_section][key] = value
                        # 🔥 ลบระบบ unsaved changes - บันทึกทันทีไม่ต้องแจ้งเตือน
                        # self.has_unsaved_changes = True
                        self.logging_manager.log_info(
                            f"Added new entry with key='{key}' to {self.current_section}"
                        )
                        return True
                else:
                    self.logging_manager.log_error(
                        f"Value is missing for key='{key}' in {self.current_section}"
                    )
                    messagebox.showerror("ข้อมูลไม่ถูกต้อง", f"ข้อมูลสำหรับ '{key}' ไม่ครบถ้วน")
                    return False
            else:
                self.logging_manager.log_error(
                    f"Add logic not defined for section: {self.current_section}"
                )
                return False

        except Exception as e:
            self.logging_manager.log_error(f"Add data item error: {e}")
            messagebox.showerror("Error", f"Failed to add/update data: {str(e)}")
            return False

    def _synchronize_character_and_role(self, character_name, character_style=None):
        """ปรับปรุงข้อมูลบทบาทของตัวละครโดยอัตโนมัติเมื่อมีการเพิ่มหรือแก้ไขตัวละคร


        Args:

            character_name (str): ชื่อตัวละคร

            character_style (str, optional): รูปแบบของตัวละคร หากไม่ระบุจะใช้ค่าเริ่มต้น


        Returns:

            bool: True ถ้าสำเร็จ, False ถ้าไม่สำเร็จ

        """

        try:

            if not character_name:

                return False

            # ถ้าไม่ระบุ character_style ให้ใช้ค่าเริ่มต้น

            if not character_style:

                character_style = "ใช้ภาษาทั่วไปแบบสนทนาปกติ"

            # ตรวจสอบว่ามีตัวละครนี้ใน character_roles หรือไม่

            if character_name in self.data.get("character_roles", {}):

                # ถ้าไม่ได้ระบุ style ให้ใช้ค่าเดิม

                if not character_style:

                    return True

                # ถ้ามีการระบุ style ใหม่ ให้อัพเดต

                self.data["character_roles"][character_name] = character_style

                return True

            else:

                # เพิ่มตัวละครใหม่ใน character_roles

                if "character_roles" not in self.data:

                    self.data["character_roles"] = {}

                self.data["character_roles"][character_name] = character_style

                self.logging_manager.log_info(
                    f"เพิ่มตัวละคร '{character_name}' ใน character_roles สำเร็จ"
                )

                return True

        except Exception as e:

            self.logging_manager.log_error(f"ไม่สามารถปรับปรุงข้อมูลบทบาทของตัวละคร: {e}")

            return False

    def _on_card_edit(self, data):
        """จัดการเมื่อมีการคลิกแก้ไขการ์ด หรือดับเบิลคลิกรายการ"""
        # 🎯 แก้ไขปัญหา import scope - ย้าย import มาข้างนอก
        from tkinter import messagebox

        try:
            # 🔥 ลบระบบ unsaved changes ออกทั้งหมด
            # เมื่อเข้าโหมดแก้ไขแล้วไม่ได้กด save จะถือว่าไม่จำเป็นต้องเซฟ
            # รีเซ็ต state เดิมก่อนเสมอ (ไม่ถาม confirmation)

            if (
                hasattr(self, "current_edit_data")
                and self.current_edit_data is not None
            ):
                # มีการแก้ไขค้างอยู่ - รีเซ็ต state เดิมโดยไม่ถาม
                try:
                    self._hide_detail_form()  # รีเซ็ต form เดิม
                except Exception as e:
                    self.logging_manager.log_warning(
                        f"Error resetting previous edit state: {e}"
                    )
                    # Fallback: clear state variables manually
                    self.current_edit_data = None
                    if hasattr(self, "detail_form_elements"):
                        self.detail_form_elements.clear()

            # ตรวจสอบว่า detail_panel พร้อมใช้งานหรือไม่
            if (
                not hasattr(self, "detail_panel")
                or not self.detail_panel.winfo_exists()
            ):
                self.logging_manager.log_error(
                    "Detail panel does not exist in _on_card_edit"
                )
                self._create_detail_panel()  # พยายามสร้างใหม่ถ้าไม่มี
                if not self.detail_panel.winfo_exists():
                    messagebox.showerror(
                        "Error", "Cannot display edit form: Detail panel is missing."
                    )
                    return  # ออกถ้ายังสร้างไม่ได้

            self.current_edit_data = data  # เก็บข้อมูลที่จะแก้ไข
            self.has_actual_changes = False  # ⭐ เพิ่ม: ติดตามการเปลี่ยนแปลงจริง
            self._clear_detail_content_frame()  # ล้างพื้นที่ content กลาง

            # --- สร้างโครงสร้างพื้นฐานใหม่ภายใน detail_panel ถ้าจำเป็น ---
            # (อาจไม่จำเป็นต้องสร้าง title/button container ใหม่ทุกครั้ง ถ้า _clear_detail_content_frame ไม่ได้ลบมัน)
            # ตรวจสอบว่า title และ button container ยังอยู่หรือไม่ ถ้าไม่ ให้สร้างใหม่
            title_exists = (
                hasattr(self, "detail_title") and self.detail_title.winfo_exists()
            )
            button_cont_exists = (
                hasattr(self, "button_container")
                and self.button_container.winfo_exists()
            )
            save_btn_exists = (
                hasattr(self, "save_edit_btn") and self.save_edit_btn.winfo_exists()
            )

            if not title_exists:
                title_container = tk.Frame(
                    self.detail_panel, bg=self.style["bg_secondary"]
                )
                title_container.grid(row=0, column=0, sticky="ew", pady=(20, 10))
                self.detail_title = tk.Label(
                    title_container,
                    text="Edit",
                    font=(self.font, self.font_size_large_bold),
                    bg=self.style["bg_secondary"],
                    fg=self.style["text_primary"],
                )
                self.detail_title.pack()

            if not button_cont_exists:
                self.button_container = tk.Frame(
                    self.detail_panel, bg=self.style["bg_secondary"]
                )
                self.button_container.grid(
                    row=2, column=0, sticky="ew", pady=(10, 20), padx=20
                )
                save_btn_exists = False  # ต้องสร้างปุ่มใหม่ด้วย

            if not save_btn_exists:
                self.save_edit_btn = tk.Button(
                    self.button_container,
                    text="SAVE EDIT",  # ตั้งค่าเริ่มต้นสำหรับ Edit
                    bg=self.style["accent"],
                    fg="white",
                    font=(
                        self.font,
                        self.font_size_small,
                    ),  # 🎨 เปลี่ยนจาก medium เป็น small
                    bd=0,
                    relief="flat",
                    highlightthickness=0,
                    padx=8,  # 🎨 เปลี่ยนจาก 6 เป็น 8 (เพิ่มขึ้นเล็กน้อย)
                    pady=4,  # 🎨 เปลี่ยนจาก 6 เป็น 4 (เล็กลง)
                    command=self._save_detail_edit,
                )
                # ผูก hover effect ใหม่
                self.save_edit_btn.bind(
                    "<Enter>",
                    lambda e, btn=self.save_edit_btn: (
                        btn.configure(bg=self.style["accent_hover"])
                        if btn.winfo_exists()
                        else None
                    ),
                )
                self.save_edit_btn.bind(
                    "<Leave>",
                    lambda e, btn=self.save_edit_btn: (
                        btn.configure(bg=self.style["accent"])
                        if btn.winfo_exists()
                        else None
                    ),
                )
            else:
                # แค่กำหนดค่าปุ่มที่มีอยู่แล้ว
                self.save_edit_btn.configure(
                    text="SAVE EDIT", command=self._save_detail_edit
                )

            # สร้าง Widget ของฟอร์มภายใน self.detail_form_frame (ที่อยู่ใน detail_content_frame)
            self._create_detail_form_for_section()

            # แสดง detail_form_frame ใน content area (ใช้ grid)
            if (
                hasattr(self, "detail_form_frame")
                and self.detail_form_frame.winfo_exists()
            ):
                self.detail_form_frame.grid(
                    row=0, column=0, sticky="nsew"
                )  # แสดง Frame ที่มี widget ฟอร์ม
            else:
                self.logging_manager.log_error(
                    "detail_form_frame missing after creation in _on_card_edit"
                )
                return

            # เติมข้อมูลลงในฟอร์ม
            self._fill_detail_form(data)

            # อัพเดท Title หลักของ Panel ให้ถูกต้อง
            if self.current_section == "main_characters":
                edit_title = f"Edit: {data.get('firstName', '')}"
            elif self.current_section == "npcs":
                edit_title = f"Edit: {data.get('name', '')}"
            elif self.current_section in ["lore", "character_roles", "word_fixes"]:
                key_to_edit = data.get("key")
                if key_to_edit is None and self.current_section == "character_roles":
                    key_to_edit = data.get("character")
                elif key_to_edit is None and self.current_section == "lore":
                    key_to_edit = data.get("term")
                elif key_to_edit is None and self.current_section == "word_fixes":
                    key_to_edit = data.get("incorrect")
                edit_title = f"Edit: {key_to_edit or 'Entry'}"
            else:
                edit_title = f"Edit {self.current_section.replace('_', ' ').title()}"
            # ตรวจสอบ title_exists อีกครั้งก่อน configure
            if hasattr(self, "detail_title") and self.detail_title.winfo_exists():
                self.detail_title.configure(text=edit_title)

            # แสดงปุ่ม "SAVE EDIT" (ใช้ pack เพราะอยู่ใน button_container)
            if hasattr(self, "save_edit_btn") and self.save_edit_btn.winfo_exists():
                if not self.save_edit_btn.winfo_ismapped():
                    self.save_edit_btn.pack(fill="x")
            else:
                self.logging_manager.log_error(
                    "Save edit button missing or destroyed in _on_card_edit"
                )

            self.current_detail_widget = self.detail_form_frame  # เก็บ reference

            self.window.update_idletasks()

            # 🎯 แก้ไขปัญหา focus - ใช้วิธีที่ปลอดภัยกว่า
            first_field_key = next(iter(self.detail_form_elements.keys()), None)
            if first_field_key:
                first_field_widget = self.detail_form_elements.get(first_field_key)
                if first_field_widget and isinstance(
                    first_field_widget, (tk.Entry, tk.Text)
                ):
                    # 🎯 เปลี่ยนจาก window.after เป็น direct focus เพื่อหลีกเลี่ยง timer conflicts
                    try:
                        # ตรวจสอบ widget ยังอยู่และสามารถ focus ได้
                        if (
                            first_field_widget.winfo_exists()
                            and first_field_widget.winfo_viewable()
                        ):
                            # Focus ทันทีแทนการใช้ timer
                            first_field_widget.focus_set()
                            self.logging_manager.log_info(
                                f"Direct focus set to {first_field_key}"
                            )
                        else:
                            self.logging_manager.log_warning(
                                f"Cannot focus {first_field_key}: widget not ready"
                            )
                    except Exception as e:
                        self.logging_manager.log_warning(
                            f"Error setting focus to {first_field_key}: {e}"
                        )

                    # เคลียร์ _focus_after_id เพื่อป้องกัน confusion
                    self._focus_after_id = None
                else:
                    self._focus_after_id = None  # ไม่มี widget ให้ focus
            else:
                self._focus_after_id = None

        except Exception as e:
            self.logging_manager.log_error(f"Error showing edit form: {e}")
            import traceback

            self.logging_manager.log_error(traceback.format_exc())
            messagebox.showerror(
                "Error", f"An error occurred while preparing the edit form:\n{e}"
            )

    def _fill_detail_form(self, data):
        """เติมข้อมูลในฟอร์มรายละเอียด"""

        # ⭐ เพิ่ม debug logging สำหรับ word_fixes
        if self.current_section == "word_fixes":
            if hasattr(self, "logging_manager"):
                self.logging_manager.log_info(
                    f"Filling word_fixes form with data: {data}"
                )
                self.logging_manager.log_info(
                    f"Available form elements: {list(self.detail_form_elements.keys())}"
                )

        self._clear_detail_form()  # ล้างข้อมูลเก่าก่อน

        if not isinstance(data, dict):  # ตรวจสอบประเภทข้อมูล
            self.logging_manager.log_error(
                f"Invalid data type passed to _fill_detail_form: {type(data)}"
            )
            return

        # จัดการข้อมูลตาม section type
        if self.current_section in ["main_characters", "npcs"]:
            # กรณี List of Dicts: ใช้ key ของ data โดยตรง
            for field, widget_var in self.detail_form_elements.items():
                value = data.get(field, "")  # ดึงค่าจาก data dict

                # 🎨 จัดการ lastName พิเศษสำหรับ compact layout
                if field == "lastName" and self.current_section == "main_characters":
                    # ถ้า lastName ว่าง ไม่ต้องใส่อะไร (จะแสดง placeholder)
                    if value.strip():  # มีค่าจริง
                        widget_var.set(value)
                        # หา entry widget เพื่อเปลี่ยนสี
                        for widget in self.detail_form_frame.winfo_children():
                            if isinstance(widget, tk.Frame):
                                for subwidget in widget.winfo_children():
                                    if isinstance(subwidget, tk.Frame):
                                        for entry_widget in subwidget.winfo_children():
                                            if (
                                                isinstance(entry_widget, tk.Entry)
                                                and entry_widget.cget("width") == 10
                                            ):
                                                entry_widget.config(
                                                    fg=self.style["text_primary"]
                                                )
                                                break
                    # ถ้าไม่มีค่า ปล่อยให้เป็น placeholder
                    continue

                if isinstance(widget_var, tk.Text):
                    widget_var.insert("1.0", value)
                else:  # StringVar
                    widget_var.set(value)

                    # *** อัปเดตปุ่ม tag เพศสำหรับ compact layout ***
                    if field == "gender" and hasattr(self, "gender_buttons"):
                        self._set_gender(value)  # ใช้ฟังก์ชันใหม่
        elif self.current_section in ["lore", "character_roles", "word_fixes"]:
            # ⭐ สำหรับ word_fixes ต้องแน่ใจว่าใช้ layout แบบ 2 ฝั่ง
            if self.current_section == "word_fixes":
                # ตรวจสอบว่า layout ถูกสร้างแล้วหรือไม่
                if (
                    not hasattr(self, "detail_form_elements")
                    or "incorrect" not in self.detail_form_elements
                ):
                    if hasattr(self, "logging_manager"):
                        self.logging_manager.log_warning(
                            "word_fixes layout not found, recreating..."
                        )
                    # สร้าง layout ใหม่
                    self._create_word_fixes_layout()

            # [โค้ดส่วนนี้คงเดิม]
            # กรณี Dict: data ที่ส่งมาควรมี 'key' และ 'value'
            key_to_fill = data.get("key")
            value_to_fill = data.get("value", "")

            target_key_field = None
            target_value_field = None

            if self.current_section == "lore":
                target_key_field = "term"
                target_value_field = "description"
            elif self.current_section == "character_roles":
                target_key_field = "character"
                target_value_field = "style"
            elif self.current_section == "word_fixes":
                target_key_field = "incorrect"
                target_value_field = "correct"

            # ⭐ เพิ่ม debug logging สำหรับ word_fixes
            if self.current_section == "word_fixes":
                if hasattr(self, "logging_manager"):
                    self.logging_manager.log_info(
                        f"word_fixes - key_to_fill: '{key_to_fill}', value_to_fill: '{value_to_fill}'"
                    )
                    self.logging_manager.log_info(
                        f"word_fixes - target fields: {target_key_field}, {target_value_field}"
                    )

            # เติม Key
            if target_key_field and target_key_field in self.detail_form_elements:
                # ⭐ เพิ่ม logging สำหรับ word_fixes
                if self.current_section == "word_fixes" and hasattr(
                    self, "logging_manager"
                ):
                    self.logging_manager.log_info(
                        f"Setting {target_key_field} = '{key_to_fill}'"
                    )

                if isinstance(
                    self.detail_form_elements[target_key_field], tk.Text
                ):  # Should be Entry/StringVar
                    self.detail_form_elements[target_key_field].insert(
                        "1.0", key_to_fill or ""
                    )
                else:
                    self.detail_form_elements[target_key_field].set(key_to_fill or "")
            else:
                # ⭐ เพิ่มการแจ้งเตือนหาก field ไม่พบ (สำหรับ debug)
                if self.current_section == "word_fixes" and hasattr(
                    self, "logging_manager"
                ):
                    if target_key_field not in self.detail_form_elements:
                        self.logging_manager.log_warning(
                            f"word_fixes - {target_key_field} field not found in form elements!"
                        )

            # เติม Value
            if target_value_field and target_value_field in self.detail_form_elements:
                # ⭐ เพิ่ม logging สำหรับ word_fixes
                if self.current_section == "word_fixes" and hasattr(
                    self, "logging_manager"
                ):
                    self.logging_manager.log_info(
                        f"Setting {target_value_field} = '{value_to_fill}'"
                    )

                if isinstance(self.detail_form_elements[target_value_field], tk.Text):
                    self.detail_form_elements[target_value_field].insert(
                        "1.0", value_to_fill
                    )
                else:  # Should be Text for description/style, Entry for correct
                    self.detail_form_elements[target_value_field].set(value_to_fill)
            else:
                # ⭐ เพิ่มการแจ้งเตือนหาก field ไม่พบ (สำหรับ debug)
                if self.current_section == "word_fixes" and hasattr(
                    self, "logging_manager"
                ):
                    if target_value_field not in self.detail_form_elements:
                        self.logging_manager.log_warning(
                            f"word_fixes - {target_value_field} field not found in form elements!"
                        )
        else:
            self.logging_manager.log_warning(
                f"Attempted to fill form for unknown section: {self.current_section}"
            )

    def _on_card_delete(self, data):
        """จัดการเมื่อมีการคลิกลบการ์ด"""

        # ตรวจสอบการยืนยัน

        if self.current_section == "main_characters":

            name = data.get("firstName", "")

            if data.get("lastName"):

                name += f" {data.get('lastName')}"

            confirm_message = f"คุณแน่ใจหรือไม่ที่จะลบ '{name}'?"

        elif self.current_section == "npcs":

            confirm_message = f"คุณแน่ใจหรือไม่ที่จะลบ '{data.get('name', '')}'?"

        elif self.current_section in ["lore", "character_roles", "word_fixes"]:

            confirm_message = f"คุณแน่ใจหรือไม่ที่จะลบ '{data.get('key', '')}'?"

        else:

            confirm_message = "คุณแน่ใจหรือไม่ที่จะลบรายการนี้?"

        if not messagebox.askyesno("ยืนยันการลบ", confirm_message):

            return

        # เก็บค่าการค้นหาปัจจุบัน

        current_search = (
            self.search_var.get().lower() if self.search_var.get() else None
        )

        # ดำเนินการลบ

        if self._delete_data_item(data):

            # บันทึกการเปลี่ยนแปลงลงไฟล์ทันที

            save_success = self.save_changes()

            if save_success:

                # อัพเดตผลการค้นหาใหม่ถ้ามีการค้นหาอยู่

                if current_search:

                    # ล้างแคชการค้นหา

                    if hasattr(self, "_search_cache"):

                        self._search_cache = {}

                    # ทำการค้นหาใหม่เพื่ออัพเดตตัวเลข indicator

                    self._search_in_background(current_search)

                else:

                    # ถ้าไม่มีการค้นหา อัพเดตการ์ดตามปกติ

                    self._clear_cards()

                    self._create_cards_for_section()

                # ซ่อนรายละเอียดด้านขวาถ้ากำลังแสดงข้อมูลที่ถูกลบ

                if (
                    hasattr(self, "current_edit_data")
                    and self.current_edit_data == data
                ):

                    self._hide_detail_form()

                # แสดงข้อความสำเร็จ

                self.flash_success_message("ลบรายการและบันทึกลงไฟล์เรียบร้อยแล้ว")

                # อัพเดทสถานะ

                self._update_status("การเปลี่ยนแปลงถูกบันทึกแล้ว")

            else:

                # แสดงข้อความเตือนหากบันทึกไม่สำเร็จ

                self.flash_error_message(
                    "ลบรายการในหน่วยความจำแล้ว แต่ไม่สามารถบันทึกลงไฟล์ได้"
                )

    def _delete_data_item(self, data):
        """ลบรายการในโครงสร้างข้อมูล"""

        try:

            if not self.current_section:

                return False

            # กรณีรายการ (main_characters, npcs)

            if isinstance(self.data[self.current_section], list):

                # ค้นหารายการที่ต้องการลบ

                for i, item in enumerate(self.data[self.current_section]):

                    # ตรวจสอบว่าเป็นรายการเดียวกันหรือไม่

                    if self.current_section == "main_characters":

                        if item.get("firstName") == data.get("firstName"):

                            del self.data[self.current_section][i]

                            return True

                    elif self.current_section == "npcs":

                        if item.get("name") == data.get("name"):

                            del self.data[self.current_section][i]

                            return True

            # กรณีพจนานุกรม (lore, character_roles, word_fixes)

            elif isinstance(self.data[self.current_section], dict):

                key = data.get("key")

                if key in self.data[self.current_section]:

                    del self.data[self.current_section][key]

                    return True

            return False

        except Exception as e:

            self.logging_manager.log_error(f"Delete data error: {e}")

            messagebox.showerror("Error", f"Failed to delete data: {str(e)}")

            return False

    def _hide_detail_form(self):
        """รีเซ็ต Panel ขวา กลับสู่สถานะ Add Entry เริ่มต้น"""
        try:
            self.current_edit_data = None
            self.has_actual_changes = False  # ⭐ รีเซ็ต change tracking
            self._clear_detail_content_frame()  # ล้างพื้นที่ content

            # สร้าง Widget ของฟอร์มเปล่าสำหรับ section ปัจจุบัน
            self._create_detail_form_for_section()  # สร้าง widget ใน self.detail_form_frame

            # แสดง detail_form_frame ใน content area (ใช้ grid)
            if (
                hasattr(self, "detail_form_frame")
                and self.detail_form_frame.winfo_exists()
            ):
                self.detail_form_frame.grid(row=0, column=0, sticky="nsew")

            # อัพเดท Title หลักของ Panel สำหรับการ Add
            section_title = (
                self.current_section.replace("_", " ").title()
                if self.current_section
                else "Details"
            )
            self.detail_title.configure(text=f"Add New {section_title}")

            # ⭐ ปรับปรุง: แสดงปุ่ม "ADD ENTRY" เฉพาะเมื่อไม่มีการเลือกข้อมูลใน Treeview
            selected_items = (
                self.tree.selection()
                if hasattr(self, "tree") and self.tree.winfo_exists()
                else []
            )

            if not selected_items:
                # ไม่มีการเลือกข้อมูล - แสดงปุ่ม "ADD ENTRY"
                self.save_edit_btn.configure(
                    text="ADD ENTRY", command=self._quick_add_new_entry
                )
                if not self.save_edit_btn.winfo_ismapped():
                    self.save_edit_btn.pack(fill="x")  # Pack ปุ่มใน button_container
            else:
                # มีการเลือกข้อมูลอยู่ - แสดงปุ่ม "EDIT"
                self.save_edit_btn.configure(
                    text="EDIT", command=lambda: self._edit_selected_item()
                )
                if not self.save_edit_btn.winfo_ismapped():
                    self.save_edit_btn.pack(fill="x")  # Pack ปุ่มใน button_container

            self.current_detail_widget = self.detail_form_frame  # เก็บ reference

            self.window.update_idletasks()

        except Exception as e:
            self.logging_manager.log_error(f"Error hiding/resetting detail form: {e}")
            import traceback

            self.logging_manager.log_error(traceback.format_exc())

    def _edit_selected_item(self):
        """แก้ไขรายการที่เลือกใน Treeview"""
        try:
            selected_items = (
                self.tree.selection()
                if hasattr(self, "tree") and self.tree.winfo_exists()
                else []
            )

            if not selected_items:
                self.flash_error_message("กรุณาเลือกรายการที่ต้องการแก้ไข")
                return

            selected_iid = selected_items[0]

            if selected_iid in self.tree_items:
                item_data = self.tree_items[selected_iid]
                self._on_card_edit(item_data)
            else:
                self.logging_manager.log_error(
                    f"Selected item data not found for iid: {selected_iid}"
                )
                self.flash_error_message("ไม่พบข้อมูลรายการที่เลือก")

        except Exception as e:
            self.logging_manager.log_error(f"Error editing selected item: {e}")
            self.flash_error_message("เกิดข้อผิดพลาดในการแก้ไขรายการ")

    def flash_message(self, message, message_type="info"):
        """แสดงข้อความแจ้งเตือนแบบ fade effect"""

        colors = {
            "info": self.style["accent"],
            "error": self.style["error"],
            "success": self.style["success"],
            "warning": self.style["warning"],
        }

        bg_color = colors.get(message_type, colors["info"])

        popup = tk.Toplevel(self.window)

        popup.overrideredirect(True)

        popup.configure(bg=bg_color)

        popup.attributes("-alpha", 0.9)

        popup.attributes("-topmost", True)

        # จัดตำแหน่งกลางหน้าต่าง

        x = self.window.winfo_x() + self.window.winfo_width() // 2 - 150

        y = self.window.winfo_y() + self.window.winfo_height() // 2 - 30

        popup.geometry(f"300x60+{x}+{y}")

        # ข้อความ

        label = tk.Label(
            popup,
            text=message,
            fg=self.style["text_primary"],
            bg=bg_color,
            font=(self.font, 12),
            padx=20,
            pady=10,
        )

        label.pack(fill="both", expand=True)

        # Fade effect

        def fade_away():

            alpha = popup.attributes("-alpha")

            if alpha > 0:

                popup.attributes("-alpha", alpha - 0.1)

                popup.after(50, fade_away)

            else:

                popup.destroy()

        popup.after(1500, fade_away)

    def flash_success_message(self, message):
        """แสดงข้อความสำเร็จ"""

        self.flash_message(message, "success")

    def flash_error_message(self, message):
        """แสดงข้อความผิดพลาด"""

        self.flash_message(message, "error")

    def show_enhanced_character_added_dialog(self, character_name, character_data):
        """
        แสดง Enhanced Dialog Box สำหรับแจ้งการเพิ่มตัวละครใหม่
        ตามที่ผู้ใช้ต้องการ: สีสันโดดเด่น ข้อมูลชัดเจน ขนาดใหญ่ขึ้น
        """
        try:
            # สร้าง Enhanced Dialog
            dialog = tk.Toplevel(self.window)
            dialog.overrideredirect(True)
            dialog.attributes("-topmost", True)
            dialog.attributes("-alpha", 0.95)

            # 🔝 เพิ่ม z-level ให้สูงกว่า NPC Manager เพื่อแสดงบนสุด
            dialog.wm_attributes("-topmost", True)
            dialog.lift()  # ยกขึ้นบนสุด
            dialog.focus_set()  # ✅ ใช้ focus_set แทน focus_force สำหรับ dialog

            # ขนาดใหญ่ขึ้นตามที่ต้องการ (เพิ่มขนาดเพื่อให้ปุ่มเห็นชัดขึ้น)
            dialog_width = 480
            dialog_height = 300

            # จัดตำแหน่งกึ่งกลางหน้าจอ
            screen_width = dialog.winfo_screenwidth()
            screen_height = dialog.winfo_screenheight()
            x = (screen_width // 2) - (dialog_width // 2)
            y = (screen_height // 2) - (dialog_height // 2)

            dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")

            # สีสันตามที่ผู้ใช้ต้องการ: ขอบเหลือง พื้นหลังดำ ตัวอักษรเหลือง
            dialog.configure(bg="#000000")  # พื้นหลังดำ

            # สร้างขอบสีเหลือง
            border_frame = tk.Frame(dialog, bg="#FFD700", bd=3, relief="raised")  # ขอบสีเหลือง
            border_frame.pack(fill="both", expand=True, padx=3, pady=3)

            content_frame = tk.Frame(border_frame, bg="#000000")  # เนื้อหาพื้นหลังดำ
            content_frame.pack(fill="both", expand=True, padx=3, pady=3)

            # หัวข้อหลัก
            title_label = tk.Label(
                content_frame,
                text="✅ เพิ่มตัวละครใหม่สำเร็จ!",
                fg="#FFD700",  # ตัวอักษรสีเหลือง
                bg="#000000",  # พื้นหลังดำ
                font=(self.font, 16, "bold"),
                pady=5
            )
            title_label.pack()

            # ข้อมูลรายละเอียด
            gender = character_data.get("gender", "Female")
            role = character_data.get("role", "Adventure")
            relationship = character_data.get("relationship", "Neutral")

            details_text = f"ชื่อ: {character_name} | เพศ: {gender} | บทบาท: {role}\nสถานะความสัมพันธ์: {relationship}"

            details_label = tk.Label(
                content_frame,
                text=details_text,
                fg="#FFD700",  # ตัวอักษรสีเหลือง
                bg="#000000",  # พื้นหลังดำ
                font=(self.font, 12),
                pady=5
            )
            details_label.pack()

            # ข้อมูลไฟล์และคำแนะนำ
            info_text = "บันทึกลงไฟล์: npc.json\nหากต้องการแก้ไขสามารถทำได้ผ่าน NPC Manager"

            info_label = tk.Label(
                content_frame,
                text=info_text,
                fg="#CCCCCC",  # ตัวอักษรสีเทาอ่อน
                bg="#000000",  # พื้นหลังดำ
                font=(self.font, 10),
                pady=2
            )
            info_label.pack()

            # เพิ่มปุ่มตกลง
            button_frame = tk.Frame(content_frame, bg="#000000")
            button_frame.pack(pady=10)

            def close_dialog():
                try:
                    dialog.destroy()
                except:
                    pass

            ok_button = tk.Button(
                button_frame,
                text="ตกลง",
                command=close_dialog,
                bg="#FFD700",  # ปุ่มสีเหลือง
                fg="#000000",  # ตัวอักษรสีดำ
                font=(self.font, 12, "bold"),
                padx=20,
                pady=5,
                relief="raised",
                bd=2
            )
            ok_button.pack()

            # ให้ Enter key สามารถปิด dialog ได้
            def on_enter(event):
                close_dialog()

            dialog.bind('<Return>', on_enter)
            dialog.bind('<Escape>', on_enter)  # Escape key ก็ปิดได้

            # Focus ที่ปุ่มเพื่อให้กด Enter ได้ทันที
            ok_button.focus_set()

            # 🔝 บังคับให้ dialog อยู่บนสุดอีกครั้งหลังจากสร้างเสร็จ
            dialog.after_idle(lambda: [
                dialog.lift(),
                dialog.focus_set(),  # ✅ ใช้ focus_set แทน focus_force
                dialog.wm_attributes("-topmost", True)
            ])

            self.logging_manager.log_info(f"Enhanced dialog shown for character: {character_name}")

        except Exception as e:
            self.logging_manager.log_error(f"Error showing enhanced dialog: {e}")
            # Fallback ใช้ flash_message เดิม
            self.flash_message(f"เพิ่มตัวละคร '{character_name}' ลงในฐานข้อมูลแล้ว!", "success")

    def show_window(self):
        """แสดงหน้าต่าง NPC Manager - รวมการหยุดการแปลและการคืนสถานะ"""

        # 🐛 DEBUG: Log initial state
        initial_state = self.window.state() if hasattr(self, 'window') and self.window.winfo_exists() else "no_window"
        self.logging_manager.log_info(f"🔍 [SHOW WINDOW] Initial window state: '{initial_state}'")

        # 🎯 UI INDEPENDENCE: เปิด NPC Manager โดยไม่หยุดการแปล
        self.logging_manager.log_info(
            "NPC Manager opened independently - translation continues"
        )

        # อ่านค่าสถานะปักหมุดจากตัวแปรกลาง
        global _topmost_state
        self.is_topmost = _topmost_state

        # 🐛 DEBUG: Log state before deiconify
        before_deiconify = self.window.state() if hasattr(self, 'window') and self.window.winfo_exists() else "no_window"
        self.logging_manager.log_info(f"🔍 [SHOW WINDOW] Before deiconify: '{before_deiconify}'")

        # แสดงหน้าต่าง
        self.window.deiconify()

        # Position relative to MBB main window (right side, aligned top)
        try:
            if hasattr(self, "parent_app") and self.parent_app and hasattr(self.parent_app, "_get_mbb_geometry"):
                mx, my, mw, mh = self.parent_app._get_mbb_geometry()
                x = mx + mw + 10
                y = my
                self.window.geometry(f"+{x}+{y}")
        except Exception:
            pass  # keep current position if fails

        # ✅ ปรับปรุง: แสดงหน้าต่างตามสถานะ
        if self.is_topmost:
            self.window.attributes("-topmost", True)  # บังคับ topmost ถ้า pin อยู่
        self.window.lift()  # ยกขึ้นบนสุด

        # มุมโค้ง (ต้องรอ geometry update ก่อน)
        self.window.update_idletasks()
        self._apply_rounded_corners()

        # ✅ แก้ไข: Focus ที่ search entry แทน window เพื่อให้ผู้ใช้พิมพ์ได้ทันที
        if hasattr(self, "search_entry") and self.search_entry.winfo_exists():
            self.search_entry.focus_set()
        else:
            self._safe_focus_force()  # fallback: focus ที่ window

        # ✅ คืนค่าสถานะที่บันทึกไว้
        self._restore_saved_state()

        # ตั้งค่า topmost ตามสถานะที่บันทึกไว้ (หลังจากแสดงแล้ว)
        self._safe_after(
            200, lambda: self.window.attributes("-topmost", self.is_topmost)
        )

        # ปรับไอคอนปักหมุดตามสถานะที่บันทึกไว้
        if hasattr(self, "pin_icon"):
            if self.is_topmost:
                if hasattr(self, "pin_image"):
                    self.pin_button.itemconfig(self.pin_icon, image=self.pin_image)
                else:
                    self.pin_button.itemconfig(self.pin_icon, fill="#FF9500")
            else:
                if hasattr(self, "unpin_image"):
                    self.pin_button.itemconfig(self.pin_icon, image=self.unpin_image)
                else:
                    self.pin_button.itemconfig(self.pin_icon, fill="#AAAAAA")

        # ตรวจสอบว่ามีการเลือก section หรือไม่ (ถ้าไม่มีสถานะที่บันทึกไว้)
        if (
            not self.current_section
            and self.data
            and not self.saved_state.get("current_section")
        ):
            first_section = next(iter(self.data.keys()))
            self.show_section(first_section)

        # เรียก update_idletasks เพื่อให้ UI อัพเดตทันที
        self.window.update_idletasks()
        
        # อัพเดตคำอธิบายของแท็บเริ่มต้น
        if self.current_section:
            self._update_section_description(self.current_section)
        else:
            self._update_section_description("main_characters")

        # ถ้าสถานะปักหมุดเป็น True ให้ตรวจสอบซ้ำอีกครั้ง
        if self.is_topmost:
            self._safe_after(300, self._ensure_topmost)

    def _configure_window_for_taskbar(self):
        """ตั้งค่าพิเศษเพื่อให้หน้าต่างปรากฏในแถบงาน"""

        try:

            # เมื่อใช้ Windows

            if hasattr(self.window, "attributes"):

                # ยกเลิกการเป็นหน้าต่างย่อย

                self.window.transient("")

                # ตั้งค่าให้เป็นหน้าต่างปกติ

                self.window.attributes("-toolwindow", 0)

            # สำหรับ Windows โดยเฉพาะ

            import platform

            if platform.system() == "Windows":

                try:

                    # เพิ่ม icon ให้กับหน้าต่าง (ถ้ามี)

                    self.window.iconbitmap(default="icon.ico")

                except:

                    pass

                # ตั้งค่าเพิ่มเติมสำหรับ Windows

                self.window.wm_attributes("-topmost", 0)

        except Exception as e:

            self.logging_manager.log_error(f"Error configuring window for taskbar: {e}")

    def hide_window(self):
        """ซ่อนหน้าต่าง NPC Manager พร้อมบันทึกสถานะและทำความสะอาดครอบคลุม"""
        # ✅ บันทึกสถานะก่อนซ่อน
        self._save_current_state()

        # ทำความสะอาดก่อนซ่อน
        self._comprehensive_cleanup()

        self.window.withdraw()

        # เรียก callback ถ้ามี
        if hasattr(self, "on_close_callback") and self.on_close_callback:
            self.on_close_callback()

    def _save_current_state(self):
        """บันทึกสถานะปัจจุบันของ NPC Manager"""
        try:
            # บันทึกคำค้นหา
            if hasattr(self, "search_var") and self.search_var:
                self.saved_state["search_term"] = self.search_var.get()

            # บันทึก current section
            if hasattr(self, "current_section"):
                self.saved_state["current_section"] = self.current_section

            # บันทึกตำแหน่งและขนาดหน้าต่าง
            if hasattr(self, "window") and self.window.winfo_exists():
                self.saved_state["window_geometry"] = self.window.geometry()

            # บันทึกตำแหน่ง scroll ถ้าทำได้
            if hasattr(self, "main_canvas") and self.main_canvas:
                try:
                    scroll_top, scroll_bottom = self.main_canvas.yview()
                    self.saved_state["scroll_position"] = scroll_top
                except:
                    pass

            self.logging_manager.log_info(
                f"Saved NPC Manager state: {self.saved_state}"
            )

        except Exception as e:
            self.logging_manager.log_error(f"Error saving NPC Manager state: {e}")

    def _restore_saved_state(self):
        """คืนค่าสถานะที่บันทึกไว้"""
        try:
            # คืนค่าคำค้นหา
            if self.saved_state.get("search_term") and hasattr(self, "search_var"):
                self.search_var.set(self.saved_state["search_term"])
                self.logging_manager.log_info(
                    f"Restored search term: {self.saved_state['search_term']}"
                )

            # คืนค่า current section
            saved_section = self.saved_state.get("current_section")
            if saved_section and saved_section in self.data:
                self.show_section(saved_section)
                self.logging_manager.log_info(f"Restored section: {saved_section}")

            # คืนค่าตำแหน่งหน้าต่าง
            if self.saved_state.get("window_geometry"):
                try:
                    self.window.geometry(self.saved_state["window_geometry"])
                except:
                    pass  # อาจไม่สำเร็จถ้าความละเอียดหน้าจอเปลี่ยน

            # คืนค่าตำแหน่ง scroll
            if self.saved_state.get("scroll_position") and hasattr(self, "main_canvas"):

                def restore_scroll():
                    try:
                        self.main_canvas.yview_moveto(
                            self.saved_state["scroll_position"]
                        )
                    except:
                        pass

                # ใช้ after เพื่อให้ UI โหลดเสร็จก่อน
                self._safe_after(100, restore_scroll)

        except Exception as e:
            self.logging_manager.log_error(f"Error restoring NPC Manager state: {e}")

    def destroy(self):
        """ทำลาย NPC Manager และทำความสะอาดทรัพยากรทั้งหมด"""
        try:
            # ตั้งค่า flag ว่า instance ถูกทำลายแล้ว
            self._is_destroyed = True

            # ทำความสะอาดครอบคลุม
            self._comprehensive_cleanup()

            # ทำลาย window
            if hasattr(self, "window") and self.window.winfo_exists():
                self.window.destroy()

            if hasattr(self, "logging_manager"):
                self.logging_manager.log_info("NPC Manager destroyed successfully")

        except Exception as e:
            if hasattr(self, "logging_manager"):
                self.logging_manager.log_error(
                    f"Error during NPC Manager destruction: {e}"
                )

    def is_window_showing(self):
        """ตรวจสอบว่าหน้าต่าง NPC Manager กำลังแสดงอยู่หรือไม่"""

        return (
            hasattr(self, "window")
            and self.window.winfo_exists()
            and self.window.state() != "withdrawn"
        )

    # 🔧 ระบบจัดการ Timer และ Focus อย่างครอบคลุม
    def _safe_after(self, delay, callback):
        """สร้าง timer อย่างปลอดภัยและติดตาม พร้อมป้องกัน recursion"""
        if self._is_destroyed or not hasattr(self, "window"):
            return None

        # ✅ ทำความสะอาด timers ที่เสร็จสิ้นแล้วก่อนสร้างใหม่
        self._cleanup_finished_timers()

        # ✅ ป้องกัน timer สะสมมากเกินไป (ลดจาก 100 เป็น 50)
        if len(self._all_timers) > 50:  # ลดจาก 100 เป็น 50
            if hasattr(self, "logging_manager"):
                self.logging_manager.log_warning(
                    f"High timer count ({len(self._all_timers)}), cleaning up old timers"
                )
            self._aggressive_timer_cleanup()

            # ถ้ายังเกิน ให้ยกเลิกทั้งหมดและรีเซ็ต
            if len(self._all_timers) > 50:
                self._cancel_all_timers()

        try:
            timer_id = self.window.after(
                delay, callback
            )  # 🔥 แก้ไข: ใช้ self.window.after แทน self._safe_after
            if timer_id:
                self._all_timers.append(timer_id)
            return timer_id
        except Exception as e:
            if hasattr(self, "logging_manager"):
                self.logging_manager.log_error(f"Error creating timer: {e}")
            return None

    def _safe_after_cancel(self, timer_id):
        """ยกเลิก timer อย่างปลอดภัย"""
        if not timer_id or self._is_destroyed:
            return

        try:
            if hasattr(self, "window") and not self._is_destroyed:
                self.window.after_cancel(
                    timer_id
                )
            # ลบออกจากรายการ timer ที่ active
            if timer_id in self._all_timers:
                self._all_timers.remove(timer_id)
        except Exception as e:
            if hasattr(self, "logging_manager"):
                self.logging_manager.log_error(
                    f"Error cancelling timer {timer_id}: {e}"
                )

    def _cancel_all_timers(self):
        """ยกเลิก timer ทั้งหมด"""
        timers_to_cancel = list(self._all_timers)  # สำเนารายการ
        self._all_timers.clear()  # ล้างรายการก่อน

        for timer_id in timers_to_cancel:
            try:
                if hasattr(self, "window") and self.window.winfo_exists():
                    self.window.after_cancel(
                        timer_id
                    )  # 🔥 ใช้ window.after_cancel โดยตรงเพื่อป้องกัน recursion
            except Exception as e:
                if hasattr(self, "logging_manager"):
                    self.logging_manager.log_error(
                        f"Error cancelling timer in cleanup: {e}"
                    )

    def _cleanup_finished_timers(self):
        """✅ ทำความสะอาด timers ที่เสร็จสิ้นแล้ว (ไม่ active)"""
        if not hasattr(self, "_all_timers") or not self._all_timers:
            return

        # ✅ ตรวจสอบว่า window ยังมีอยู่ก่อน
        if not hasattr(self, "window") or not self.window.winfo_exists():
            return

        # ใช้ try-except เพื่อตรวจสอบว่า timer ยัง active อยู่หรือไม่
        active_timers = []
        for timer_id in self._all_timers:
            try:
                # พยายามเช็คว่า timer ยัง active หรือไม่
                # หาก after_cancel สำเร็จ แสดงว่า timer ยัง active
                info = self.window.tk.call('after', 'info', timer_id)
                if info:
                    active_timers.append(timer_id)
            except:
                # Timer หมดอายุแล้ว หรือไม่ valid ไม่ต้องเก็บ
                pass

        # บันทึกจำนวนที่ทำความสะอาด
        cleaned_count = len(self._all_timers) - len(active_timers)
        if cleaned_count > 0 and hasattr(self, "logging_manager"):
            self.logging_manager.log_info(
                f"Cleaned up {cleaned_count} finished timers, {len(active_timers)} still active"
            )

        self._all_timers = active_timers

    def _aggressive_timer_cleanup(self):
        """✅ ทำความสะอาด timers แบบรุนแรงเมื่อมีจำนวนมากเกินไป"""
        if not hasattr(self, "_all_timers") or not self._all_timers:
            return

        # ยกเลิก timers เก่าที่สุด 50% ของ list
        cleanup_count = len(self._all_timers) // 2
        timers_to_cancel = self._all_timers[:cleanup_count]

        for timer_id in timers_to_cancel:
            try:
                if hasattr(self, "window") and self.window.winfo_exists():
                    self.window.after_cancel(timer_id)
            except:
                pass

        # ลบออกจาก list
        self._all_timers = self._all_timers[cleanup_count:]

        if hasattr(self, "logging_manager"):
            self.logging_manager.log_info(
                f"Aggressive cleanup: cancelled {cleanup_count} timers, {len(self._all_timers)} remaining"
            )

    def _safe_bind(self, widget, event, callback):
        """ผูก event อย่างปลอดภัยและติดตาม"""
        if self._is_destroyed or not widget or not widget.winfo_exists():
            return None

        try:
            binding_id = widget.bind(event, callback)
            self._active_bindings.append((widget, event, binding_id))
            return binding_id
        except Exception as e:
            if hasattr(self, "logging_manager"):
                self.logging_manager.log_error(f"Error binding event {event}: {e}")
            return None

    def _cleanup_all_bindings(self):
        """ลบ event bindings ทั้งหมด"""
        bindings_to_cleanup = list(self._active_bindings)
        self._active_bindings.clear()

        for widget, event, binding_id in bindings_to_cleanup:
            try:
                if widget and widget.winfo_exists():
                    widget.unbind(event, binding_id)
            except Exception as e:
                if hasattr(self, "logging_manager"):
                    self.logging_manager.log_error(
                        f"Error unbinding event in cleanup: {e}"
                    )

    def _safe_focus_force(self, widget=None):
        """✅ บังคับ focus อย่างปลอดภัย พร้อมป้องกัน focus loop"""
        target = widget or self.window

        # ตรวจสอบว่า widget มี focus อยู่แล้วหรือไม่
        try:
            current_focus = self.window.focus_get()
            if current_focus == target:
                return  # มี focus อยู่แล้ว ไม่ต้องทำอะไร
        except:
            pass

        # ✅ เพิ่ม cooldown เพื่อป้องกัน focus spam
        current_time = time.time()
        if hasattr(self, "_last_focus_time"):
            if current_time - self._last_focus_time < 0.1:  # 100ms cooldown
                return  # เพิ่ง focus ไปเมื่อสักครู่ ข้ามไป

        try:
            target.focus_set()  # ✅ ใช้ focus_set แทน focus_force เพื่อความปลอดภัย
            self._last_focus_time = current_time
        except Exception as e:
            if hasattr(self, "logging_manager"):
                self.logging_manager.log_error(f"Error setting focus: {e}")

    def _force_ui_unlock(self):
        """บังคับ unlock UI ที่อาจติดค้าง (ปรับปรุงแล้ว)"""
        try:
            if hasattr(self, "window") and self.window.winfo_exists():
                # ปลด grab ที่อาจติดค้าง
                self.window.grab_release()

                # รีเซ็ต cursor
                self.window.config(cursor="")

                # ✅ ใช้ _safe_focus_force แทน focus_force โดยตรง
                self._safe_focus_force()

                # อัพเดท UI state แบบปลอดภัย
                self.window.update_idletasks()
                # self.window.update()  # ปิดการใช้ update() เพื่อป้องกัน UI freeze

            if hasattr(self, "logging_manager"):
                self.logging_manager.log_info("UI unlock forced successfully")

        except Exception as e:
            if hasattr(self, "logging_manager"):
                self.logging_manager.log_error(f"Error forcing UI unlock: {e}")

    def toggle_window(self):
        """สลับการแสดง/ซ่อนหน้าต่าง พร้อมระบบจัดการ timer และ focus ใหม่"""
        if self.is_window_showing():
            self.hide_window()
        else:
            # 🔧 ใช้ระบบจัดการใหม่
            self.logging_manager.log_info(
                "Opening NPC Manager - using new comprehensive management system"
            )

            # ทำความสะอาดครอบคลุม
            self._comprehensive_cleanup()

            # บังคับ unlock UI
            self._force_ui_unlock()

            # อัพเดทข้อมูลก่อนแสดงหน้าต่าง
            self.load_data(self.current_section)

            # รีเซ็ตสถานะ UI อย่างครอบคลุม
            self.reset_ui_state()

            # แสดงหน้าต่าง
            self.show_window()

            # ให้แน่ใจว่าหน้าต่างอยู่บนสุดเสมอ
            self._ensure_topmost()

            # 🎯 เพิ่ม: Force update UI เพื่อให้แน่ใจว่า responsive
            try:
                self.window.update_idletasks()
                # self.window.update()  # ปิดการใช้ update() เพื่อป้องกัน UI freeze
                self.window.config(cursor="")  # ยืนยันว่า cursor ปกติ
            except Exception as e:
                self.logging_manager.log_warning(f"Error forcing UI update: {e}")

            # แสดงสถานะพร้อมใช้งาน
            self._update_status("พร้อมใช้งาน - หน้าต่างเปิดใหม่")
            self.logging_manager.log_info(
                "NPC Manager opened successfully with full cleanup"
            )

    def cleanup(self):
        """ทำความสะอาดทรัพยากรก่อนปิด"""

        try:

            self.logging_manager.log_info("Cleaning up NPC Manager Card resources")

            # ซ่อนหน้าต่าง

            if hasattr(self, "window") and self.window.winfo_exists():

                self.window.withdraw()

            # ล้างค่าต่างๆ

            if hasattr(self, "search_var"):

                self.search_var.set("")

            # ล้าง Treeview และ panel รายละเอียด โดยเรียกเมธอดที่แก้ไขแล้ว

            self._clear_cards()

        except Exception as e:

            self.logging_manager.log_error(f"Error during cleanup: {e}")

    def find_and_display_character(self, character_name, is_verified=False):
        """
        ค้นหาและแสดงข้อมูลตัวละครจากชื่อ - ปรับปรุงใหม่ตามความต้องการผู้ใช้

        พฤติกรรม:
        - ถ้าพบในฐานข้อมูล: ใส่ชื่อในช่อง search และเลือก (focus) ตัวละครนั้น
        - ถ้าไม่พบ: ใส่ชื่อในฟอร์มเพิ่มข้อมูลใหม่ รอให้ผู้ใช้แก้ไขและกด Add Entry

        Args:
            character_name (str): ชื่อตัวละครที่ต้องการค้นหา
            is_verified (bool): สถานะการยืนยันของชื่อตัวละคร
        """
        try:
            # ทำความสะอาดและเตรียมสภาพแวดล้อม
            self.logging_manager.log_info(
                f"Finding character '{character_name}' (verified: {is_verified})"
            )

            # 🔥 ปิด callback การหยุดแปลตามคำสั่งผู้ใช้ - ให้การแปลดำเนินต่อไป
            # if self.stop_translation_callback:
            #     try:
            #         self.stop_translation_callback()
            #         self.logging_manager.log_info(
            #             "Translation stopped for character search"
            #         )
            #     except Exception as e:
            #         self.logging_manager.log_warning(f"Error stopping translation: {e}")

            self.logging_manager.log_info("Character search without stopping translation")

            # ตรวจสอบ window พร้อมใช้งาน
            if not hasattr(self, "window") or not self.window.winfo_exists():
                self.logging_manager.log_error("NPC Manager window not available")
                return False

            # Clear any pending operations
            self._comprehensive_cleanup()

            # โหลดข้อมูลถ้ายังไม่มี
            if not hasattr(self, "data") or not self.data:
                self.load_data()
                if not self.data:
                    self.logging_manager.log_error("Failed to load NPC data")
                    return False

            found = False
            found_data = None
            found_section = None

            # ค้นหาในส่วน main_characters
            if "main_characters" in self.data:
                for character in self.data["main_characters"]:
                    first_name = character.get("firstName", "")
                    full_name = first_name
                    if character.get("lastName"):
                        full_name = f"{first_name} {character.get('lastName')}"

                    if (
                        first_name.lower() == character_name.lower()
                        or full_name.lower() == character_name.lower()
                    ):
                        found = True
                        found_data = character
                        found_section = "main_characters"
                        break

            # ถ้าไม่พบ ค้นหาใน npcs
            if not found and "npcs" in self.data:
                for npc in self.data["npcs"]:
                    if npc.get("name", "").lower() == character_name.lower():
                        found = True
                        found_data = npc
                        found_section = "npcs"
                        break

            # ถ้าพบข้อมูล: ใส่ชื่อในช่อง search และ focus
            if found:
                self.logging_manager.log_info(
                    f"Character '{character_name}' found in {found_section}"
                )

                # บังคับแสดง NPC Manager UI เมื่อพบตัวละคร โดยใช้ callback จาก main app
                # 🐛 FIX: ส่ง character_name เพื่อให้ระบบรู้ว่าเป็น character click flow ไม่ใช่ manual toggle
                if hasattr(self, 'parent_app') and self.parent_app:
                    if hasattr(self.parent_app, 'toggle_npc_manager'):
                        self.parent_app.toggle_npc_manager(character_name)  # ส่ง character_name
                        self.logging_manager.log_info(f"NPC Manager opened via main app callback for existing character: '{character_name}'")
                    else:
                        self.show_window()  # Fallback
                        self.logging_manager.log_info("NPC Manager opened via direct call (fallback)")
                else:
                    self.show_window()  # Fallback
                    self.logging_manager.log_info("NPC Manager opened via direct call (no parent_app)")

                # แสดง section ที่ถูกต้อง
                self.show_section(found_section)

                # ใส่ชื่อในช่อง search และให้มันค้นหา
                self._set_search_and_focus(character_name)

                # บันทึกสถานะ
                self._save_current_state()

                # แสดงข้อความแจ้งเตือน
                self.flash_message(
                    f"พบตัวละคร '{character_name}' ในฐานข้อมูล กรุณาเลือกจากรายการ", "info"
                )

                return True

            # ถ้าไม่พบ: เพิ่มตัวละครใหม่อัตโนมัติ
            else:
                self.logging_manager.log_info(
                    f"Character '{character_name}' not found, auto-adding to database"
                )

                # เรียกฟังก์ชันเพิ่มตัวละครใหม่อัตโนมัติ
                return self._auto_add_new_character(character_name)

        except Exception as e:
            self.logging_manager.log_error(f"Error in find_and_display_character: {e}")
            import traceback

            self.logging_manager.log_error(traceback.format_exc())

            try:
                import tkinter.messagebox as messagebox

                messagebox.showerror("Error", f"เกิดข้อผิดพลาดในการค้นหาตัวละคร: {e}")
            except:
                pass

            return False

    def _prepare_add_form_with_name(self, character_name):
        """
        เตรียมฟอร์มเพิ่มข้อมูลใหม่พร้อมใส่ชื่อที่ได้รับมา

        Args:
            character_name (str): ชื่อตัวละครที่จะใส่ในฟอร์ม
        """
        try:
            # ล้างพื้นที่แสดงรายละเอียดก่อน
            self._clear_detail_content_frame()

            # เซ็ต current_section ก่อนสร้างฟอร์ม
            self.current_section = "main_characters"

            # สร้างฟอร์มใหม่สำหรับ main_characters
            self._create_detail_form_for_section()

            # ใส่ชื่อในฟอร์ม
            if "firstName" in self.detail_form_elements:
                # ใช้ StringVar.set() แทน Entry.delete() และ .insert()
                self.detail_form_elements["firstName"].set(character_name)

            # ตั้งค่าเริ่มต้นสำหรับฟิลด์อื่นๆ
            default_values = {
                "lastName": "",
                "gender": "Female",
                "role": "Adventure",
                "relationship": "Neutral",
            }

            for field, value in default_values.items():
                if field in self.detail_form_elements:
                    widget = self.detail_form_elements[field]
                    # ตรวจสอบชนิดของ widget และใช้วิธีที่เหมาะสม
                    if hasattr(widget, "set"):  # StringVar หรือ Combobox
                        widget.set(value)
                    elif isinstance(widget, tk.Entry):  # Entry widget
                        widget.delete(0, tk.END)
                        widget.insert(0, value)
                    else:
                        # สำหรับ widget ชนิดอื่นๆ ที่อาจมีในอนาคต
                        try:
                            widget.set(value)
                        except AttributeError:
                            # หากไม่มี .set() method ให้ข้ามไป
                            pass

            # แสดงฟอร์ม
            if hasattr(self, "detail_form_frame") and self.detail_form_frame:
                self.detail_form_frame.grid(row=0, column=0, sticky="nsew")
                self.current_detail_widget = self.detail_form_frame

            # อัพเดท title
            if hasattr(self, "detail_title"):
                self.detail_title.configure(text="เพิ่มตัวละครใหม่")

            # แสดงปุ่ม ADD ENTRY
            if hasattr(self, "save_edit_btn"):
                self.save_edit_btn.configure(
                    text="ADD ENTRY", command=self._quick_add_new_entry
                )
                self.save_edit_btn.pack(side="left", padx=5)

            # Focus ที่ช่อง firstName - แก้ไข StringVar issue
            # เนื่องจาก detail_form_elements เก็บ StringVar ไม่ใช่ Entry widget
            # เราจึงต้องหา Entry widget ที่เชื่อมกับ StringVar นี้
            if "firstName" in self.detail_form_elements:
                try:
                    # พยายามหา Entry widget ที่มี textvariable เป็น StringVar นี้
                    firstname_var = self.detail_form_elements["firstName"]
                    # ค้นหา Entry widget ใน detail_form_frame
                    if hasattr(self, "detail_form_frame") and self.detail_form_frame:
                        for widget in self.detail_form_frame.winfo_children():
                            # ค้นหาใน container ย่อย
                            for child in widget.winfo_children():
                                if isinstance(child, tk.Entry):
                                    try:
                                        if child.cget("textvariable") == str(
                                            firstname_var
                                        ):
                                            child.focus_set()
                                            break
                                    except:
                                        pass
                except Exception as e:
                    # หากไม่สามารถ focus ได้ ไม่ต้อง error
                    self.logging_manager.log_warning(
                        f"Could not focus firstName field: {e}"
                    )
                    pass

            self._update_status(
                f"กรุณาตรวจสอบข้อมูลและกด Add Entry เพื่อเพิ่ม '{character_name}'"
            )

        except Exception as e:
            self.logging_manager.log_error(f"Error preparing add form: {e}")
            import traceback

            self.logging_manager.log_error(traceback.format_exc())

    def _start_health_monitoring(self):
        """✅ เริ่มระบบตรวจสอบสุขภาพ UI อัตโนมัติ"""
        def _health_check():
            if self._is_destroyed:
                return

            try:
                # ตรวจสอบจำนวน timers
                if len(self._all_timers) > 30:  # เตือนที่ 30 timers
                    self.logging_manager.log_warning(
                        f"⚠️ Health check: High timer count ({len(self._all_timers)})"
                    )
                    self._cleanup_finished_timers()

                # ตรวจสอบว่ามีการใช้งานหรือไม่
                idle_time = time.time() - self._last_interaction_time
                if idle_time > 300:  # 5 นาที
                    self.logging_manager.log_info(
                        "Health check: UI idle for 5 min, performing maintenance"
                    )
                    # ✅ แก้ไข: ทำ lightweight cleanup แทน comprehensive cleanup
                    # เพื่อไม่ให้ยกเลิก health check timer
                    self._cleanup_finished_timers()
                    self._last_interaction_time = time.time()

                # ✅ Schedule check ครั้งต่อไป (ทุก 30 วินาที)
                if not self._is_destroyed:
                    self._health_check_timer = self._safe_after(30000, _health_check)
            except Exception as e:
                self.logging_manager.log_error(f"Health check error: {e}")

        # เริ่ม health check
        self._health_check_timer = self._safe_after(30000, _health_check)

    def _record_interaction(self):
        """✅ บันทึกการโต้ตอบของผู้ใช้"""
        self._last_interaction_time = time.time()
        self._interaction_count += 1

        # ตรวจสอบว่ามีการโต้ตอบมากเกินไปหรือไม่ (อาจเป็น loop)
        if self._interaction_count > 1000:
            self.logging_manager.log_warning(
                "⚠️ Very high interaction count, resetting counter"
            )
            self._interaction_count = 0
            self._comprehensive_cleanup()

    def _comprehensive_cleanup(self):
        """ทำความสะอาดทรัพยากรและ state ต่างๆ อย่างครอบคลุม (ปรับปรุงแล้ว)"""
        try:
            # ✅ 1. ยกเลิก health check timer ก่อน
            if hasattr(self, "_health_check_timer") and self._health_check_timer:
                try:
                    self.window.after_cancel(self._health_check_timer)
                except:
                    pass
                self._health_check_timer = None

            # ✅ 2. ยกเลิก pending timers ทั้งหมดแบบปลอดภัย
            self._cancel_all_timers()

            # ✅ 3. ยกเลิก focus timer โดยเฉพาะ
            if hasattr(self, "_focus_after_id") and self._focus_after_id:
                try:
                    self.window.after_cancel(self._focus_after_id)
                except:
                    pass
                self._focus_after_id = None

            # ✅ 4. ปลด event bindings ที่อาจค้างอยู่
            self._cleanup_all_bindings()

            # ✅ 5. ปลด grab และ reset focus (ไม่ใช้ focus_force)
            try:
                if hasattr(self, "window") and self.window.winfo_exists():
                    self.window.grab_release()
                    self.window.focus_set()  # ใช้ focus_set แทน focus_force
            except:
                pass

            # ✅ 6. Reset UI states
            self.current_edit_data = None
            self.has_actual_changes = False

            # ✅ 7. ทำความสะอาด detail form elements
            if hasattr(self, "detail_form_elements"):
                for field, widget in list(self.detail_form_elements.items()):
                    try:
                        if hasattr(widget, "winfo_exists") and widget.winfo_exists():
                            # ไม่ต้อง force focus ออก แค่ปล่อยให้เป็นธรรมชาติ
                            pass
                    except:
                        pass
                self.detail_form_elements.clear()

            # ✅ 8. Update UI แบบปลอดภัย
            try:
                self.window.config(cursor="")
                self.window.update_idletasks()  # ใช้แค่ update_idletasks
            except:
                pass

            # ✅ 9. รีเซ็ตตัวนับ interaction
            if hasattr(self, "_interaction_count"):
                self._interaction_count = 0

            self.logging_manager.log_info("✅ Comprehensive cleanup completed successfully")

        except Exception as e:
            self.logging_manager.log_error(f"Error during comprehensive cleanup: {e}")

    # NOTE: _safe_after และ _safe_after_cancel ถูกกำหนดไว้แล้วที่บรรทัด ~6307
    # ไม่ต้องกำหนดซ้ำ เพราะจะ override ตัวเดิมที่มี safety checks ดีกว่า

    def _force_ui_unlock(self):
        """บังคับปลดล็อค UI ในกรณีที่ค้างอยู่"""
        try:
            # Release any grab
            self.window.grab_release()

            # Reset cursor
            self.window.config(cursor="")

            # Force focus to window
            self.window.focus_set()

            # Update UI
            self.window.update_idletasks()

        except Exception:
            # Ignore errors during force unlock
            pass

    def _prepare_new_character_form_safe(self, character_name):
        """
        เตรียมฟอร์มสำหรับเพิ่มตัวละครใหม่พร้อมข้อมูลเริ่มต้น - เวอร์ชันปลอดภัยที่หลีกเลี่ยงปัญหา freeze

        Args:
            character_name (str): ชื่อตัวละครที่จะเพิ่ม
        """

        try:
            # 🎯 ปรับปรุง: ทำความสะอาดก่อนสร้างฟอร์มใหม่
            self.logging_manager.log_info(
                f"Preparing safe new character form for '{character_name}'"
            )

            # ยกเลิก timers ที่อาจค้างอยู่
            if hasattr(self, "_focus_after_id") and self._focus_after_id:
                try:
                    self._safe_after_cancel(self._focus_after_id)
                except:
                    pass
                self._focus_after_id = None

            # รีเซ็ตสถานะ
            self.current_edit_data = None
            self.has_actual_changes = False

            # เคลียร์ฟอร์มและ content frame อย่างปลอดภัย
            self._clear_detail_content_frame()

            # 🎯 ปรับปรุง: แสดงในโหมดดูก่อน แทนที่จะเข้าสู่โหมดแก้ไขทันที
            # สร้างข้อมูลตัวอย่างเพื่อแสดง
            preview_data = {
                "firstName": character_name,
                "lastName": "",  # เก็บเป็นค่าว่าง
                "gender": "Female",  # ค่าเริ่มต้น
                "role": "Adventure",  # ค่าเริ่มต้น
                "relationship": "Neutral",  # ค่าเริ่มต้น
            }

            # แสดงข้อมูลตัวอย่างในโหมดดู พร้อมปุ่ม ADD ENTRY
            self._show_card_detail(preview_data, is_preview=True)

            # อัพเดทชื่อหัวเรื่องให้ชัดเจน
            if hasattr(self, "detail_title") and self.detail_title.winfo_exists():
                self.detail_title.configure(
                    text=f"Preview: {character_name} (Click ADD ENTRY to create)"
                )

            # ตั้งค่าปุ่มให้เป็น ADD ENTRY พร้อม data
            if hasattr(self, "save_edit_btn") and self.save_edit_btn.winfo_exists():
                self.save_edit_btn.configure(
                    text="ADD ENTRY",
                    command=lambda: self._create_new_character_with_data(preview_data),
                )
                if not self.save_edit_btn.winfo_ismapped():
                    self.save_edit_btn.pack(fill="x")

            # Force UI update แบบปลอดภัย
            try:
                self.window.update_idletasks()
                # self.window.update()  # ปิดการใช้ update() เพื่อป้องกัน UI freeze
                self.logging_manager.log_info(
                    f"Safe character form prepared for '{character_name}' in preview mode"
                )
            except Exception as e:
                self.logging_manager.log_warning(
                    f"Error updating UI in prepare_new_character_form_safe: {e}"
                )

        except Exception as e:
            self.logging_manager.log_error(
                f"Error preparing safe new character form: {e}"
            )

    def _create_new_character_with_data(self, character_data):
        """สร้างตัวละครใหม่จากข้อมูลที่เตรียมไว้"""
        try:
            # เข้าสู่โหมดแก้ไข เพื่อให้ผู้ใช้สามารถปรับแต่งข้อมูลได้
            self._on_card_edit(character_data)

            # อัพเดท title ให้ชัดเจน
            if hasattr(self, "detail_title") and self.detail_title.winfo_exists():
                self.detail_title.configure(
                    text=f"Add New Character: {character_data.get('firstName', '')}"
                )

            self.logging_manager.log_info(
                f"Entered edit mode for new character: {character_data.get('firstName', '')}"
            )

        except Exception as e:
            self.logging_manager.log_error(
                f"Error creating new character with data: {e}"
            )

    def _quick_add_new_entry(self):
        """เพิ่มรายการใหม่และบันทึกลงไฟล์ทันทีในขั้นตอนเดียว"""
        try:
            # เก็บข้อมูลจากฟอร์ม
            new_entry = {}
            form_valid = True
            missing_fields = []
            key_field_name_for_check = None  # ชื่อ key field ที่ห้ามว่าง (ถ้ามี)

            # หา key field ที่จำเป็นสำหรับ section ปัจจุบัน
            if self.current_section in ["lore", "character_roles", "word_fixes"]:
                key_field_map = {
                    "lore": "term",
                    "character_roles": "character",
                    "word_fixes": "incorrect",
                }
                key_field_name_for_check = key_field_map.get(self.current_section)
            elif self.current_section == "main_characters":
                key_field_name_for_check = "firstName"
            elif self.current_section == "npcs":
                key_field_name_for_check = "name"

            # อ่านค่าจาก form และ validate
            for field, widget_var in self.detail_form_elements.items():
                value = ""
                if isinstance(widget_var, tk.Text):
                    value = widget_var.get("1.0", tk.END).strip()
                elif isinstance(widget_var, tk.StringVar):
                    value = widget_var.get().strip()
                else:
                    continue  # ข้าม widget ที่ไม่รู้จัก

                new_entry[field] = value

                # 🎨 จัดการ lastName placeholder สำหรับ main_characters
                if field == "lastName" and self.current_section == "main_characters":
                    if value == "Surname" or not value.strip():
                        new_entry[field] = ""  # เก็บเป็นค่าว่าง

                # ตรวจสอบ field ที่จำเป็น
                if field == key_field_name_for_check and not value:
                    missing_fields.append(field.capitalize())
                    form_valid = False

            if not form_valid:
                messagebox.showwarning(
                    "ข้อมูลไม่ครบถ้วน", f"กรุณากรอกข้อมูลในช่อง: {', '.join(missing_fields)}"
                )
                return

            # เพิ่ม: อัพเดท UI ก่อนเริ่มงานหนัก
            self.window.update_idletasks()

            # แสดงสถานะกำลังดำเนินการ
            self._update_status("กำลังบันทึกข้อมูล...")

            # เพิ่มรายการใหม่ (จะมีการเขียนทับถ้า key ซ้ำอยู่แล้ว)
            if self._add_data_item(new_entry):
                # บันทึกการเปลี่ยนแปลงลงไฟล์ทันที
                save_success = self.save_changes()

                if save_success:
                    # รีเซ็ต Panel ขวา กลับไปสถานะ Add เริ่มต้น
                    self._hide_detail_form()

                    # อัพเดทการ์ด/รายการใน Treeview
                    search_term = (
                        self.search_var.get().lower() if self.search_var.get() else None
                    )
                    self._clear_cards()
                    self._create_cards_for_section(search_term)

                    # แสดงข้อความสำเร็จที่ต้องการ
                    self.flash_success_message("บันทึกข้อมูลใหม่แล้ว")

                    # อัพเดทสถานะ
                    self._update_status("บันทึกข้อมูลใหม่เรียบร้อย")

                    # เพิ่ม: อัพเดท UI เพื่อให้แน่ใจว่าไม่ค้าง
                    self.window.update_idletasks()

                    # แสดงคำเตือนเรื่อง roles สำหรับตัวละครหลักที่เพิ่มใหม่
                    if self.current_section == "main_characters":
                        char_name = new_entry.get("firstName", "")
                        roles_data = self.data.get("character_roles", {})
                        has_role = any(
                            k.lower() == char_name.lower() for k in roles_data.keys()
                        ) if char_name else False
                        if char_name and not has_role:
                            self.window.after(
                                400, lambda n=char_name: self._show_role_warning_popup(n)
                            )
                else:
                    # แสดงข้อความเตือนหากบันทึกไม่สำเร็จ
                    self.flash_error_message("เพิ่มรายการในโปรแกรมแล้ว แต่บันทึกลงไฟล์ไม่สำเร็จ")
                    self._update_status("เกิดข้อผิดพลาดในการบันทึกลงไฟล์")
            # else: การเพิ่มข้อมูลล้มเหลว (messagebox แสดงจาก _add_data_item แล้ว)

        except Exception as e:
            self.logging_manager.log_error(f"Error in quick add new entry: {e}")
            import traceback

            self.logging_manager.log_error(traceback.format_exc())
            messagebox.showerror("Error", f"เกิดข้อผิดพลาดในการเพิ่มรายการ: {e}")

    def _show_role_warning_popup(self, character_name):
        """แสดง popup เตือนให้เพิ่มน้ำเสียงตัวละคร"""
        try:
            popup = tk.Toplevel(self.window)
            popup.overrideredirect(True)
            popup.configure(bg=self.style["bg_tertiary"])
            popup.attributes("-topmost", True)

            # จัดตำแหน่งกลางหน้าต่าง NPC Manager
            popup.update_idletasks()
            pw, ph = 380, 180
            wx = self.window.winfo_x() + (self.window.winfo_width() - pw) // 2
            wy = self.window.winfo_y() + (self.window.winfo_height() - ph) // 2
            popup.geometry(f"{pw}x{ph}+{wx}+{wy}")

            # ขอบ
            border = tk.Frame(popup, bg=self.style["warning"], padx=1, pady=1)
            border.pack(fill="both", expand=True)
            inner = tk.Frame(border, bg=self.style["bg_secondary"])
            inner.pack(fill="both", expand=True)

            # Icon + ข้อความ
            tk.Label(
                inner, text="⚠️", font=(self.font, 20),
                bg=self.style["bg_secondary"], fg=self.style["warning"],
            ).pack(pady=(12, 0))

            tk.Label(
                inner,
                text=f"'{character_name}' ยังไม่มีข้อมูลน้ำเสียง\nการแปลอาจไม่ได้อรรถรสเพียงพอ",
                font=(self.font, self.font_size_small),
                bg=self.style["bg_secondary"], fg=self.style["text_primary"],
                justify="center", wraplength=340,
            ).pack(pady=(4, 10))

            # ปุ่ม
            btn_frame = tk.Frame(inner, bg=self.style["bg_secondary"])
            btn_frame.pack(pady=(0, 12))

            def on_add_role():
                popup.destroy()
                self._navigate_and_prepare_role(character_name, "add")

            tk.Button(
                btn_frame, text="เพิ่มน้ำเสียง", font=(self.font, self.font_size_small),
                bg=self.style["accent"], fg="white", bd=0, relief="flat",
                padx=16, pady=6, cursor="hand2", command=on_add_role,
            ).pack(side="left", padx=(0, 8))

            tk.Button(
                btn_frame, text="ข้าม", font=(self.font, self.font_size_small),
                bg=self.style["bg_tertiary"], fg=self.style["text_secondary"],
                bd=0, relief="flat", padx=16, pady=6, cursor="hand2",
                command=popup.destroy,
            ).pack(side="left")

            # คลิกนอก popup ปิด
            popup.bind("<FocusOut>", lambda e: None)

        except Exception as e:
            self.logging_manager.log_error(f"Role warning popup error: {e}")

    def _navigate_and_prepare_role(self, character_name, mode):
        """
        Handles navigation from Main Character card to Roles section.
        Mode 'edit': Searches for the character.
        Mode 'add': Prepares the 'Add New Role' form with the character name.
        """
        try:
            if not character_name:
                self.logging_manager.log_warning(
                    "Character name is empty, cannot navigate to roles."
                )
                return

            self.logging_manager.log_info(
                f"Navigating to ROLES section for '{character_name}', mode: {mode}"
            )

            # 1. สลับไปที่ Section "character_roles" หรือ รีเซ็ต Panel ถ้าอยู่ section เดิมแล้ว
            #    (show_section/_hide_detail_form จะรีเซ็ต panel ขวาเป็น Add mode เริ่มต้น)
            if self.current_section != "character_roles":
                self.show_section("character_roles")
                # Delay subsequent actions until section switch UI is likely complete
                delay = 75  # เพิ่ม delay เล็กน้อยเผื่อ UI update
            else:
                # ถ้าอยู่ section เดิมแล้ว แค่รีเซ็ต panel ขวาไปที่สถานะ Add เริ่มต้น
                self._hide_detail_form()  # ทำให้แน่ใจว่า panel อยู่ในสถานะ Add เสมอ
                delay = 20  # Shorter delay if section didn't change

            # 2. Perform action based on mode after delay
            #    ใช้ lambda เพื่อส่งค่าล่าสุดของ character_name และ mode ไปยัง helper function
            self._safe_after(
                delay,
                lambda name=character_name, m=mode: self._post_navigation_action(
                    name, m
                ),
            )

        except Exception as e:
            self.logging_manager.log_error(f"Error navigating/preparing role: {e}")
            import traceback

            self.logging_manager.log_error(traceback.format_exc())
            messagebox.showerror(
                "Error", f"An error occurred while navigating to the role section:\n{e}"
            )

    def _post_navigation_action(self, character_name, mode):
        """Actions performed after navigating to the ROLES section."""
        try:
            # Clear Treeview selection from previous section (if any)
            if hasattr(self, "tree") and self.tree.winfo_exists():
                selection = self.tree.selection()
                if selection:
                    try:
                        self.tree.selection_remove(selection)
                    except (
                        tk.TclError
                    ):  # Handle case where tree might be cleared already
                        pass

            # --- Action based on Mode ---
            if mode == "edit":
                # Mode Edit: ใส่ชื่อในช่องค้นหาและ Focus
                self._set_search_and_focus(character_name)
                self._update_status(f"Searching roles for '{character_name}'...")

            elif mode == "add":
                # Mode Add: เติมชื่อในช่อง 'character' ของฟอร์ม Add Entry
                self.logging_manager.log_info(
                    f"Preparing 'Add Role' form for: {character_name}"
                )
                # Panel ควรอยู่ในสถานะ Add แล้ว (จาก show_section/_hide_detail_form)
                if "character" in self.detail_form_elements:
                    widget_var = self.detail_form_elements["character"]
                    if isinstance(widget_var, tk.StringVar):
                        widget_var.set(character_name)
                        self.logging_manager.log_info(
                            f"Pre-filled 'character' field with '{character_name}'"
                        )

                        # Focus on the 'style' field (Text widget)
                        if "style" in self.detail_form_elements:
                            style_widget = self.detail_form_elements["style"]
                            if (
                                style_widget
                                and isinstance(style_widget, tk.Text)
                                and style_widget.winfo_exists()
                            ):
                                widget_to_focus = style_widget
                                # Cancel pending focus if any
                                if (
                                    hasattr(self, "_focus_after_id")
                                    and self._focus_after_id
                                ):
                                    try:
                                        self._safe_after_cancel(self._focus_after_id)
                                    except ValueError:
                                        pass
                                # Set new focus timer
                                self._focus_after_id = self._safe_after(
                                    50,
                                    lambda w=widget_to_focus: (
                                        w.focus_set() if w.winfo_exists() else None
                                    ),
                                )
                            else:
                                self._focus_after_id = None  # Reset timer ID
                        else:
                            self._focus_after_id = None  # Reset timer ID
                    else:
                        self.logging_manager.log_warning(
                            "Character field widget is not a StringVar in add mode."
                        )
                        self._focus_after_id = None  # Reset timer ID
                else:
                    self.logging_manager.log_warning(
                        "'character' field not found in form elements for add mode."
                    )
                    self._focus_after_id = None  # Reset timer ID

                # ไม่ต้องทำอะไรกับช่องค้นหาหลัก
                self._update_status(f"Ready to add role for '{character_name}'.")

            else:
                self.logging_manager.log_warning(
                    f"Unknown mode '{mode}' in _post_navigation_action."
                )
                self._focus_after_id = None  # Ensure timer ID is cleared

        except Exception as e:
            self.logging_manager.log_error(f"Error in post-navigation action: {e}")
            import traceback

            self.logging_manager.log_error(traceback.format_exc())
            messagebox.showerror("Error", f"An error occurred after navigating:\n{e}")

    def _set_search_and_focus(self, search_term):
        """ตั้งค่าช่องค้นหาและ focus (Helper function)"""
        try:
            # 2. ใส่ชื่อตัวละครในช่องค้นหาหลัก
            if hasattr(self, "search_var"):
                self.search_var.set(
                    search_term
                )  # การ set นี้จะ trigger _on_search_change -> search
                self.logging_manager.log_info(f"Set search term to: {search_term}")
            else:
                self.logging_manager.log_error(
                    "Search variable (search_var) not found."
                )

            # 3. (Optional) Focus ที่ช่องค้นหา
            if hasattr(self, "search_entry") and self.search_entry.winfo_exists():
                self.search_entry.focus_set()
                self.logging_manager.log_info("Focused on search entry.")

            # ✅ บันทึกสถานะหลังจากตั้งค่าการค้นหา
            self._save_current_state()

        except Exception as e:
            self.logging_manager.log_error(f"Error setting search term or focus: {e}")

    def auto_add_character(self, character_name, is_verified=False):
        """
        เพิ่มตัวละครใหม่แบบอัตโนมัติทันทีโดยไม่ต้องผ่านการยืนยันจากผู้ใช้

        ขั้นตอน:
        1. เช็คว่ามีข้อมูลตัวละครนี้อยู่แล้วหรือไม่
        2. ถ้าไม่มี ให้สร้างข้อมูลเริ่มต้นและบันทึกทันที
        3. แสดงข้อความแจ้งเตือนว่าเพิ่มข้อมูลแล้ว
        4. เลือก (highlight) ข้อมูลที่เพิ่งเพิ่มไปใน list view
        5. แจ้ง MBB เพื่ออัพเดตข้อมูลไปยังระบบอื่น

        Args:
            character_name (str): ชื่อตัวละครที่จะเพิ่ม
            is_verified (bool): สถานะการยืนยันของชื่อตัวละคร

        Returns:
            bool: True ถ้าสำเร็จ, False ถ้าไม่สำเร็จ
        """
        try:
            # ล็อคการใช้งาน UI ชั่วคราว
            self.window.config(cursor="wait")
            self.window.update_idletasks()

            # 1. ตรวจสอบว่ามีตัวละครนี้อยู่แล้วหรือไม่
            found = False
            found_data = None

            # ค้นหาในส่วน main_characters
            if "main_characters" in self.data:
                for character in self.data["main_characters"]:
                    first_name = character.get("firstName", "")
                    if first_name.lower() == character_name.lower():
                        found = True
                        found_data = character
                        break

            # ถ้าไม่พบใน main_characters ให้ค้นหาใน npcs
            if not found and "npcs" in self.data:
                for npc in self.data["npcs"]:
                    if npc.get("name", "").lower() == character_name.lower():
                        found = True
                        found_data = npc
                        break

            # 2. ถ้าพบตัวละครแล้ว แค่แสดงข้อมูลที่มี
            if found:
                self.logging_manager.log_info(
                    f"Character '{character_name}' found in database, showing details"
                )

                # แสดงหน้า section ที่เหมาะสม
                if "firstName" in found_data:
                    self.show_section("main_characters")
                    # แสดงและ highlight ข้อมูลที่พบ
                    self._show_and_highlight_character_data(
                        found_data, "main_characters"
                    )
                else:
                    self.show_section("npcs")
                    # แสดงและ highlight ข้อมูลที่พบ
                    self._show_and_highlight_character_data(found_data, "npcs")

                # แสดงข้อความแจ้งเตือน
                self.flash_message(
                    f"พบข้อมูลตัวละคร '{character_name}' ในฐานข้อมูลแล้ว", "info"
                )
                self._update_status(f"แสดงข้อมูลตัวละคร: {character_name}")

                # ปลดล็อค UI
                self.window.config(cursor="")
                return True

            # 3. ถ้าไม่พบข้อมูล ให้สร้างข้อมูลใหม่
            self.logging_manager.log_info(
                f"Character '{character_name}' not found, creating new entry automatically"
            )

            # เตรียม section สำหรับเพิ่มข้อมูลตัวละครใหม่ (เลือกเป็น main_characters เสมอ)
            self.show_section("main_characters")

            # สร้างข้อมูลเริ่มต้น
            new_entry = {
                "firstName": character_name,
                "lastName": "",
                "gender": "Female",  # ค่าเริ่มต้น
                "role": "Adventure",  # ค่าเริ่มต้น
                "relationship": "Neutral",  # ค่าเริ่มต้น
            }

            # เพิ่มข้อมูลและบันทึกทันที
            if self._add_data_item(new_entry):
                # บันทึกลงไฟล์
                save_success = self.save_changes()

                if save_success:
                    # อัพเดท UI
                    if self.search_var.get():
                        # ล้างค่าค้นหาเพื่อให้แสดงรายการทั้งหมด
                        self.search_var.set("")
                    else:
                        # สร้างการ์ดใหม่
                        self._clear_cards()
                        self._create_cards_for_section()

                    # รอสักครู่ให้ UI อัพเดทเสร็จ
                    self._safe_after(
                        100,
                        lambda: self._show_and_highlight_character_data(
                            new_entry, "main_characters"
                        ),
                    )

                    # แสดงข้อความแจ้งเตือน
                    self.flash_success_message(
                        f"เพิ่มตัวละคร '{character_name}' เรียบร้อยแล้ว"
                    )
                    self._update_status(f"เพิ่มตัวละครใหม่: {character_name}")

                    # 5. เรียก reload_callback เพื่อแจ้ง MBB ให้อัพเดตข้อมูลไปยังระบบอื่น
                    if self.reload_callback and callable(self.reload_callback):
                        self.logging_manager.log_info(
                            "Calling reload_callback to update NPC data in other components"
                        )
                        try:
                            # ใช้ after เพื่อแยกการทำงานจาก UI thread
                            self._safe_after(200, self.reload_callback)
                        except Exception as cb_error:
                            self.logging_manager.log_error(
                                f"Error in reload_callback: {cb_error}"
                            )

                    # ปลดล็อค UI
                    self.window.config(cursor="")
                    return True
                else:
                    # บันทึกไม่สำเร็จ
                    self.flash_error_message("บันทึกข้อมูลไม่สำเร็จ")
                    self._update_status("เกิดข้อผิดพลาดในการบันทึกข้อมูล")

                    # ปลดล็อค UI
                    self.window.config(cursor="")
                    return False
            else:
                # เพิ่มข้อมูลไม่สำเร็จ
                self.flash_error_message("เพิ่มข้อมูลไม่สำเร็จ")
                self._update_status("เกิดข้อผิดพลาดในการเพิ่มข้อมูล")

                # ปลดล็อค UI
                self.window.config(cursor="")
                return False

        except Exception as e:
            self.logging_manager.log_error(f"Error in auto_add_character: {e}")
            import traceback

            self.logging_manager.log_error(traceback.format_exc())
            try:
                import tkinter.messagebox as messagebox

                messagebox.showerror("Error", f"เกิดข้อผิดพลาดในการเพิ่มตัวละคร: {e}")
            except Exception:
                pass

            # ปลดล็อค UI
            self.window.config(cursor="")
            return False

    def search_character_and_focus(self, character_name):
        """
        ค้นหาตัวละครและจัดการตามสถานะข้อมูล:
        - หากมีข้อมูลแล้ว: search + highlight
        - หากไม่มีข้อมูล: auto add เหมือนเดิม

        Args:
            character_name (str): ชื่อตัวละครที่จะค้นหา

        Returns:
            bool: True ถ้าสำเร็จ, False ถ้าไม่สำเร็จ
        """
        try:
            # ล็อคการใช้งาน UI ชั่วคราว
            self.window.config(cursor="wait")
            self.window.update_idletasks()

            # 1. ตรวจสอบว่ามีตัวละครนี้อยู่แล้วหรือไม่
            found = False
            found_data = None

            # ค้นหาในส่วน main_characters
            if "main_characters" in self.data:
                for character in self.data["main_characters"]:
                    first_name = character.get("firstName", "")
                    if first_name.lower() == character_name.lower():
                        found = True
                        found_data = character
                        break

            # ถ้าไม่พบใน main_characters ให้ค้นหาใน npcs
            if not found and "npcs" in self.data:
                for npc in self.data["npcs"]:
                    if npc.get("name", "").lower() == character_name.lower():
                        found = True
                        found_data = npc
                        break

            # 2. ถ้าพบตัวละครแล้ว: search + highlight
            if found:
                self.logging_manager.log_info(
                    f"Character '{character_name}' found in database, searching and highlighting"
                )

                # แสดงหน้า section ที่เหมาะสม
                if "firstName" in found_data:
                    self.show_section("main_characters")
                else:
                    self.show_section("npcs")

                # ใส่ชื่อในช่อง search และ focus
                self._set_search_and_focus(character_name)

                # ✅ บันทึกสถานะหลังจากค้นหาเสร็จ
                self._save_current_state()

                # แสดงข้อความแจ้งเตือน
                self.flash_message(f"พบและค้นหาตัวละคร '{character_name}' แล้ว", "info")
                self._update_status(f"ค้นหาตัวละคร: {character_name}")

                # ปลดล็อค UI
                self.window.config(cursor="")
                return True

            # 3. ถ้าไม่พบข้อมูล: เรียกใช้ auto_add_character เหมือนเดิม
            self.logging_manager.log_info(
                f"Character '{character_name}' not found, calling auto_add_character"
            )

            # ปลดล็อค UI ก่อนเรียก auto_add_character
            self.window.config(cursor="")

            # เรียกใช้ auto_add_character ที่มีอยู่แล้ว
            return self.auto_add_character(character_name, is_verified=False)

        except Exception as e:
            self.logging_manager.log_error(f"Error in search_character_and_focus: {e}")
            import traceback

            self.logging_manager.log_error(traceback.format_exc())
            try:
                import tkinter.messagebox as messagebox

                messagebox.showerror("Error", f"เกิดข้อผิดพลาดในการค้นหาตัวละคร: {e}")

            except Exception:
                pass

            # ปลดล็อค UI
            self.window.config(cursor="")
            return False

    def _show_and_highlight_character_data(self, character_data, section_type):
        """
        แสดงและ highlight ข้อมูลตัวละครใน list view และแสดง detail view - ปรับปรุงเพื่อการทำงานที่ดีขึ้น

        Args:
            character_data (dict): ข้อมูลตัวละคร
            section_type (str): ประเภทของ section ('main_characters' หรือ 'npcs')
        """
        try:
            # 🎯 ขั้นตอนที่ 1: Clear search filter เพื่อให้แน่ใจว่าตัวละครจะปรากฏใน list
            if hasattr(self, "search_var") and self.search_var.get():
                self.logging_manager.log_info(
                    "Clearing search filter to show character"
                )
                self.search_var.set("")  # Clear search
                self._create_cards_for_section()  # Refresh list
                self.window.update_idletasks()  # Update UI

            # 🎯 ขั้นตอนที่ 2: หาและเลือกรายการใน treeview
            found_item = None
            name_to_find = ""

            if section_type == "main_characters":
                name_to_find = character_data.get("firstName", "")
                if character_data.get("lastName"):
                    name_to_find += f" {character_data.get('lastName')}"
            else:  # npcs
                name_to_find = character_data.get("name", "")

            treeview_items_count = len(self.tree.get_children())
            self.logging_manager.log_info(
                f"Searching for '{name_to_find}' in treeview with {treeview_items_count} items"
            )

            # 🎯 เพิ่ม: ตรวจสอบว่า treeview มีข้อมูลหรือไม่
            if treeview_items_count == 0:
                self.logging_manager.log_warning(
                    "Treeview is empty, refreshing section data first"
                )
                self._create_cards_for_section()
                self.window.update_idletasks()
                treeview_items_count = len(self.tree.get_children())
                self.logging_manager.log_info(
                    f"After refresh: treeview now has {treeview_items_count} items"
                )

            # ค้นหาใน treeview โดยเปรียบเทียบทั้ง text และ values
            for item in self.tree.get_children():
                item_text = self.tree.item(item, "text")
                item_values = self.tree.item(item, "values")
                item_name = item_values[0] if item_values else item_text

                if item_name.lower() == name_to_find.lower():
                    found_item = item
                    break

            # 🎯 ขั้นตอนที่ 3: เลือกและแสดงรายการใน treeview
            if found_item:
                self.logging_manager.log_info(
                    f"Found '{name_to_find}' in treeview, selecting and focusing"
                )

                # Clear selection เดิมก่อน
                current_selection = self.tree.selection()
                if current_selection:
                    self.tree.selection_remove(current_selection)

                # เลือกรายการใหม่
                self.tree.selection_set(found_item)
                self.tree.focus(found_item)
                self.tree.see(found_item)  # scroll to make item visible

                # อัพเดท tree_items ถ้าจำเป็น
                if found_item not in self.tree_items:
                    self.tree_items[found_item] = character_data

                # Force update UI
                self.window.update_idletasks()

                # 🎯 ขั้นตอนที่ 4: แสดง detail view ในโหมดดูก่อน (ไม่ใช่แก้ไข)
                self._show_card_detail(character_data)

                # 🎯 เพิ่ม: แสดงสถานะให้ user ทราบ
                self._update_status(f"แสดงข้อมูลตัวละคร: {name_to_find}")

                self.logging_manager.log_info(
                    f"Successfully highlighted and displayed '{name_to_find}'"
                )
            else:
                # ถ้าหารายการใน treeview ไม่พบ (อาจเกิดจากปัญหาการ sync)
                self.logging_manager.log_warning(
                    f"'{name_to_find}' not found in treeview, refreshing and showing detail directly"
                )

                # ลองรีเฟรช treeview แล้วค้นหาอีกครั้ง
                self._create_cards_for_section()
                self.window.update_idletasks()

                # ค้นหาอีกครั้งหลัง refresh
                for item in self.tree.get_children():
                    item_text = self.tree.item(item, "text")
                    item_values = self.tree.item(item, "values")
                    item_name = item_values[0] if item_values else item_text

                    if item_name.lower() == name_to_find.lower():
                        found_item = item
                        break

                if found_item:
                    # เลือกรายการที่พบใหม่
                    self.tree.selection_set(found_item)
                    self.tree.focus(found_item)
                    self.tree.see(found_item)
                    if found_item not in self.tree_items:
                        self.tree_items[found_item] = character_data
                    self.window.update_idletasks()
                    self._show_card_detail(character_data)
                    self._update_status(f"แสดงข้อมูลตัวละคร: {name_to_find} (หลัง refresh)")
                    self.logging_manager.log_info(
                        f"Found and displayed '{name_to_find}' after refresh"
                    )
                else:
                    # ยังไม่พบ - แสดง detail view โดยตรง
                    self._show_card_detail(character_data)
                    self._update_status(f"แสดงข้อมูลตัวละคร: {name_to_find} (โหมดตรง)")
                    self.logging_manager.log_warning(
                        f"Still not found '{name_to_find}' in treeview, showing detail only"
                    )

        except Exception as e:
            self.logging_manager.log_error(
                f"Error showing/highlighting character data: {e}"
            )
            # Fallback: แสดง detail view อย่างน้อย
            try:
                self._show_card_detail(character_data)
                self._update_status(
                    f"แสดงข้อมูลตัวละคร: {character_data.get('firstName', character_data.get('name', 'Unknown'))} (fallback)"
                )
            except Exception as fallback_error:
                self.logging_manager.log_error(
                    f"Fallback display also failed: {fallback_error}"
                )

    def _auto_add_new_character(self, character_name):
        """
        เพิ่มตัวละครใหม่อัตโนมัติพร้อมข้อมูลพื้นฐาน แล้วใส่ชื่อในช่อง search

        Args:
            character_name (str): ชื่อตัวละครที่จะเพิ่ม

        Returns:
            bool: True หากเพิ่มสำเร็จ, False หากเกิดข้อผิดพลาด
        """
        try:
            self.logging_manager.log_info(
                f"Auto-adding new character: '{character_name}'"
            )

            # ตรวจสอบว่ามีข้อมูลอยู่แล้วหรือไม่
            if not hasattr(self, "data") or not self.data:
                self.load_data()

            # ตรวจสอบว่ามี section main_characters หรือไม่
            if "main_characters" not in self.data:
                self.data["main_characters"] = []

            # สร้างข้อมูลพื้นฐานสำหรับตัวละครใหม่
            new_character = {
                "firstName": character_name.strip(),
                "lastName": "",
                "gender": "Female",  # ค่าเริ่มต้น
                "role": "Adventure",  # ค่าเริ่มต้น
                "relationship": "Neutral",  # ค่าเริ่มต้น
                "appearance": "",
                "personality": "",
                "background": "",
                "notes": "",
            }

            # เพิ่มเข้าไปใน main_characters
            self.data["main_characters"].append(new_character)

            # บันทึกลงไฟล์ทันที
            with open(self._get_npc_file_path(), "w", encoding="utf-8") as file:
                json.dump(self.data, file, indent=4, ensure_ascii=False)

            # รีเซ็ตสถานะ
            self.has_unsaved_changes = False

            # อัพเดทแคช
            self.data_cache = self.data.copy()

            # แสดง section main_characters
            self.show_section("main_characters")

            # ใส่ชื่อในช่อง search
            if hasattr(self, "search_var") and self.search_var:
                self.search_var.set(character_name)
                # รีเฟรชการแสดงผลเพื่อให้เห็นตัวละครใหม่
                self.show_section("main_characters")  # เรียกซ้ำเพื่อ refresh

            # แสดง Enhanced Dialog แทน flash_message
            self.show_enhanced_character_added_dialog(character_name, new_character)

            # บังคับแสดง NPC Manager UI หลังจากเพิ่มตัวละครใหม่ โดยใช้ callback จาก main app
            # 🐛 FIX: ส่ง character_name เพื่อให้ระบบรู้ว่าเป็น character click flow ไม่ใช่ manual toggle
            if hasattr(self, 'parent_app') and self.parent_app:
                if hasattr(self.parent_app, 'toggle_npc_manager'):
                    self.parent_app.toggle_npc_manager(character_name)  # ส่ง character_name
                    self.logging_manager.log_info(f"NPC Manager opened via main app callback for new character: '{character_name}'")
                else:
                    self.show_window()  # Fallback
                    self.logging_manager.log_info("NPC Manager opened via direct call for new character (fallback)")
            else:
                self.show_window()  # Fallback
                self.logging_manager.log_info("NPC Manager opened via direct call for new character (no parent_app)")

            self.logging_manager.log_info(
                f"Successfully auto-added character: '{character_name}'"
            )
            return True

        except Exception as e:
            error_msg = f"Error auto-adding character '{character_name}': {e}"
            self.logging_manager.log_error(error_msg)

            # แสดงข้อความ error
            self.flash_message(
                f"ไม่สามารถเพิ่มตัวละคร '{character_name}' ได้: {str(e)}", "error"
            )
            return False

    def _create_info_panel(self):
        """สร้าง Panel สำหรับแสดงข้อมูลเกมและคำอธิบาย Section"""
        # 1. สร้าง Frame หลักสำหรับ Panel นี้ทั้งหมด โดยเพิ่มความสูงเป็น 70px
        self.info_panel_frame = tk.Frame(
            self.window, bg=self.style["bg_primary"], height=70
        )
        self.info_panel_frame.pack(fill="x", side="top", padx=15, pady=(5, 0))
        self.info_panel_frame.pack_propagate(False)

        # กำหนดให้ column 0 ของ Frame นี้ขยายตามความกว้าง
        self.info_panel_frame.grid_columnconfigure(0, weight=1)

        # 2. สร้างส่วนแสดงชื่อเกม (วางในแถวที่ 0 ของ grid)
        game_info_container = tk.Frame(
            self.info_panel_frame, bg=self.style["bg_primary"]
        )
        game_info_container.grid(row=0, column=0, sticky="ew", padx=5)

        game_name_from_file = self.current_game_info.get("name", "Unknown Game")
        game_name_label = tk.Label(
            game_info_container,
            text=f"Game Database: {game_name_from_file}",
            font=(self.font, self.font_size_small, "bold"),
            fg=self.style["accent"],
            bg=self.style["bg_primary"],
            anchor="w",
        )
        game_name_label.pack(side="left", pady=(5, 2))

        # 3. สร้างเส้นคั่น
        separator = tk.Frame(
            self.info_panel_frame, height=1, bg=self.style["bg_tertiary"]
        )
        separator.grid(row=1, column=0, sticky="ew", padx=5, pady=2)

        # 4. สร้างส่วนแสดงคำอธิบาย Section (วางในแถวที่ 2 ของ grid)
        self.section_description_label = tk.Label(
            self.info_panel_frame,
            text="เลือกแท็บเพื่อดูคำอธิบาย",
            bg=self.style["bg_primary"],
            fg=self.style["text_secondary"],
            font=(self.font, self.font_size_small),
            anchor="w",
            justify="left",
        )
        self.section_description_label.grid(
            row=2, column=0, sticky="ew", padx=5, pady=(2, 5)
        )

    def update_game_info(self, game_info):
        """อัปเดตข้อมูลเกมที่แสดง"""
        self.current_game_info = game_info

        # อัปเดต label
        if hasattr(self, "game_name_label"):
            self.game_name_label.configure(
                text=f"เกม: {game_info.get('name', 'Unknown')}"
            )

        # รีโหลดข้อมูล NPC ถ้าต้องการ
        if game_info.get("reload_data", False):
            self.load_data()
            self.refresh_view()


def create_npc_manager_card(
    parent,
    reload_callback=None,
    logging_manager=None,
    stop_translation_callback=None,
):
    """สร้างและส่งคืน instance ใหม่ของ NPC Manager Card"""
    return NPCManagerCard(
        parent,
        reload_callback,
        logging_manager,
        stop_translation_callback,
    )


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()  # ซ่อนหน้าต่างหลัก

    # สร้าง LoggingManager จำลอง (ถ้าไม่มีไฟล์จริง)
    class MockLoggingManager:
        def log_info(self, msg):
            print(f"INFO: {msg}")

        def log_error(self, msg):
            print(f"ERROR: {msg}")

        def log_npc_manager(self, msg):
            print(f"NPC_MGR: {msg}")

        def log_warning(self, msg):
            print(f"WARN: {msg}")

    mock_logger = MockLoggingManager()

    # สร้างไฟล์ NPC.json ตัวอย่าง (ถ้ายังไม่มี)
    from npc_file_utils import get_npc_file_path
    npc_test_path = get_npc_file_path()
    if not os.path.exists(npc_test_path):
        sample_data = {
            "main_characters": [
                {
                    "firstName": "Almet",
                    "lastName": "Test",
                    "gender": "female",
                    "role": "Test Role",
                    "relationship": "Test Rel",
                },
                {
                    "firstName": "Tester",
                    "lastName": "McTest",
                    "gender": "Male",
                    "role": "Debug",
                    "relationship": "Friendly",
                },
            ],
            "npcs": [
                {"name": "Shopkeeper", "role": "Vendor", "description": "Sells items"},
                {"name": "Guard", "role": "Security", "description": "Stands watch"},
            ],
            "lore": {
                "Ancient Ruin": "A place of mystery.",
                "Magic Crystal": "Source of power.",
            },
            "character_roles": {
                "Almet Test": "Sarcastic tone",
                "Tester McTest": "Formal speech",
            },
            "word_fixes": {"teh": "the", "wierd": "weird"},
        }
        try:
            with open(npc_test_path, "w", encoding="utf-8") as f:
                json.dump(sample_data, f, indent=4, ensure_ascii=False)
            print(f"Created sample NPC.json at {npc_test_path}")
        except Exception as e:
            print(f"Error creating sample NPC.json: {e}")

    # ส่ง mock_logger เข้าไป
    app = create_npc_manager_card(root, logging_manager=mock_logger)
    app.show_window()

    root.mainloop()
