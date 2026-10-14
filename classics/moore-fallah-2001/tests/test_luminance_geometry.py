"""Photometry and geometry helpers."""

from __future__ import annotations

import math

import numpy as np
import pytest
from alhazen.errors import ConfigError

from moore_fallah2001.geometry import distractor_positions, outside_location
from moore_fallah2001.luminance import (
    Photometry,
    dimmed_luminance,
    level,
    michelson_pct,
    to_rgb,
)

PHOT = Photometry(black_cd_m2=0.5, white_cd_m2=100.5)


def test_luminance_maps_linearly_onto_signed_rgb():
    assert level(0.5, PHOT) == 0.0 and level(100.5, PHOT) == 1.0
    assert to_rgb(50.5, PHOT) == (0.0, 0.0, 0.0)


def test_a_luminance_the_display_cannot_show_is_refused():
    with pytest.raises(ConfigError, match="photometer"):
        level(0.2, PHOT)


@pytest.mark.parametrize("pct", [0.0, 10.0, 44.0, 90.0])
def test_dimming_is_a_michelson_contrast_round_trip(pct):
    assert michelson_pct(26.0, dimmed_luminance(26.0, pct)) == pytest.approx(pct)


@pytest.mark.parametrize("mf", [(10.0, -6.0), (-8.0, 5.0), (0.0, 12.0), (14.0, 0.0)])
def test_outside_is_90_degrees_away_at_the_same_eccentricity(mf):
    out = outside_location(mf, 90.0)
    assert math.hypot(*out) == pytest.approx(math.hypot(*mf))
    assert mf[0] * out[0] + mf[1] * out[1] == pytest.approx(0.0, abs=1e-9)
    if mf[0] != 0 and abs(mf[1]) > 0:
        assert math.copysign(1, out[0]) == math.copysign(1, mf[0])


def test_distractors_respect_the_exclusions():
    pts = distractor_positions(np.random.default_rng(1), 500, half_w=12, half_h=7, half_side=0.4,
                               target=(5, -3), exclusion_radius=3.5, fixation_clearance=1.5)
    assert len(pts) == 500
    for x, y in pts:
        assert math.hypot(x - 5, y + 3) > 3.5 and math.hypot(x, y) > 1.5
        assert abs(x) <= 11.6 and abs(y) <= 6.6
