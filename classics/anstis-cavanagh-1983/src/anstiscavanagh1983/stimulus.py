"""The pixels: the four-stroke minimum-motion cycle, the two-stroke counterphase flicker,
a uniform flickering field, and the fixation mark.

Anstis & Cavanagh (1983), Fig. 1 and p. 155-157. A square-wave grating of test (A) and
reference (B) colour bars alternates with a light/dark grating of their mixture, each
grating displaced a quarter cycle (half a bar) from its predecessor, in a repeating
cycle T1..T4:

    T1  colour grating        A|B        at offset x0
    T2  luminance grating     light|dark at x0 + s*P/4
    T3  colour grating        B|A        at x0 + s*P/2   (T1 shifted half a cycle)
    T4  luminance grating     dark|light at x0 + 3*s*P/4 (T2 shifted half a cycle)

``s`` (``step``) is the direction of the quarter-cycle steps: +1 rightward on the screen,
-1 leftward. If the A bars are lighter than the B bars, A bars pair with the light bars a
quarter cycle away in direction ``s`` and the grating is seen to move in direction ``s``;
if darker, A pairs with the dark bars a quarter cycle the other way and it moves in
direction ``-s``; at equal luminance neither pairing is favoured (Fig. 1 legend). The
colour gratings alone (T1, T3) are a counterphase pair, and so are the luminance gratings
(T2, T4): neither carries a direction by itself.

The light/dark grating is the mixture of the two colours (paper: red and green raster
lines dithered within each bar; here by default their additive mean, see
``interleave_mix``), at mean luminance equal to the colour grating's mean and Michelson
luminance contrast ``interleave_contrast`` (6.25% in Experiment 1).

Everything is per-gun luminance (cd/m2) until the last step, which turns it into linear
gun levels through the photometry (color.py). Bars are vertical; x grows rightward.
Pure numpy: the psychopy stimulus, the preview and the tests all use these arrays.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal

import numpy as np

from anstiscavanagh1983.color import ColourSpace

Mix = Literal["additive", "line_dither"]
Layout = Literal["four_stroke", "counterphase", "uniform"]


def period_px(px_per_deg: float, sf_cpd: float, multiple: int = 4) -> int:
    """The grating period in whole pixels, a multiple of ``multiple`` (4: so a quarter
    cycle is a whole number of pixels and every step is exactly a quarter cycle)."""
    raw = px_per_deg / sf_cpd
    return max(multiple, multiple * int(round(raw / multiple)))


def frames_per_stroke(refresh_hz: float, cycle_hz: float, strokes: int) -> int:
    """Whole frames each grating of a ``strokes``-stroke cycle stays up so that the cycle
    repeats at ``cycle_hz`` (nearest whole number, at least one)."""
    return max(1, int(round(refresh_hz / (strokes * cycle_hz))))


@dataclass(frozen=True)
class Spec:
    """One trial's stimulus, in pixels and cd/m2."""

    layout: Layout
    test_colour: str
    reference_colour: str
    test_cd_m2: float
    reference_cd_m2: float
    size_px: int
    period_px: int = 16
    step: int = 1
    offset_px: int = 0
    interleave_contrast: float = 0.0625
    interleave_mix: Mix = "additive"
    dither_rows: int = 2
    disc: bool = False  # uniform layout: a disc of diameter size_px, else a square

    def __post_init__(self) -> None:
        if self.step not in (1, -1):
            raise ValueError("step must be +1 (rightward) or -1 (leftward)")
        if self.layout != "uniform" and self.period_px % 4:
            raise ValueError("period_px must be a multiple of 4 (whole-pixel quarter steps)")
        if not 0.0 <= self.interleave_contrast < 1.0:
            raise ValueError("interleave_contrast must be within 0..1")
        if self.dither_rows < 1:
            raise ValueError("dither_rows must be >= 1")

    @property
    def strokes(self) -> int:
        return 4 if self.layout == "four_stroke" else 2

    def with_test(self, cd_m2: float) -> Spec:
        return replace(self, test_cd_m2=float(cd_m2))


def _square(x: np.ndarray, offset: float, period: int) -> np.ndarray:
    """True on the first half-period of each cycle, starting at ``offset``."""
    return ((x - offset) % period) < (period / 2)


def stroke_luminance(spec: Spec, space: ColourSpace, k: int) -> np.ndarray:
    """Per-gun luminance (size, size, 3) of stroke ``k`` (0-based; T1 is k = 0)."""
    n = spec.size_px
    x = np.arange(n)
    a = space.gun_luminance(spec.test_colour, spec.test_cd_m2)
    b = space.gun_luminance(spec.reference_colour, spec.reference_cd_m2)
    out = np.empty((n, n, 3))
    k = k % spec.strokes
    if spec.layout == "uniform":
        out[:] = a if k == 0 else b
        return out
    P = spec.period_px
    q = P // 4
    if spec.layout == "counterphase":
        on = _square(x, spec.offset_px + k * 2 * q, P)
        out[:] = np.where(on[:, None], a, b)[None, :, :]
        return out
    offset = spec.offset_px + spec.step * k * q
    on = _square(x, offset, P)
    if k % 2 == 0:  # colour grating (T1, T3)
        out[:] = np.where(on[:, None], a, b)[None, :, :]
        return out
    c = spec.interleave_contrast
    light, dark = 1.0 + c, 1.0 - c
    if spec.interleave_mix == "additive":
        mix = 0.5 * (a + b)
        out[:] = np.where(on[:, None], light * mix, dark * mix)[None, :, :]
        return out
    # line_dither: bands of `dither_rows` rows alternate between the two colours, each
    # scaled light or dark (the paper's raster-line dither, p. 156).
    band = (np.arange(n) // spec.dither_rows) % 2 == 0
    scale = np.where(on, light, dark)[None, :, None]
    colour = np.where(band[:, None, None], a[None, None, :], b[None, None, :])
    out[:] = colour * scale
    return out


def mean_luminance(spec: Spec, space: ColourSpace) -> float:
    """Space-time mean luminance of the patch (cd/m2): the colour grating's mean, which
    the luminance grating shares."""
    return 0.5 * (spec.test_cd_m2 + spec.reference_cd_m2)


@dataclass(frozen=True)
class Fixation:
    """A white cross on a blue square (paper: "a white cross on a blue 6-min square",
    p. 157). Square side, cross span and line width in arcmin."""

    square_arcmin: float = 6.0
    cross_arcmin: float = 6.0
    line_arcmin: float = 1.0
    blue_level: float = 1.0  # linear level of the blue gun (ASSUMED full)


def fixation_mask(n: int, px_per_deg: float, fix: Fixation) -> tuple[np.ndarray, np.ndarray]:
    """(square, cross) boolean masks on an n x n patch centred on the screen centre."""
    c = (n - 1) / 2.0
    y, x = np.mgrid[0:n, 0:n]
    dx, dy = np.abs(x - c), np.abs(y - c)
    half = lambda arcmin: max(0.5, arcmin / 60.0 * px_per_deg / 2.0)  # noqa: E731
    square = (dx <= half(fix.square_arcmin)) & (dy <= half(fix.square_arcmin))
    arm, line = half(fix.cross_arcmin), half(fix.line_arcmin)
    cross = ((dx <= line) & (dy <= arm)) | ((dy <= line) & (dx <= arm))
    return square, cross


def frames(spec: Spec, space: ColourSpace, px_per_deg: float, fix: Fixation | None
           ) -> list[np.ndarray]:
    """Linear RGB (n, n, 3) of every stroke, with the fixation mark drawn on top. Outside a
    uniform disc the patch is the surround (black)."""
    out = []
    mask = None
    if fix is not None:
        mask = fixation_mask(spec.size_px, px_per_deg, fix)
    disc = None
    if spec.layout == "uniform" and spec.disc:
        n = spec.size_px
        c = (n - 1) / 2.0
        y, x = np.mgrid[0:n, 0:n]
        disc = np.hypot(x - c, y - c) <= n / 2.0
    for k in range(spec.strokes):
        rgb = space.levels(stroke_luminance(spec, space, k))
        if disc is not None:
            rgb[~disc] = 0.0
        if mask is not None:
            square, cross = mask
            rgb[square] = (0.0, 0.0, fix.blue_level)
            rgb[cross] = 1.0
        out.append(rgb)
    return out


def fixation_frame(n: int, px_per_deg: float, fix: Fixation) -> np.ndarray:
    """The fixation mark alone on the dark surround."""
    rgb = np.zeros((n, n, 3))
    square, cross = fixation_mask(n, px_per_deg, fix)
    rgb[square] = (0.0, 0.0, fix.blue_level)
    rgb[cross] = 1.0
    return rgb


def luminance_fundamental(lum_row: np.ndarray, period: int) -> complex:
    """Complex amplitude of the grating's fundamental in a 1-D luminance profile
    (cd/m2 summed over guns), phase measured rightward from pixel 0."""
    x = np.arange(lum_row.size)
    return complex(np.sum((lum_row - lum_row.mean()) * np.exp(-2j * np.pi * x / period)))


def net_luminance_motion(spec: Spec, space: ColourSpace) -> float:
    """Signed net quarter-cycle phase stepping of the luminance fundamental over one
    cycle (positive = rightward on the screen), weighted by amplitude:
    sum over k of Im(F_{k+1} conj(F_k)) with the sign chosen so a rightward step of the
    pattern counts positive. Zero when the colour gratings carry no luminance modulation.
    A first-order (luminance) motion signal, used by the tests to check the phase
    relations; not a model of the observer."""
    rows = []
    for k in range(spec.strokes):
        lum = stroke_luminance(spec, space, k)[0].sum(axis=1)  # first row, summed guns
        rows.append(luminance_fundamental(lum, spec.period_px))
    total = 0.0
    for k in range(spec.strokes):
        f0, f1 = rows[k], rows[(k + 1) % spec.strokes]
        # A pattern shifted right by d has phase -2 pi d / P: rightward = negative phase step.
        total += -(f1 * np.conj(f0)).imag
    return float(total)
