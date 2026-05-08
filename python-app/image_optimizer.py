"""
Image Optimizer — convert raw images into small + sharp avatars suitable for
the NPC Manager character profile pictures.

Pipeline:
  1. Open via PIL (supports PNG, JPG, WebP, BMP, etc.)
  2. Convert to RGBA (preserves any transparency)
  3. Center-crop to a square
  4. Resize with LANCZOS (sharp downscale)
  5. Save as WebP (lossy quality=88, alpha preserved) — ~30% the size of PNG
     at visually-identical quality. The Polaroid view displays at ~480px so
     512px source has just-enough headroom for HiDPI without storage bloat.

Typical output: 512×512 WebP, alpha preserved, ~30-80 KB (vs ~200-500KB PNG).

CLI usage:
  python image_optimizer.py <input> <output> [--size 512]

Library usage:
  from image_optimizer import optimize_avatar
  ok = optimize_avatar('raw.png', 'out.webp', size=512)
"""
from __future__ import annotations

import argparse
import logging
import os
import re
from typing import Optional, Tuple

from PIL import Image

log = logging.getLogger("image-optimizer")


# Default avatar size — 512px supports the Polaroid view (~480px on screen)
# with mild headroom for HiDPI. WebP at quality=88 keeps files ~30-80KB.
DEFAULT_SIZE = 512
DEFAULT_QUALITY = 88  # WebP lossy quality (0-100). 88 is visually lossless for portraits.
SUPPORTED_IN = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tiff")


def _center_crop_square(img: Image.Image) -> Image.Image:
    """Crop image to a square from the center."""
    w, h = img.size
    if w == h:
        return img
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    return img.crop((left, top, left + side, top + side))


def optimize_avatar(
    src_path: str,
    dst_path: str,
    size: int = DEFAULT_SIZE,
    *,
    keep_transparency: bool = True,
) -> bool:
    """Convert and optimize a raw image into a small square avatar PNG.

    Args:
        src_path: Path to input image (PNG/JPG/WebP/etc).
        dst_path: Path to output PNG (will be created/overwritten).
        size: Final square dimension in pixels (default 128).
        keep_transparency: If True, preserve alpha channel.

    Returns:
        True on success, False on failure (errors logged).
    """
    if not os.path.exists(src_path):
        log.error(f"Source image not found: {src_path}")
        return False

    try:
        img = Image.open(src_path)
        # Force load (some formats are lazy)
        img.load()
    except Exception as e:
        log.error(f"Failed to open image {src_path}: {e}")
        return False

    try:
        # Convert mode
        if keep_transparency:
            if img.mode != "RGBA":
                img = img.convert("RGBA")
        else:
            if img.mode != "RGB":
                img = img.convert("RGB")

        # Center-crop to square
        img = _center_crop_square(img)

        # Resize with LANCZOS (high-quality downscale)
        if img.size[0] != size:
            img = img.resize((size, size), Image.Resampling.LANCZOS)

        # Ensure output dir exists
        out_dir = os.path.dirname(dst_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)

        # Save format chosen by destination extension (so callers can override).
        # Default is WebP — much smaller than PNG at indistinguishable quality.
        ext = os.path.splitext(dst_path)[1].lower().lstrip(".")
        if ext == "webp":
            img.save(dst_path, format="WEBP", quality=DEFAULT_QUALITY, method=6)
        elif ext in ("jpg", "jpeg"):
            # JPEG can't hold alpha — flatten over white if needed
            if img.mode == "RGBA":
                bg = Image.new("RGB", img.size, (255, 255, 255))
                bg.paste(img, mask=img.split()[3])
                img = bg
            img.save(dst_path, format="JPEG", quality=DEFAULT_QUALITY, optimize=True)
        else:
            # Fallback PNG (legacy behavior — keeps existing call sites working)
            save_kwargs = {"optimize": True}
            if keep_transparency:
                save_kwargs["compress_level"] = 9
            img.save(dst_path, format="PNG", **save_kwargs)

        in_kb = os.path.getsize(src_path) / 1024
        out_kb = os.path.getsize(dst_path) / 1024
        log.info(f"Optimized {os.path.basename(src_path)}: "
                 f"{in_kb:.1f}KB → {out_kb:.1f}KB ({size}×{size}, .{ext or 'png'})")
        return True
    except Exception as e:
        log.error(f"Optimization failed for {src_path}: {e}")
        return False


def safe_filename(name: str, ext: str = ".webp") -> str:
    """Convert a character name into a filesystem-safe filename.

    Examples:
        "Y'shtola" → "y_shtola.webp"
        "G'raha Tia" → "g_raha_tia.webp"
        "Wuk Lamat" → "wuk_lamat.webp"
    """
    # Lowercase, replace non-alphanumeric with underscore, collapse runs
    base = re.sub(r"[^a-zA-Z0-9]+", "_", name.lower()).strip("_")
    if not base:
        base = "character"
    return base + ext


def is_supported_input(path: str) -> bool:
    """Check if file extension is supported as input."""
    return path.lower().endswith(SUPPORTED_IN)


# ─── CLI ───
def _cli():
    parser = argparse.ArgumentParser(description="Optimize image for NPC avatar")
    parser.add_argument("input", help="Input image path")
    parser.add_argument("output", help="Output PNG path")
    parser.add_argument("--size", type=int, default=DEFAULT_SIZE,
                        help=f"Output square size in px (default {DEFAULT_SIZE})")
    parser.add_argument("--no-transparency", action="store_true",
                        help="Discard alpha channel (smaller files for opaque images)")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s"
    )

    ok = optimize_avatar(
        args.input, args.output,
        size=args.size,
        keep_transparency=not args.no_transparency,
    )
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    _cli()
