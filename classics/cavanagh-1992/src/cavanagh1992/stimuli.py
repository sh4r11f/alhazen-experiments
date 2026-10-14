"""Drawing a ``Scene``: the psychopy stimulus, and the stand-in a simulated session uses.

alhazen's house pattern (its ``stimuli/fixation.py``): degrees in, pixels computed once,
psychopy imported lazily inside the class so this module imports on a machine with no
renderer, and a factory that gives a simulated backend a stand-in. The stand-in is not a
bare NullStimulus: it owns the same ``Scene`` and advances the same clock, because where
the bars are, and so which pair a pointer aims at, is state the trial logic and the
tests depend on.

The real stimulus draws a full-screen rectangle at the mean yellow (the field), then the
scene's pixels (``SceneRaster``) as one image, refreshed every frame.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from alhazen.display.backend import DisplayBackend
from alhazen.display.screen import Screen

from cavanagh1992.color import to_psychopy
from cavanagh1992.scene import Scene, SceneRaster


class SimulatedScene:
    """The scene without a window: advances, counts draws, never renders."""

    def __init__(self, scene: Scene) -> None:
        self.scene = scene
        self.draw_count = 0

    def update(self, dt: float) -> None:
        self.scene.update(dt)

    def draw(self) -> None:
        self.draw_count += 1


class SceneStimulus:
    """The scene on a psychopy window."""

    def __init__(self, display: DisplayBackend, screen: Screen, scene: Scene) -> None:
        from psychopy import visual

        self.scene = scene
        self.draw_count = 0
        # psychopy reads a numpy image bottom row first.
        self._raster = SceneRaster(scene, screen.px_per_deg, bottom_up=True)
        n = self._raster.size_px
        mean = tuple(float(v) for v in to_psychopy(np.array(scene.color.mean_rgb())))
        self._field: Any = visual.Rect(
            display.window, width=screen.width_px * 1.1, height=screen.height_px * 1.1,
            units="pix", fillColor=mean, lineColor=mean, colorSpace="rgb")
        self._image: Any = visual.ImageStim(
            display.window, image=to_psychopy(self._raster.render()), size=(n, n),
            units="pix", colorSpace="rgb", interpolate=False)

    def update(self, dt: float) -> None:
        self.scene.update(dt)

    def draw(self) -> None:
        self.draw_count += 1
        self._image.image = to_psychopy(self._raster.render())
        self._field.draw()
        self._image.draw()


def make_scene_stimulus(display: DisplayBackend, screen: Screen, scene: Scene) -> Any:
    if display.kind == "simulated":
        return SimulatedScene(scene)
    return SceneStimulus(display, screen, scene)
