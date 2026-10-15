"""docs/preview.png is drawn from the real parameters and is small enough to ship."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from raymond1992.glyphs import glyph, ink_width_px
from raymond1992.preview import render

PROJECT = Path(__file__).resolve().parents[1]


def test_the_preview_renders(tmp_path):
    out = render(tmp_path / "preview.png")
    with Image.open(out) as img:
        assert img.width > 800
    assert out.stat().st_size < 400_000


def test_the_shipped_preview_is_small():
    assert (PROJECT / "docs" / "preview.png").stat().st_size < 400_000


def test_letters_are_cap_height_high_and_about_as_wide():
    cap = 100.0
    g = glyph("H", cap)
    rows = (g.alpha > 0.5).any(axis=1).sum()
    assert abs(rows - cap) <= 2
    widths = [ink_width_px(c, cap) / cap for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"]
    assert 0.9 < sum(widths) / len(widths) < 1.2
