"""What a trial draws: the uniform grey field, the letters, the fixation dot, prompts.

Each factory returns the real PsychoPy stimulus on a rendering backend and a recording
``NullStimulus`` on the simulated one (alhazen's own convention, ``make_fixation``), so
the task runs unchanged headless. PsychoPy is imported inside the constructors, never
at module import. Positions are centred pixels, y up; sizes come in pixels, converted
from degrees once by the caller through alhazen's ``Screen``.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from alhazen.display.backend import DisplayBackend
from alhazen.stimuli.base import NullStimulus, Stimulus

from raymond1992.glyphs import Glyph


def _grey(value: float) -> tuple[float, float, float]:
    return (value, value, value)


class LetterImage:
    """One glyph, drawn in a uniform colour through its alpha mask.

    The glyph's cap-height centre is placed at ``pos``. Numpy textures reach OpenGL
    bottom row first, so both arrays are flipped vertically."""

    def __init__(self, display: DisplayBackend, glyph: Glyph, rgb: float,
                 pos: tuple[float, float] = (0.0, 0.0)) -> None:
        from psychopy import visual

        h, w = glyph.alpha.shape
        image = np.full((h, w, 3), rgb, dtype=float)
        mask = np.flipud(glyph.alpha * 2.0 - 1.0)
        center_y = pos[1] + (glyph.cap_center_y - h / 2.0)
        self._stim: Any = visual.ImageStim(
            display.window, image=np.flipud(image), mask=mask, size=(w, h),
            pos=(pos[0], center_y), units="pix", colorSpace="rgb", interpolate=False,
        )

    def update(self, dt: float) -> None:
        return

    def draw(self) -> None:
        self._stim.draw()


class Rectangle:
    def __init__(self, display: DisplayBackend, width_px: float, height_px: float,
                 rgb: float) -> None:
        from psychopy import visual

        self._stim: Any = visual.Rect(
            display.window, width=width_px, height=height_px, pos=(0, 0), units="pix",
            fillColor=_grey(rgb), lineColor=None, colorSpace="rgb",
        )

    def update(self, dt: float) -> None:
        return

    def draw(self) -> None:
        self._stim.draw()


class Dot:
    def __init__(self, display: DisplayBackend, diameter_px: float, rgb: float) -> None:
        from psychopy import visual

        self._stim: Any = visual.Circle(
            display.window, radius=diameter_px / 2.0, pos=(0, 0), units="pix",
            fillColor=_grey(rgb), lineColor=None, colorSpace="rgb",
        )

    def update(self, dt: float) -> None:
        return

    def draw(self) -> None:
        self._stim.draw()


class Prompt:
    def __init__(self, display: DisplayBackend, text: str, height_px: float, rgb: float,
                 wrap_px: float) -> None:
        from psychopy import visual

        self._stim: Any = visual.TextStim(
            display.window, text=text, height=height_px, pos=(0, 0), units="pix",
            color=_grey(rgb), colorSpace="rgb", wrapWidth=wrap_px, alignText="center",
        )

    def update(self, dt: float) -> None:
        return

    def draw(self) -> None:
        self._stim.draw()


def make_letter(display: DisplayBackend, glyph: Glyph, rgb: float) -> Stimulus:
    if display.kind == "simulated":
        return NullStimulus(f"letter_{glyph.letter}")
    return LetterImage(display, glyph, rgb)


def make_rect(display: DisplayBackend, name: str, width_px: float, height_px: float,
              rgb: float) -> Stimulus:
    if display.kind == "simulated":
        return NullStimulus(name)
    return Rectangle(display, width_px, height_px, rgb)


def make_dot(display: DisplayBackend, diameter_px: float, rgb: float) -> Stimulus:
    if display.kind == "simulated":
        return NullStimulus("fixation")
    return Dot(display, diameter_px, rgb)


def make_prompt(display: DisplayBackend, name: str, text: str, height_px: float, rgb: float,
                wrap_px: float) -> Stimulus:
    if display.kind == "simulated":
        return NullStimulus(name)
    return Prompt(display, text, height_px, rgb, wrap_px)
