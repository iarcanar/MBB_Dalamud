"""
UI Configuration - Centralized button and widget configurations
สำหรับ MBB.py redesign
"""
from dataclasses import dataclass
from typing import Tuple


@dataclass
class ButtonStyle:
    """Standard button style configuration"""
    fg: str
    bg: str
    hover_bg: str
    font: Tuple[str, int, str]
    relief: str = "solid"
    bd: int = 1
    cursor: str = "hand2"


# Predefined styles
STYLES = {
    "primary": ButtonStyle(
        fg="#00FFFF",  # Cyan
        bg="#0a0a0f",
        hover_bg="#1a1a2e",
        font=("Nasalization Rg", 11, "bold"),
    ),
    "secondary": ButtonStyle(
        fg="#FF00FF",  # Magenta
        bg="#0a0a0f",
        hover_bg="#1a1a2e",
        font=("Nasalization Rg", 9, "bold"),
    ),
    "toggle": ButtonStyle(
        fg="#00FFFF",
        bg="#0a0a0f",
        hover_bg="#33FFFF",
        font=("Nasalization Rg", 9, "normal"),
    ),
    "utility": ButtonStyle(
        fg="#ffffff",
        bg="#2c2c2c",
        hover_bg="#00FFFF",
        font=("Nasalization Rg", 10, "normal"),
    ),
    "area": ButtonStyle(
        fg="#ffffff",
        bg="#1a1a2e",
        hover_bg="#00FFFF",
        font=("Nasalization Rg", 10, "normal"),
    ),
}

# Button configurations for all 13 UI elements
BUTTON_CONFIGS = {
    "btn_start_stop": {
        "text": "START",
        "style": "primary",
        "width": 24,  # Character-based
        "height": 2,
        "tooltip": "Start/Stop translation",
    },
    "btn_swap": {
        "text": "FFXIV",
        "style": "secondary",
        "width": 22,
        "height": 1,
        "tooltip": "Switch NPC database",
    },
    "btn_tui": {
        "text": "TUI",
        "style": "toggle",
        "tooltip": "Translation output (F9)",
    },
    "btn_log": {
        "text": "LOG",
        "style": "toggle",
        "tooltip": "Translation history",
    },
    "btn_mini": {
        "text": "MINI",
        "style": "toggle",
        "tooltip": "Switch to mini UI",
    },
    "btn_npc_manager": {
        "text": "NPC Manager",
        "style": "utility",
        "width": 12,
        "height": 1,
        "tooltip": "Manage character data",
    },
    "btn_area_a": {
        "text": "Select Area-A",
        "style": "area",
        "width": 24,
        "tooltip": "Select translation area A",
    },
    "btn_area_b": {
        "text": "Select-B",
        "style": "area",
        "width": 11,
        "tooltip": "Select translation area B",
    },
    "btn_area_c": {
        "text": "Select-C",
        "style": "area",
        "width": 11,
        "tooltip": "Select translation area C",
    },
}
