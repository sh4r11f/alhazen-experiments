"""The real PsychoPy stimuli, drawn into a real window (marked `display`).

Skipped by the default run (pyproject addopts: -m 'not display'). On a machine
with a screen, or under Xvfb:

    uv sync --locked --extra psychopy
    xvfb-run -a uv run pytest -m display -q

It reads the back buffer before the flip: under Xvfb the front buffer reads
back black.
"""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest
from alhazen.display.screen import Screen
from conftest import params_with

from stroop1935.stimuli import apply_background, make_patch, make_word

pytestmark = pytest.mark.display
SCREEN = Screen(width_px=800, height_px=600, px_per_deg=40.0)


@pytest.fixture
def window():
    # Imported here, not skipped: asking for the display tests on a machine
    # without the psychopy extra is a setup error and should say so.
    from psychopy import visual
    win = visual.Window(size=(800, 600), units="pix", color=(0, 0, 0), fullscr=False,
                        allowGUI=False, checkTiming=False)
    yield win
    win.close()


def frame(win) -> np.ndarray:
    return np.asarray(win.getMovieFrame(buffer="back"))


def test_the_page_is_the_params_background_and_the_square_its_ink(window):
    p = params_with()
    display = SimpleNamespace(kind="psychopy", window=window)
    apply_background(display, p.background_rgb)
    window.flip()  # the new clear colour takes effect on the next frame
    make_patch(display, SCREEN, p.colors["green"], p.patch_size_dva).draw()
    img = frame(window)
    corner, centre = img[10, 10], img[300, 400]
    assert np.allclose(corner, 0.9 * 255, atol=3)  # rgb 0.8 -> 229.5
    assert np.allclose(centre, (0, 127.5, 0), atol=3)
    side = int(np.sum(np.all(np.abs(img[300].astype(int) - (0, 128, 0)) <= 3, axis=1)))
    assert abs(side - p.patch_size_dva * 40) <= 2


def test_a_word_is_drawn_in_its_ink(window):
    p = params_with()
    display = SimpleNamespace(kind="psychopy", window=window)
    apply_background(display, p.background_rgb)
    window.flip()
    make_word(display, SCREEN, "purple", p.colors["red"], p.letter_height_dva, p.font).draw()
    img = frame(window).astype(int)
    red = np.all(np.abs(img - (255, 0, 0)) <= 40, axis=2)
    ys, xs = np.nonzero(red)
    assert red.sum() > 50
    assert abs(xs.mean() - 400) < 20 and abs(ys.mean() - 300) < 20
    assert ys.max() - ys.min() <= p.letter_height_dva * 40 * 1.5


def test_the_demo_views_draw_real_stimuli(window):
    from alhazen.modes.demo import DemoSetup

    from stroop1935.task import StroopColorNamingTask

    task = StroopColorNamingTask(params_with(block_order="A"))
    setup = DemoSetup(display=SimpleNamespace(kind="psychopy", window=window), screen=SCREEN,
                      params=task.params, rng=np.random.default_rng(0))
    views = task.demo_views(setup)
    assert len(views) == 6 and views[0].key == "1" and views[3].key == "2"
    for view in views:
        view.draw(0.0)
    assert tuple(window.color) == tuple(task.params.background_rgb)
