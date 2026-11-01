"""The grating's numbers: contrast definition, waveform, sampling, quantisation, realised values."""

from __future__ import annotations

import math

import numpy as np
import pytest

from campbell_robson1968.grating import (
    GratingSpec,
    code_step_contrast,
    field_px,
    measure,
    profile,
    quantise,
    render,
    sampling_problem,
)

PPD = 36.0


def test_michelson_contrast_of_the_intended_profile():
    spec = GratingSpec(sf_cpd=1.0, contrast=0.4, field_dva=4.0, mean=0.5)
    img = profile(spec, PPD)
    lmax, lmin = img.max(), img.min()
    assert (lmax - lmin) / (lmax + lmin) == pytest.approx(0.4, abs=2e-3)
    # the paper's form, (Lmax - Lmin) / (2 L mean), is the same number
    assert (lmax - lmin) / (2 * img.mean()) == pytest.approx(0.4, abs=5e-3)


def test_sine_is_sinusoidal_not_square():
    spec = GratingSpec(sf_cpd=1.0, contrast=0.5, field_dva=4.0)
    row = profile(spec, PPD)[0]
    assert len(np.unique(np.round(row, 6))) > 10  # many grey levels, not two
    # the profile matches mean * (1 + c cos) exactly at every pixel centre
    n = field_px(4.0, PPD)
    x = (np.arange(n) - (n - 1) / 2) / PPD
    np.testing.assert_allclose(row, 0.5 * (1 + 0.5 * np.cos(2 * math.pi * x)), atol=1e-12)


def test_square_wave_has_two_levels_and_fundamental_4_over_pi():
    spec = GratingSpec(sf_cpd=1.0, contrast=0.3, field_dva=8.0, waveform="square", phase_deg=10)
    img, r = render(spec, PPD, bits=16)
    assert len(np.unique(np.round(img[0], 4))) <= 3
    assert r.contrast == pytest.approx(0.3, abs=2e-3)
    assert r.fundamental_contrast == pytest.approx(0.3 * 4 / math.pi, rel=0.02)


def test_stripes_are_vertical_and_vary_along_x():
    img = profile(GratingSpec(sf_cpd=2.0, contrast=0.5, field_dva=2.0), PPD)
    assert np.allclose(img, img[0][None, :])  # every row the same: vertical stripes
    hor = profile(GratingSpec(sf_cpd=2.0, contrast=0.5, field_dva=2.0, orientation_deg=90), PPD)
    assert np.allclose(hor, hor[:, :1])


def test_phase_zero_puts_a_bright_stripe_at_the_centre():
    img = profile(GratingSpec(sf_cpd=0.5, contrast=0.5, field_dva=4.0), PPD)
    centre = img[0, img.shape[1] // 2 - 1 : img.shape[1] // 2 + 1].mean()
    assert centre == pytest.approx(img.max(), abs=1e-3)


def test_field_is_even_pixels_and_spans_the_field():
    assert field_px(10.0, 36.04) == 360
    assert field_px(2.0, 94.8) % 2 == 0


def test_rounding_loses_contrast_below_one_code_step_and_dithering_keeps_it():
    step = code_step_contrast(128 / 255, 8)
    assert step == pytest.approx(1 / 128, rel=1e-6)
    spec = GratingSpec(sf_cpd=2.0, contrast=0.003, field_dva=10.0, mean=128 / 255)
    _, flat = render(spec, PPD, bits=8, dither="none")
    assert flat.n_codes == 1 and abs(flat.contrast) < 1e-9
    _, noisy = render(spec, PPD, bits=8, dither="noisy-bit", rng=np.random.default_rng(1))
    assert noisy.contrast == pytest.approx(0.003, rel=0.1)


def test_noisy_bit_is_unbiased_per_pixel():
    v = np.full((200, 200), 0.3001)
    q = quantise(v, 8, "noisy-bit", np.random.default_rng(0))
    assert q.mean() == pytest.approx(0.3001, abs=2e-4)
    with pytest.raises(ValueError):
        quantise(v, 8, "noisy-bit", None)


def test_realised_matches_requested_at_ordinary_contrast():
    spec = GratingSpec(sf_cpd=4.0, contrast=0.05, field_dva=10.0, mean=128 / 255, phase_deg=33)
    img, r = render(spec, PPD, bits=8, dither="noisy-bit", rng=np.random.default_rng(3))
    assert r.contrast == pytest.approx(0.05, rel=0.02)
    assert r.px_per_cycle == pytest.approx(9.0)
    assert r.field_px == 360 and r.mean == pytest.approx(128 / 255, abs=1e-3)
    assert measure(img, spec, PPD).contrast == r.contrast


def test_sampling_limits():
    assert sampling_problem(8.0, 36.04, "sine", 4, 12) is None
    msg = sampling_problem(16.0, 36.04, "sine", 4, 12)
    assert msg and "2.25 px per cycle" in msg
    assert sampling_problem(3.0, 36.04, "square", 4, 12) is None
    assert sampling_problem(4.0, 36.04, "square", 4, 12)


def test_out_of_range_contrast_is_refused():
    with pytest.raises(ValueError):
        GratingSpec(sf_cpd=1.0, contrast=1.2, field_dva=2.0)
    with pytest.raises(ValueError):
        GratingSpec(sf_cpd=1.0, contrast=0.9, field_dva=2.0, mean=0.6)
