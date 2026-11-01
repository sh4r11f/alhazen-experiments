"""The grating itself, as numbers: pure numpy, no renderer, so every value a session
logs can be recomputed and tested without a window.

Definitions (Campbell & Robson, 1968, p. 551 footnote and Fig. 1):

- **Contrast** m = (Lmax - Lmin) / (Lmax + Lmin), Michelson's definition, which the
  paper writes as (Lmax - Lmin) / (2 L), L the space-average luminance. The two are
  the same thing for a grating modulated symmetrically about its mean. Contrast is a
  pure number between 0 and 1 (often written as a percentage).
- **Contrast sensitivity** = 1 / threshold contrast.
- **Spatial frequency** = cycles per degree of visual angle (c/deg): the reciprocal of
  the angle one complete cycle subtends at the eye. On a display it becomes cycles per
  pixel = sf / px_per_deg, so the same file is a different stimulus at a different
  viewing distance. That is why the geometry check below runs on the rig's own scale.

Luminance here is in **linearised display units**: 0 is the darkest and 1 the brightest
the display can show, after the rig's gamma correction (``alhazen calibrate gamma``).
They are not cd/m2; only a photometer measurement turns them into that.

The luminance profile is L(x) = mean * (1 + m * w(2 pi f x + phase)), with w the unit
waveform (sine, or a square wave of the same period), varying along the wave vector
(perpendicular to the stripes). The drawn image is that profile sampled at the centre
of every pixel and quantised to the display's code values; what was actually drawn is
measured back from the image (``measure``) and logged next to what was asked for.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

import numpy as np

Waveform = Literal["sine", "square"]
Dither = Literal["none", "noisy-bit"]


@dataclass(frozen=True)
class GratingSpec:
    sf_cpd: float  # spatial frequency, cycles per degree
    contrast: float  # Michelson contrast asked for, 0..1
    field_dva: float  # side of the square field, degrees
    mean: float = 0.5  # mean luminance, linearised display units 0..1
    phase_deg: float = 0.0  # carrier phase at the field centre (cosine convention)
    orientation_deg: float = 0.0  # wave vector, deg counter-clockwise from +x; 0 = vertical stripes
    waveform: Waveform = "sine"

    def __post_init__(self) -> None:
        if not (self.sf_cpd > 0 and math.isfinite(self.sf_cpd)):
            raise ValueError(f"sf_cpd must be positive, got {self.sf_cpd}")
        if not 0.0 <= self.contrast <= 1.0:
            raise ValueError(f"contrast must be within 0..1, got {self.contrast}")
        if not 0.0 < self.mean < 1.0:
            raise ValueError(f"mean must be within (0, 1), got {self.mean}")
        if self.mean * (1 + self.contrast) > 1.0 + 1e-12:
            raise ValueError(
                f"contrast {self.contrast} at mean {self.mean} needs luminance above the "
                f"display's maximum: lower the mean or the contrast"
            )
        if self.field_dva <= 0:
            raise ValueError("field_dva must be positive")
        if self.waveform not in ("sine", "square"):
            raise ValueError(f"waveform must be sine or square, got {self.waveform!r}")


def unit_wave(theta: np.ndarray, waveform: Waveform) -> np.ndarray:
    """cos for a sine grating; for a square wave +1 where cos > 0, -1 where < 0 (0 on edges)."""
    c = np.cos(theta)
    return c if waveform == "sine" else np.sign(c)


def field_px(field_dva: float, px_per_deg: float) -> int:
    """Pixels per side of the square field: the nearest EVEN number (at least 2), so a
    field centred on a window of even width and height sits exactly on the pixel grid
    and the renderer does not resample it."""
    return max(2, 2 * int(round(field_dva * px_per_deg / 2.0)))


def coordinates(n: int, px_per_deg: float) -> np.ndarray:
    """Pixel-centre coordinates (deg) of an n-pixel side, centred on the field centre."""
    return (np.arange(n) - (n - 1) / 2.0) / px_per_deg


def profile(spec: GratingSpec, px_per_deg: float) -> np.ndarray:
    """The intended luminance image (n x n, rows top to bottom, y up), before quantisation."""
    n = field_px(spec.field_dva, px_per_deg)
    x = coordinates(n, px_per_deg)
    y = x[::-1]
    xx, yy = np.meshgrid(x, y)
    ori = math.radians(spec.orientation_deg)
    u = xx * math.cos(ori) + yy * math.sin(ori)  # position along the wave vector
    theta = 2 * math.pi * spec.sf_cpd * u + math.radians(spec.phase_deg)
    return spec.mean * (1.0 + spec.contrast * unit_wave(theta, spec.waveform))


def quantise(
    lum: np.ndarray, bits: int, dither: Dither, rng: np.random.Generator | None
) -> np.ndarray:
    """Code values the display receives, as fractions k / (2**bits - 1).

    ``none`` rounds to the nearest code. ``noisy-bit`` (Allard & Faubert, 2008) adds
    uniform noise of one code step before truncating, so each pixel's EXPECTED
    luminance equals the asked-for value and contrasts below one code step stay
    represented on average, at the cost of a static luminance noise of about 0.29
    code steps (SD) per pixel. Neither makes an 8-bit display a 10-bit one.
    """
    if bits < 1:
        raise ValueError("bits must be >= 1")
    levels = float(2**bits - 1)
    v = np.clip(lum, 0.0, 1.0) * levels
    if dither == "none":
        q = np.rint(v)
    elif dither == "noisy-bit":
        if rng is None:
            raise ValueError("noisy-bit dithering needs an rng (reproducible noise)")
        q = np.floor(v + rng.random(v.shape))
    else:
        raise ValueError(f"dither must be none or noisy-bit, got {dither!r}")
    return np.clip(q, 0.0, levels) / levels


@dataclass(frozen=True)
class Realised:
    """What the drawn image contains, measured back from its pixels."""

    contrast: float  # least-squares contrast of the asked-for waveform fitted to the drawn profile
    fundamental_contrast: (
        float  # amplitude of the drawn profile's sinusoid at sf_cpd, over its mean
    )
    mean: float  # mean of the drawn field
    px_per_cycle: float
    n_codes: int  # distinct code values in the field
    field_px: int

    def as_record(self, prefix: str = "") -> dict[str, float | int]:
        return {
            f"{prefix}contrast_realised": self.contrast,
            f"{prefix}fundamental_contrast_realised": self.fundamental_contrast,
            f"{prefix}mean_realised": self.mean,
            f"{prefix}px_per_cycle": self.px_per_cycle,
            f"{prefix}n_codes": self.n_codes,
            f"{prefix}field_px": self.field_px,
        }


def measure(image: np.ndarray, spec: GratingSpec, px_per_deg: float) -> Realised:
    """Fit the drawn image back. Along the wave vector the image is averaged over the
    other axis (which also averages out most of the dither noise), then:

    - contrast: L ~ a + b w(theta) by least squares, contrast = b / a; for a sine grating
      this is the Michelson contrast of the best-fitting sinusoid;
    - fundamental: L ~ a + c cos(theta) + s sin(theta), amplitude sqrt(c^2+s^2) / a; for a
      square wave of contrast m it is 4 m / pi (the paper's p. 555).

    Only vertical (0 deg) and horizontal (90 deg) stripes are measured this way; other
    orientations raise, since averaging along a pixel axis would not follow the stripes.
    """
    n = image.shape[0]
    x = coordinates(n, px_per_deg)
    ori = spec.orientation_deg % 180.0
    if math.isclose(ori, 0.0, abs_tol=1e-9):
        prof, u = image.mean(axis=0), x
    elif math.isclose(ori, 90.0, abs_tol=1e-9):
        prof, u = image.mean(axis=1)[::-1], x
    else:
        raise ValueError("measure() handles vertical or horizontal stripes only")
    if spec.orientation_deg % 360.0 >= 180.0:
        u = -u
    theta = 2 * math.pi * spec.sf_cpd * u + math.radians(spec.phase_deg)
    w = unit_wave(theta, spec.waveform)
    a, b = np.linalg.lstsq(np.column_stack([np.ones_like(w), w]), prof, rcond=None)[0]
    a2, c, s = np.linalg.lstsq(
        np.column_stack([np.ones_like(theta), np.cos(theta), np.sin(theta)]), prof, rcond=None
    )[0]
    return Realised(
        contrast=float(b / a),
        fundamental_contrast=float(math.hypot(c, s) / a2),
        mean=float(image.mean()),
        px_per_cycle=float(px_per_deg / spec.sf_cpd),
        n_codes=int(np.unique(image).size),
        field_px=int(n),
    )


def render(
    spec: GratingSpec,
    px_per_deg: float,
    *,
    bits: int = 8,
    dither: Dither = "none",
    rng: np.random.Generator | None = None,
) -> tuple[np.ndarray, Realised]:
    """The image the display gets (linearised code fractions, n x n, top row first) and
    what it measures back to."""
    image = quantise(profile(spec, px_per_deg), bits, dither, rng)
    return image, measure(image, spec, px_per_deg)


def code_step_contrast(mean: float, bits: int) -> float:
    """The smallest nonzero contrast a sine grating gets without dithering: one code
    step of amplitude about the mean."""
    return (1.0 / (2**bits - 1)) / mean


def sampling_problem(
    sf_cpd: float,
    px_per_deg: float,
    waveform: Waveform,
    min_px_per_cycle: float,
    square_min_px_per_cycle: float,
) -> str | None:
    """Why this display cannot draw this grating faithfully, or None.

    Nyquist: a pixel grid represents frequencies below half a cycle per pixel. A
    sinusoid near that limit is drawn with an amplitude and shape that depend on its
    phase relative to the pixels, so the task asks for at least ``min_px_per_cycle``.
    A square wave is a sum of odd harmonics (3f, 5f, ...); at fewer than
    ``square_min_px_per_cycle`` pixels per cycle its third harmonic is already near
    the display's own limit, and what reaches the eye is the display's filtering,
    not the paper's square wave.
    """
    ppc = px_per_deg / sf_cpd
    need = square_min_px_per_cycle if waveform == "square" else min_px_per_cycle
    if ppc < need:
        return (
            f"{sf_cpd:g} c/deg is {ppc:.2f} px per cycle at {px_per_deg:.1f} px/deg; a "
            f"{waveform} grating here needs at least {need:g} (so at most "
            f"{px_per_deg / need:.2f} c/deg on this rig, or a viewing distance of at "
            f"least {need * sf_cpd / px_per_deg:.2f} times the rig's)"
        )
    return None
