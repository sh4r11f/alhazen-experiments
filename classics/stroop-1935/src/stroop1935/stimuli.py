"""What a trial draws: a colour word, a solid colour square, and the page.

Each stimulus follows alhazen's contract (alhazen.stimuli.base): sizes in
degrees of visual angle converted to pixels once, through ``Screen``, at
construction; the renderer imported lazily inside construction; and a
recording ``NullStimulus`` on the simulated backend, so the same task code runs
on a machine with no renderer installed.
"""

from __future__ import annotations

from typing import Any

from alhazen.display.backend import DisplayBackend
from alhazen.display.screen import Screen
from alhazen.stimuli.base import NullStimulus, Stimulus

RGB = tuple[float, float, float]


class ColorWord:
    """A lower-case colour name printed in one ink, centred on the screen."""

    def __init__(self, display: DisplayBackend, screen: Screen, text: str, color: RGB,
                 height_dva: float, font: str) -> None:
        from psychopy import visual

        self._stim: Any = visual.TextStim(
            display.window, text=text, color=color, colorSpace="rgb",
            height=screen.deg2px(height_dva), font=font, units="pix", pos=(0.0, 0.0),
            anchorHoriz="center", anchorVert="center",
        )

    def update(self, dt: float) -> None:
        return

    def draw(self) -> None:
        self._stim.draw()


class ColorPatch:
    """A solid square of one ink, centred on the screen: Stroop's NC item."""

    def __init__(self, display: DisplayBackend, screen: Screen, color: RGB,
                 size_dva: float) -> None:
        from psychopy import visual

        side = screen.deg2px(size_dva)
        self._stim: Any = visual.Rect(
            display.window, width=side, height=side, fillColor=color, lineColor=color,
            colorSpace="rgb", units="pix", pos=(0.0, 0.0),
        )

    def update(self, dt: float) -> None:
        return

    def draw(self) -> None:
        self._stim.draw()


def make_word(display: DisplayBackend, screen: Screen, text: str, color: RGB,
              height_dva: float, font: str) -> Stimulus:
    if display.kind == "simulated":
        return NullStimulus(f"word:{text}")
    return ColorWord(display, screen, text, color, height_dva, font)


def make_patch(display: DisplayBackend, screen: Screen, color: RGB,
               size_dva: float) -> Stimulus:
    if display.kind == "simulated":
        return NullStimulus("patch")
    return ColorPatch(display, screen, color, size_dva)


def apply_background(display: DisplayBackend, color: RGB) -> None:
    """Give the window the colour of the printed page.

    alhazen opens its PsychoPy window on mid-grey and offers no setting for the
    background, and Stroop's tests were printed on paper. Grey is a poor page
    for these inks (a saturated green is nearly as light as mid-grey), so the
    window's clear colour is set here, once per trial, before anything is
    drawn. Setting it again to the same value is harmless. The simulated
    backend has no surface, and nothing is done there. The instruction and
    pause panels alhazen draws carry their own fill, so they read the same.
    """
    window = getattr(display, "window", None)
    if display.kind != "psychopy" or window is None:
        return
    if tuple(getattr(window, "color", ())) != tuple(color):
        window.color = color
