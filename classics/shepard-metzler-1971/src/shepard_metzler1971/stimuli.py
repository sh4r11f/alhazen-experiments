"""What is drawn: the black surface with two circular apertures, and a pair of drawings.

The original display (p. 703): line drawings on cards, seen through two circular
apertures in a vertical black surface, 9 degrees apart centre to centre, at about 60 cm.
Here the surface is the screen, each aperture is one image of the stimulus bank (a white
disc with the drawing, on black), and a picture-plane rotation is the image turned about
the aperture's centre, as the paper turned the card.

Built the alhazen way: sizes in dva converted to pixels once through the Screen, the
renderer imported lazily, and the simulated backend given recording stand-ins, so the
same task code runs with no display stack installed.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from alhazen.display.backend import DisplayBackend
from alhazen.display.screen import Screen
from alhazen.stimuli.base import NullStimulus, Stimulus

WHITE = (1.0, 1.0, 1.0)


class Surface:
    """The black surface and the two empty (white) apertures, between pairs."""

    def __init__(self, display: DisplayBackend, screen: Screen, aperture_dva: float,
                 spacing_dva: float, color: tuple[float, float, float]) -> None:
        from psychopy import visual

        half = screen.deg2px(spacing_dva) / 2.0
        r = screen.deg2px(aperture_dva) / 2.0
        self._stims: list[Any] = [
            visual.Rect(display.window, width=screen.width_px * 2, height=screen.height_px * 2,
                        fillColor=color, lineColor=color, units="pix"),
            visual.Circle(display.window, radius=r, pos=(-half, 0.0), fillColor=WHITE,
                          lineColor=WHITE, units="pix", edges=256),
            visual.Circle(display.window, radius=r, pos=(half, 0.0), fillColor=WHITE,
                          lineColor=WHITE, units="pix", edges=256),
        ]

    def update(self, dt: float) -> None:
        return

    def draw(self) -> None:
        for s in self._stims:
            s.draw()


class DrawingPair:
    """Two bank images in the two apertures, each turned by its own picture-plane angle
    (clockwise positive, as PsychoPy's ``ori``)."""

    def __init__(self, display: DisplayBackend, screen: Screen, bank_dir: Path,
                 left: tuple[str, float], right: tuple[str, float], aperture_dva: float,
                 spacing_dva: float) -> None:
        from psychopy import visual

        half = screen.deg2px(spacing_dva) / 2.0
        size = screen.deg2px(aperture_dva)
        self._stims: list[Any] = [
            visual.ImageStim(display.window, image=str(bank_dir / name), pos=(x, 0.0),
                             size=(size, size), ori=ori, units="pix", interpolate=True)
            for (name, ori), x in ((left, -half), (right, half))
        ]

    def update(self, dt: float) -> None:
        return

    def draw(self) -> None:
        for s in self._stims:
            s.draw()


def make_surface(display: DisplayBackend, screen: Screen, aperture_dva: float,
                 spacing_dva: float, color: tuple[float, float, float]) -> Stimulus:
    if display.kind == "simulated":
        return NullStimulus("surface")
    return Surface(display, screen, aperture_dva, spacing_dva, color)


def make_pair(display: DisplayBackend, screen: Screen, bank_dir: Path,
              left: tuple[str, float], right: tuple[str, float], aperture_dva: float,
              spacing_dva: float) -> Stimulus:
    for name, _ in (left, right):
        if not (bank_dir / name).is_file():
            raise FileNotFoundError(f"stimulus bank has no {name}: regenerate stimuli/bank")
    if display.kind == "simulated":
        return NullStimulus("pair")
    return DrawingPair(display, screen, bank_dir, left, right, aperture_dva, spacing_dva)
