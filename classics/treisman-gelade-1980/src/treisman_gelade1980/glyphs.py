"""The letters, drawn: one renderer for the session, the preview and the tests.

The original letters were drawn with stencils and coloured inks on white cards (paper
p. 102); each subtended 0.8 x 0.6 deg (p. 103). Here each letter is a set of strokes in a
box ``letter_height_dva`` high and ``letter_width_dva`` wide, drawn with PIL at three times
the screen's resolution and reduced (anti-aliasing), so what the session shows, what
docs/preview.png shows and what the tests measure are the same pixels.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from typing import Any

from PIL import Image, ImageDraw

SUPERSAMPLE = 3

Point = tuple[float, float]


def _arc(cx: float, cy: float, rx: float, ry: float, start_deg: float, stop_deg: float,
         n: int = 24) -> list[Point]:
    """Points along an ellipse arc in a y-down unit box, angles counter-clockwise."""
    out = []
    for i in range(n + 1):
        t = math.radians(start_deg + (stop_deg - start_deg) * i / n)
        out.append((cx + rx * math.cos(t), cy - ry * math.sin(t)))
    return out


def _s_spine() -> list[Point]:
    upper = _arc(0.5, 0.25, 0.5, 0.25, 25, 270)
    lower = _arc(0.5, 0.75, 0.5, 0.25, 90, -155)
    return upper + lower[1:]


# Stroke centre lines in a unit box (x right, y down, 0..1). "O" is an ellipse.
STROKES: dict[str, list[list[Point]]] = {
    "T": [[(0.0, 0.0), (1.0, 0.0)], [(0.5, 0.0), (0.5, 1.0)]],
    "X": [[(0.0, 0.0), (1.0, 1.0)], [(1.0, 0.0), (0.0, 1.0)]],
    "N": [[(0.0, 1.0), (0.0, 0.0), (1.0, 1.0), (1.0, 0.0)]],
    "S": [_s_spine()],
    "O": [],
}
LETTERS = frozenset(STROKES)


def _extend(points: list[Point], by: float) -> list[Point]:
    """Square caps: push each open end out along its own direction by ``by``."""
    if len(points) < 2 or by <= 0:
        return points
    pts = list(points)
    for end, nxt in ((0, 1), (-1, -2)):
        (x0, y0), (x1, y1) = pts[end], pts[nxt]
        d = math.hypot(x0 - x1, y0 - y1) or 1.0
        pts[end] = (x0 + (x0 - x1) / d * by, y0 + (y0 - y1) / d * by)
    return pts


def draw_letter(img: Image.Image, letter: str, cx: float, cy: float, w: float, h: float,
                stroke: float, fill: Sequence[int]) -> None:
    """One letter centred on (cx, cy) px (y down) in ``img``: ``w`` x ``h`` px outside,
    strokes ``stroke`` px wide. Strokes are drawn with square caps into a mask the size of
    the letter's box and clipped to it, so every letter's ink fills exactly its box."""
    if letter not in STROKES:
        raise ValueError(f"no strokes for letter {letter!r}; known: {sorted(STROKES)}")
    color = tuple(int(c) for c in fill)
    width = max(1, round(stroke))
    left, top = round(cx - w / 2), round(cy - h / 2)
    bw, bh = max(1, round(w)), max(1, round(h))
    mask = Image.new("L", (bw, bh), 0)
    draw = ImageDraw.Draw(mask)
    if letter == "O":
        draw.ellipse([0, 0, bw - 1, bh - 1], outline=255, width=width)
    else:
        inner_w, inner_h = max(bw - stroke, 1.0), max(bh - stroke, 1.0)
        x0, y0 = (bw - inner_w) / 2, (bh - inner_h) / 2
        for line in STROKES[letter]:
            pts = [(x0 + u * inner_w, y0 + v * inner_h) for u, v in line]
            if letter != "S":
                pts = _extend(pts, stroke)
            draw.line(pts, fill=255, width=width, joint="curve")
    img.paste(Image.new("RGB", (bw, bh), color), (left, top), mask)


def _px(x_deg: float, y_deg: float, width_px: int, height_px: int, ppd: float) -> Point:
    """Centred deg (y up) to image px (y down)."""
    return width_px / 2 + x_deg * ppd, height_px / 2 - y_deg * ppd


def render_patch(items: Iterable[Any], *, width_px: int, height_px: int, px_per_deg: float,
                 p: Any, fixation: bool = False, margin_dva: float = 0.5
                 ) -> tuple[Image.Image | None, tuple[float, float]]:
    """The smallest image holding every letter (and the fixation spot when asked), and its
    centre in centred screen px (y up) — what an ImageStim needs. None when empty."""
    items = list(items)
    boxes = []
    for it in items:
        boxes.append((it.x - p.letter_width_dva / 2, it.y - p.letter_height_dva / 2,
                      it.x + p.letter_width_dva / 2, it.y + p.letter_height_dva / 2))
    if fixation:
        r = p.fixation_size_dva / 2
        boxes.append((-r, -r, r, r))
    if not boxes:
        return None, (0.0, 0.0)
    x0 = min(b[0] for b in boxes) - margin_dva
    y0 = min(b[1] for b in boxes) - margin_dva
    x1 = max(b[2] for b in boxes) + margin_dva
    y1 = max(b[3] for b in boxes) + margin_dva
    # Whole screen pixels, so the patch lands on the pixel grid where a full-screen
    # render would put it.
    ppd = px_per_deg
    left = math.floor(width_px / 2 + x0 * ppd)
    right = math.ceil(width_px / 2 + x1 * ppd)
    top = math.floor(height_px / 2 - y1 * ppd)
    bottom = math.ceil(height_px / 2 - y0 * ppd)
    pw, ph = right - left, bottom - top
    ss = SUPERSAMPLE
    img = Image.new("RGB", (pw * ss, ph * ss), tuple(p.background_rgb))
    draw = ImageDraw.Draw(img)
    for it in items:
        cx, cy = _px(it.x, it.y, width_px, height_px, ppd)
        draw_letter(img, it.letter, (cx - left) * ss, (cy - top) * ss,
                    p.letter_width_dva * ppd * ss, p.letter_height_dva * ppd * ss,
                    p.stroke_dva * ppd * ss, p.inks[it.ink])
    if fixation:
        cx, cy = _px(0.0, 0.0, width_px, height_px, ppd)
        r = p.fixation_size_dva / 2 * ppd * ss
        cx, cy = (cx - left) * ss, (cy - top) * ss
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=tuple(p.fixation_rgb))
    img = img.reduce(ss)
    centre = (left + pw / 2 - width_px / 2, height_px / 2 - (top + ph / 2))
    return img, centre


def render_canvas(items: Iterable[Any], *, width_px: int, height_px: int, px_per_deg: float,
                  p: Any, fixation: bool = False) -> Image.Image:
    """The whole screen as the subject sees it: the white field with the patch on it."""
    canvas = Image.new("RGB", (width_px, height_px), tuple(p.background_rgb))
    patch, (cx, cy) = render_patch(items, width_px=width_px, height_px=height_px,
                                   px_per_deg=px_per_deg, p=p, fixation=fixation)
    if patch is not None:
        left = round(width_px / 2 + cx - patch.width / 2)
        top = round(height_px / 2 - cy - patch.height / 2)
        canvas.paste(patch, (left, top))
    return canvas
