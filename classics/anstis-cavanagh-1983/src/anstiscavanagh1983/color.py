"""Colours as per-gun luminances, and the display's photometry that turns them into
linear gun levels.

Anstis & Cavanagh (1983, p. 157) specify their stimuli in cd/m2 measured with a
photometer on a P22-phosphor colour TV: red bars of a chosen luminance, green bars
held at 13.4 cd/m2, and so on. Here a colour is a fixed split of luminance across the
display's three guns (its *shares*, summing to 1), and a bar of that colour at L cd/m2
asks each gun for ``share * L``. The photometry file says how many cd/m2 each gun gives
at full drive, which turns those luminances into linear drive levels 0..1.

What this does NOT give you:

- **Linear levels are only right on a linearised display.** Turning a linear level into
  a code value is the display's gamma, which the rig applies (`alhazen calibrate gamma`).
- **cd/m2 are only physical when the photometry file is measured** (``measured: true``:
  each gun alone at full drive, read with a photometer through the rig's gamma
  correction). The example file ``configs/photometry-booth.yaml`` holds an sRGB panel's
  nominal values, not a measurement; numbers computed from it are device-specific
  demonstration values.
- **Photometric cd/m2 are not equiluminance.** A photometer weights light by the CIE
  V(lambda) standard observer. The point of the minimum-motion method is that each
  observer's own luminance match differs from it (the paper's two observers matched red
  to 13.4 cd/m2 green at 9.54 and 10.47 cd/m2, p. 157). A setting made here holds for
  this observer, these phosphors, this stimulus (spatial frequency matters, Fig. 3) and
  this display, nothing wider.
- **Chromaticities are the display's.** The paper's red, green and blue are P22
  phosphors (p. 157); a modern panel's primaries differ, so a "red" bar here is the
  display's red primary, not the paper's chromaticity.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import yaml
from alhazen import Model
from pydantic import Field

GUNS = ("red", "green", "blue")
COLOURS = ("red", "green", "blue", "yellow", "grey")

# The paper's chromaticities (p. 157): P22 red and green, and the yellow of the
# blue/yellow grating. The yellow lies on the red-green line (at x = 0.51 the line
# through red and green has y = 0.439; the paper gives 0.44), so it is a mixture of the
# red and green phosphors, and its red share follows from the chromaticities.
P22_RED_XY = (0.68, 0.32)
P22_GREEN_XY = (0.28, 0.60)
PAPER_YELLOW_XY = (0.51, 0.44)


def red_luminance_share(red_xy, green_xy, mix_xy) -> float:
    """The red primary's share of the luminance of a red+green mixture at ``mix_xy``.

    Additive mixing in CIE xy: a primary contributes X+Y+Z = Y/y, and the mixture's x is
    the (X+Y+Z)-weighted mean of the primaries' x. Solved for the red weight from x, then
    turned into a luminance share. Paper yellow from P22 red and green: 0.419.
    """
    (xr, yr), (xg, yg), (xm, _) = red_xy, green_xy, mix_xy
    if not min(xr, xg) < xm < max(xr, xg):
        raise ValueError(f"mixture x {xm} is not between the primaries' x ({xr}, {xg})")
    w = (xm - xg) / (xr - xg)
    lr, lg = w * yr, (1.0 - w) * yg
    return lr / (lr + lg)


PAPER_YELLOW_RED_SHARE = red_luminance_share(P22_RED_XY, P22_GREEN_XY, PAPER_YELLOW_XY)


class Photometry(Model):
    """Each gun's luminance at full drive, alone, through the rig's gamma correction.

    Rig-specific, so it lives in its own file named by the params' ``photometry_file``.
    ``measured: false`` marks example values: sessions run with them are labelled
    device-specific demonstrations, and a real-data session in ``calibrated`` mode is
    refused (common.py).
    """

    red_max_cd_m2: float = Field(gt=0)
    green_max_cd_m2: float = Field(gt=0)
    blue_max_cd_m2: float = Field(gt=0)
    measured: bool = False

    @classmethod
    def load(cls, path: Path) -> Photometry:
        if not path.is_file():
            raise FileNotFoundError(
                f"photometry file {path} does not exist; copy configs/photometry-booth.yaml, "
                f"measure each gun's maximum luminance and name the copy in photometry_file")
        return cls.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))

    @property
    def max_cd_m2(self) -> np.ndarray:
        return np.array([self.red_max_cd_m2, self.green_max_cd_m2, self.blue_max_cd_m2])


@dataclass(frozen=True)
class ColourSpace:
    """Named colours as gun shares, and per-gun luminance to linear levels."""

    photometry: Photometry
    yellow_red_share: float = PAPER_YELLOW_RED_SHARE

    def shares(self, colour: str) -> np.ndarray:
        """Per-gun luminance shares (sum 1). ``grey`` is the display's own white
        (all three guns at equal drive), i.e. the white point of the panel, not the
        paper's x = 0.30, y = 0.30 (p. 159)."""
        if colour == "red":
            return np.array([1.0, 0.0, 0.0])
        if colour == "green":
            return np.array([0.0, 1.0, 0.0])
        if colour == "blue":
            return np.array([0.0, 0.0, 1.0])
        if colour == "yellow":
            s = self.yellow_red_share
            return np.array([s, 1.0 - s, 0.0])
        if colour == "grey":
            m = self.photometry.max_cd_m2
            return m / m.sum()
        raise ValueError(f"unknown colour {colour!r}; one of {COLOURS}")

    def gun_luminance(self, colour: str, cd_m2: float) -> np.ndarray:
        return self.shares(colour) * float(cd_m2)

    def levels(self, gun_cd_m2: np.ndarray) -> np.ndarray:
        """Linear drive levels 0..1 for per-gun luminances (..., 3). Raises when a gun
        would need to go outside 0..1, rather than clipping a stimulus silently."""
        lv = np.asarray(gun_cd_m2, dtype=float) / self.photometry.max_cd_m2
        lo, hi = float(lv.min(initial=0.0)), float(lv.max(initial=0.0))
        if lo < -1e-9 or hi > 1.0 + 1e-9:
            raise ValueError(
                f"the stimulus needs gun levels from {lo:.3f} to {hi:.3f} (allowed 0..1): "
                f"this display cannot show it; lower the luminances or contrast, or use a "
                f"brighter display")
        return np.clip(lv, 0.0, 1.0)

    def max_cd_m2(self, colour: str) -> float:
        """The most luminance a bar of ``colour`` can have on this display."""
        s = self.shares(colour)
        m = self.photometry.max_cd_m2
        return float(min(m[i] / s[i] for i in range(3) if s[i] > 0))
