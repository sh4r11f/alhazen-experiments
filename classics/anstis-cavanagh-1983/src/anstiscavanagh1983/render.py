"""Putting the frames on a window: the psychopy stimulus, and the stand-in a simulated
session uses.

The stimulus is frame-locked, not clock-driven: each ``draw()`` is one display frame,
and stroke ``(draws // frames_per_stroke) % strokes`` is shown. The cycle rate is
therefore exactly ``refresh / (frames_per_stroke * strokes)`` whenever no frame is
dropped (the rig's frame QA recycles a trial with too many drops). ``update(dt)`` is
accepted and ignored for that reason.

psychopy (at the version uv.lock pins) reads a float numpy image as 0..1 per channel and
draws its first row at the bottom. The frames here are symmetric top to bottom except
for the optional line dither, which is flipped to match. Linear levels are only right
on a gamma-linearised display (color.py).
"""

from __future__ import annotations

from typing import Any

import numpy as np

from anstiscavanagh1983.color import ColourSpace
from anstiscavanagh1983.stimulus import Fixation, Spec, fixation_frame, frames


class CycleCore:
    """The frame counter and the frames, shared by the real and simulated stimulus."""

    def __init__(self, spec: Spec, space: ColourSpace, px_per_deg: float, fix: Fixation,
                 frames_per_stroke: int) -> None:
        self.space, self.px_per_deg, self.fix = space, px_per_deg, fix
        self.frames_per_stroke = int(frames_per_stroke)
        self.draw_count = 0
        self.shown: list[int] = []  # stroke index of every drawn frame (tests read it)
        self.set_spec(spec)

    def set_spec(self, spec: Spec) -> None:
        self.spec = spec
        self.images = frames(spec, self.space, self.px_per_deg, self.fix)

    def stroke_now(self) -> int:
        return (self.draw_count // self.frames_per_stroke) % self.spec.strokes

    def advance(self) -> int:
        k = self.stroke_now()
        self.shown.append(k)
        self.draw_count += 1
        return k


class SimulatedCycle(CycleCore):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.scene = self

    def update(self, dt: float) -> None:
        pass

    def draw(self) -> None:
        self.advance()


class PsychopyCycle(CycleCore):
    def __init__(self, display: Any, screen: Any, *args: Any, **kwargs: Any) -> None:
        from psychopy import visual

        super().__init__(*args, **kwargs)
        n = self.spec.size_px
        self._bg: Any = visual.Rect(display.window, width=screen.width_px * 1.1,
                                    height=screen.height_px * 1.1, units="pix",
                                    fillColor=(-1, -1, -1), lineColor=(-1, -1, -1),
                                    colorSpace="rgb")
        self._stims = [visual.ImageStim(display.window, image=self._rgba(i), size=(n, n),
                                        units="pix", colorSpace="rgb", interpolate=False)
                       for i in self.images]

    @staticmethod
    def _rgba(img: np.ndarray) -> np.ndarray:
        rgba = np.ones(img.shape[:2] + (4,), dtype=np.float32)
        rgba[..., :3] = img[::-1]  # psychopy: first row at the bottom
        return rgba

    def set_spec(self, spec: Spec) -> None:
        super().set_spec(spec)
        for stim, img in zip(getattr(self, "_stims", []), self.images, strict=False):
            stim.image = self._rgba(img)

    def update(self, dt: float) -> None:
        pass

    def draw(self) -> None:
        k = self.advance()
        self._bg.draw()
        self._stims[k].draw()


class FixationStim:
    """The fixation mark alone on the dark surround."""

    def __init__(self, display: Any, screen: Any, n: int, px_per_deg: float,
                 fix: Fixation) -> None:
        self.image = fixation_frame(n, px_per_deg, fix)
        self.draw_count = 0
        self._real = display.kind != "simulated"
        if self._real:
            from psychopy import visual

            self._bg: Any = visual.Rect(display.window, width=screen.width_px * 1.1,
                                        height=screen.height_px * 1.1, units="pix",
                                        fillColor=(-1, -1, -1), lineColor=(-1, -1, -1),
                                        colorSpace="rgb")
            self._stim: Any = visual.ImageStim(display.window,
                                               image=PsychopyCycle._rgba(self.image),
                                               size=(n, n), units="pix", colorSpace="rgb",
                                               interpolate=False)

    def update(self, dt: float) -> None:
        pass

    def draw(self) -> None:
        self.draw_count += 1
        if self._real:
            self._bg.draw()
            self._stim.draw()


def make_cycle(display: Any, screen: Any, spec: Spec, space: ColourSpace, fix: Fixation,
               frames_per_stroke: int) -> CycleCore:
    if display.kind == "simulated":
        return SimulatedCycle(spec, space, screen.px_per_deg, fix, frames_per_stroke)
    return PsychopyCycle(display, screen, spec, space, screen.px_per_deg, fix,
                         frames_per_stroke)
