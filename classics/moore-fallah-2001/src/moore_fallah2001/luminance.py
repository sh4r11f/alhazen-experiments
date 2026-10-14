"""Luminances in cd/m², and how they become display values.

The paper states its stimuli photometrically (target and distractor 26 cd/m²
on a 1 cd/m² background, the dimming as a % Michelson contrast), so this task
keeps them in cd/m² and converts once, here. The secret this module hides is
the display model: a *linearised* display (alhazen applies the gamma that
``alhazen calibrate gamma`` stored beside the rig file), whose luminance runs
linearly from ``black_cd_m2`` at level 0 to ``white_cd_m2`` at level 1. Those
two numbers are the rig's, measured with a photometer; the values shipped in
the configs are examples and are flagged as such.
"""

from __future__ import annotations

from alhazen.config.models import Model
from alhazen.errors import ConfigError
from pydantic import model_validator


class Photometry(Model):
    """The linearised display's luminance at level 0 and level 1 (cd/m²)."""

    black_cd_m2: float
    white_cd_m2: float

    @model_validator(mode="after")
    def _ordered(self) -> Photometry:
        if not (0.0 <= self.black_cd_m2 < self.white_cd_m2):
            raise ValueError(
                f"photometry needs 0 <= black_cd_m2 < white_cd_m2, got "
                f"{self.black_cd_m2} and {self.white_cd_m2}"
            )
        return self


def level(luminance_cd_m2: float, photometry: Photometry) -> float:
    """The display level (0..1) that shows ``luminance_cd_m2``.

    Raises ConfigError for a luminance the display cannot show: a stimulus
    drawn at the nearest reachable value would silently be a different
    stimulus from the one the parameters (and the paper) state.
    """
    lo, hi = photometry.black_cd_m2, photometry.white_cd_m2
    if not lo <= luminance_cd_m2 <= hi:
        raise ConfigError(
            f"{luminance_cd_m2:g} cd/m² is outside what this display shows "
            f"({lo:g} to {hi:g} cd/m², the params' photometry block). Measure the rig "
            f"with a photometer and enter its black and white luminance there."
        )
    return (luminance_cd_m2 - lo) / (hi - lo)


def to_rgb(luminance_cd_m2: float, photometry: Photometry) -> tuple[float, float, float]:
    """An achromatic colour in PsychoPy's signed RGB (-1..1) for a luminance."""
    v = 2.0 * level(luminance_cd_m2, photometry) - 1.0
    return (v, v, v)


def dimmed_luminance(luminance_cd_m2: float, michelson_pct: float) -> float:
    """The target's luminance during the dimming ("blink").

    The paper gives the dimming magnitude as a % Michelson contrast between
    the target and its dimmed self, C = (L0 - Ld) / (L0 + Ld), so
    Ld = L0 (1 - C) / (1 + C).
    """
    if not 0.0 <= michelson_pct < 100.0:
        raise ValueError(f"a Michelson contrast in % is in [0, 100), got {michelson_pct}")
    c = michelson_pct / 100.0
    return luminance_cd_m2 * (1.0 - c) / (1.0 + c)


def michelson_pct(l_high: float, l_low: float) -> float:
    """% Michelson contrast between two luminances."""
    return 100.0 * (l_high - l_low) / (l_high + l_low)
