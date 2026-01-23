"""
ButtonFactory - Standardized button creation for MBB
สร้าง tk.Button ที่เป็นมาตรฐานเดียวกันทั้งหมด
"""
import tkinter as tk
from typing import Callable, Optional
from ui_config import STYLES, ButtonStyle


class ButtonFactory:
    """Factory for creating standardized tk.Button widgets"""

    def __init__(self, appearance_manager):
        """
        Args:
            appearance_manager: AppearanceManager instance for theme colors
        """
        self.appearance = appearance_manager

    def create_button(
        self,
        parent: tk.Widget,
        text: str,
        command: Callable,
        style: str = "primary",
        width: Optional[int] = None,
        height: Optional[int] = None,
    ) -> tk.Button:
        """
        Create a standardized tk.Button

        Args:
            parent: Parent widget
            text: Button text
            command: Click callback
            style: Style name from STYLES dict ("primary", "secondary", etc.)
            width: Button width (character-based)
            height: Button height (character-based)

        Returns:
            Configured tk.Button widget
        """
        # Get style configuration
        style_config = STYLES.get(style, STYLES["primary"])

        # Get theme colors
        accent = self.appearance.get_accent_color()
        bg_color = style_config.bg or self.appearance.bg_color

        button = tk.Button(
            parent,
            text=text,
            command=command,
            font=style_config.font,
            fg=style_config.fg,
            bg=bg_color,
            activebackground=style_config.hover_bg,
            activeforeground=self.appearance.get_theme_color("accent_light", "#4cfefe"),
            relief=style_config.relief,
            bd=style_config.bd,
            highlightthickness=1,
            highlightbackground=style_config.fg,
            highlightcolor=style_config.fg,
            cursor=style_config.cursor,
        )

        if width is not None:
            button.config(width=width)
        if height is not None:
            button.config(height=height)

        # Add hover effects
        self._add_hover_effects(button, style_config)

        return button

    def create_icon_button(
        self,
        parent: tk.Widget,
        image: tk.PhotoImage,
        command: Callable,
        bg_color: Optional[str] = None,
    ) -> tk.Button:
        """
        Create an icon-based button

        Args:
            parent: Parent widget
            image: PhotoImage for the icon
            command: Click callback
            bg_color: Background color (defaults to theme bg)

        Returns:
            Configured tk.Button with icon
        """
        if bg_color is None:
            bg_color = self.appearance.bg_color

        button = tk.Button(
            parent,
            image=image,
            command=command,
            bg=bg_color,
            activebackground=bg_color,
            bd=0,
            highlightthickness=0,
            relief="flat",
            cursor="hand2",
        )

        # Add hover effect for icon buttons
        accent = self.appearance.get_accent_color()

        def on_enter(e):
            button.config(bg=accent)

        def on_leave(e):
            button.config(bg=bg_color)

        button.bind("<Enter>", on_enter)
        button.bind("<Leave>", on_leave)

        return button

    def _add_hover_effects(self, button: tk.Button, style: ButtonStyle):
        """
        Add hover effects to button

        Args:
            button: Button widget
            style: ButtonStyle configuration
        """
        # Get glow color for cyberpunk effect
        glow = self.appearance.get_theme_color("accent_light", "#4cfefe")
        normal_fg = style.fg
        normal_border = style.fg
        normal_bg = button.cget("bg")
        hover_bg = style.hover_bg

        def on_enter(e):
            button.config(
                bg=hover_bg,
                highlightbackground=glow,
                fg=glow
            )

        def on_leave(e):
            button.config(
                bg=normal_bg,
                highlightbackground=normal_border,
                fg=normal_fg
            )

        button.bind("<Enter>", on_enter)
        button.bind("<Leave>", on_leave)
