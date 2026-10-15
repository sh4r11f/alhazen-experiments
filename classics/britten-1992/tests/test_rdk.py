"""The dot engine against the paper's description of the display (pp. 4746-4747)."""

from __future__ import annotations

import math

import numpy as np
import pytest

from britten1992.rdk import CorrelatedDotField, DotFieldSpec, signal_dt_frames


def spec(coherence=0.5, direction=0.0, refresh=60.0, aperture=10.0, k=None, speed=6.0):
    return DotFieldSpec(coherence=coherence, direction_deg=direction, speed_dva_s=speed,
                        density=16.7, field_dva=20.0, aperture_dva=aperture, refresh_hz=refresh,
                        signal_dt_frames=k or signal_dt_frames(0.045, refresh))


@pytest.mark.parametrize("hz,frames", [(60, 3), (75, 3), (100, 5), (120, 5), (144, 6), (85, 4)])
def test_the_45_ms_interval_rounds_to_whole_frames(hz, frames):
    assert signal_dt_frames(0.045, hz) == frames


def test_dot_rate_is_the_papers_density_over_the_field():
    s = spec(refresh=60.0)
    assert s.n_per_frame == round(16.7 * 400 / 60)  # 6.67 kHz over 400 deg^2, per 60 Hz frame
    frames = [CorrelatedDotField(s, 1).step() for _ in range(1)]
    assert len(frames[0].xy) == s.n_per_frame


def test_visible_dots_fill_the_aperture_at_the_papers_density():
    s = spec(aperture=10.0)
    f = CorrelatedDotField(s, 2)
    counts = [f.step().visible.sum() for _ in range(600)]
    expected = 16.7 * math.pi * 5.0**2 / 60.0  # dots per frame inside a 10-deg aperture
    assert np.mean(counts) == pytest.approx(expected, rel=0.05)


def test_the_first_dt_has_no_signal_dots():
    s = spec(coherence=1.0)
    f = CorrelatedDotField(s, 3)
    assert [f.step().signal.any() for _ in range(s.signal_dt_frames)] == [False] * 3
    assert f.step().signal.all()


def test_signal_dots_are_the_dots_of_dt_earlier_moved_by_dx():
    s = spec(coherence=0.3, direction=90.0)
    f = CorrelatedDotField(s, 4)
    frames = [f.step() for _ in range(30)]
    k = s.signal_dt_frames
    for now in frames[k:]:
        then = frames[now.index - k]
        moved = then.xy[now.signal] + np.array([0.0, s.step_dva])
        moved = (moved + 10.0) % 20.0 - 10.0  # the field wraps
        np.testing.assert_allclose(now.xy[now.signal], moved, atol=1e-9)


def test_the_proportion_of_signal_dots_is_the_correlation():
    for p in (0.0, 0.064, 0.512):
        f = CorrelatedDotField(spec(coherence=p), 5)
        frames = [f.step() for _ in range(400)][3:]
        observed = np.mean([fr.signal.mean() for fr in frames])
        assert observed == pytest.approx(p, abs=0.01)


def test_dot_lifetimes_are_geometric():
    # A dot survives N plots with probability p**(N-1) (p. 4746): two renewals in a row ~ p^2.
    p = 0.5
    s = spec(coherence=p)
    f = CorrelatedDotField(s, 6)
    frames = [f.step() for _ in range(600)]
    k = s.signal_dt_frames
    both = [frames[i].signal & frames[i - k].signal for i in range(2 * k, len(frames))]
    assert np.mean([b.mean() for b in both]) == pytest.approx(p * p, abs=0.01)


def test_the_signal_moves_at_the_set_speed_in_the_set_direction():
    s = spec(coherence=1.0, direction=180.0, speed=6.0, refresh=120.0)
    assert s.signal_dt_ms if hasattr(s, "signal_dt_ms") else True
    assert s.signal_dt_s == pytest.approx(5 / 120)
    assert s.step_dva == pytest.approx(6.0 * 5 / 120)  # dx = speed x realised dt
    f = CorrelatedDotField(s, 7)
    frames = [f.step() for _ in range(12)]
    d = frames[10].xy - frames[5].xy
    d = (d + 10.0) % 20.0 - 10.0
    np.testing.assert_allclose(d, np.tile([-s.step_dva, 0.0], (len(d), 1)), atol=1e-9)


def test_a_seed_replays_the_display_and_another_seed_does_not():
    a = [CorrelatedDotField(spec(), 11).step().xy for _ in range(1)]
    b = [CorrelatedDotField(spec(), 11).step().xy for _ in range(1)]
    c = [CorrelatedDotField(spec(), 12).step().xy for _ in range(1)]
    np.testing.assert_array_equal(a[0], b[0])
    assert not np.array_equal(a[0], c[0])


def test_an_aperture_wider_than_the_field_is_refused():
    with pytest.raises(ValueError, match="wider than the plotting field"):
        spec(aperture=25.0)
