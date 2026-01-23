import logging
import tkinter as tk
from PIL import Image, ImageTk
from appearance import appearance_manager


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
        self.mini_loading_label = None  # <-- เพิ่มบรรทัดนี้
        self.mini_ui_blinking = False
        self.is_translating = False
        self.toggle_translation_callback = None  # สำหรับเก็บ callback จาก main UI

        # NEW: Add icon and button references for vertical layout
        self.play_icon = None
        self.pause_icon = None
        self.play_pause_button = None  # Reference to icon button

        self.load_icons()
        self.create_mini_ui()

    def load_icons(self):
        # เพิ่มขนาดไอคอนจาก 10x10 เป็น 15x15
        icon_size = (15, 15)
        self.blink_icon = ImageTk.PhotoImage(
            Image.open("assets/red_icon.png").resize(icon_size)
        )
        self.black_icon = ImageTk.PhotoImage(
            Image.open("assets/black_icon.png").resize(icon_size)
        )
        # เพิ่มไอคอน expand สำหรับปุ่ม toggle (ขนาดใหญ่ขึ้น 2 เท่า)
        toggle_icon_size = (32, 32)
        self.expand_icon = ImageTk.PhotoImage(
            Image.open("assets/expand.png").resize(toggle_icon_size)
        )

        # NEW: Play/Pause icons (22×22 - reduced 20% from 28×28)
        play_pause_size = (22, 22)
        self.play_icon = ImageTk.PhotoImage(
            Image.open("assets/play.png").resize(play_pause_size)
        )
        self.pause_icon = ImageTk.PhotoImage(
            Image.open("assets/pause.png").resize(play_pause_size)
        )

    def create_mini_ui(self):
        """Create vertical Mini UI with play/pause icons"""
        if self.mini_ui and self.mini_ui.winfo_exists():
            self.mini_ui.destroy()

        self.mini_ui = tk.Toplevel(self.root)

        # NEW: Vertical geometry (50×176 - reduced 20% from 220)
        self.mini_ui.geometry("50x176")

        self.mini_ui.overrideredirect(True)
        self.mini_ui.attributes("-topmost", True)

        bg_c = getattr(appearance_manager, "bg_color", "#0a0a0f")  # Cyberpunk: very dark
        self.mini_ui.configure(bg=bg_c)
        self.mini_ui.withdraw()

        # Main frame (NO BORDER in normal state for seamless look)
        main_frame = tk.Frame(
            self.mini_ui,
            bg=bg_c,
            highlightthickness=0,  # No border in normal state
        )
        main_frame.pack(expand=True, fill=tk.BOTH, padx=0, pady=0)

        # COMPONENT 1: Toggle button (expand icon) - TOP
        toggle_button = tk.Button(
            main_frame,
            image=self.expand_icon,
            command=self.show_main_ui_callback,
            bg=bg_c,
            bd=0,
            highlightthickness=0,
            cursor="hand2",
        )
        toggle_button.pack(side=tk.TOP, pady=(8, 8))

        # COMPONENT 2: Play/Pause button (icon-based) - MIDDLE
        self.play_pause_button = tk.Button(
            main_frame,
            image=self.play_icon,  # Start with play icon
            command=self._handle_toggle_translation,
            bg=bg_c,
            bd=0,
            highlightthickness=0,
            cursor="hand2",
        )
        self.play_pause_button.pack(side=tk.TOP, pady=(8, 8))

        # COMPONENT 3: Loading indicator (keep for compatibility, smaller font)
        self.mini_loading_label = tk.Label(
            main_frame,
            text="",
            bg=bg_c,
            fg="#00FFFF",  # Cyberpunk: cyan text
            font=("Arial", 8, "bold"),  # Smaller for narrow width
        )
        self.mini_loading_label.pack(side=tk.TOP, pady=(2, 2))

        # COMPONENT 4: Status indicator - BOTTOM
        status_frame = tk.Frame(
            main_frame,
            bg=bg_c,
            width=25,
            height=25,
        )
        status_frame.pack(side=tk.TOP, pady=(8, 8))
        status_frame.pack_propagate(False)

        self.mini_ui_blink_label = tk.Label(
            status_frame,
            image=self.black_icon,
            bg=bg_c
        )
        self.mini_ui_blink_label.pack(expand=True, fill=tk.BOTH)

        # Hover effects
        def on_play_pause_enter(e):
            self.play_pause_button.config(bg="#2a2a3e")  # Cyberpunk: dark blue-gray

        def on_play_pause_leave(e):
            current_bg = getattr(appearance_manager, "bg_color", "#1a1a1a")
            self.play_pause_button.config(bg=current_bg)

        def on_toggle_enter(e):
            toggle_button.config(bg="#2a2a3e")  # Cyberpunk: dark blue-gray

        def on_toggle_leave(e):
            current_bg = getattr(appearance_manager, "bg_color", "#1a1a1a")
            toggle_button.config(bg=current_bg)

        self.play_pause_button.bind("<Enter>", on_play_pause_enter)
        self.play_pause_button.bind("<Leave>", on_play_pause_leave)
        toggle_button.bind("<Enter>", on_toggle_enter)
        toggle_button.bind("<Leave>", on_toggle_leave)

        # Event bindings for window dragging
        self.mini_ui.bind("<Button-1>", self.start_move_mini_ui)
        self.mini_ui.bind("<B1-Motion>", self.do_move_mini_ui)
        self.mini_ui.bind("<Double-Button-1>", lambda e: self.show_main_ui_from_mini())

        # Apply asymmetric rounded corners
        self.mini_ui.after(100, lambda: self.apply_asymmetric_rounded_corners())

    def apply_asymmetric_rounded_corners(self):
        """
        Apply rounded corners ONLY to the right side (top-right, bottom-right).
        Left side remains sharp since it touches the screen edge.
        """
        try:
            import win32gui
            import win32con
            from ctypes import windll

            self.mini_ui.update_idletasks()
            hwnd = windll.user32.GetParent(self.mini_ui.winfo_id())

            # Remove window decorations
            style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
            style &= ~win32con.WS_CAPTION
            style &= ~win32con.WS_THICKFRAME
            win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)

            width = self.mini_ui.winfo_width()   # 50
            height = self.mini_ui.winfo_height() # 176
            radius = 12

            # Create left rectangle (sharp corners)
            left_region = win32gui.CreateRectRgn(0, 0, 25, height)

            # Create right rounded rectangle
            right_region = win32gui.CreateRoundRectRgn(
                25 - radius,  # Overlap for seamless join
                0,
                width,
                height,
                radius,
                radius
            )

            # Combine regions
            combined_region = win32gui.CreateRectRgn(0, 0, 0, 0)
            win32gui.CombineRgn(combined_region, left_region, right_region, win32con.RGN_OR)

            # Apply to window
            win32gui.SetWindowRgn(hwnd, combined_region, True)

            # Cleanup temporary regions (SetWindowRgn takes ownership of combined_region)
            win32gui.DeleteObject(left_region)
            win32gui.DeleteObject(right_region)

        except Exception as e:
            print(f"Error applying asymmetric rounded corners: {e}")
            # Fallback: Try uniform corners on all sides
            try:
                import win32gui
                from ctypes import windll
                hwnd = windll.user32.GetParent(self.mini_ui.winfo_id())
                region = win32gui.CreateRoundRectRgn(0, 0, 50, 176, 12, 12)
                win32gui.SetWindowRgn(hwnd, region, True)
            except:
                pass  # Give up on rounded corners

    def get_monitor_bounds_for_window(self, window_x, window_y):
        """
        Detect which monitor contains the given window coordinates.
        Returns the monitor's left edge X coordinate.

        Args:
            window_x: X coordinate of the window
            window_y: Y coordinate of the window

        Returns:
            int: Left edge X coordinate of the monitor (0 for primary, 2560 for secondary, etc.)
        """
        try:
            import ctypes
            from ctypes import wintypes, windll, Structure

            # Define RECT structure
            class RECT(Structure):
                _fields_ = [
                    ('left', wintypes.LONG),
                    ('top', wintypes.LONG),
                    ('right', wintypes.LONG),
                    ('bottom', wintypes.LONG)
                ]

            # Define MONITORINFO structure
            class MONITORINFO(Structure):
                _fields_ = [
                    ('cbSize', wintypes.DWORD),
                    ('rcMonitor', RECT),
                    ('rcWork', RECT),
                    ('dwFlags', wintypes.DWORD)
                ]

            # Get window handle
            hwnd = windll.user32.GetParent(self.root.winfo_id())

            # Get monitor containing this window (MONITOR_DEFAULTTONEAREST = 2)
            monitor = windll.user32.MonitorFromWindow(hwnd, 2)

            # Get monitor information
            info = MONITORINFO()
            info.cbSize = ctypes.sizeof(MONITORINFO)
            result = windll.user32.GetMonitorInfoW(monitor, ctypes.byref(info))

            if result:
                monitor_left = info.rcMonitor.left
                print(f"🖥️ Detected monitor left edge: {monitor_left}")
                return monitor_left
            else:
                print("⚠️ Monitor detection failed, defaulting to x=0")
                return 0

        except Exception as e:
            print(f"❌ Error detecting monitor bounds: {e}")
            return 0  # Default to primary monitor

    def show_loading(self):
        """แสดง loading indicator ใน Mini UI"""
        try:
            if hasattr(self, "mini_loading_label") and self.mini_loading_label:
                # ตรวจสอบว่า widget ยังมีอยู่
                if self.mini_loading_label.winfo_exists():
                    self.mini_loading_label.config(text="...")  # หรือใช้สัญลักษณ์อื่น เช่น ⏳
        except tk.TclError:
            # Widget ถูกทำลายแล้ว - ไม่ต้องทำอะไร
            pass
        except Exception as e:
            print(f"Error in show_loading: {e}")

    def hide_loading(self):
        """ซ่อน loading indicator ใน Mini UI"""
        try:
            if hasattr(self, "mini_loading_label") and self.mini_loading_label:
                # ตรวจสอบว่า widget ยังมีอยู่
                if self.mini_loading_label.winfo_exists():
                    self.mini_loading_label.config(text="")
        except tk.TclError:
            # Widget ถูกทำลายแล้ว - ไม่ต้องทำอะไร
            pass
        except Exception as e:
            print(f"Error in hide_loading: {e}")

    # เมธอด lighten_color ควรมีอยู่ในคลาส MiniUI ด้วย ถ้ายังไม่มี
    def lighten_color(self, color, factor=1.3):
        """ทำให้สีอ่อนลงตามค่า factor (เหมือนใน control_ui)"""
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
        except Exception as e:
            print(f"Error lightening color: {e}")
            return color

    def add_highlight_border(self):
        """เพิ่มเอฟเฟกต์ขอบสีฟ้าเมื่อ Mini UI ปรากฏ"""
        try:
            # หา main frame (frame แรกใน mini_ui)
            main_frame = None
            for child in self.mini_ui.winfo_children():
                if isinstance(child, tk.Frame):
                    main_frame = child
                    break

            if main_frame:
                # เก็บสีขอบเดิม
                original_color = main_frame.cget("highlightbackground")
                original_thickness = main_frame.cget("highlightthickness")

                # เปลี่ยนเป็นขอบสีฟ้าหนาขึ้น - เพิ่มความหนาเป็น 3 (จากเดิม 2)
                main_frame.configure(
                    highlightthickness=3, highlightbackground="#00FFFF"
                )

                # ตั้งเวลาเปลี่ยนกลับหลังจาก 1.5 วินาที (เพิ่มจาก 1 วินาที)
                self.mini_ui.after(
                    1500,
                    lambda: main_frame.configure(
                        highlightthickness=original_thickness,
                        highlightbackground=original_color,
                    ),
                )
        except Exception as e:
            print(f"Error adding highlight effect: {e}")

    def update_theme(self, accent_color=None, highlight_color=None):
        """อัพเดท UI ของ MiniUI ด้วยสีธีมใหม่"""
        try:
            # ดึงค่าสีล่าสุดจาก appearance_manager ถ้าไม่ได้ส่งมา
            if accent_color is None:
                accent_color = appearance_manager.get_accent_color()
            if highlight_color is None:
                highlight_color = appearance_manager.get_highlight_color()
            bg_c = appearance_manager.bg_color  # สีพื้นหลังหลัก

            if not self.mini_ui or not self.mini_ui.winfo_exists():
                return

            # อัพเดทพื้นหลังหน้าต่างและ Frame หลัก
            self.mini_ui.configure(bg=bg_c)
            main_frame = None
            for child in self.mini_ui.winfo_children():
                if isinstance(child, tk.Frame):
                    main_frame = child
                    main_frame.configure(bg=bg_c)
                    # อาจจะต้องอัพเดทขอบด้วย ถ้าใช้ highlightbackground
                    # main_frame.configure(highlightbackground="#333333") # หรือสีขอบตามธีม
                    break

            if main_frame:
                toggle_button = None

                for widget in main_frame.winfo_children():
                    # Find toggle button by image
                    if isinstance(widget, tk.Button) and widget.cget("image") == str(self.expand_icon):
                        toggle_button = widget
                        widget.configure(bg=bg_c, activebackground=bg_c)

                    # Find play/pause button by reference
                    elif isinstance(widget, tk.Button) and widget == getattr(self, "play_pause_button", None):
                        widget.configure(bg=bg_c, activebackground=accent_color)

                    # Update loading label
                    elif isinstance(widget, tk.Label) and widget == getattr(self, "mini_loading_label", None):
                        widget.configure(bg=bg_c)

                    # Update status frame
                    elif isinstance(widget, tk.Frame):
                        widget.configure(bg=bg_c)
                        if hasattr(self, "mini_ui_blink_label") and self.mini_ui_blink_label:
                            self.mini_ui_blink_label.configure(bg=bg_c)

                # Re-bind hover effects with updated colors
                def on_play_pause_enter(e):
                    self.play_pause_button.config(bg="#2a2a3e")  # Cyberpunk: dark blue-gray

                def on_play_pause_leave(e):
                    self.play_pause_button.config(bg=appearance_manager.bg_color)

                def on_toggle_enter(e):
                    if toggle_button:
                        toggle_button.config(bg="#2a2a3e")  # Cyberpunk: dark blue-gray

                def on_toggle_leave(e):
                    if toggle_button:
                        toggle_button.config(bg=appearance_manager.bg_color)

                # Rebind events
                if hasattr(self, "play_pause_button"):
                    self.play_pause_button.unbind("<Enter>")
                    self.play_pause_button.unbind("<Leave>")
                    self.play_pause_button.bind("<Enter>", on_play_pause_enter)
                    self.play_pause_button.bind("<Leave>", on_play_pause_leave)

                if toggle_button:
                    toggle_button.unbind("<Enter>")
                    toggle_button.unbind("<Leave>")
                    toggle_button.bind("<Enter>", on_toggle_enter)
                    toggle_button.bind("<Leave>", on_toggle_leave)

            logging.info("MiniUI theme updated.")

        except Exception as e:
            print(f"Error updating mini UI theme: {e}")
            logging.error(f"Error updating mini UI theme: {e}")

    def _handle_toggle_translation(self):
        """จัดการการกดปุ่ม Start/Stop โดยเรียกใช้ callback จาก main UI"""
        if self.toggle_translation_callback:
            self.toggle_translation_callback()

    def update_translation_status(self, is_translating):
        """
        Update translation status and switch play/pause icon.

        Args:
            is_translating: Boolean indicating if translation is active
        """
        try:
            self.is_translating = is_translating
            self.mini_ui_blinking = is_translating

            if is_translating:
                # Switch to PAUSE icon
                if hasattr(self, 'play_pause_button') and self.play_pause_button:
                    self.play_pause_button.config(image=self.pause_icon)

                # Start status indicator blinking (red)
                if hasattr(self, "mini_ui_blink_label") and self.mini_ui_blink_label.winfo_exists():
                    self.start_blinking()
            else:
                # Switch to PLAY icon
                if hasattr(self, 'play_pause_button') and self.play_pause_button:
                    self.play_pause_button.config(image=self.play_icon)

                # Stop blinking (black)
                self.stop_blinking()

            # Refresh UI
            if hasattr(self, "mini_ui") and self.mini_ui.winfo_exists():
                self.mini_ui.update_idletasks()

        except tk.TclError:
            pass  # Widget destroyed
        except Exception as e:
            print(f"❌ Error in update_translation_status: {e}")

    def set_toggle_translation_callback(self, callback):
        """ตั้งค่า callback สำหรับการ toggle การแปล"""
        self.toggle_translation_callback = callback

    def start_blinking(self):
        """แสดงไฟแดงนิ่งๆ แทนการกระพริบ เมื่อกำลังแปล"""
        try:
            # หยุดการกระพริบที่อาจค้างอยู่ก่อน
            self.stop_blinking()

            # ตั้งค่าสถานะว่ากำลังทำงาน แต่ไม่ได้กระพริบแล้ว
            self.mini_ui_blinking = True

            # ตรวจสอบว่า mini_ui_blink_label มีอยู่จริง
            if (
                hasattr(self, "mini_ui_blink_label")
                and self.mini_ui_blink_label.winfo_exists()
            ):
                # แสดงไฟแดงนิ่งๆ เมื่อเริ่มการแปล
                self.mini_ui_blink_label.config(image=self.blink_icon)
        except tk.TclError:
            # Widget ถูกทำลายแล้ว
            pass
        except Exception as e:
            print(f"Error in start_blinking: {e}")

    def stop_blinking(self):
        """หยุดการทำงานและเปลี่ยนไฟกลับเป็นสีดำ"""
        try:
            self.mini_ui_blinking = False

            # ยกเลิกการกระพริบที่อาจกำลังทำงานอยู่ (สำหรับความเข้ากันได้กับโค้ดเดิม)
            if hasattr(self, "blink_timer_id") and self.blink_timer_id:
                try:
                    if (
                        hasattr(self, "mini_ui")
                        and self.mini_ui
                        and self.mini_ui.winfo_exists()
                    ):
                        self.mini_ui.after_cancel(self.blink_timer_id)
                except tk.TclError:
                    pass  # Widget ถูกทำลายแล้ว
                except Exception:
                    pass  # ถ้ายกเลิกไม่ได้ ก็ไม่เป็นไร
                self.blink_timer_id = None

            # รีเซ็ตรูปภาพกลับเป็นสีดำ
            if (
                hasattr(self, "mini_ui_blink_label")
                and self.mini_ui_blink_label.winfo_exists()
            ):
                self.mini_ui_blink_label.config(image=self.black_icon)
        except tk.TclError:
            # Widget ถูกทำลายแล้ว
            pass
        except Exception as e:
            print(f"Error in stop_blinking: {e}")

    def start_move_mini_ui(self, event):
        """เริ่มการเคลื่อนย้ายหน้าต่าง"""
        self.mini_x = event.x_root - self.mini_ui.winfo_x()
        self.mini_y = event.y_root - self.mini_ui.winfo_y()

    def do_move_mini_ui(self, event):
        """ทำการเคลื่อนย้ายหน้าต่าง"""
        x = event.x_root - self.mini_x
        y = event.y_root - self.mini_y
        self.mini_ui.geometry(f"+{x}+{y}")

    def show_main_ui_from_mini(self):
        """สลับกลับไปแสดง main UI"""
        if hasattr(self, "mini_ui"):
            # บันทึกตำแหน่ง mini UI ก่อนซ่อน
            self.mini_ui.withdraw()
        self.show_main_ui_callback()

    def position_at_center_of_main(self, main_x, main_y, main_width, main_height):
        """
        Position mini UI at the left edge of the monitor containing the main UI,
        preserving Y coordinate from main UI.

        Args:
            main_x: Main UI X coordinate
            main_y: Main UI Y coordinate
            main_width: Not used (kept for compatibility)
            main_height: Not used (kept for compatibility)
        """
        # Detect which monitor contains main UI
        monitor_left_edge = self.get_monitor_bounds_for_window(main_x, main_y)

        # Snap to left edge of detected monitor, preserve Y
        self.mini_ui.geometry(f"+{monitor_left_edge}+{main_y}")
        print(f"📍 Mini UI positioned at x={monitor_left_edge}, y={main_y}")

        # Add highlight effect
        self.add_highlight_border()

    def blink_mini_ui(self):
        """จัดการการกระพริบของไฟสถานะ"""
        if (
            self.mini_ui_blinking
            and hasattr(self, "mini_ui")
            and self.mini_ui
            and self.mini_ui.winfo_exists()
        ):
            if (
                hasattr(self, "mini_ui_blink_label")
                and self.mini_ui_blink_label.winfo_exists()
            ):
                try:
                    current_image = self.mini_ui_blink_label.cget("image")
                    # กรณีการเปรียบเทียบ image failed ให้ใช้วิธีสลับไปมา
                    new_image = (
                        self.black_icon
                        if self.blink_timer % 2 == 0
                        else self.blink_icon
                    )
                    self.mini_ui_blink_label.config(image=new_image)
                    # เพิ่มการเก็บค่ารอบการกระพริบ
                    self.blink_timer = (
                        0 if not hasattr(self, "blink_timer") else self.blink_timer + 1
                    )

                    # กำหนดการกระพริบรอบถัดไป
                    self.blink_timer_id = self.mini_ui.after(
                        self.blink_interval, self.blink_mini_ui
                    )
                except Exception as e:
                    print(f"Error in blink animation: {e}")
                    # ถ้ามีข้อผิดพลาด ให้หยุดการกระพริบ
                    self.stop_blinking()
            else:
                self.stop_blinking()
        else:
            self.stop_blinking()
