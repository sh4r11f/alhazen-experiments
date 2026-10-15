"""The two things this experiment draws: text at the fixed locus, and a feedback lamp.

Built like alhazen's own stimuli: sizes in dva converted to pixels once at construction,
the renderer imported lazily, and a recording stand-in on the simulated backend so trial
logic runs with no window (tests, ``--mode simulate --headless``).
"""

from __future__ import annotations

from typing import Any

from alhazen.display.backend import DisplayBackend
from alhazen.display.screen import Screen

# The face the digits are drawn in. ASSUMED (not in the paper): the paper does not
# describe the display at all. DejaVu Sans Mono is the face alhazen registers from
# matplotlib's copy when a rig lacks it, so every rig draws the same glyphs.
FONT = "DejaVu Sans Mono"


class TextStimulus:
    """A line of text centred at ``pos`` (centred px), ``height_dva`` tall."""

    def __init__(
        self,
        display: DisplayBackend,
        screen: Screen,
        text: str,
        height_dva: float,
        color: tuple[float, float, float],
        pos: tuple[float, float] = (0.0, 0.0),
    ) -> None:
        from psychopy import visual

        self._stim: Any = visual.TextStim(
            display.window,
            text=text,
            font=FONT,
            height=screen.deg2px(height_dva),
            color=color,
            colorSpace="rgb",
            pos=pos,
            units="pix",
            anchorHoriz="center",
            anchorVert="center",
            wrapWidth=screen.deg2px(40.0),
        )

    @property
    def text(self) -> str:
        return str(self._stim.text)

    @text.setter
    def text(self, value: str) -> None:
        self._stim.text = value

    def update(self, dt: float) -> None:
        return

    def draw(self) -> None:
        self._stim.draw()


class RecordingText:
    """The simulated backend's text: remembers what it would have drawn."""

    def __init__(self, name: str, text: str) -> None:
        self.name = name
        self.text = text
        self.drawn: list[str] = []

    def update(self, dt: float) -> None:
        return

    def draw(self) -> None:
        self.drawn.append(self.text)


class Lamp:
    """The feedback light: a filled disc whose colour says right or wrong."""

    def __init__(
        self,
        display: DisplayBackend,
        screen: Screen,
        size_dva: float,
        pos: tuple[float, float],
    ) -> None:
        from psychopy import visual

        self._stim: Any = visual.Circle(
            display.window,
            radius=screen.deg2px(size_dva) / 2.0,
            pos=pos,
            fillColor=(0.0, 0.0, 0.0),
            lineColor=(0.0, 0.0, 0.0),
            units="pix",
        )

    def set_color(self, color: tuple[float, float, float]) -> None:
        self._stim.fillColor = color
        self._stim.lineColor = color

    def update(self, dt: float) -> None:
        return

    def draw(self) -> None:
        self._stim.draw()


class RecordingLamp:
    """The simulated backend's lamp: remembers every colour it was set to and drawn in."""

    def __init__(self) -> None:
        self.color: tuple[float, float, float] | None = None
        self.colors: list[tuple[float, float, float]] = []
        self.draw_count = 0

    def set_color(self, color: tuple[float, float, float]) -> None:
        self.color = (float(color[0]), float(color[1]), float(color[2]))
        self.colors.append(self.color)

    def update(self, dt: float) -> None:
        return

    def draw(self) -> None:
        self.draw_count += 1


def make_text(
    display: DisplayBackend,
    screen: Screen,
    name: str,
    text: str,
    height_dva: float,
    color: tuple[float, float, float],
    pos: tuple[float, float] = (0.0, 0.0),
) -> TextStimulus | RecordingText:
    if display.kind == "simulated":
        return RecordingText(name, text)
    return TextStimulus(display, screen, text, height_dva, color, pos)


def make_lamp(
    display: DisplayBackend, screen: Screen, size_dva: float, pos: tuple[float, float]
) -> Lamp | RecordingLamp:
    if display.kind == "simulated":
        return RecordingLamp()
    return Lamp(display, screen, size_dva, pos)
