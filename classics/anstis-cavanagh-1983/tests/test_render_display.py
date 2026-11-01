"""The psychopy stimulus draws what the arrays say, on a real (or Xvfb) window.

Marked ``display``: skipped by the default run (pyproject addopts). Run it on a machine
with a screen, or headless with `xvfb-run -a uv run --extra psychopy pytest -m display`.
Not yet run: no machine with psychopy was used for this folder (docs/methods.md,
Verification). It checks that a red and a green bar of T1 come out at their linear levels
and that T2 follows three frames later at 5 Hz.
"""

from __future__ import annotations

import numpy as np
import pytest

pytestmark = pytest.mark.display


@pytest.fixture
def window():
    visual = pytest.importorskip("psychopy.visual")
    win = visual.Window(size=(800, 600), units="pix", fullscr=False, color=(-1, -1, -1),
                        colorSpace="rgb", allowGUI=False)
    yield win
    win.close()


def test_the_window_shows_t1_then_t2(window):
    from alhazen.display.screen import Screen

    from anstiscavanagh1983.color import ColourSpace, Photometry
    from anstiscavanagh1983.render import PsychopyCycle
    from anstiscavanagh1983.stimulus import Fixation, Spec

    class Display:
        kind = "psychopy"

    Display.window = window
    space = ColourSpace(Photometry(red_max_cd_m2=60.0, green_max_cd_m2=200.0, blue_max_cd_m2=20.0))
    spec = Spec("four_stroke", "red", "green", 30.0, 100.0, 80, 16, 1, 0)
    stim = PsychopyCycle(Display, Screen(width_px=800, height_px=600, px_per_deg=40.0), spec,
                         space, 40.0, Fixation(), 3)

    def frame():
        stim.draw()
        img = np.asarray(window.getMovieFrame(buffer="back")).astype(float) / 255.0
        window.clearBuffer()
        return img

    img = frame()
    cy, cx = 300, 400
    left = cx - 40  # patch's first column: a red bar (offset 0)
    assert img[cy + 20, left + 2][:2] == pytest.approx([0.5, 0.0], abs=0.02)
    assert img[cy + 20, left + 10][:2] == pytest.approx([0.0, 0.5], abs=0.02)
    frame(), frame()
    t2 = frame()
    assert not np.allclose(t2[cy + 20, left + 2], img[cy + 20, left + 2])
