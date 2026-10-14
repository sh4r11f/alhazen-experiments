"""The cue: a filled square, the paper's "filled white squares (0.7 x 0.7 deg)".

Same pattern as alhazen's fixation point: degrees in, pixels once, the renderer imported
only when a real window is drawn, and a recording stand-in on the simulated backend.
"""

from __future__ import annotations

from typing import Any

from alhazen.display.backend import DisplayBackend
from alhazen.display.screen import Screen
from alhazen.stimuli.base import NullStimulus, Stimulus


class FilledSquare:
    """A filled, axis-aligned square at a centred-px position."""

    def __init__(self, display: DisplayBackend, screen: Screen, size_dva: float,
                 fill_color: tuple[float, float, float], pos: tuple[float, float]) -> None:
        from psychopy import visual

        side = screen.deg2px(size_dva)
        self._stim: Any = visual.Rect(display.window, width=side, height=side, pos=pos,
                                      fillColor=fill_color, lineColor=fill_color, units="pix")

    def update(self, dt: float) -> None:
        return

    def draw(self) -> None:
        self._stim.draw()


def make_square(display: DisplayBackend, screen: Screen, size_dva: float,
                fill_color: tuple[float, float, float], pos: tuple[float, float]) -> Stimulus:
    if display.kind == "simulated":
        return NullStimulus("cue")
    return FilledSquare(display, screen, size_dva, fill_color, pos)
