import tkinter as tk
from tkinter import ttk, messagebox
import logging
from loggings import LoggingManager
from appearance import appearance_manager
import threading
import time


class AdvanceUI:
    def __init__(
        self, parent, settings, apply_settings_callback
    ):
        self.parent = parent
        self.settings = settings
        self.apply_settings_callback = apply_settings_callback
        # OCR removed - ocr_toggle_callback parameter deleted
        self.advance_window = None
        self.is_changed = False
        self.create_advance_window()

    def check_screen_resolution(self):
        """ตรวจสอบขนาดหน้าจอที่ตั้งค่าในวินโดว์
        Returns:
            dict: ผลการตรวจสอบ
        """
        try:
            # ดึงข้อมูลหน้าจอที่แท้จริงโดยใช้เมธอดใหม่
            screen_info = self.get_true_screen_info()

            # ใช้ข้อมูล physical resolution เป็นค่าปัจจุบัน
            current_width = screen_info["physical_width"]
            current_height = screen_info["physical_height"]
            scale_factor = screen_info["scale_factor"]

            # ดึงค่าที่ตั้งไว้ใน settings มาเทียบ
            expected_resolution = self.settings.get("screen_size", "2560x1440")
            expected_width, expected_height = map(int, expected_resolution.split("x"))

            # แสดงค่า scale เป็น percentage
            scale_percent = int(scale_factor * 100)

            # เปรียบเทียบค่า (ให้มี tolerance ±5%)
            width_tolerance = expected_width * 0.05
            height_tolerance = expected_height * 0.05

            if (
                abs(current_width - expected_width) > width_tolerance
                or abs(current_height - expected_height) > height_tolerance
            ):
                return {
                    "is_valid": False,
                    "message": (
                        f"ความละเอียดหน้าจอไม่ตรงกับการตั้งค่า!\n"
                        f"ปัจจุบัน: {current_width}x{current_height} (Scale: {scale_percent}%)\n"
                        f"ที่ตั้งไว้: {expected_width}x{expected_height}\n"
                        f"กรุณาตรวจสอบการตั้งค่าความละเอียดหน้าจอ"
                    ),
                    "current": f"{current_width}x{current_height}",
                    "expected": expected_resolution,
                    "scale": scale_factor,
                }

            return {
                "is_valid": True,
                "current": f"{current_width}x{current_height}",
                "expected": expected_resolution,
                "scale": scale_factor,
            }

        except Exception as e:
            print(f"Error checking screen resolution: {e}")
            return {
                "is_valid": False,
                "message": f"เกิดข้อผิดพลาดในการตรวจสอบความละเอียด: {str(e)}",
                "current": "Unknown",
                "expected": "Unknown",
                "scale": 1.0,
            }

    def get_true_screen_info(self):
        """ดึงข้อมูลความละเอียดหน้าจอที่แท้จริงและค่า scale ที่ถูกต้อง โดยใช้หลายวิธีร่วมกัน

        Returns:
            dict: {
                "physical_width": ความกว้างทางกายภาพ,
                "physical_height": ความสูงทางกายภาพ,
                "scale_factor": ค่า scale factor ที่แท้จริง,
                "logical_width": ความกว้างหลังคำนวณ scale,
                "logical_height": ความสูงหลังคำนวณ scale,
                "detection_method": วิธีการที่ใช้ตรวจสอบ
            }
        """
        try:
            import ctypes
            from ctypes import windll, wintypes
            import win32api
            import win32con

            # วิธีที่ 1: ดึงความละเอียดทางกายภาพจาก EnumDisplaySettings
            dm = win32api.EnumDisplaySettings(None, win32con.ENUM_CURRENT_SETTINGS)
            physical_width = dm.PelsWidth
            physical_height = dm.PelsHeight

            # รายการวิธีการดึง scale factor ที่เราจะลองใช้
            scale_methods = []

            # วิธีที่ 2: ใช้ GetScaleFactorForMonitor (Windows 8.1+)
            try:
                DEVICE_PRIMARY = 0
                shcore = ctypes.windll.LoadLibrary("Shcore.dll")
                scale_factor_value = ctypes.c_uint()
                monitor = windll.user32.MonitorFromWindow(
                    0, 1
                )  # MONITOR_DEFAULTTOPRIMARY
                result = shcore.GetScaleFactorForMonitor(
                    monitor, ctypes.byref(scale_factor_value)
                )
                if result == 0:  # S_OK
                    scale_factor = scale_factor_value.value / 100.0
                    scale_methods.append(
                        {"method": "GetScaleFactorForMonitor", "scale": scale_factor}
                    )
            except Exception as e:
                print(f"GetScaleFactorForMonitor failed: {e}")

            # วิธีที่ 3: ใช้ GetDpiForMonitor (Windows 8.1+)
            try:
                MDT_EFFECTIVE_DPI = 0
                shcore = ctypes.windll.LoadLibrary("Shcore.dll")
                dpi_x = ctypes.c_uint()
                dpi_y = ctypes.c_uint()
                monitor = windll.user32.MonitorFromWindow(
                    0, 1
                )  # MONITOR_DEFAULTTOPRIMARY
                result = shcore.GetDpiForMonitor(
                    monitor, MDT_EFFECTIVE_DPI, ctypes.byref(dpi_x), ctypes.byref(dpi_y)
                )
                if result == 0:  # S_OK
                    scale_factor = dpi_x.value / 96.0
                    scale_methods.append(
                        {"method": "GetDpiForMonitor", "scale": scale_factor}
                    )
            except Exception as e:
                print(f"GetDpiForMonitor failed: {e}")

            # วิธีที่ 4: ใช้ GetDeviceCaps (วิธีดั้งเดิม)
            try:
                LOGPIXELSX = 88
                dc = windll.user32.GetDC(None)
                dpi_x = windll.gdi32.GetDeviceCaps(dc, LOGPIXELSX)
                windll.user32.ReleaseDC(None, dc)
                scale_factor = dpi_x / 96.0
                scale_methods.append({"method": "GetDeviceCaps", "scale": scale_factor})
            except Exception as e:
                print(f"GetDeviceCaps failed: {e}")

            # วิธีที่ 5: ดึงค่าจาก registry
            try:
                import winreg

                registry_key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop\WindowMetrics"
                )
                registry_value = winreg.QueryValueEx(registry_key, "AppliedDPI")[0]
                scale_factor = registry_value / 96.0
                scale_methods.append({"method": "Registry", "scale": scale_factor})
            except Exception as e:
                print(f"Registry method failed: {e}")

            # วิธีที่ 6: ขนาดหน้าจอแบบ logical vs physical
            try:
                # ความละเอียดแบบ logical ที่ปรากฏหลังจาก scaling
                logical_width = windll.user32.GetSystemMetrics(0)  # SM_CXSCREEN
                logical_height = windll.user32.GetSystemMetrics(1)  # SM_CYSCREEN

                # ถ้าแตกต่างจาก physical แสดงว่ามี scaling
                if logical_width != physical_width or logical_height != physical_height:
                    width_ratio = physical_width / logical_width
                    height_ratio = physical_height / logical_height
                    # ใช้ค่าเฉลี่ยของอัตราส่วนความกว้างและความสูง
                    scale_factor = (width_ratio + height_ratio) / 2
                    scale_methods.append(
                        {"method": "Screen Dimensions", "scale": scale_factor}
                    )
            except Exception as e:
                print(f"Screen Dimensions method failed: {e}")

            # เลือกวิธีที่น่าเชื่อถือที่สุด (ถ้ามีหลายวิธี)
            best_method = None

            if scale_methods:
                # พิมพ์ค่าที่ได้จากแต่ละวิธีเพื่อตรวจสอบ
                print("Available scale detection methods:")
                for method in scale_methods:
                    print(
                        f"- {method['method']}: {method['scale']:.2f} ({int(method['scale']*100)}%)"
                    )

                # ถ้ามี GetScaleFactorForMonitor ให้ใช้วิธีนี้ก่อน
                for method in scale_methods:
                    if method["method"] == "GetScaleFactorForMonitor":
                        best_method = method
                        break

                # ถ้ายังไม่มี best_method ให้ลองใช้ GetDpiForMonitor
                if not best_method:
                    for method in scale_methods:
                        if method["method"] == "GetDpiForMonitor":
                            best_method = method
                            break

                # ถ้ายังไม่มี best_method ให้ใช้ค่าแรกที่พบ
                if not best_method and scale_methods:
                    best_method = scale_methods[0]

            # ถ้าไม่มีวิธีที่ใช้ได้เลย ให้ใช้ค่าเริ่มต้น
            if not best_method:
                scale_factor = 1.0
                detection_method = "Default"
            else:
                scale_factor = best_method["scale"]
                detection_method = best_method["method"]

            # คำนวณความละเอียดเชิงตรรกะ (logical) ที่มองเห็นจริง
            logical_width = int(physical_width / scale_factor)
            logical_height = int(physical_height / scale_factor)

            print(
                f"Selected method: {detection_method}, Scale: {scale_factor:.2f} ({int(scale_factor*100)}%)"
            )
            print(f"Physical resolution: {physical_width}x{physical_height}")
            print(f"Logical resolution: {logical_width}x{logical_height}")

            return {
                "physical_width": physical_width,
                "physical_height": physical_height,
                "scale_factor": scale_factor,
                "logical_width": logical_width,
                "logical_height": logical_height,
                "detection_method": detection_method,
            }

        except Exception as e:
            print(f"Error getting screen info: {e}")
            # กรณีเกิดข้อผิดพลาด ส่งค่าเริ่มต้น
            return {
                "physical_width": 1920,
                "physical_height": 1080,
                "scale_factor": 1.0,
                "logical_width": 1920,
                "logical_height": 1080,
                "detection_method": "Error",
            }

    def create_advance_window(self):
        """สร้างหน้าต่าง Advanced Settings"""
        if self.advance_window is None or not self.advance_window.winfo_exists():
            self.advance_window = tk.Toplevel(self.parent)
            self.advance_window.title("Advanced Settings")
            self.advance_window.geometry("360x400")  # เพิ่มความสูงรองรับปุ่มใหม่
            self.advance_window.overrideredirect(True)
            appearance_manager.apply_style(self.advance_window)

            # Screen Size Settings
            screen_frame = tk.LabelFrame(
                self.advance_window,
                text="Screen Resolution",
                bg=appearance_manager.bg_color,
                fg="white",
            )
            screen_frame.pack(fill=tk.X, padx=10, pady=5)

            # Current Resolution Display
            current_res_frame = tk.Frame(screen_frame, bg=appearance_manager.bg_color)
            current_res_frame.pack(fill=tk.X, padx=5, pady=2)
            tk.Label(
                current_res_frame,
                text="Current:",
                bg=appearance_manager.bg_color,
                fg="white",
            ).pack(side=tk.LEFT)
            self.current_res_label = tk.Label(
                current_res_frame,
                text="Detecting...",
                bg=appearance_manager.bg_color,
                fg="#2ECC71",
            )
            self.current_res_label.pack(side=tk.RIGHT, padx=5)

            # Width dropdown
            width_frame = tk.Frame(screen_frame, bg=appearance_manager.bg_color)
            width_frame.pack(fill=tk.X, padx=5, pady=2)
            tk.Label(
                width_frame,
                text="Set Width:",
                bg=appearance_manager.bg_color,
                fg="white",
            ).pack(side=tk.LEFT)
            self.screen_width_var = tk.StringVar()
            self.width_combo = ttk.Combobox(
                width_frame,
                values=["1920", "2560", "3440", "3840"],
                textvariable=self.screen_width_var,
                width=8,
            )
            self.width_combo.pack(side=tk.RIGHT, padx=5)

            # Height dropdown
            height_frame = tk.Frame(screen_frame, bg=appearance_manager.bg_color)
            height_frame.pack(fill=tk.X, padx=5, pady=2)
            tk.Label(
                height_frame,
                text="Set Height:",
                bg=appearance_manager.bg_color,
                fg="white",
            ).pack(side=tk.LEFT)
            self.screen_height_var = tk.StringVar()
            self.height_combo = ttk.Combobox(
                height_frame,
                values=["1080", "1440", "1600", "2160"],
                textvariable=self.screen_height_var,
                width=8,
            )
            self.height_combo.pack(side=tk.RIGHT, padx=5)

            # Screen Control Buttons
            screen_btn_frame = tk.Frame(screen_frame, bg=appearance_manager.bg_color)
            screen_btn_frame.pack(fill=tk.X, padx=5, pady=5)

            self.apply_res_button = ttk.Button(
                screen_btn_frame, text="Apply Resolution", command=self.apply_resolution
            )
            self.apply_res_button.pack(side=tk.LEFT, padx=2)

            self.check_res_button = ttk.Button(
                screen_btn_frame, text="Check", command=self.check_resolution_status
            )
            self.check_res_button.pack(side=tk.RIGHT, padx=2)

            # Display Scale Settings
            scale_frame = tk.LabelFrame(
                self.advance_window,
                text="Display Scale",
                bg=appearance_manager.bg_color,
                fg="white",
            )
            scale_frame.pack(fill=tk.X, padx=10, pady=5)

            # Scale info
            scale_info_frame = tk.Frame(scale_frame, bg=appearance_manager.bg_color)
            scale_info_frame.pack(fill=tk.X, padx=5, pady=5)
            tk.Label(
                scale_info_frame,
                text="Current Scale:",
                bg=appearance_manager.bg_color,
                fg="white",
            ).pack(side=tk.LEFT)
            self.scale_label = tk.Label(
                scale_info_frame,
                text="Detecting...",
                bg=appearance_manager.bg_color,
                fg="#2ECC71",
            )
            self.scale_label.pack(side=tk.RIGHT, padx=5)

            # เพิ่มแถบเลื่อนสำหรับปรับค่า scale
            scale_slider_frame = tk.Frame(scale_frame, bg=appearance_manager.bg_color)
            scale_slider_frame.pack(fill=tk.X, padx=5, pady=5)
            tk.Label(
                scale_slider_frame,
                text="Adjust Scale:",
                bg=appearance_manager.bg_color,
                fg="white",
            ).pack(side=tk.LEFT)

            self.scale_var = tk.IntVar(value=100)  # ค่าเริ่มต้น 100%
            self.scale_slider = ttk.Scale(
                scale_slider_frame,
                from_=100,
                to=200,
                orient=tk.HORIZONTAL,
                variable=self.scale_var,
                command=lambda v: self.update_scale_value(int(float(v))),
            )
            self.scale_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

            self.scale_value_label = tk.Label(
                scale_slider_frame,
                text="100%",
                width=4,
                bg=appearance_manager.bg_color,
                fg="white",
            )
            self.scale_value_label.pack(side=tk.RIGHT)

            # Scale buttons
            scale_button_frame = tk.Frame(scale_frame, bg=appearance_manager.bg_color)
            scale_button_frame.pack(fill=tk.X, padx=5, pady=5)

            self.apply_scale_button = ttk.Button(
                scale_button_frame, text="Apply Scale", command=self.apply_scale
            )
            self.apply_scale_button.pack(side=tk.LEFT, padx=5)

            self.detect_button = ttk.Button(
                scale_button_frame,
                text="Detect Current",
                command=self.check_display_scale,
            )
            self.detect_button.pack(side=tk.RIGHT, padx=5)

            # ========================================================================
            # OCR Settings section removed (49 lines deleted)
            # Project is now 100% text hook - no OCR UI needed
            # ========================================================================

            # Save Button
            self.save_button = appearance_manager.create_styled_button(
                self.advance_window, "Save", self.save_settings, hover_bg="#404040"
            )
            self.save_button.pack(pady=10)

            # Close Button - แก้ไขให้เป็นวงกลมสีแดงที่มุมขวาบน
            close_button_size = 24
            close_canvas = tk.Canvas(
                self.advance_window,
                width=close_button_size,
                height=close_button_size,
                bg=appearance_manager.bg_color,
                highlightthickness=0,
            )
            close_canvas.place(x=330, y=5)  # ตำแหน่งขวาบน

            # วาดวงกลมสีแดง
            circle = close_canvas.create_oval(2, 2, 22, 22, fill="#FF4136", outline="")
            # วาดเครื่องหมาย • สีขาว
            x_mark = close_canvas.create_text(
                12, 12, text="•", fill="white", font=("Arial", 12, "bold")
            )

            # เพิ่ม effect เมื่อโฮเวอร์
            def on_close_enter(event):
                close_canvas.itemconfig(circle, fill="#E60000")

            def on_close_leave(event):
                close_canvas.itemconfig(circle, fill="#FF4136")

            close_canvas.tag_bind(circle, "<Enter>", on_close_enter)
            close_canvas.tag_bind(circle, "<Leave>", on_close_leave)
            close_canvas.tag_bind(x_mark, "<Enter>", on_close_enter)
            close_canvas.tag_bind(x_mark, "<Leave>", on_close_leave)

            # เพิ่ม event เมื่อคลิก
            def on_close_click(event):
                self.close()

            close_canvas.tag_bind(circle, "<Button-1>", on_close_click)
            close_canvas.tag_bind(x_mark, "<Button-1>", on_close_click)

            # Bind Events
            self.width_combo.bind("<<ComboboxSelected>>", self.on_change)
            self.height_combo.bind("<<ComboboxSelected>>", self.on_change)
            # OCR removed - gpu_var trace listener deleted

            # Window Movement
            self.advance_window.bind("<Button-1>", self.start_move)
            self.advance_window.bind("<ButtonRelease-1>", self.stop_move)
            self.advance_window.bind("<B1-Motion>", self.do_move)

            # Load Current Settings
            self.load_current_settings()

            # ซ่อนหน้าต่างตอนเริ่มต้น
            self.advance_window.withdraw()

            # ตรวจสอบ scale หลังจากสร้างหน้าต่างเสร็จ
            self.advance_window.after(1000, self.check_display_scale)

            def adjust_window_size():
                # บังคับให้ window คำนวณขนาดที่ต้องการ
                self.advance_window.update_idletasks()

                # รับขนาดที่ต้องการของเนื้อหา
                required_width = self.advance_window.winfo_reqwidth()
                required_height = self.advance_window.winfo_reqheight()

                # เพิ่มพื้นที่ว่างเล็กน้อย
                width = required_width + 20
                height = required_height + 30

                # กำหนดขนาดหน้าต่างใหม่
                self.advance_window.geometry(f"{width}x{height}")
                print(f"ปรับขนาดตามเนื้อหาเป็น: {width}x{height}")

            # เรียกฟังก์ชันหลังจากสร้างเนื้อหาทั้งหมดแล้ว
            self.advance_window.after(100, adjust_window_size)


    def show_mode_notification(self, message, bg_color=None):  # CYBERPUNK: Use theme color default
        """แสดง notification แบบสวยงามเมื่อเปลี่ยนโหมด"""
        if bg_color is None:
            bg_color = appearance_manager.get_theme_color("accent", "#00FFFF")  # CYBERPUNK: Cyan default
        notification = tk.Toplevel(self.advance_window)
        notification.overrideredirect(True)
        notification.attributes("-topmost", True)
        notification.configure(bg=bg_color)

        # สร้างกรอบ notification สวยงาม
        padding = 20  # เพิ่ม padding
        label = tk.Label(
            notification,
            text=message,
            bg=bg_color,
            fg="white",
            font=("IBM Plex Sans Thai Medium", 14, "bold"),  # เพิ่มขนาดฟอนต์
            padx=padding,
            pady=padding,
        )
        label.pack()

        # จัดตำแหน่งตรงกลางหน้าต่าง advance_ui
        notification.update_idletasks()
        width = notification.winfo_width()
        height = notification.winfo_height()
        parent_x = (
            self.advance_window.winfo_x() + self.advance_window.winfo_width() // 2
        )
        parent_y = (
            self.advance_window.winfo_y() + self.advance_window.winfo_height() // 2
        )
        notification.geometry(f"+{parent_x - width // 2}+{parent_y - height // 2}")

        # จางหายไปหลัง 2 วินาที
        def fade_out():
            for i in range(10, -1, -1):
                alpha = i / 10.0
                notification.attributes("-alpha", alpha)
                notification.update()
                time.sleep(0.05)
            notification.destroy()

        notification.after(
            2000, lambda: threading.Thread(target=fade_out, daemon=True).start()
        )

    def update_scale_value(self, value):
        """อัพเดทค่า display scale บน label"""
        self.scale_value_label.config(text=f"{value}%")

    def apply_scale(self):
        """นำค่า scale จากแถบเลื่อนไปใช้"""
        try:
            scale_percent = self.scale_var.get()
            scale_value = scale_percent / 100.0

            # บันทึกค่า scale ลงใน settings
            self.settings.set("display_scale", scale_value)

            # อัพเดทค่าที่แสดง
            self.scale_label.config(text=f"{scale_percent}%")

            # แสดงข้อความยืนยัน
            self.show_status_message(
                f"บันทึกค่า Display Scale {scale_percent}% เรียบร้อยแล้ว ✓", "success"
            )

            # ปิดปุ่มชั่วคราว
            self.apply_scale_button.config(state="disabled")
            self.advance_window.after(
                2000, lambda: self.apply_scale_button.config(state="normal")
            )

        except Exception as e:
            self.show_status_message(f"เกิดข้อผิดพลาด: {str(e)}", "error")

    def apply_resolution(self):
        """Apply the selected screen resolution"""
        try:
            new_width = self.screen_width_var.get()
            new_height = self.screen_height_var.get()
            new_resolution = f"{new_width}x{new_height}"

            # บันทึกค่าใหม่
            self.settings.set("screen_size", new_resolution)

            # อัพเดท UI โดยตรงโดยไม่เรียก check_resolution_status
            self.current_res_label.config(text=new_resolution, fg="#2ECC71")  # สีเขียว

            # แสดงข้อความยืนยัน
            messagebox.showinfo(
                "บันทึกเรียบร้อย", f"บันทึกความละเอียด {new_resolution} เรียบร้อยแล้ว"
            )

            # อัพเดท UI
            self.apply_res_button.config(state="disabled")
            self.advance_window.after(
                2000, lambda: self.apply_res_button.config(state="normal")
            )

        except Exception as e:
            messagebox.showerror("Error", f"Failed to apply resolution: {str(e)}")

    def show_resolution_warning(self, resolution_info):
        """ฟังก์ชันนี้ยังคงอยู่เพื่อความเข้ากันได้กับโค้ดเดิม แต่จะไม่แสดงหน้าต่าง dialog"""
        # แทนที่จะแสดงหน้าต่างเตือน ให้แสดงข้อความผ่าน messagebox และทำงานต่อไป
        current_res = resolution_info["current"]
        expected_res = resolution_info["expected"]

        # ใช้ความละเอียดปัจจุบันแทน
        width, height = current_res.split("x")
        self.screen_width_var.set(width)
        self.screen_height_var.set(height)
        self.settings.set("screen_size", current_res)

        # แจ้งผู้ใช้
        messagebox.showinfo(
            "ปรับความละเอียดอัตโนมัติ",
            f"ปรับความละเอียดเป็น {current_res} โดยอัตโนมัติ\n(จากเดิม: {expected_res})",
        )
        return None  # ส่งคืน None แทนหน้าต่าง dialog

    def show_scale_warning(self, current_scale, screen_res=None):
        """ฟังก์ชันนี้ยังคงอยู่เพื่อความเข้ากันได้กับโค้ดเดิม แต่จะไม่แสดงหน้าต่าง dialog"""
        # แทนที่จะแสดงหน้าต่างเตือน ให้บันทึกค่า scale ปัจจุบันและแจ้งผู้ใช้
        scale_percent = int(current_scale * 100)
        self.settings.set("display_scale", current_scale)
        self.scale_label.config(text=f"{scale_percent}%")

        if hasattr(self, "scale_slider"):
            self.scale_slider.set(scale_percent)

        # แจ้งผู้ใช้
        messagebox.showinfo(
            "ปรับ Display Scale อัตโนมัติ",
            f"ปรับ Display Scale เป็น {scale_percent}% โดยอัตโนมัติ",
        )
        return None  # ส่งคืน None แทนหน้าต่าง dialog

    def use_current_resolution_auto(self, current_res):
        """ใช้ความละเอียดหน้าจอปัจจุบันเป็นการตั้งค่าโดยอัตโนมัติ โดยไม่แสดงข้อความ"""
        try:
            # แยกค่าความกว้างและความสูงจากสตริง (เช่น "1920x1080")
            width, height = current_res.split("x")

            # อัพเดตค่าใน combobox
            self.screen_width_var.set(width)
            self.screen_height_var.set(height)

            # บันทึกการตั้งค่าใหม่
            new_resolution = f"{width}x{height}"
            self.settings.set("screen_size", new_resolution)

            # อัพเดทสถานะ UI
            self.current_res_label.config(text=new_resolution, fg="#2ECC71")

            # ไม่แสดง messagebox เพื่อไม่ให้รบกวนการทำงาน
            print(f"ปรับค่าอัตโนมัติเป็น {new_resolution}")
            return True
        except Exception as e:
            print(f"เกิดข้อผิดพลาดในการปรับค่าอัตโนมัติ: {e}")
            return False

    def check_resolution_status(self):
        """ตรวจสอบและแสดงสถานะความละเอียดหน้าจอโดยไม่แสดงหน้าต่างแจ้งเตือน"""
        resolution_info = self.check_screen_resolution()
        current_res = resolution_info["current"]
        self.current_res_label.config(text=current_res)

        if not resolution_info["is_valid"]:
            # แสดงข้อความเตือนด้วยสีแดง
            self.current_res_label.config(fg="#FF6B6B")  # สีแดง

            # ปรับใช้ความละเอียดปัจจุบันโดยอัตโนมัติ
            try:
                width, height = current_res.split("x")
                self.screen_width_var.set(width)
                self.screen_height_var.set(height)

                # บันทึกการเปลี่ยนแปลงลง settings โดยอัตโนมัติ
                self.settings.set("screen_size", current_res)

                # แสดงข้อความยืนยันการปรับอัตโนมัติโดยใช้ messagebox แทนหน้าต่างแจ้งเตือนเดิม
                print(f"ปรับความละเอียดเป็น {current_res} โดยอัตโนมัติ")
                messagebox.showinfo(
                    "ปรับความละเอียดอัตโนมัติ", f"ปรับความละเอียดเป็น {current_res} เรียบร้อยแล้ว"
                )
            except Exception as e:
                print(f"เกิดข้อผิดพลาดในการปรับความละเอียด: {e}")
                messagebox.showerror("Error", f"ไม่สามารถปรับความละเอียดได้: {e}")
        else:
            self.current_res_label.config(fg="#2ECC71")  # สีเขียว

    def show_status_message(self, message, status_type="info"):
        """แสดงข้อความสถานะบนหน้าต่าง advance_ui โดยไม่ใช้หน้าต่าง dialog

        Args:
            message (str): ข้อความที่จะแสดง
            status_type (str): ประเภทข้อความ ("success", "error", "info")
        """
        if not hasattr(self, "status_label"):
            # ก่อนปุ่ม Save Button เพิ่ม frame สำหรับแสดงข้อความสถานะ
            status_frame = tk.Frame(self.advance_window, bg=appearance_manager.bg_color)
            status_frame.pack(fill=tk.X, padx=10, pady=5)

            # เส้นคั่นด้านบน - CYBERPUNK
            separator = tk.Frame(status_frame, height=1, bg=appearance_manager.get_theme_color("border", "#00FFFF"))
            separator.pack(fill=tk.X, pady=5)

            # สร้าง label สำหรับแสดงข้อความ
            self.status_label = tk.Label(
                status_frame,
                text="",
                bg=appearance_manager.bg_color,
                fg="white",
                wraplength=330,
                justify=tk.LEFT,
                font=("IBM Plex Sans Thai Medium", 10),
            )
            self.status_label.pack(fill=tk.X, padx=5, pady=5)

            # เส้นคั่นด้านล่าง - CYBERPUNK
            separator2 = tk.Frame(status_frame, height=1, bg=appearance_manager.get_theme_color("border", "#00FFFF"))
            separator2.pack(fill=tk.X, pady=5)

            # Save Button (คงเดิม)
            self.save_button = appearance_manager.create_styled_button(
                self.advance_window, "Save", self.save_settings, hover_bg="#404040"
            )
            self.save_button.pack(pady=10)

        # กำหนดสีตามประเภทข้อความ - CYBERPUNK
        color = {
            "success": appearance_manager.get_theme_color("accent", "#00FFFF"),  # Cyan (CYBERPUNK)
            "error": appearance_manager.get_theme_color("error", "#FF1493"),  # Deep pink (CYBERPUNK)
            "info": appearance_manager.get_theme_color("accent_light", "#4cfefe"),  # Light cyan (CYBERPUNK)
        }.get(status_type, "white")

        # อัพเดทข้อความและสี
        self.status_label.config(text=message, fg=color)

        # ยกเลิกข้อความหลังผ่านไป 5 วินาที
        self.advance_window.after(5000, lambda: self.status_label.config(text=""))

        # อัพเดท UI
        self.advance_window.update()

    def validate_screen_resolution(self):
        """ตรวจสอบความละเอียดหน้าจอโดยคำนึงถึง Display Scale
        Returns:
            dict: ผลการตรวจสอบ {"is_valid": bool, "message": str}
        """
        try:
            # ใช้ข้อมูลที่แม่นยำจากฟังก์ชันใหม่
            screen_info = self.get_true_screen_info()

            physical_width = screen_info["physical_width"]
            physical_height = screen_info["physical_height"]
            current_scale = screen_info["scale_factor"]

            # ดึงค่าที่ตั้งไว้ใน settings
            set_resolution = self.settings.get("screen_size", "2560x1440")
            set_width, set_height = map(int, set_resolution.split("x"))

            # เปรียบเทียบค่าความละเอียดทางกายภาพ (ให้มี tolerance ±5%)
            width_tolerance = set_width * 0.05
            height_tolerance = set_height * 0.05

            scale_percent = int(current_scale * 100)

            if (
                abs(physical_width - set_width) > width_tolerance
                or abs(physical_height - set_height) > height_tolerance
            ):
                return {
                    "is_valid": False,
                    "message": (
                        f"ความละเอียดหน้าจอไม่ตรงกับการตั้งค่า!\n"
                        f"ปัจจุบัน: {physical_width}x{physical_height} (Scale: {scale_percent}%)\n"
                        f"ที่ตั้งไว้: {set_width}x{set_height}\n"
                        f"กรุณาตรวจสอบการตั้งค่าความละเอียดหน้าจอ"
                    ),
                    "current": f"{physical_width}x{physical_height}",
                    "expected": set_resolution,
                    "scale": current_scale,
                }

            return {
                "is_valid": True,
                "message": "ความละเอียดหน้าจอตรงกับการตั้งค่า",
                "current": f"{physical_width}x{physical_height}",
                "expected": set_resolution,
                "scale": current_scale,
            }

        except Exception as e:
            return {
                "is_valid": False,
                "message": f"เกิดข้อผิดพลาดในการตรวจสอบความละเอียด: {e}",
                "current": "Unknown",
                "expected": "Unknown",
                "scale": 1.0,
            }

    def check_display_scale(self):
        """ตรวจสอบ Display Scale โดยไม่แสดงหน้าต่างแจ้งเตือน"""
        try:
            # 1. ตรวจสอบความละเอียดหน้าจอก่อน
            resolution_check = self.check_screen_resolution()
            if not resolution_check["is_valid"]:
                # ไม่แสดงหน้าต่างแจ้งเตือน แต่ปรับใช้ค่าปัจจุบันโดยอัตโนมัติ
                current_res = resolution_check["current"]
                try:
                    width, height = current_res.split("x")
                    self.screen_width_var.set(width)
                    self.screen_height_var.set(height)
                    self.settings.set("screen_size", current_res)
                    print(f"ปรับความละเอียดเป็น {current_res} อัตโนมัติ")
                except Exception as e:
                    print(f"เกิดข้อผิดพลาด: {e}")

                self.scale_label.config(text="ค่าอัตโนมัติ")
                return None

            # 2. ดึงข้อมูล Scale โดยใช้เมธอดใหม่
            screen_info = self.get_true_screen_info()
            current_scale = screen_info["scale_factor"]
            scale_percent = int(current_scale * 100)
            detection_method = screen_info["detection_method"]

            # อัพเดท label แสดงค่า scale
            self.scale_label.config(text=f"{scale_percent}%")

            # ตั้งค่าแถบเลื่อน scale ให้ตรงกับค่าปัจจุบัน
            if hasattr(self, "scale_slider"):
                self.scale_slider.set(scale_percent)

            # บันทึกค่า scale ปัจจุบันลงใน settings
            saved_scale = self.settings.get("display_scale")
            if saved_scale is None or abs(current_scale - saved_scale) > 0.01:
                self.settings.set("display_scale", current_scale)
                print(
                    f"Updated display_scale in settings to {current_scale:.2f} ({scale_percent}%)"
                )

            return current_scale

        except Exception as e:
            print(f"Error checking display scale: {e}")
            self.scale_label.config(text="Error")
            return None

    def open_display_settings(self):
        """เปิดหน้าต่าง Display Settings ของ Windows"""
        import os

        os.system("start ms-settings:display")

    def ensure_dialog_on_top(self, dialog, title="แจ้งเตือน"):
        """ฟังก์ชันนี้ทำให้แน่ใจว่า dialog จะอยู่บนสุดโดยใช้หลายเทคนิครวมกัน"""

        # ทำให้หน้าต่างหลักอยู่บนสุดก่อน
        self.advance_window.attributes("-topmost", True)
        self.advance_window.lift()
        self.advance_window.focus_force()
        self.advance_window.update()

        # ตั้งค่า dialog
        dialog.title(title)
        dialog.attributes("-topmost", True)
        dialog.focus_force()
        dialog.grab_set()
        dialog.update()

        # ทำให้ dialog กะพริบเพื่อดึงความสนใจ
        def blink_dialog():
            colors = ["#FF4500", "#FF6347", "#FF7F50", "#FF6347", "#FF4500"]
            original_bg = dialog.cget("bg")

            # สร้างเฟรมขอบสำหรับเน้นความสนใจ
            border_frame = tk.Frame(dialog, bg=colors[0], padx=3, pady=3)
            if not hasattr(dialog, "content_frame"):
                # ย้ายทุก widget ไปที่ content_frame ใหม่
                dialog.content_frame = tk.Frame(border_frame, bg=original_bg)
                dialog.content_frame.pack(fill=tk.BOTH, expand=True)
                for widget in dialog.winfo_children():
                    if widget != border_frame:
                        widget.pack_forget()
                        widget.pack(in_=dialog.content_frame, fill=tk.BOTH, expand=True)
            border_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

            # ทำให้กะพริบ
            for color in colors:
                border_frame.config(bg=color)
                dialog.attributes("-topmost", True)
                dialog.lift()
                dialog.update()
                time.sleep(0.05)

            border_frame.config(bg="#FF4500")

            # ทำซ้ำอีกครั้งหลังจาก 500ms
            dialog.after(500, lambda: dialog.attributes("-topmost", True))
            dialog.after(800, lambda: dialog.lift())

        # เรียกใช้งานการกะพริบหลังจาก dialog แสดงแล้ว
        dialog.after(100, blink_dialog)

        # ตั้งเวลาเพื่อทำให้แน่ใจว่ายังอยู่บนสุด
        for delay in [1000, 2000, 3000]:
            dialog.after(delay, lambda d=dialog: d.attributes("-topmost", True))
            dialog.after(delay + 100, lambda d=dialog: d.lift())

        return dialog

    def check_dialog_visibility(self, dialog):
        """ตรวจสอบว่า dialog ยังมองเห็นได้และอยู่บนสุดหรือไม่
        ถ้าไม่ จะทำให้มองเห็นได้อีกครั้ง"""
        try:
            if dialog and dialog.winfo_exists():
                # ตรวจสอบว่า dialog ถูกย่อหรือไม่
                if dialog.state() == "iconic":
                    dialog.deiconify()

                # ทำให้ dialog อยู่บนสุดอีกครั้ง
                dialog.attributes("-topmost", True)
                dialog.lift()
                dialog.focus_force()

                # หาตำแหน่งปัจจุบันของ dialog
                x = dialog.winfo_x()
                y = dialog.winfo_y()

                # ถ้าอยู่นอกหน้าจอ เอากลับมาวางกลางหน้าจอ
                if (
                    x < 0
                    or y < 0
                    or x > dialog.winfo_screenwidth()
                    or y > dialog.winfo_screenheight()
                ):
                    width = dialog.winfo_width()
                    height = dialog.winfo_height()
                    new_x = (dialog.winfo_screenwidth() // 2) - (width // 2)
                    new_y = (dialog.winfo_screenheight() // 2) - (height // 2)
                    dialog.geometry(f"+{new_x}+{new_y}")

                # กะพริบขอบหน้าต่างเพื่อดึงความสนใจ
                original_bg = dialog.cget("bg")
                for _ in range(2):
                    dialog.configure(bg="#FF4500")
                    dialog.update()
                    time.sleep(0.1)
                    dialog.configure(bg=original_bg)
                    dialog.update()
                    time.sleep(0.1)

                return True
            else:
                return False
        except Exception as e:
            print(f"ข้อผิดพลาดในการตรวจสอบหน้าต่าง: {e}")
            return False

    def load_current_settings(self):
        """โหลดค่าปัจจุบันจาก settings"""
        screen_size = self.settings.get("screen_size", "2560x1440")
        width, height = screen_size.split("x")
        self.screen_width_var.set(width)
        self.screen_height_var.set(height)
        # OCR removed - gpu_var line deleted
        self.is_changed = False
        self.update_save_button()

    # OCR removed - toggle_gpu() method deleted
    # def toggle_gpu(self):
    #     """OCR removed - project is 100% text hook"""
    #     pass

    def save_settings(self):
        """Save current settings"""
        try:
            # Save screen resolution
            screen_size = (
                f"{self.screen_width_var.get()}x{self.screen_height_var.get()}"
            )
            self.settings.set_screen_size(screen_size)

            # OCR removed - GPU setting lines deleted

            print(f"\n=== Settings Saved ===")
            print(f"Screen Size: {screen_size}")
            # OCR removed - GPU print line deleted
            print("====================\n")

            new_settings = {"screen_size": screen_size}

            if callable(self.apply_settings_callback):
                self.apply_settings_callback(new_settings)

            self.save_button.config(text="Saved!")
            self.advance_window.after(
                2000, lambda: self.save_button.config(text="Save")
            )
            self.is_changed = False

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {str(e)}")

    def on_change(self, event):
        """Called when any setting is changed"""
        self.is_changed = True
        self.update_save_button()

    def update_save_button(self):
        """Update save button state based on changes"""
        self.save_button.config(text="SAVE" if self.is_changed else "Save")

    def open(self):
        """Show the advanced settings window"""
        if not self.advance_window.winfo_viewable():
            # Position window
            x = self.parent.winfo_x() + self.parent.winfo_width() + 10
            y = self.parent.winfo_y()
            self.advance_window.geometry(f"+{x}+{y}")

            # Show window
            self.advance_window.deiconify()
            self.advance_window.lift()
            self.advance_window.attributes("-topmost", True)

            # Reset state
            self.load_current_settings()
            self.is_changed = False
            self.update_save_button()

    def close(self):
        """Hide the advanced settings window"""
        if self.advance_window and self.advance_window.winfo_exists():
            self.advance_window.withdraw()
            self.is_changed = False
            self.save_button.config(text="Save")

    def start_move(self, event):
        """Start window drag operation"""
        self.x = event.x
        self.y = event.y

    def stop_move(self, event):
        """End window drag operation"""
        self.x = None
        self.y = None

    def do_move(self, event):
        """Handle window dragging"""
        if hasattr(self, "x") and hasattr(self, "y"):
            deltax = event.x - self.x
            deltay = event.y - self.y
            x = self.advance_window.winfo_x() + deltax
            y = self.advance_window.winfo_y() + deltay
            self.advance_window.geometry(f"+{x}+{y}")
