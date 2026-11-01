"""Drawing: the psychopy objects a real session uses, and the stand-ins a simulated one uses.

alhazen's house pattern (its ``stimuli/fixation.py``): degrees in, pixels computed once,
psychopy imported lazily inside the class so this module imports on a machine with no
renderer, and a factory that hands a simulated backend a stand-in. The grating's
stand-in still builds the image and measures it (``grating.render``), because the
realised contrast is data the trial records whether or not a window exists.

The grating is one ``ImageStim`` of the field's pixels, 1:1 (``units="pix"``, size = the
image's own pixel count, ``interpolate=False``), as RGBA float32 in 0..1 per channel with
the bottom row first, the convention this repository's cavanagh-1992 folder checked by
drawing under Xvfb and reading the frame back. That readback has NOT been repeated for
this folder (docs/methods.md, Verification). The surround is a full-screen rectangle at
the same mean code value, so the field's edge carries no step in mean luminance (the
paper's matched cardboard surround, p. 553).
"""

from __future__ import annotations

from typing import Any

import numpy as np
from alhazen.display.backend import DisplayBackend
from alhazen.display.screen import Screen
from alhazen.stimuli.base import NullStimulus

from campbell_robson1968.grating import Dither, GratingSpec, Realised, render


def to_signed(v: float) -> tuple[float, float, float]:
    """A grey in linearised 0..1 as psychopy's signed rgb triple."""
    s = float(v) * 2.0 - 1.0
    return (s, s, s)


class GratingImage:
    """The grating's pixels and what they measure to; shared by both stand-ins."""

    def __init__(
        self, spec: GratingSpec, px_per_deg: float, bits: int, dither: Dither, seed: int
    ) -> None:
        self.px_per_deg, self.bits, self.dither, self.seed = px_per_deg, bits, dither, seed
        self.set_spec(spec)

    def set_spec(self, spec: GratingSpec) -> None:
        self.spec = spec
        # The same seed every time a spec is drawn: a setting the subject returns to
        # shows the same pixels, and any image can be rebuilt from the record.
        self.image, self.realised = render(
            spec,
            self.px_per_deg,
            bits=self.bits,
            dither=self.dither,
            rng=np.random.default_rng(self.seed),
        )

    def rgba(self) -> np.ndarray:
        img = self.image[::-1].astype(np.float32)  # bottom row first
        out = np.empty(img.shape + (4,), dtype=np.float32)
        out[..., 0] = out[..., 1] = out[..., 2] = img
        out[..., 3] = 1.0
        return out


class SimulatedGrating:
    """The grating without a window: counts frames shown, never renders."""

    def __init__(self, image: GratingImage) -> None:
        self.grating = image
        self.draw_count = 0

    @property
    def realised(self) -> Realised:
        return self.grating.realised

    def set_spec(self, spec: GratingSpec) -> None:
        self.grating.set_spec(spec)

    def update(self, dt: float) -> None:
        pass

    def draw(self) -> None:
        self.draw_count += 1


class GratingStimulus(SimulatedGrating):
    """The grating on a psychopy window, at the screen centre."""

    def __init__(self, display: DisplayBackend, image: GratingImage) -> None:
        from psychopy import visual

        super().__init__(image)
        n = image.image.shape[0]
        self._stim: Any = visual.ImageStim(
            display.window,
            image=image.rgba(),
            size=(n, n),
            units="pix",
            pos=(0, 0),
            colorSpace="rgb",
            interpolate=False,
        )

    def set_spec(self, spec: GratingSpec) -> None:
        super().set_spec(spec)
        self._stim.image = self.grating.rgba()

    def draw(self) -> None:
        super().draw()
        self._stim.draw()


def make_grating(
    display: DisplayBackend,
    screen: Screen,
    spec: GratingSpec,
    *,
    bits: int,
    dither: Dither,
    seed: int,
) -> SimulatedGrating:
    image = GratingImage(spec, screen.px_per_deg, bits, dither, seed)
    if display.kind == "simulated":
        return SimulatedGrating(image)
    return GratingStimulus(display, image)


class FlickerGrating:
    """A grating switched on and off at a fixed period, counted in frames (the paper's
    "switched on and off at 0.5 c/s", p. 553): on for ``on_frames``, then off (the mean
    field shows through) until ``period_frames``, from the first frame it is drawn.
    The contrast can be changed while it runs (``set_contrast``)."""

    def __init__(self, inner: SimulatedGrating, on_frames: int, period_frames: int) -> None:
        if not 0 < on_frames < period_frames:
            raise ValueError("need 0 < on_frames < period_frames")
        self.inner, self.on_frames, self.period_frames = inner, on_frames, period_frames
        self.frame = 0
        self.frames_on = 0

    @property
    def realised(self) -> Realised:
        return self.inner.realised

    @property
    def contrast(self) -> float:
        return self.inner.grating.spec.contrast

    def set_contrast(self, contrast: float) -> None:
        spec = self.inner.grating.spec
        self.inner.set_spec(GratingSpec(**{**spec.__dict__, "contrast": float(contrast)}))

    def visible(self) -> bool:
        return self.frame % self.period_frames < self.on_frames

    def update(self, dt: float) -> None:
        pass

    def draw(self) -> None:
        if self.visible():
            self.inner.draw()
            self.frames_on += 1
        self.frame += 1


class MeanField:
    """The whole screen at the mean grey: the surround and the blank intervals."""

    def __init__(self, display: DisplayBackend, screen: Screen, mean: float) -> None:
        from psychopy import visual

        c = to_signed(mean)
        self._rect: Any = visual.Rect(
            display.window,
            width=screen.width_px * 1.1,
            height=screen.height_px * 1.1,
            units="pix",
            fillColor=c,
            lineColor=c,
            colorSpace="rgb",
        )

    def update(self, dt: float) -> None:
        pass

    def draw(self) -> None:
        self._rect.draw()


def make_mean_field(display: DisplayBackend, screen: Screen, mean: float) -> Any:
    if display.kind == "simulated":
        return NullStimulus("field")
    return MeanField(display, screen, mean)


def bracket_segments(
    field_dva: float, gap_dva: float, arm_dva: float
) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    """Four L-shaped corner marks just outside the field, in dva from the centre, as
    line segments ((x1, y1), (x2, y2)): two per corner."""
    h = field_dva / 2.0 + gap_dva
    segs = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            corner = (sx * h, sy * h)
            segs.append((corner, (sx * (h - arm_dva), sy * h)))
            segs.append((corner, (sx * h, sy * (h - arm_dva))))
    return segs


class IntervalMarks:
    """The corner marks that show when an observation interval is running."""

    def __init__(
        self,
        display: DisplayBackend,
        screen: Screen,
        field_dva: float,
        gap_dva: float,
        arm_dva: float,
        width_dva: float,
        luminance: float,
    ) -> None:
        from psychopy import visual

        d = screen.px_per_deg
        c = to_signed(luminance)
        self._lines: list[Any] = [
            visual.Line(
                display.window,
                start=(a[0] * d, a[1] * d),
                end=(b[0] * d, b[1] * d),
                units="pix",
                lineWidth=max(1.0, width_dva * d),
                lineColor=c,
                colorSpace="rgb",
            )
            for a, b in bracket_segments(field_dva, gap_dva, arm_dva)
        ]

    def update(self, dt: float) -> None:
        pass

    def draw(self) -> None:
        for line in self._lines:
            line.draw()


def make_marks(display: DisplayBackend, screen: Screen, **kw: Any) -> Any:
    if display.kind == "simulated":
        return NullStimulus("marks")
    return IntervalMarks(display, screen, **kw)
