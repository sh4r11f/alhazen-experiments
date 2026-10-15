"""The PsychoPy drawing classes in a real window (marked `display`, skipped by default).

    xvfb-run -a uv run --extra psychopy pytest -m display     # or on a machine with a screen

Draws an L (ink along its bottom), checks it is upright and its capitals sit between
the cap-top and baseline lines around the stream's location, and that the field, letter
and surround colours are the luminance fractions the task asks for. Read back from the
back buffer before the flip (a window's front buffer reads back black under Xvfb).
"""

from __future__ import annotations

import numpy as np
import pytest

from raymond1992 import design
from raymond1992.glyphs import glyph
from raymond1992.stimuli import make_letter, make_rect

pytestmark = pytest.mark.display


def test_letters_and_field_render_upright_at_the_right_level():
    visual = pytest.importorskip("psychopy.visual")
    win = visual.Window(size=(400, 300), units="pix", color=(0, 0, 0), fullscr=False,
                        checkTiming=False)

    class Display:
        kind = "psychopy"
        window = win

    try:
        cap = 60.0
        surround = make_rect(Display, "surround", 600, 450, -1.0)
        field = make_rect(Display, "field", 300, 200, design.to_rgb(9.1, 32.9))
        letter = make_letter(Display, glyph("L", cap), design.to_rgb(32.9, 32.9))
        for s in (surround, field, letter):
            s.draw()
        frame = np.asarray(win.getMovieFrame(buffer="back"), dtype=float)[..., 0]
        win.flip()
    finally:
        win.close()
    h, w = frame.shape
    assert frame[5, 5] < 5  # black surround
    assert frame[h // 2 + 80, w // 2 + 120] == pytest.approx(255 * 9.1 / 32.9, abs=3)
    ink = frame > 200  # the white letter only
    rows = np.where(ink.any(axis=1))[0]
    assert abs((rows.max() - rows.min() + 1) - cap) <= 2  # capitals are cap px high
    assert abs((rows.max() + rows.min()) / 2 - (h - 1) / 2) <= 1.5  # centred on the location
    top, bottom = ink[rows.min()].sum(), ink[rows.max()].sum()
    assert bottom > 2 * top  # an L: the bar is at the bottom, so the image is not flipped
