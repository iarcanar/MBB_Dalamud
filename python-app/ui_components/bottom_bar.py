"""
BottomBar - Manages bottom toolbar
จัดการ: TUI, LOG, MINI, NPC Manager, Settings buttons
"""
import tkinter as tk
from PIL import Image, ImageTk
from typing import Callable, Dict, Optional


class BottomBar:
    """Bottom toolbar with toggle buttons and utility buttons"""

    def __init__(
        self,
        parent: tk.Widget,
        button_factory,
        appearance_manager,
        button_state_manager,
        callbacks: Dict[str, Callable]
    ):
        """
        Args:
            parent: Parent widget (root window, not frame)
            button_factory: ButtonFactory instance
            appearance_manager: AppearanceManager for theme colors
            button_state_manager: ButtonStateManager for state tracking
            callbacks: Dict with keys:
                - 'toggle_tui'
                - 'toggle_log'
                - 'toggle_mini'
                - 'toggle_npc_manager'
                - 'toggle_settings'
        """
        self.parent = parent
        self.button_factory = button_factory
        self.appearance = appearance_manager
        self.state_manager = button_state_manager
        self.callbacks = callbacks

        # Widget references (new naming convention)
        self.btn_tui: Optional[tk.Button] = None
        self.btn_log: Optional[tk.Button] = None
        self.btn_mini: Optional[tk.Button] = None
        self.btn_npc_manager: Optional[tk.Button] = None
        self.btn_settings: Optional[tk.Button] = None
        self.lbl_description: Optional[tk.Label] = None
        self.lbl_info: Optional[tk.Label] = None

        # Icon references
        self._settings_icon: Optional[ImageTk.PhotoImage] = None

        # Button descriptions for hover (displayed in lbl_description)
        self._descriptions = {
            "tui": "หน้าต่างแสดงคำแปลหลัก",
            "log": "หน้าต่างแสดงประวัติการแปล",
            "mini": "สลับไปโหมดขนาดเล็ก",
        }

        self._build()

    def _build(self):
        """Build the bottom bar UI"""
        bottom_bg = "#141414"

        # Main container
        self.frame = tk.Frame(
            self.parent,
            bg=bottom_bg,
            height=148,
            bd=0,
            highlightthickness=0
        )
        self.frame.pack(side=tk.BOTTOM, fill=tk.X)
        self.frame.pack_propagate(False)

        # Top section: description label + toggle buttons
        self._create_top_section(bottom_bg)

        # Middle section: NPC Manager + Settings
        self._create_middle_section(bottom_bg)

        # Bottom section: Info label
        self._create_info_section(bottom_bg)

    def _create_top_section(self, bg_color: str):
        """Create description label and toggle buttons"""
        top_frame = tk.Frame(self.frame, bg=bg_color, bd=0, highlightthickness=0)
        top_frame.pack(fill=tk.X, pady=(0, 0))

        # Description label
        self.lbl_description = tk.Label(
            top_frame,
            text="",
            font=("Tahoma", 9),
            bg=bg_color,
            fg=self.appearance.get_theme_color("text_dim", "#b2b2b2"),
            pady=2
        )
        self.lbl_description.pack(fill=tk.X, padx=10)

        # Button container
        btn_container = tk.Frame(top_frame, bg=bg_color, height=35, bd=0, highlightthickness=0)
        btn_container.pack(fill=tk.X, pady=(0, 2))

        btn_frame = tk.Frame(btn_container, bg=bg_color, bd=0, highlightthickness=0)
        btn_frame.pack(fill=tk.X)

        # Create toggle buttons
        self._create_toggle_buttons(btn_frame)

    def _create_toggle_buttons(self, parent: tk.Frame):
        """Create TUI, LOG, MINI toggle buttons"""
        # TUI button
        self.btn_tui = self.button_factory.create_button(
            parent,
            text="TUI",
            command=self._on_tui_click,
            style="toggle"
        )
        self.btn_tui.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2, pady=2)

        # LOG button
        self.btn_log = self.button_factory.create_button(
            parent,
            text="LOG",
            command=self._on_log_click,
            style="toggle"
        )
        self.btn_log.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2, pady=2)

        # MINI button
        self.btn_mini = self.button_factory.create_button(
            parent,
            text="MINI",
            command=self.callbacks.get('toggle_mini', lambda: None),
            style="toggle"
        )
        self.btn_mini.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2, pady=2)

        # Register with state manager (TUI, LOG, and MINI)
        self.state_manager.register_button("tui", self.btn_tui)
        self.state_manager.register_button("log", self.btn_log)
        self.state_manager.register_button("mini", self.btn_mini)

        # Add hover effects
        self._setup_hover_effects()

    def _create_middle_section(self, bg_color: str):
        """Create NPC Manager and Settings buttons"""
        middle_frame = tk.Frame(self.frame, bg=bg_color, bd=0, highlightthickness=0)
        middle_frame.pack(pady=(10, 5), fill=tk.X)

        center_frame = tk.Frame(middle_frame, bg=bg_color, bd=0, highlightthickness=0)
        center_frame.pack(expand=True)

        # NPC Manager button
        self.btn_npc_manager = self.button_factory.create_button(
            center_frame,
            text="NPC Manager",
            command=self.callbacks.get('toggle_npc_manager', lambda: None),
            style="utility",
            width=12,
            height=1
        )
        self.btn_npc_manager.pack(side=tk.LEFT, padx=(0, 10))

        # Settings button (icon)
        self._create_settings_button(center_frame, bg_color)

    def _create_settings_button(self, parent: tk.Frame, bg_color: str):
        """Create settings icon button"""
        try:
            setting_img = Image.open("assets/setting.png")
            setting_img.thumbnail((20, 20), Image.Resampling.LANCZOS)
            self._settings_icon = ImageTk.PhotoImage(setting_img)

            self.btn_settings = self.button_factory.create_icon_button(
                parent,
                self._settings_icon,
                self.callbacks.get('toggle_settings', lambda: None),
                bg_color
            )
            self.btn_settings.pack(side=tk.LEFT)
        except Exception as e:
            print(f"Could not load settings icon: {e}")
            # Fallback to text button
            self.btn_settings = self.button_factory.create_button(
                parent,
                text="⚙",
                command=self.callbacks.get('toggle_settings', lambda: None),
                style="utility"
            )
            self.btn_settings.pack(side=tk.LEFT)

    def _create_info_section(self, bg_color: str):
        """Create info label at bottom"""
        info_container = tk.Frame(self.frame, bg=bg_color, height=30, bd=0, highlightthickness=0)
        info_container.pack(fill=tk.X, pady=(2, 0))
        info_container.pack_propagate(False)

        self.lbl_info = tk.Label(
            info_container,
            text="",  # Set via set_info()
            bg=bg_color,
            fg="#b2b2b2",
            font=("Consolas", 8),
            justify=tk.CENTER,
        )
        self.lbl_info.pack(expand=True, fill=tk.BOTH)

    def _setup_hover_effects(self):
        """Setup hover effects for toggle buttons"""
        for key, btn in [("tui", self.btn_tui), ("log", self.btn_log), ("mini", self.btn_mini)]:
            if btn:
                btn.bind("<Enter>", lambda e, k=key: self._on_hover_enter(k), add="+")
                btn.bind("<Leave>", lambda e, k=key: self._on_hover_leave(k), add="+")

    def _on_hover_enter(self, button_key: str):
        """Handle hover enter"""
        if self.lbl_description:
            self.lbl_description.config(text=self._descriptions.get(button_key, ""))

        # Use state manager for TUI/LOG/MINI
        if button_key in ["tui", "log", "mini"]:
            self.state_manager.handle_hover_enter(button_key)

    def _on_hover_leave(self, button_key: str):
        """Handle hover leave"""
        if self.lbl_description:
            self.lbl_description.config(text="")

        # Use state manager for TUI/LOG/MINI
        if button_key in ["tui", "log", "mini"]:
            self.state_manager.handle_hover_leave(button_key)

    def _on_tui_click(self):
        """Handle TUI button click"""
        self.state_manager.toggle_button_immediate("tui")
        callback = self.callbacks.get('toggle_tui')
        if callback:
            callback()

    def _on_log_click(self):
        """Handle LOG button click"""
        self.state_manager.toggle_button_immediate("log")
        callback = self.callbacks.get('toggle_log')
        if callback:
            callback()

    # Public methods
    def set_info(self, text: str):
        """
        Set info label text

        Args:
            text: Info text to display
        """
        if self.lbl_info:
            self.lbl_info.config(text=text)

    def update_theme(self):
        """Update colors when theme changes"""
        bottom_bg = "#141414"
        self.frame.config(bg=bottom_bg)

        # Update labels
        if self.lbl_description and self.lbl_description.winfo_exists():
            self.lbl_description.config(
                bg=bottom_bg,
                fg=self.appearance.get_theme_color("text_dim", "#b2b2b2")
            )

        if self.lbl_info and self.lbl_info.winfo_exists():
            self.lbl_info.config(bg=bottom_bg)

        # Get theme colors
        toggle_bg = self.appearance.get_theme_color("button_bg", "#262637")
        toggle_fg = self.appearance.get_theme_color("toggle", "#00FFFF")
        utility_fg = self.appearance.get_theme_color("text", "#ffffff")
        accent = self.appearance.get_accent_color()

        # Update TUI, LOG, MINI buttons (let ButtonStateManager apply current states)
        for btn in [self.btn_tui, self.btn_log, self.btn_mini]:
            if btn and btn.winfo_exists():
                # Set base colors (ButtonStateManager will override with state-specific colors)
                btn.config(
                    bg=toggle_bg,
                    fg=toggle_fg,
                    activebackground=accent
                )

        # Update NPC Manager button
        if self.btn_npc_manager and self.btn_npc_manager.winfo_exists():
            self.btn_npc_manager.config(
                bg=toggle_bg,
                fg=utility_fg,
                activebackground=accent
            )

        # Update Settings button (icon button)
        if self.btn_settings and self.btn_settings.winfo_exists():
            self.btn_settings.config(bg=bottom_bg)

        # Re-apply current states from ButtonStateManager
        if hasattr(self, 'state_manager'):
            for key in ["tui", "log", "mini"]:
                if key in self.state_manager.button_states:
                    current_state = self.state_manager.button_states[key]["active"]
                    visual_state = "toggle_on" if current_state else "toggle_off"
                    self.state_manager.update_button_visual(key, visual_state)
