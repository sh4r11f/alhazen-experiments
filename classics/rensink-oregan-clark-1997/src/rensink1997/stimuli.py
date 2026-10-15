"""The few stimuli this task draws: a photograph, a filled or outlined rectangle, a text.

alhazen ships a fixation point and leaves the rest to the experiment. These follow its
pattern (stimuli/fixation.py): sizes arrive in pixels already converted from dva by the
task, the renderer (psychopy) is imported only inside construction, and on the simulated
backend each factory returns alhazen's recording NullStimulus, so the task runs headless
with nothing installed.
"""

from __future__ import annotations

from typing import Any

from alhazen.stimuli.base import NullStimulus, Stimulus
from PIL import Image


class ImageStimulus:
    """A photograph scaled to ``size_px`` (width, height), centred at ``pos``."""

    def __init__(self, display: Any, image: Image.Image, size_px: tuple[float, float],
                 pos: tuple[float, float] = (0.0, 0.0)) -> None:
        from psychopy import visual

        self._stim = visual.ImageStim(display.window, image=image.convert("RGB"),
                                      size=size_px, pos=pos, units="pix", interpolate=True)

    def update(self, dt: float) -> None:
        return

    def draw(self) -> None:
        self._stim.draw()


class RectStimulus:
    """A rectangle: filled (``fill``) and/or outlined (``line``), signed RGB."""

    def __init__(self, display: Any, size_px: tuple[float, float],
                 pos: tuple[float, float] = (0.0, 0.0),
                 fill: tuple[float, float, float] | None = None,
                 line: tuple[float, float, float] | None = None, line_px: float = 0.0) -> None:
        from psychopy import visual

        self._stim = visual.Rect(display.window, width=size_px[0], height=size_px[1], pos=pos,
                                 fillColor=fill, lineColor=line, lineWidth=line_px, units="pix")

    def update(self, dt: float) -> None:
        return

    def draw(self) -> None:
        self._stim.draw()


class TextStimulus:
    """One or more lines of text, centred at ``pos``."""

    def __init__(self, display: Any, text: str, height_px: float,
                 pos: tuple[float, float] = (0.0, 0.0),
                 color: tuple[float, float, float] = (1.0, 1.0, 1.0),
                 wrap_px: float | None = None) -> None:
        from psychopy import visual

        self._stim = visual.TextStim(display.window, text=text, height=height_px, pos=pos,
                                     color=color, units="pix", wrapWidth=wrap_px,
                                     alignText="center", anchorHoriz="center")

    def update(self, dt: float) -> None:
        return

    def draw(self) -> None:
        self._stim.draw()


def make_image(display: Any, image: Image.Image, size_px: tuple[float, float],
               pos: tuple[float, float] = (0.0, 0.0), name: str = "image") -> Stimulus:
    if display.kind == "simulated":
        return NullStimulus(name)
    return ImageStimulus(display, image, size_px, pos)


def make_rect(display: Any, size_px: tuple[float, float], pos: tuple[float, float] = (0.0, 0.0),
              fill: tuple[float, float, float] | None = None,
              line: tuple[float, float, float] | None = None, line_px: float = 0.0,
              name: str = "rect") -> Stimulus:
    if display.kind == "simulated":
        return NullStimulus(name)
    return RectStimulus(display, size_px, pos, fill, line, line_px)


def make_text(display: Any, text: str, height_px: float, pos: tuple[float, float] = (0.0, 0.0),
              color: tuple[float, float, float] = (1.0, 1.0, 1.0), wrap_px: float | None = None,
              name: str = "text") -> Stimulus:
    if display.kind == "simulated":
        return NullStimulus(name)
    return TextStimulus(display, text, height_px, pos, color, wrap_px)
