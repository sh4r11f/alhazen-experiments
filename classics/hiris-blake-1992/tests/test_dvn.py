"""The dot engine: the paper's displays, frame by frame (hirisblake1992.dvn)."""

from __future__ import annotations

import math

import numpy as np
import pytest

from hirisblake1992.dvn import DvnSpec, DynamicDotField, update_frames_for, wrap_along


def spec(fraction=0.4, direction=270.0, frames=3):
    return DvnSpec(n_dots=100, aperture_dva=3.25, step_dva=0.0957, update_frames=frames,
                   signal_fraction=fraction, signal_direction_deg=direction)


def stepped_frames(field, n):
    """(previous positions, frame) for the next n frames on which the dots moved."""
    out, prev = [], field.step().xy
    while len(out) < n:
        f = field.step()
        if f.stepped:
            out.append((prev, f))
        prev = f.xy
    return out


def test_the_paper_step_and_speed_give_a_whole_number_of_frames():
    # 5 px on the paper's monitor ~ 0.0957 deg; at ~2 deg/s that is a step every ~48 ms
    assert update_frames_for(0.0957, 2.0, 60.0) == 3
    assert update_frames_for(0.0957, 2.0, 120.0) == 6
    assert update_frames_for(0.0957, 2.0, 67.0) == 3  # the paper's 67 Hz: every third frame
    assert spec(frames=3).speed_dva_s(60.0) == pytest.approx(1.914)


def test_dots_move_only_every_update_frames():
    f = DynamicDotField(spec(frames=3), seed=1)
    flags = [f.step().stepped for _ in range(10)]
    assert flags == [False, False, False, True, False, False, True, False, False, True]


def test_exactly_the_signal_count_moves_the_signal_step_every_step():
    for fraction, n_signal in ((0.0, 0), (0.4, 40), (0.13, 13), (1.0, 100)):
        f = DynamicDotField(spec(fraction=fraction, direction=270.0), seed=2)
        for prev, frame in stepped_frames(f, 20):
            assert frame.signal.sum() == n_signal
            d = frame.xy - prev
            inside = (prev ** 2).sum(1) < (3.25 / 2 - 0.2) ** 2  # far from the edge: no wrap
            sig = frame.signal & inside
            assert np.allclose(d[sig], [0.0, -0.0957], atol=1e-12)  # straight down


def test_every_dot_moves_one_step_and_noise_directions_are_uniform():
    f = DynamicDotField(spec(fraction=0.0), seed=3)
    angles = []
    for prev, frame in stepped_frames(f, 200):
        d = frame.xy - prev
        inside = (prev ** 2).sum(1) < (3.25 / 2 - 0.2) ** 2
        assert np.allclose(np.hypot(d[inside, 0], d[inside, 1]), 0.0957)
        angles.extend(np.degrees(np.arctan2(d[inside, 1], d[inside, 0])) % 360)
    counts, _ = np.histogram(angles, bins=8, range=(0, 360))
    assert counts.min() > 0.85 * counts.mean()  # no net direction in RDVN
    mean_vec = np.mean(np.exp(1j * np.radians(angles)))
    assert abs(mean_vec) < 0.03


def test_dots_stay_inside_and_the_density_stays_uniform_under_coherent_motion():
    f = DynamicDotField(spec(fraction=1.0, direction=90.0), seed=4)
    r = 3.25 / 2
    radii = []
    ys = []
    for _ in range(3000):
        fr = f.step()
        assert ((fr.xy ** 2).sum(1) <= r * r + 1e-9).all()
        radii.extend(np.hypot(fr.xy[:, 0], fr.xy[:, 1]))
        ys.extend(fr.xy[:, 1])
    # uniform on a disc: P(radius < r/sqrt 2) = 1/2; no pile-up at the top or bottom
    assert np.mean(np.array(radii) < r / math.sqrt(2)) == pytest.approx(0.5, abs=0.03)
    assert abs(np.mean(ys)) < 0.05


def test_wrap_puts_a_dot_back_across_the_chord():
    p = np.array([[0.0, 1.70]])
    u = np.array([[0.0, 1.0]])
    q = wrap_along(p, u, 1.625)
    assert q[0] == pytest.approx([0.0, -1.625 + 0.075])


def test_a_seed_replays_the_same_display_and_the_noise_does_not_depend_on_coherence():
    a = [DynamicDotField(spec(0.4), seed=7).step().xy for _ in range(1)]
    b = [DynamicDotField(spec(0.4), seed=7).step().xy for _ in range(1)]
    assert np.array_equal(a[0], b[0])
    fa, fb = DynamicDotField(spec(0.4), 9), DynamicDotField(spec(0.4), 9)
    for _ in range(30):
        assert np.array_equal(fa.step().xy, fb.step().xy)


def test_invalid_specs_are_refused():
    with pytest.raises(ValueError):
        spec(fraction=1.2)
    with pytest.raises(ValueError):
        spec(frames=0)
