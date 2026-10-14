"""The two stimuli a trial draws: a picture on the white field, and feedback text.

Both follow alhazen's stimulus contract (update/draw), import PsychoPy lazily, and have a
recording stand-in for the simulated backend, so the task runs unchanged headless.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from alhazen.display.backend import DisplayBackend
from alhazen.display.screen import Screen
from PIL import Image


def _signed(rgb: Sequence[int]) -> tuple[float, float, float]:
    """0-255 RGB to PsychoPy's signed RGB (-1..1)."""
    r, g, b = (float(c) / 127.5 - 1.0 for c in rgb)
    return (r, g, b)


class FieldPicture:
    """The white field filling the screen (the tachistoscope card), with an optional
    patch of pixels on it, placed by its centre in centred px."""

    def __init__(self, display: DisplayBackend, screen: Screen, background_rgb: Sequence[int],
                 patch: Image.Image | None, centre_px: tuple[float, float]) -> None:
        from psychopy import visual

        color = _signed(background_rgb)
        self._field = visual.Rect(display.window, width=screen.width_px, height=screen.height_px,
                                  units="pix", fillColor=color, lineColor=color)
        self._image: Any = None
        if patch is not None:
            self._image = visual.ImageStim(display.window, image=patch, size=patch.size,
                                           pos=centre_px, units="pix", interpolate=False)

    def update(self, dt: float) -> None:
        return

    def draw(self) -> None:
        self._field.draw()
        if self._image is not None:
            self._image.draw()


class RecordedPicture:
    """The simulated backend's FieldPicture: keeps the pixels and counts draws."""

    def __init__(self, name: str, patch: Image.Image | None,
                 centre_px: tuple[float, float]) -> None:
        self.name = name
        self.patch = patch
        self.centre_px = centre_px
        self.draw_count = 0

    def update(self, dt: float) -> None:
        return

    def draw(self) -> None:
        self.draw_count += 1


def make_picture(display: DisplayBackend, screen: Screen, name: str,
                 background_rgb: Sequence[int], patch: Image.Image | None,
                 centre_px: tuple[float, float]) -> Any:
    if display.kind == "simulated":
        return RecordedPicture(name, patch, centre_px)
    return FieldPicture(display, screen, background_rgb, patch, centre_px)


class FeedbackText:
    """A line of text on the white field: the trial's RT and whether it was correct."""

    def __init__(self, display: DisplayBackend, screen: Screen, background_rgb: Sequence[int],
                 text_rgb: Sequence[int], height_dva: float) -> None:
        from psychopy import visual

        color = _signed(background_rgb)
        self._field = visual.Rect(display.window, width=screen.width_px, height=screen.height_px,
                                  units="pix", fillColor=color, lineColor=color)
        self._text = visual.TextStim(display.window, text="", units="pix",
                                     height=screen.deg2px(height_dva), color=_signed(text_rgb),
                                     colorSpace="rgb", wrapWidth=screen.width_px * 0.8)

    def set_text(self, text: str) -> None:
        self._text.text = text

    def update(self, dt: float) -> None:
        return

    def draw(self) -> None:
        self._field.draw()
        self._text.draw()


class RecordedText:
    """The simulated backend's FeedbackText: keeps every text it was given."""

    def __init__(self) -> None:
        self.texts: list[str] = []
        self.draw_count = 0

    def set_text(self, text: str) -> None:
        self.texts.append(text)

    def update(self, dt: float) -> None:
        return

    def draw(self) -> None:
        self.draw_count += 1


def make_feedback_text(display: DisplayBackend, screen: Screen, background_rgb: Sequence[int],
                       text_rgb: Sequence[int], height_dva: float) -> Any:
    if display.kind == "simulated":
        return RecordedText()
    return FeedbackText(display, screen, background_rgb, text_rgb, height_dva)
