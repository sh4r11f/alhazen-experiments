"""The colour arithmetic against the paper's numbers and its own definitions."""

from __future__ import annotations

import numpy as np
import pytest

from cavanagh1992.color import ColorModel, Photometry, red_luminance_share
from cavanagh1992.common import CONFIGS

PAPER_RED, PAPER_GREEN, PAPER_MEAN = (0.608, 0.348), (0.249, 0.602), (0.409, 0.488)


def model(k=1.0):
    return ColorModel(45.0, red_luminance_share(PAPER_RED, PAPER_GREEN, PAPER_MEAN), 53.0,
                      179.0, k)


def test_the_paper_phosphors_and_mean_give_a_consistent_red_share():
    share = red_luminance_share(PAPER_RED, PAPER_GREEN, PAPER_MEAN)
    assert share == pytest.approx(0.3173, abs=1e-3)
    # The mixture's y implied by that share matches the paper's 0.488 to 0.001.
    w = (0.409 - 0.249) / (0.608 - 0.249)
    assert w * 0.348 + (1 - w) * 0.602 == pytest.approx(0.488, abs=0.0015)


def test_the_mean_field_is_45_cd_m2():
    red, green = model().luminances(np.zeros(1), np.zeros(1))
    assert float(red[0] + green[0]) == pytest.approx(45.0)


def test_a_colour_modulation_at_k_1_keeps_the_summed_luminance_constant():
    s = np.linspace(-1, 1, 11)
    red, green = model(1.0).luminances(np.zeros_like(s), 0.4 * s)
    assert np.allclose(red + green, 45.0)
    assert np.allclose(red - model().red_mean, 0.4 * model().red_mean * s)


def test_k_scales_the_green_modulation_only():
    red1, green1 = model(1.0).luminances(0.0, 0.4)
    red2, green2 = model(1.5).luminances(0.0, 0.4)
    assert red1 == pytest.approx(red2)
    assert (model().green_mean - green2) == pytest.approx(1.5 * (model().green_mean - green1))


def test_a_luminance_modulation_is_michelson_contrast_on_the_sum():
    red_hi, green_hi = model().luminances(0.1, 0.0)
    red_lo, green_lo = model().luminances(-0.1, 0.0)
    hi, lo = red_hi + green_hi, red_lo + green_lo
    assert (hi - lo) / (hi + lo) == pytest.approx(0.1)


def test_a_stimulus_the_display_cannot_reach_is_refused_not_clipped():
    with pytest.raises(ValueError, match="cannot show it"):
        model().drive(np.array([0.0]), np.array([-1.2]))  # red below zero
    with pytest.raises(ValueError):
        ColorModel(45.0, 0.3173, 10.0, 179.0).check_headroom(0.4, 0.4)


def test_the_example_photometry_file_loads_and_says_it_is_not_a_measurement():
    ph = Photometry.load(CONFIGS / "photometry-booth.yaml")
    assert ph.measured is False and ph.red_max_cd_m2 > 0
