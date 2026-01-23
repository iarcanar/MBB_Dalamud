"""
ControlPanel - Manages main control area
จัดการ: start/stop, status, area selection buttons (Swap Data removed)
"""
import tkinter as tk
from typing import Callable, Dict, Optional


class ControlPanel:
    """Control panel for translation controls and area selection"""

    def __init__(self, parent: tk.Frame, button_factory, appearance_manager, callbacks: Dict[str, Callable]):
        """
        Args:
            parent: Parent frame
            button_factory: ButtonFactory instance
            appearance_manager: AppearanceManager for theme colors
            callbacks: Dict with keys:
                - 'toggle_translation'
                # Swap Data removed - 'swap_npc_data' deleted
                - 'start_selection_a'
                - 'start_selection_b'
                - 'start_selection_c'
        """
        self.parent = parent
        self.button_factory = button_factory
        self.appearance = appearance_manager
        self.callbacks = callbacks

        # Widget references (new naming convention)
        self.btn_start_stop: Optional[tk.Button] = None
        self.lbl_status: Optional[tk.Label] = None
        # Swap button (UI only - swap functionality disabled)
        self.lbl_swap: Optional[tk.Label] = None  # Display label for current database
        self.lbl_swap_border: Optional[tk.Frame] = None  # Border frame for lbl_swap
        self.btn_swap: Optional[tk.Button] = None  # Small button (disabled for now)
        # OCR Area Selection removed - btn_area_a, btn_area_b, btn_area_c deleted
        self.lbl_info: Optional[tk.Label] = None

        # State
        self._is_translating = False

        self._build()

    def _build(self):
        """Build the control panel UI"""
        bg_color = self.appearance.bg_color

        self.frame = tk.Frame(
            self.parent,
            bg=bg_color,
            bd=0,
            highlightthickness=0
        )
        self.frame.pack(fill=tk.BOTH, expand=True, pady=0)
        self.frame.pack_propagate(False)

        # START/STOP button
        self._create_start_stop_button()

        # Status label
        self._create_status_label()

        # Swap button (UI restored from original project)
        self._create_swap_button()

        # Info label
        self._create_info_label()

    def _create_start_stop_button(self):
        """Create the START/STOP toggle button (แปลงจาก Canvas เป็น tk.Button)"""
        self.btn_start_stop = self.button_factory.create_button(
            self.frame,
            text="START",
            command=self.callbacks.get('toggle_translation', lambda: None),
            style="primary",
            width=24,
            height=2
        )
        self.btn_start_stop.pack(pady=5, anchor="center")

    def _create_status_label(self):
        """Create status display label"""
        bg_color = self.appearance.bg_color

        status_frame = tk.Frame(self.frame, bg=bg_color, bd=0, highlightthickness=0)
        status_frame.pack(fill=tk.X, pady=(5, 5), anchor="center")

        self.lbl_status = tk.Label(
            status_frame,
            text="Ready",
            font=("Arial", 10),
            bg=bg_color,
            fg=self.appearance.get_theme_color("secondary", "#b2b2b2"),
            pady=2
        )
        self.lbl_status.pack(fill="x", expand=True, padx=5, pady=2)

    # OCR Area Selection removed - _create_area_buttons() method deleted (39 lines)

    def _create_swap_button(self):
        """Create NPC data display label and swap button (from original project)"""
        bg_color = self.appearance.bg_color

        # Container frame for label + button
        swap_container = tk.Frame(self.frame, bg=bg_color, bd=0, highlightthickness=0)
        swap_container.pack(pady=3, anchor="center")

        # Border frame for label (to create colored border like buttons)
        magenta_color = self.appearance.get_theme_color("secondary", "#FF00FF")
        border_frame = tk.Frame(
            swap_container,
            bg=magenta_color,
            bd=0,
            highlightthickness=1,
            highlightbackground=magenta_color,
            highlightcolor=magenta_color
        )
        border_frame.pack(side=tk.LEFT)

        # Display label (non-clickable, shows current database)
        # Styled to look like a button but not clickable
        self.lbl_swap = tk.Label(
            border_frame,
            text="ใช้: FFXIV",  # Default, will be updated
            font=("Nasalization Rg", 9, "bold"),
            fg=magenta_color,
            bg="#0a0a0f",  # Same as primary button bg
            relief="flat",
            bd=0,
            width=19,
            height=2,  # Match START/STOP button height
            anchor="center",
            justify="center"
        )
        self.lbl_swap.pack(padx=1, pady=1)  # Inner padding creates border effect

        # Spacer to push swap button to the right
        spacer = tk.Frame(swap_container, bg=bg_color, width=5)
        spacer.pack(side=tk.LEFT)

        # Small swap button on the right (functionality disabled)
        self.btn_swap = self.button_factory.create_button(
            swap_container,
            text="⇄",  # Swap icon
            command=lambda: None,  # Disabled - no swap functionality
            style="utility",
            width=3,
            height=2  # Match label height
        )
        self.btn_swap.pack(side=tk.LEFT)

        # Disable button interaction (no hover, no click)
        self.btn_swap.config(state="disabled", cursor="arrow")

        # Keep references
        self.lbl_swap_border = border_frame
        self.btn_swap_display = self.lbl_swap

    def _create_info_label(self):
        """Create info label at bottom of control panel"""
        bg_color = self.appearance.bg_color

        self.lbl_info = tk.Label(
            self.frame,
            text="",
            font=("Tahoma", 8),
            bg=bg_color,
            fg=self.appearance.get_theme_color("text_dim", "#666666"),
            justify=tk.CENTER,
            wraplength=250
        )
        self.lbl_info.pack(pady=(0, 5), anchor="center")

    # Public methods
    def set_translating(self, is_translating: bool):
        """
        Update START/STOP button state

        Args:
            is_translating: True if translation is active
        """
        self._is_translating = is_translating
        text = "STOP" if is_translating else "START"
        if self.btn_start_stop:
            self.btn_start_stop.config(text=text)

    def set_status(self, status: str):
        """
        Update status label text

        Args:
            status: Status text to display
        """
        if self.lbl_status:
            self.lbl_status.config(text=status)

    def set_swap_text(self, text: str):
        """
        Update swap display label text

        Args:
            text: Text to display (e.g., "FFXIV", game name)
        """
        if self.lbl_swap:
            # Add prefix if text doesn't start with it
            display_text = text if text.startswith("ใช้: ") else f"ใช้: {text}"
            self.lbl_swap.config(text=display_text)

    def set_info(self, text: str):
        """
        Update info label text

        Args:
            text: Info text to display
        """
        if self.lbl_info:
            self.lbl_info.config(text=text)

    # OCR Area Selection removed - update_area_highlights() method deleted (17 lines)

    def update_theme(self):
        """Update colors when theme changes"""
        bg_color = self.appearance.bg_color
        self.frame.config(bg=bg_color)

        # Update all widgets
        if self.lbl_status and self.lbl_status.winfo_exists():
            self.lbl_status.config(
                bg=bg_color,
                fg=self.appearance.get_theme_color("secondary", "#b2b2b2")
            )

        # Update swap label and border
        if self.lbl_swap and self.lbl_swap.winfo_exists():
            magenta_color = self.appearance.get_theme_color("secondary", "#FF00FF")
            self.lbl_swap.config(
                bg="#0a0a0f",  # Same as primary button bg
                fg=magenta_color
            )
            # Update border frame color
            if self.lbl_swap_border and self.lbl_swap_border.winfo_exists():
                self.lbl_swap_border.config(
                    bg=magenta_color,
                    highlightbackground=magenta_color,
                    highlightcolor=magenta_color
                )

        if self.lbl_info and self.lbl_info.winfo_exists():
            self.lbl_info.config(
                bg=bg_color,
                fg=self.appearance.get_theme_color("text_dim", "#666666")
            )

        # Update START/STOP button
        if self.btn_start_stop and self.btn_start_stop.winfo_exists():
            btn_bg = self.appearance.get_theme_color("button_bg", "#0a0a0f")
            btn_fg = self.appearance.get_theme_color("primary", "#00FFFF")
            hover_bg = self.appearance.get_theme_color("hover_bg", "#1a1a2e")

            self.btn_start_stop.config(
                bg=btn_bg,
                fg=btn_fg,
                activebackground=hover_bg
            )

        # Update SWAP button (small ⇄ button)
        if self.btn_swap and self.btn_swap.winfo_exists():
            btn_bg = self.appearance.get_theme_color("button_bg", "#0a0a0f")
            utility_fg = self.appearance.get_theme_color("text", "#ffffff")
            accent = self.appearance.get_accent_color()

            self.btn_swap.config(
                bg=btn_bg,
                fg=utility_fg,
                activebackground=accent
            )

        # OCR Area Selection removed - area buttons theme update deleted (11 lines)
