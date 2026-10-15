"""Draw the stimulus preview, docs/preview.png: what the search displays look like.

    uv run python -m treisman_gelade1980.preview            # writes docs/preview.png

Four displays, one per parameter set, each with the largest display size and a target:
Experiment I conjunction (a green T among brown Ts and green Xs) and feature (here a blue
letter), Experiment II easy (a red O among green Os and red Ns) and difficult (a green T
among blue Ts and green Xs, similar inks). Rendered by the same code the session draws
with (glyphs.render_canvas), from the shipped params files and the example booth rig's
geometry, so the preview is the stimulus. No window needed.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from alhazen.config.loader import load_params, load_rig
from alhazen.display.screen import Screen
from PIL import Image, ImageDraw, ImageFont

from treisman_gelade1980 import design, glyphs
from treisman_gelade1980.task import PROJECT, FeatureConjunctionSearchTaskParams

PANELS = [
    ("task.yaml", "Exp. I conjunction: find a green T"),
    ("task-exp1-feature.yaml", "Exp. I feature: find a blue letter or an S"),
    ("task-exp2-easy.yaml", "Exp. II easy: find a red O"),
    ("task-exp2-difficult.yaml", "Exp. II difficult: find a green T"),
]
CROP_DVA = (15.0, 10.6)  # width, height of each panel, deg


def panel(name: str, screen: Screen, seed: int = 11) -> Image.Image:
    p = load_params(PROJECT / "configs" / name, FeatureConjunctionSearchTaskParams)
    deck = design.build_deck(p, np.random.default_rng(seed))
    n = max(p.display_sizes)
    cond = next(c for c in deck if c["display_size"] == n and c["target_present"])
    card = design.build_card(p, cond)
    canvas = glyphs.render_canvas(card.items, width_px=screen.width_px,
                                  height_px=screen.height_px, px_per_deg=screen.px_per_deg, p=p)
    w, h = (screen.deg2px(d) for d in CROP_DVA)
    cx, cy = screen.width_px / 2, screen.height_px / 2
    return canvas.crop((round(cx - w / 2), round(cy - h / 2), round(cx + w / 2), round(cy + h / 2)))


def render(out: Path) -> Path:
    screen = Screen.from_monitor(load_rig(PROJECT / "configs" / "rig-booth.yaml").monitor)
    tiles = [(panel(name, screen), title) for name, title in PANELS]
    tw, th = tiles[0][0].size
    gap, title_h = 12, 34
    sheet = Image.new("RGB", (2 * tw + 3 * gap, 2 * (th + title_h) + 3 * gap), (228, 228, 231))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default(size=20)
    for i, (tile, title) in enumerate(tiles):
        x = gap + (i % 2) * (tw + gap)
        y = gap + (i // 2) * (th + title_h + gap)
        draw.text((x + 4, y + 6), title, fill=(39, 39, 42), font=font)
        sheet.paste(tile, (x, y + title_h))
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, optimize=True)
    return out


if __name__ == "__main__":
    print(render(Path(sys.argv[1]) if len(sys.argv) > 1 else PROJECT / "docs" / "preview.png"))
