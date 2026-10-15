"""The rendered pixels: letters the paper's size, in their inks, where the card says."""

from __future__ import annotations

import numpy as np
import pytest
from support import SCREEN, params

from treisman_gelade1980 import design, glyphs

GEOM = dict(width_px=SCREEN.width_px, height_px=SCREEN.height_px, px_per_deg=SCREEN.px_per_deg)


def ink_mask(img, rgb, tol=40):
    a = np.asarray(img).astype(int)
    return (np.abs(a - np.array(rgb)).sum(axis=2) < tol)


@pytest.mark.parametrize("letter", sorted(glyphs.LETTERS))
def test_each_letter_fills_its_box(letter):
    p = params()
    item = design.Item(f"{letter}_green", 0.0, 0.0)
    img = glyphs.render_canvas([item], p=p, **GEOM)
    ys, xs = np.nonzero(ink_mask(img, p.inks["green"], tol=200))
    height = (ys.max() - ys.min() + 1) / SCREEN.px_per_deg
    width = (xs.max() - xs.min() + 1) / SCREEN.px_per_deg
    assert height == pytest.approx(p.letter_height_dva, abs=0.06)  # paper p. 103: 0.8 deg
    assert width == pytest.approx(p.letter_width_dva, abs=0.06)  # 0.6 deg


def test_the_target_is_drawn_in_its_ink_at_its_place():
    p = params()
    task_deck = design.build_deck(p, np.random.default_rng(4))
    cond = next(c for c in task_deck if c["display_size"] == 30 and c["target_present"])
    card = design.build_card(p, cond)
    img = glyphs.render_canvas(card.items, p=p, **GEOM)
    t = card.target
    cx = SCREEN.width_px / 2 + t.x * SCREEN.px_per_deg
    cy = SCREEN.height_px / 2 - t.y * SCREEN.px_per_deg
    r = SCREEN.px_per_deg * 0.45
    window = img.crop((round(cx - r), round(cy - r), round(cx + r), round(cy + r)))
    assert ink_mask(window, p.inks["green"]).sum() > 20
    # Green also appears on the green Xs; brown never at the target's place.
    assert ink_mask(window, p.inks["brown"]).sum() == 0


def test_the_patch_and_the_full_canvas_agree():
    p = params("task-exp2-easy.yaml")
    cond = design.build_deck(p, np.random.default_rng(0))[5]
    items = design.build_card(p, cond).items
    canvas = glyphs.render_canvas(items, p=p, **GEOM)
    patch, (cx, cy) = glyphs.render_patch(items, p=p, **GEOM)
    left = round(SCREEN.width_px / 2 + cx - patch.width / 2)
    top = round(SCREEN.height_px / 2 - cy - patch.height / 2)
    crop = canvas.crop((left, top, left + patch.width, top + patch.height))
    assert np.array_equal(np.asarray(crop), np.asarray(patch))


def test_the_field_is_white_and_the_fixation_spot_is_central():
    p = params()
    img = np.asarray(glyphs.render_canvas([], p=p, fixation=True, **GEOM))
    assert tuple(img[0, 0]) == (255, 255, 255)
    assert tuple(img[SCREEN.height_px // 2, SCREEN.width_px // 2]) == (0, 0, 0)


def test_an_unknown_letter_is_refused():
    from PIL import Image

    with pytest.raises(ValueError):
        glyphs.draw_letter(Image.new("RGB", (10, 10)), "Q", 5, 5, 4, 6, 1, (0, 0, 0))
