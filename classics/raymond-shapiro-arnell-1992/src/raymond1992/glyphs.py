"""Block-style upper-case letters, rendered once from a font file into alpha masks.

The paper's letters were "simple, block-style upper case letters" 0.82° high and
"approximately the same width" (pp. 851-852); the typeface is not named. We use DejaVu
Sans Bold (ASSUMED), the bold sans-serif that ships inside matplotlib (a dependency),
so every machine draws the identical glyphs and the preview shows exactly what a
session shows.

A glyph is scaled so that the capital letters' height (the ink height of "H") is the
requested number of pixels. All letters share one vertical frame, from the cap top to
the lowest descender in the alphabet, so they sit on a common baseline; each is cropped
to its own ink horizontally.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

FONT_NAME = "DejaVu Sans Bold"
_RENDER_PX = 400  # font size of the master rendering, before downscaling


def font_path() -> Path:
    """DejaVuSans-Bold.ttf from matplotlib's bundled fonts."""
    import matplotlib

    path = Path(matplotlib.get_data_path()) / "fonts" / "ttf" / "DejaVuSans-Bold.ttf"
    if not path.is_file():
        raise FileNotFoundError(f"matplotlib's DejaVu Sans Bold is missing: {path}")
    return path


@dataclass(frozen=True)
class Glyph:
    """An alpha mask (rows top to bottom, 0..1) and where its cap box sits.

    ``cap_center_y`` is the row (from the top, fractional) of the middle of the cap
    height, which is what is placed at the stream's location."""

    letter: str
    alpha: np.ndarray
    cap_center_y: float

    @property
    def height_px(self) -> int:
        return int(self.alpha.shape[0])

    @property
    def width_px(self) -> int:
        return int(self.alpha.shape[1])


@lru_cache(maxsize=1)
def _master() -> tuple[ImageFont.FreeTypeFont, int, int, int]:
    font = ImageFont.truetype(str(font_path()), _RENDER_PX)
    cap_top, cap_bottom = font.getbbox("H")[1], font.getbbox("H")[3]
    lowest = max(font.getbbox(c)[3] for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    return font, cap_top, cap_bottom, lowest


def cap_height_ratio() -> float:
    """Cap height as a fraction of the font size (for reference in the docs)."""
    _, top, bottom, _ = _master()
    return (bottom - top) / _RENDER_PX


@lru_cache(maxsize=256)
def glyph(letter: str, cap_height_px: float) -> Glyph:
    """``letter`` with its capitals ``cap_height_px`` high, antialiased."""
    if len(letter) != 1 or not letter.isupper():
        raise ValueError(f"one upper-case letter, got {letter!r}")
    if cap_height_px <= 0:
        raise ValueError("cap_height_px must be > 0")
    font, cap_top, cap_bottom, lowest = _master()
    left, _, right, _ = font.getbbox(letter)
    width = right - left
    height = lowest - cap_top
    canvas = Image.new("L", (width + 4, height + 4), 0)
    ImageDraw.Draw(canvas).text((2 - left, 2 - cap_top), letter, fill=255, font=font)
    scale = cap_height_px / (cap_bottom - cap_top)
    out_w = max(1, round(canvas.width * scale))
    out_h = max(1, round(canvas.height * scale))
    small = canvas.resize((out_w, out_h), Image.Resampling.LANCZOS)
    alpha = np.asarray(small, dtype=float) / 255.0
    cap_center = (2 + (cap_bottom - cap_top) / 2) * scale
    return Glyph(letter, alpha, cap_center)


def ink_width_px(letter: str, cap_height_px: float) -> float:
    """The letter's ink width at this cap height (the paper: about its height)."""
    font, cap_top, cap_bottom, _ = _master()
    left, _, right, _ = font.getbbox(letter)
    return (right - left) * cap_height_px / (cap_bottom - cap_top)
