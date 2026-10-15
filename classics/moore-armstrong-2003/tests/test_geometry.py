"""The pure geometry: site classification, distracter placement, bar luminance."""

from __future__ import annotations

import math

import pytest

from moore_armstrong2003 import geometry as geo


def test_an_end_point_inside_the_rf_is_an_overlapping_site():
    assert geo.classify_site((-7.8, -7.8), 5.0, (-8.5, -7.0)) == "overlapping"


def test_more_than_45_degrees_away_is_non_overlapping():
    assert geo.classify_site((-7.8, -7.8), 5.0, (7.8, -7.8)) == "non-overlapping"


def test_in_between_is_refused():
    with pytest.raises(geo.SiteGeometryError):
        geo.classify_site((-7.8, -7.8), 5.0, (-12.0, -5.0))


def test_distracter_positions():
    assert geo.distracter_position("non-overlapping", (-5, -5), (5, -5)) == (5.0, -5.0)
    assert geo.distracter_position("overlapping", (-5, -4), (-5, -4)) == (5.0, 4.0)
    assert geo.distracter_position("overlapping", (-5, -4), (-5, -4), (1, 9)) == (1.0, 9.0)


def test_orientations():
    assert geo.orientation_deg("none", 30) is None
    assert geo.orientation_deg("preferred", 30) == 30
    assert geo.orientation_deg("orthogonal", 120) == 30


@pytest.mark.parametrize("c", [0.5, 0.93])
def test_a_dark_bar_has_the_michelson_contrast_asked_for(c):
    lum = geo.bar_luminance(c, "dark")
    bg = geo.BACKGROUND_LUMINANCE
    assert math.isclose((bg - lum) / (bg + lum), c)


def test_a_bright_bar_above_a_third_is_impossible_on_mid_grey():
    assert math.isclose(geo.bar_luminance(0.3, "bright"), 0.5 * 1.3 / 0.7)
    with pytest.raises(ValueError):
        geo.bar_luminance(0.5, "bright")


def test_bar_corners_follow_psychopys_orientation():
    vertical = geo.bar_corners((0, 0), 2.0, 0.2, 0.0)
    assert max(abs(y) for _, y in vertical) == pytest.approx(1.0)
    clockwise = geo.bar_corners((0, 0), 2.0, 0.0, 45.0)
    top = max(clockwise, key=lambda p: p[1])
    assert top[0] > 0  # turning clockwise tips the top to the right
