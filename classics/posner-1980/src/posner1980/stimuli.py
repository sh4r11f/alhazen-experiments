"""The cue and the detection stimulus, drawn with PsychoPy on a real window.

Same pattern as alhazen's fixation point: degrees in, pixels converted once through
``Screen``, PsychoPy imported only inside construction, and a recording
``NullStimulus`` from the factory on alhazen's simulated backend, so the task runs
unchanged where no renderer is installed.
"""

from __future__ import annotations

from typing import Any

from alhazen.display.backend import DisplayBackend
from alhazen.display.screen import Screen
from alhazen.stimuli.base import NullStimulus, Stimulus

from posner1980 import geometry

Color = tuple[float, float, float]


class StrokeShape:
    """Line strokes (an arrow, a plus sign), each drawn as a filled bar
    (``geometry.stroke_polygon``) rather than an OpenGL line, whose width some
    drivers cap at a few pixels."""

    def __init__(self, display: DisplayBackend, screen: Screen, strokes, width_dva: float,
                 color: Color) -> None:
        from psychopy import visual

        self._bars: list[Any] = []
        for start, end in strokes:
            corners = [(screen.deg2px(x), screen.deg2px(y))
                       for x, y in geometry.stroke_polygon(start, end, width_dva)]
            self._bars.append(visual.ShapeStim(display.window, vertices=corners,
                                               closeShape=True, fillColor=color,
                                               lineColor=None, units="pix"))

    def update(self, dt: float) -> None:
        return

    def draw(self) -> None:
        for bar in self._bars:
            bar.draw()


class FilledSquare:
    """The detection stimulus: a filled square."""

    def __init__(self, display: DisplayBackend, screen: Screen, center_dva, side_dva: float,
                 color: Color) -> None:
        from psychopy import visual

        corners = [(screen.deg2px(x), screen.deg2px(y))
                   for x, y in geometry.square_corners(center_dva, side_dva)]
        self._stim = visual.ShapeStim(display.window, vertices=corners, closeShape=True,
                                      fillColor=color, lineColor=color, units="pix")

    def update(self, dt: float) -> None:
        return

    def draw(self) -> None:
        self._stim.draw()


def make_cue(display: DisplayBackend, screen: Screen, cue: str, size_dva: float,
             stroke_dva: float, color: Color) -> Stimulus:
    """The plus sign (``neutral``) or an arrow (``left``/``right``) at fixation."""
    strokes = geometry.cue_strokes(cue, size_dva)
    if display.kind == "simulated":
        return NullStimulus(f"cue-{cue}")
    return StrokeShape(display, screen, strokes, stroke_dva, color)


def make_target(display: DisplayBackend, screen: Screen, side: str, eccentricity_dva: float,
                size_dva: float, color: Color) -> Stimulus:
    """The filled square, ``eccentricity_dva`` left or right of fixation."""
    center = geometry.target_center(side, eccentricity_dva)
    if display.kind == "simulated":
        return NullStimulus(f"target-{side}")
    return FilledSquare(display, screen, center, size_dva, color)
