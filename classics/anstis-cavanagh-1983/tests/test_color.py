"""Colours, shares and photometry."""

from __future__ import annotations

import numpy as np
import pytest

from anstiscavanagh1983.color import (
    P22_GREEN_XY,
    P22_RED_XY,
    PAPER_YELLOW_RED_SHARE,
    PAPER_YELLOW_XY,
    ColourSpace,
    Photometry,
)

PH = Photometry(red_max_cd_m2=60.0, green_max_cd_m2=200.0, blue_max_cd_m2=20.0)


def test_the_papers_yellow_lies_on_the_red_green_line_and_is_42_percent_red():
    (xr, yr), (xg, yg), (xm, ym) = P22_RED_XY, P22_GREEN_XY, PAPER_YELLOW_XY
    y_on_line = yr + (xm - xr) * (yg - yr) / (xg - xr)
    assert y_on_line == pytest.approx(ym, abs=0.002)
    assert PAPER_YELLOW_RED_SHARE == pytest.approx(0.419, abs=0.001)


def test_shares_sum_to_one_and_grey_is_the_display_white():
    space = ColourSpace(PH)
    for c in ("red", "green", "blue", "yellow", "grey"):
        assert space.shares(c).sum() == pytest.approx(1.0)
    grey = space.levels(space.gun_luminance("grey", 140.0))
    assert np.allclose(grey, grey[0])  # equal drive on all guns


def test_levels_refuse_what_the_display_cannot_show():
    space = ColourSpace(PH)
    assert space.levels(space.gun_luminance("red", 30.0))[0] == pytest.approx(0.5)
    with pytest.raises(ValueError):
        space.levels(space.gun_luminance("blue", 25.0))
    assert space.max_cd_m2("blue") == pytest.approx(20.0)
