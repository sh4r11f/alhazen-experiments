"""The four things on screen: background, fixation point, target, distractor.

Squares and a full-screen background, following alhazen's stimulus pattern:
degrees in, pixels once, the renderer imported lazily, and a recording
stand-in on the simulated backend so the same task code runs headless and in
the tests. The stand-in keeps every draw (position and colour), which is what
lets a test count distractor flashes and see the target dim.
"""

from __future__ import annotations

from typing import Any

from alhazen.display.backend import DisplayBackend
from alhazen.display.screen import Screen
from alhazen.stimuli.fixation import make_fixation

RGB = tuple[float, float, float]


class Square:
    """A filled square at a centred-px position, recolourable and movable."""

    def __init__(self, display: DisplayBackend, side_px: float, color: RGB,
                 pos: tuple[float, float] = (0.0, 0.0)) -> None:
        from psychopy import visual

        self._stim: Any = visual.Rect(display.window, width=side_px, height=side_px, pos=pos,
                                      fillColor=color, lineColor=None, units="pix")

    def update(self, dt: float) -> None:
        return

    def draw(self) -> None:
        self._stim.draw()

    def set_color(self, color: RGB) -> None:
        self._stim.fillColor = color

    def set_pos(self, pos: tuple[float, float]) -> None:
        self._stim.pos = pos


class RecordingSquare:
    """The simulated backend's square: draws nothing, remembers everything."""

    def __init__(self, name: str, color: RGB, pos: tuple[float, float] = (0.0, 0.0)) -> None:
        self.name = name
        self.color = color
        self.pos = pos
        self.draws: list[tuple[tuple[float, float], RGB]] = []
        self.colors: list[RGB] = []

    def update(self, dt: float) -> None:
        return

    def draw(self) -> None:
        self.draws.append((self.pos, self.color))

    def set_color(self, color: RGB) -> None:
        self.color = color
        self.colors.append(color)

    def set_pos(self, pos: tuple[float, float]) -> None:
        self.pos = pos


def make_square(display: DisplayBackend, screen: Screen, side_dva: float, color: RGB,
                pos_px: tuple[float, float] = (0.0, 0.0), name: str = "square") -> Any:
    if display.kind == "simulated":
        return RecordingSquare(name, color, pos_px)
    return Square(display, screen.deg2px(side_dva), color, pos_px)


def make_background(display: DisplayBackend, screen: Screen, color: RGB) -> Any:
    """A rectangle covering the whole window: the paper's 1 cd/m² background,
    since alhazen's window itself is mid-grey."""
    if display.kind == "simulated":
        return RecordingSquare("background", color)
    from psychopy import visual

    rect = visual.Rect(display.window, width=screen.width_px + 2, height=screen.height_px + 2,
                       pos=(0, 0), fillColor=color, lineColor=None, units="pix")

    class _Background:
        def update(self, dt: float) -> None:
            return

        def draw(self) -> None:
            rect.draw()

    return _Background()


def make_fixation_point(display: DisplayBackend, screen: Screen, size_dva: float,
                        color: RGB) -> Any:
    """alhazen's fixation point, in the given colour; recordable when simulated."""
    if display.kind == "simulated":
        return RecordingSquare("fixation", color)
    return make_fixation(display, screen, size_dva, fill_color=color)
