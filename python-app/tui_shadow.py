"""
TUI Shadow System — extracted from translated_ui.py
=====================================================

This module contains the shadow rendering subsystem used by the TUI
(translated UI) text canvas. It was extracted from `translated_ui.py`
for size and maintainability reasons (the source file is ~9000 lines).

Contents
--------
- ``ShadowConfig``       : Centralized constants + intelligent scaling
                          (``get_scaled_params(font_size)``) for blur / spread /
                          opacity / color used by all TUI text shadows.
- ``BlurShadowEngine``   : PIL-based "blur on solid shape" shadow texture
                          generator with an LRU-ish cache and a Tkinter-canvas
                          helper (``create_shadow_on_canvas``) that wraps
                          ``ImageTk.PhotoImage`` and pins the reference on the
                          canvas to avoid garbage-collection flicker.

Notes
-----
- This is a verbatim extract — no logic changes.
- The methods on the main UI class (``Translated_UI._create_text_shadows`` and
  ``_create_text_shadows_canvas``) belong to the UI class itself and were
  intentionally left in ``translated_ui.py``. They call into ``ShadowConfig``
  / ``BlurShadowEngine`` from this module via ``self.shadow_engine``.
- Originally lived at lines 25–231 of ``translated_ui.py``.
"""

import logging
import math
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageTk


class ShadowConfig:
    """Centralized shadow configuration for TUI text rendering"""

    # *** SHADOW PARAMETERS - MODIFY HERE FOR ALL SHADOWS ***
    SHADOW_BLUR_RADIUS = 8  # From TUI_shadow_test.py - balanced combination
    SHADOW_SPREAD = 6  # From TUI_shadow_test.py - balanced combination
    SHADOW_OFFSET_X = 0  # No offset - same position as text
    SHADOW_OFFSET_Y = 0  # No offset - same position as text
    SHADOW_OPACITY = 0.8  # Shadow transparency
    SHADOW_COLOR = "#000000"  # Shadow color

    # *** INTELLIGENT SCALING ***
    BASE_FONT_SIZE = 24  # Reference font size for scaling
    SPREAD_PRESERVATION_RATIO = 0.25  # Preserve visual consistency

    @classmethod
    def get_scaled_params(cls, font_size):
        """Return shadow parameters scaled for specific font size"""
        scale_factor = font_size / cls.BASE_FONT_SIZE
        # Use square root scaling for gentler spread preservation
        spread_scale = math.sqrt(scale_factor)
        radius_scale = scale_factor * 0.8  # Slightly less aggressive radius scaling

        return {
            "blur_radius": max(2, int(cls.SHADOW_BLUR_RADIUS * radius_scale)),
            "spread": max(1, int(cls.SHADOW_SPREAD * spread_scale)),
            "offset_x": int(cls.SHADOW_OFFSET_X * spread_scale),
            "offset_y": int(cls.SHADOW_OFFSET_Y * spread_scale),
            "opacity": cls.SHADOW_OPACITY,
            "color": cls.SHADOW_COLOR,
        }


class BlurShadowEngine:
    """Advanced blur shadow system for TUI text rendering"""

    def __init__(self):
        self._shadow_cache = {}
        self.max_cache_size = 50
        self.cache_hits = 0
        self.cache_misses = 0

    def _get_cache_key(self, text, font_info, shadow_params):
        """Generate cache key for shadow texture"""
        font_str = (
            f"{font_info[0]}-{font_info[1]}"
            if isinstance(font_info, tuple)
            else str(font_info)
        )
        params_str = f"{shadow_params['blur_radius']}-{shadow_params['spread']}-{shadow_params['offset_x']}-{shadow_params['offset_y']}"
        return f"{text[:50]}-{font_str}-{params_str}"

    def _cleanup_cache(self):
        """Clean up cache when it gets too large"""
        if len(self._shadow_cache) > self.max_cache_size:
            # Remove oldest 20% of cache entries
            items_to_remove = max(1, len(self._shadow_cache) // 5)
            oldest_keys = list(self._shadow_cache.keys())[:items_to_remove]
            for key in oldest_keys:
                del self._shadow_cache[key]

    def generate_shadow_texture(self, text, font_path, font_size, shadow_params):
        """Generate blurred shadow texture using 'Blur on Solid Shape' technique"""
        try:
            # Check cache first
            cache_key = self._get_cache_key(text, (font_path, font_size), shadow_params)
            if cache_key in self._shadow_cache:
                self.cache_hits += 1
                return self._shadow_cache[cache_key]

            self.cache_misses += 1

            # Load font
            try:
                if font_path and os.path.exists(font_path):
                    font = ImageFont.truetype(font_path, font_size)
                else:
                    # Fallback to system fonts
                    fallback_fonts = [
                        "C:/Windows/Fonts/tahomabd.ttf",
                        "C:/Windows/Fonts/leelawbd.ttf",
                    ]
                    font = None
                    for fallback in fallback_fonts:
                        if os.path.exists(fallback):
                            font = ImageFont.truetype(fallback, font_size)
                            break
                    if not font:
                        font = ImageFont.load_default()
            except Exception:
                font = ImageFont.load_default()

            # Calculate image dimensions with padding for spread and blur
            padding = shadow_params["spread"] + shadow_params["blur_radius"] + 10

            # Create dummy image to measure text
            dummy_img = Image.new("RGBA", (1, 1))
            draw = ImageDraw.Draw(dummy_img)
            text_bbox = draw.textbbox(
                (0, 0), text, font=font, stroke_width=shadow_params["spread"]
            )
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]

            img_width = text_width + padding * 2
            img_height = text_height + padding * 2

            # 1. Create shadow source layer (Solid Shape)
            shadow_source = Image.new("RGBA", (img_width, img_height), (0, 0, 0, 0))
            shadow_draw = ImageDraw.Draw(shadow_source)

            # Draw both fill and stroke in shadow color to create solid shape
            # Use same position as text (no offset) following TUI_shadow_test.py
            shadow_draw.text(
                (padding - text_bbox[0], padding - text_bbox[1]),
                text,
                font=font,
                fill=shadow_params["color"],  # Fill with shadow color
                stroke_width=shadow_params["spread"],
                stroke_fill=shadow_params["color"],  # Stroke with same shadow color
            )

            # 2. Apply Gaussian blur to the solid shape
            blurred_shadow = shadow_source.filter(
                ImageFilter.GaussianBlur(radius=shadow_params["blur_radius"])
            )

            # 3. Apply additional smoothing to reduce harsh edges
            # Apply a slight blur to anti-alias edges
            blurred_shadow = blurred_shadow.filter(ImageFilter.SMOOTH)

            # 4. Apply opacity to shadow
            if shadow_params["opacity"] < 1.0:
                # Create alpha mask for opacity with smoother transition
                alpha = blurred_shadow.split()[-1]  # Get alpha channel
                alpha = alpha.point(lambda p: int(p * shadow_params["opacity"]))
                blurred_shadow.putalpha(alpha)

            # Cache the result
            self._shadow_cache[cache_key] = blurred_shadow
            self._cleanup_cache()

            return blurred_shadow

        except Exception as e:
            logging.error(f"Error generating shadow texture: {e}")
            # Return transparent image as fallback
            return Image.new("RGBA", (100, 50), (0, 0, 0, 0))

    def create_shadow_on_canvas(
        self, canvas, text, x, y, font_info, width=None, anchor="nw", tags=None
    ):
        """Create shadow directly on canvas using blur shadow technique"""
        try:
            logging.debug(
                f"Shadow creation attempt - text: '{text[:50]}...', font: {font_info}"
            )

            # Get font information
            if isinstance(font_info, tuple) and len(font_info) >= 2:
                font_name, font_size = font_info[0], font_info[1]
            else:
                font_name, font_size = "TkDefaultFont", 12

            logging.debug(f"Extracted font info - name: {font_name}, size: {font_size}")

            # Get scaled shadow parameters
            shadow_params = ShadowConfig.get_scaled_params(font_size)
            logging.debug(f"Shadow params: {shadow_params}")

            # Generate shadow texture
            shadow_texture = self.generate_shadow_texture(
                text, None, font_size, shadow_params
            )

            if shadow_texture is None:
                logging.error("Shadow texture generation returned None")
                return None

            logging.debug(f"Shadow texture size: {shadow_texture.size}")

            # Convert to PhotoImage for Tkinter
            shadow_photo = ImageTk.PhotoImage(shadow_texture)

            # Create shadow on canvas
            shadow_item = canvas.create_image(
                x, y, image=shadow_photo, anchor=anchor, tags=tags
            )

            logging.debug(f"Shadow item created on canvas: {shadow_item}")

            # Keep reference to prevent garbage collection
            if not hasattr(canvas, "_shadow_images"):
                canvas._shadow_images = []
            canvas._shadow_images.append(shadow_photo)
            # Prevent unbounded growth
            if len(canvas._shadow_images) > 50:
                canvas._shadow_images = canvas._shadow_images[-20:]

            return shadow_item

        except Exception as e:
            logging.error(f"Error creating shadow on canvas: {e}")
            import traceback

            logging.error(traceback.format_exc())
            return None
