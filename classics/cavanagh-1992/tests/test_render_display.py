"""The psychopy stimulus draws what the raster says, on a real (or Xvfb) window.

Marked ``display``: skipped by the default run (pyproject addopts). Run it on a machine
with a screen, or headless with `xvfb-run -a uv run --extra psychopy pytest -m display`.
It checks the two psychopy conventions the stimulus relies on (a float image is 0..1 and
its first row is drawn at the bottom), where the pointer is, the colour of a red and a green
bar, and that direction +1 turns counterclockwise on the screen.
"""

from __future__ import annotations

import numpy as np
import pytest

pytestmark = pytest.mark.display


@pytest.fixture
def window():
    visual = pytest.importorskip("psychopy.visual")
    win = visual.Window(size=(800, 600), units="pix", fullscr=False, color=(0, 0, 0),
                        colorSpace="rgb", allowGUI=False)
    yield win
    win.close()


def test_the_window_shows_the_rasters_pointer_bars_and_direction(window):
    from alhazen.display.screen import Screen

    from cavanagh1992.color import ColorModel
    from cavanagh1992.scene import Component, Pointer, PointerGeometry, Ring, Scene
    from cavanagh1992.stimuli import SceneStimulus

    class Display:
        kind = "psychopy"
        win = window

    Display.window = window
    model = ColorModel(45.0, 0.3173, 53.0, 179.0, 1.0)
    scene = Scene([Ring(4.0, 8.4, [Component("color", 0.4, 8, 2.0, 1, 0.0)])], model, 1.0, 4,
                  PointerGeometry(1.3, 3.9, 0.08, 0.35), pointer=Pointer(0, 0, 1, 1))
    stim = SceneStimulus(Display, Screen(width_px=800, height_px=600, px_per_deg=30.0), scene)

    def frame():
        stim.draw()
        img = np.asarray(window.getMovieFrame(buffer="back")).astype(float) / 255.0
        window.clearBuffer()
        return img

    def at(img, deg, r):
        cy, cx = img.shape[0] // 2, img.shape[1] // 2
        a = np.deg2rad(deg)
        return img[int(round(cy - r * 30 * np.sin(a))), int(round(cx + r * 30 * np.cos(a)))]

    img = frame()
    mean = np.array(model.mean_rgb())
    assert np.allclose(at(img, 45, 2.6), 0, atol=0.01)        # pointer up-right
    assert np.allclose(at(img, 225, 2.6), 0, atol=0.01)       # and its partner
    assert np.allclose(at(img, 135, 2.6), mean, atol=0.01)
    red, green = model.luminances(0.0, 0.4)
    assert at(img, 0, 6)[:2] == pytest.approx([red / 53.0, green / 179.0], abs=0.01)
    scene.update(1 / 16)                                      # +1: counterclockwise
    img = frame()
    assert at(img, 5.6, 6)[0] > at(img, -5.6, 6)[0] + 0.05
