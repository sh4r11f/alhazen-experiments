"""The colour arithmetic: luminance and colour modulation to red and green gun levels.

Cavanagh (1992, Fig. 1 legend, p. 1564) built both gratings from the red and green
phosphors of a CRT: the luminance grating modulated the two phosphors IN phase about a
mean of 45 cd/m2, the colour grating modulated them OUT of phase. This module is the one
place that arithmetic lives, so the tasks, the preview, the movie and the tests all draw
the same colours.

Units. Everything here is luminance (cd/m2) per gun, then the gun's linear drive level,
the fraction of that gun's maximum luminance (0..1). Turning a linear level into a code
value is the display's gamma, which the rig applies (`alhazen calibrate gamma`): these
stimuli are only right on a linearised display.

- **Luminance contrast** ``l`` (Michelson, signed): both guns scaled by ``1 + l*s``, so
  the summed luminance swings by ``l`` around the mean.
- **Colour contrast** ``c`` (signed, 0..1): the red gun's luminance swings by
  ``c * Yr0`` and the green gun's by ``-k * c * Yr0``. ``c = 1`` takes the red gun to
  zero at the green bars, the most the red phosphor allows around this mean, which is how
  "40% of the maximum available contrast between the red and green phosphors" (p. 1563)
  is read here (ASSUMED reading, docs/methods.md).
- **k**, the green-to-red luminance modulation ratio: 1.0 is photometric equiluminance
  for the measured gun luminances; the observer's own value comes from the equiluminance
  task (minimum apparent speed, as the paper did, or flicker photometry).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import yaml
from alhazen import Model
from pydantic import Field, model_validator


def red_luminance_share(
    red_xy: tuple[float, float], green_xy: tuple[float, float], mean_xy: tuple[float, float]
) -> float:
    """The red phosphor's share of the mean luminance that mixes ``mean_xy``.

    Additive mixing in CIE xy: each primary contributes X+Y+Z = Y/y, and the mixture's x
    is the (X+Y+Z)-weighted mean of the primaries' x. Solved for the red weight from x,
    then turned into a luminance share. With the paper's phosphors (0.608, 0.348) and
    (0.249, 0.602) and its yellow mean (0.409, 0.488) the red phosphor gave 31.7% of the
    45 cd/m2 (14.3 cd/m2) and the green 68.3% (30.7 cd/m2). The mean's y is then implied;
    it comes to 0.489 against the paper's 0.488, so the three numbers agree.
    """
    (xr, yr), (xg, yg), (xm, _) = red_xy, green_xy, mean_xy
    if not min(xr, xg) < xm < max(xr, xg):
        raise ValueError(f"mean x {xm} is not between the primaries' x ({xr}, {xg})")
    weight_red = (xm - xg) / (xr - xg)  # share of X+Y+Z
    lum_red, lum_green = weight_red * yr, (1.0 - weight_red) * yg
    return lum_red / (lum_red + lum_green)


class Photometry(Model):
    """What one display's red and green guns reach, measured with a photometer.

    Rig-specific, so it lives in its own file (configs/photometry-<rig>.yaml), named by
    the task params' ``photometry_file``. The example file's numbers are an sRGB panel's
    at 250 cd/m2 white, NOT a measurement: measure each gun at full drive, alone, with the
    rig's gamma correction applied, and enter the readings before a real session.
    """

    red_max_cd_m2: float = Field(gt=0)
    green_max_cd_m2: float = Field(gt=0)
    measured: bool = False

    @classmethod
    def load(cls, path: Path) -> Photometry:
        if not path.is_file():
            raise FileNotFoundError(
                f"photometry file {path} does not exist; copy configs/photometry-booth.yaml, "
                f"measure each gun's maximum luminance and name the copy in photometry_file"
            )
        return cls.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


@dataclass(frozen=True)
class ColorModel:
    """Luminance terms in, linear gun levels out. Immutable: build one per trial."""

    mean_cd_m2: float
    red_share: float
    red_max_cd_m2: float
    green_max_cd_m2: float
    k: float = 1.0

    @property
    def red_mean(self) -> float:
        return self.mean_cd_m2 * self.red_share

    @property
    def green_mean(self) -> float:
        return self.mean_cd_m2 * (1.0 - self.red_share)

    def luminances(self, lum: np.ndarray, col: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Per-gun luminance (cd/m2) for summed luminance terms ``lum`` and colour terms
        ``col`` (each already contrast x waveform, broadcastable)."""
        lum = np.asarray(lum, dtype=float)
        col = np.asarray(col, dtype=float)
        red = self.red_mean * (1.0 + lum) + self.red_mean * col
        green = self.green_mean * (1.0 + lum) - self.k * self.red_mean * col
        return red, green

    def drive(self, lum: np.ndarray, col: np.ndarray) -> np.ndarray:
        """Linear RGB levels (..., 3) in 0..1; blue is off. Raises when a gun would have
        to go below zero or above its maximum, rather than clipping a stimulus silently."""
        red, green = self.luminances(lum, col)
        r = red / self.red_max_cd_m2
        g = green / self.green_max_cd_m2
        lo = min(r.min(initial=0.0), g.min(initial=0.0))
        hi = max(r.max(initial=0.0), g.max(initial=0.0))
        if lo < -1e-9 or hi > 1.0 + 1e-9:
            raise ValueError(
                f"the stimulus needs gun levels from {lo:.3f} to {hi:.3f} (allowed 0..1): this "
                f"display cannot show it at {self.mean_cd_m2} cd/m2; lower the contrasts or the "
                f"mean luminance, or use a brighter display"
            )
        out = np.zeros(np.broadcast(r, g).shape + (3,))
        out[..., 0] = r
        out[..., 1] = g
        return out

    def mean_rgb(self) -> tuple[float, float, float]:
        rgb = self.drive(np.zeros(1), np.zeros(1))[0]
        return (float(rgb[0]), float(rgb[1]), float(rgb[2]))

    def check_headroom(self, max_lum: float, max_col: float) -> None:
        """Refuse, at load, contrasts this display cannot reach: the extremes of
        ``|lum| <= max_lum`` and ``|col| <= max_col`` in every sign combination."""
        corners = np.array([[a * max_lum, b * max_col] for a in (-1, 1) for b in (-1, 1)])
        self.drive(corners[:, 0], corners[:, 1])


def to_psychopy(rgb01: np.ndarray) -> np.ndarray:
    """0..1 linear levels to psychopy's signed -1..1 rgb."""
    return 2.0 * np.asarray(rgb01, dtype=float) - 1.0


class EquiluminanceChoice(Model):
    """Where a session's k (green-to-red modulation ratio) comes from.

    - ``calibration``: the subject's own settings, read from their most recent run of the
      task named by ``method`` (equiluminance-speed, the paper's minimum-apparent-speed
      criterion; or flicker-photometry). A real session with none is refused.
    - ``fixed``: ``green_red_ratio`` as written.
    - ``photometric``: 1.0, equal luminance by the photometer (V(lambda)), no observer.

    ``green_red_ratio`` and ``basis`` are filled in by the task's params hook, so the
    session's params (and its config snapshot) record the value used and where it came
    from.
    """

    source: str = "calibration"
    method: str = "equiluminance-speed"
    green_red_ratio: float | None = None
    basis: str | None = None

    @model_validator(mode="after")
    def _valid(self) -> EquiluminanceChoice:
        if self.source not in ("calibration", "fixed", "photometric"):
            raise ValueError("equiluminance.source must be calibration, fixed or photometric")
        if self.method not in ("equiluminance-speed", "flicker-photometry"):
            raise ValueError(
                "equiluminance.method must be equiluminance-speed or flicker-photometry")
        if self.source == "fixed" and self.green_red_ratio is None:
            raise ValueError("equiluminance.source fixed needs green_red_ratio")
        if self.green_red_ratio is not None and not 0.2 <= self.green_red_ratio <= 5.0:
            raise ValueError("equiluminance.green_red_ratio must be within 0.2..5")
        return self
