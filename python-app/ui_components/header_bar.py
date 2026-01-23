"""
HeaderBar - Manages header UI components
จัดการ: logo, version, pin, theme, close buttons
"""
import tkinter as tk
from PIL import Image, ImageTk
from typing import Callable, Dict, Optional


class HeaderBar:
    """Header bar containing logo, version, pin, theme, and close buttons"""

    def __init__(self, parent: tk.Frame, button_factory, appearance_manager, callbacks: Dict[str, Callable]):
        """
        Args:
            parent: Parent frame to pack into
            button_factory: ButtonFactory instance
            appearance_manager: AppearanceManager for theme colors
            callbacks: Dict with keys: 'toggle_topmost', 'toggle_theme', 'exit_program'
        """
        self.parent = parent
        self.button_factory = button_factory
        self.appearance = appearance_manager
        self.callbacks = callbacks

        # Widget references (new naming convention)
        self.lbl_logo: Optional[tk.Label] = None
        self.lbl_version: Optional[tk.Label] = None
        self.btn_pin: Optional[tk.Button] = None
        self.btn_theme: Optional[tk.Button] = None
        self.btn_close: Optional[tk.Button] = None

        # Icon references
        self._logo_icon: Optional[ImageTk.PhotoImage] = None
        self._pin_icon: Optional[ImageTk.PhotoImage] = None
        self._unpin_icon: Optional[ImageTk.PhotoImage] = None
        self._theme_icon: Optional[ImageTk.PhotoImage] = None
        self._close_icon: Optional[ImageTk.PhotoImage] = None

        # State
        self._is_pinned = False

        self._build()

    def _build(self):
        """Build the header bar UI"""
        bg_color = self.appearance.bg_color

        # Main header frame
        self.frame = tk.Frame(
            self.parent,
            bg=bg_color,
            bd=0,
            highlightthickness=0
        )
        self.frame.pack(fill=tk.X, pady=(0, 10))

        # Logo frame (left side)
        logo_frame = tk.Frame(self.frame, bg=bg_color, bd=0, highlightthickness=0)
        logo_frame.pack(side=tk.LEFT, padx=5)

        # Logo
        self._load_logo()
        if self._logo_icon:
            self.lbl_logo = tk.Label(
                logo_frame,
                image=self._logo_icon,
                bg=bg_color
            )
            self.lbl_logo.pack(side=tk.LEFT, padx=(0, 5))

        # Version label
        self.lbl_version = tk.Label(
            logo_frame,
            text="",  # Set via set_version()
            font=("Arial", 8, "normal"),
            bg=bg_color,
            fg="#ffffff"
        )
        self.lbl_version.pack(side=tk.LEFT)

        # Right side buttons (pack in reverse order for right alignment)
        self._create_close_button()
        self._create_pin_button()
        self._create_theme_button()

    def _load_logo(self):
        """Load logo image"""
        try:
            logo = Image.open("assets/mbb_pixel.png")
            logo.thumbnail((64, 64), Image.Resampling.LANCZOS)
            self._logo_icon = ImageTk.PhotoImage(logo)
        except Exception as e:
            print(f"Could not load logo: {e}")

    def _create_close_button(self):
        """Create close button"""
        bg_color = self.appearance.bg_color
        try:
            close_img = Image.open("assets/del.png")
            close_img = close_img.resize((20, 20), Image.Resampling.LANCZOS)
            self._close_icon = ImageTk.PhotoImage(close_img)

            self.btn_close = self.button_factory.create_icon_button(
                self.frame,
                self._close_icon,
                self.callbacks.get('exit_program', lambda: None),
                bg_color
            )
            self.btn_close.pack(side=tk.RIGHT, padx=5)
        except Exception as e:
            print(f"Could not create close button: {e}")
            # Fallback to text button
            self.btn_close = tk.Button(
                self.frame,
                text="×",
                command=self.callbacks.get('exit_program', lambda: None),
                font=("Arial", 16, "bold"),
                fg="#ffffff",
                bg=bg_color,
                bd=0,
                cursor="hand2"
            )
            self.btn_close.pack(side=tk.RIGHT, padx=5)

    def _create_pin_button(self):
        """Create pin/topmost toggle button"""
        bg_color = self.appearance.bg_color
        try:
            # Load icons
            pin_img = Image.open("assets/pin.png").resize((24, 24), Image.Resampling.LANCZOS)
            self._pin_icon = ImageTk.PhotoImage(pin_img)
            unpin_img = Image.open("assets/unpin.png").resize((24, 24), Image.Resampling.LANCZOS)
            self._unpin_icon = ImageTk.PhotoImage(unpin_img)

            self.btn_pin = self.button_factory.create_icon_button(
                self.frame,
                self._pin_icon,
                self.callbacks.get('toggle_topmost', lambda: None),
                bg_color
            )
            self.btn_pin.pack(side=tk.RIGHT, padx=5)
        except Exception as e:
            print(f"Could not create pin button: {e}")

    def _create_theme_button(self):
        """Create theme toggle button"""
        bg_color = self.appearance.bg_color
        try:
            theme_img = Image.open("assets/theme.png").resize((24, 24), Image.Resampling.LANCZOS)
            self._theme_icon = ImageTk.PhotoImage(theme_img)

            self.btn_theme = self.button_factory.create_icon_button(
                self.frame,
                self._theme_icon,
                self.callbacks.get('toggle_theme', lambda: None),
                bg_color
            )
            self.btn_theme.pack(side=tk.RIGHT, padx=5)
        except Exception as e:
            print(f"Could not create theme button: {e}")

    # Public methods
    def set_version(self, version: str):
        """Set version text"""
        if self.lbl_version:
            self.lbl_version.config(text=f"Dalamud v{version}")

    def update_pin_state(self, is_pinned: bool):
        """
        Update pin button icon based on state

        Args:
            is_pinned: True if window is pinned on top
        """
        self._is_pinned = is_pinned
        if self.btn_pin and self._pin_icon and self._unpin_icon:
            # Show pin icon when pinned, unpin icon when not pinned
            icon = self._pin_icon if is_pinned else self._unpin_icon
            self.btn_pin.config(image=icon)

    def update_theme(self):
        """Update colors when theme changes"""
        bg_color = self.appearance.bg_color
        text_color = self.appearance.get_theme_color("text", "#ffffff")

        self.frame.config(bg=bg_color)

        # Logo and version
        if self.lbl_logo and self.lbl_logo.winfo_exists():
            self.lbl_logo.config(bg=bg_color)

        if self.lbl_version and self.lbl_version.winfo_exists():
            self.lbl_version.config(bg=bg_color, fg=text_color)

        # Icon buttons (pin, theme, close)
        for btn in [self.btn_pin, self.btn_theme, self.btn_close]:
            if btn and btn.winfo_exists():
                try:
                    btn.config(bg=bg_color, activebackground=bg_color)
                except tk.TclError:
                    pass  # Icon buttons might not support all configs
