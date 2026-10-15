"""The double-drift geometry rule, checked on the luminance the stimulus is drawn from:

- the stripes run ALONG the physical path (the grating has the path's orientation);
- the internal drift is perpendicular to the stripes, so perpendicular to the path;
- the drift reverses at every path reversal, with the pairing that makes the path look
  closer to vertical (paper: right tilt -> drift left while moving up, right while moving
  down; the other way for left tilt).
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from lisi_cavanagh2015.geometry import (
    Trajectory,
    fixation_offset_times,
    path_vectors,
    recovered_angle_deg,
)
from lisi_cavanagh2015.stimuli import SimulatedDoubleDrift

ANGLES = [-60.0, -45.0, -10.0, 0.0, 20.0, 49.0, 70.0]


def traj(angle=49.0, side="right", start=1, motion=True, sigma=0.1, phase0=0.13):
    return Trajectory(angle_deg=angle, side=side, internal_motion=motion, start_direction=start,
                      sigma_dva=sigma, phase0_cycles=phase0)


def carrier(tr, x, y, t):
    """The luminance with the envelope divided out: the grating alone."""
    wide = Trajectory(**{**tr.__dict__, "sigma_dva": 1e6})
    return wide.luminance(x, y, t)


@pytest.mark.parametrize("angle", ANGLES)
@pytest.mark.parametrize("side", ["left", "right"])
def test_the_stripes_run_along_the_path(angle, side):
    tr = traj(angle, side)
    u, n = path_vectors(angle)
    rng = np.random.default_rng(1)
    pts = np.asarray(tr.center) + rng.uniform(-0.5, 0.5, size=(200, 2))
    for t in (0.0, 0.4, 1.9):
        base = carrier(tr, pts[:, 0], pts[:, 1], t)
        # Constant along u: moving along the path never crosses a stripe...
        along = carrier(tr, pts[:, 0] + 0.37 * u[0], pts[:, 1] + 0.37 * u[1], t)
        assert np.allclose(base, along, atol=1e-9)
        # ...and the luminance varies across it, at the grating's spatial frequency.
        period = 1.0 / tr.sf_cpd
        across = carrier(tr, pts[:, 0] + period * n[0], pts[:, 1] + period * n[1], t)
        assert np.allclose(base, across, atol=1e-9)
        half = carrier(tr, pts[:, 0] + period / 2 * n[0], pts[:, 1] + period / 2 * n[1], t)
        assert np.allclose(base, -half, atol=1e-9)


@pytest.mark.parametrize("angle", ANGLES)
@pytest.mark.parametrize("side", ["left", "right"])
@pytest.mark.parametrize("start", [1, -1])
def test_the_drift_is_perpendicular_to_the_path_at_tf_over_sf(angle, side, start):
    tr = traj(angle, side, start)
    u, n = path_vectors(angle)
    rng = np.random.default_rng(2)
    pts = np.asarray(tr.center) + rng.uniform(-0.4, 0.4, size=(100, 2))
    speed = tr.tf_hz / tr.sf_cpd
    dt = 0.01
    for t in (0.2, 0.9, 1.6, 2.4):  # away from the reversals
        s = int(tr.drift_sign(t))
        assert s in (-1, 1)
        shift = s * speed * dt
        before = carrier(tr, pts[:, 0], pts[:, 1], t)
        # The pattern a moment later is the same pattern moved along n by the drift.
        after = carrier(tr, pts[:, 0] + shift * n[0], pts[:, 1] + shift * n[1], t + dt)
        assert np.allclose(before, after, atol=1e-9)
        # Moving it along the path instead does not reproduce it: the drift is across.
        wrong = carrier(tr, pts[:, 0] + shift * u[0], pts[:, 1] + shift * u[1], t + dt)
        assert not np.allclose(before, wrong, atol=1e-3)


@pytest.mark.parametrize("side", ["left", "right"])
@pytest.mark.parametrize("start", [1, -1])
def test_the_drift_reverses_on_each_pass_with_the_paper_s_pairing(side, start):
    tr = traj(49.0 if side == "right" else -52.0, side, start)
    ts = np.linspace(0.0, 3 * tr.cycle_s, 3001)
    d = tr.direction(ts)
    s = tr.drift_sign(ts)
    # Moving up the path: drift to the left (-n) for the right-tilt stimulus, to the right
    # for the left-tilt one; moving down, the other way.
    sign = 1 if side == "right" else -1
    assert np.all(s == -sign * d)
    # It flips exactly where the envelope reverses, and nowhere else.
    flips_s = np.flatnonzero(np.diff(s) != 0)
    flips_d = np.flatnonzero(np.diff(d) != 0)
    assert np.array_equal(flips_s, flips_d)
    rev = tr.first_reversal_s + tr.pass_s * np.arange(6)
    assert np.allclose(ts[flips_s + 1], rev, atol=ts[1] - ts[0] + 1e-9)


def test_the_drift_rule_makes_the_right_tilted_path_look_more_vertical():
    tr = traj(45.0, "right", 1)
    u, n = path_vectors(45.0)
    for t in (0.3, 1.0, 2.0):
        v_ext = tr.direction(t) * tr.speed_dva_s * u
        v_int = tr.drift_sign(t) * (tr.tf_hz / tr.sf_cpd) * n
        combined = v_ext + v_int
        # The combined vector's axis leans less from vertical than the path does, on the
        # way up and on the way down.
        def lean(v):
            return abs(math.degrees(math.atan(v[0] / v[1])))

        assert lean(combined) < lean(v_ext) - 20


def test_without_internal_motion_the_grating_is_still():
    tr = traj(motion=False)
    x = np.linspace(9, 11, 50)
    y = np.zeros_like(x)
    assert np.all(tr.drift_sign(np.linspace(0, 6, 100)) == 0)
    assert np.allclose(carrier(tr, x, y, 0.2), carrier(tr, x, y, 1.7))


def test_the_envelope_runs_a_triangle_wave_from_the_middle():
    tr = traj(49.0, "right", 1)
    assert np.allclose(tr.position(0.0), tr.center)
    top = np.asarray(tr.center) + 1.5 * path_vectors(49.0)[0]
    assert np.allclose(tr.position(0.75), top)
    assert np.allclose(tr.position(2.25), np.asarray(tr.center) - 1.5 * path_vectors(49.0)[0])
    assert np.allclose(tr.position(3.0), tr.center)
    ts = np.linspace(0, 6, 6001)
    speed = np.hypot(*np.diff(tr.position(ts), axis=0).T) / (ts[1] - ts[0])
    assert np.allclose(np.median(speed), 2.0)
    down = traj(49.0, "right", -1)
    assert np.allclose(down.position(0.75), np.asarray(tr.center) - 1.5 * path_vectors(49.0)[0])


def test_the_six_fixation_offset_times():
    assert fixation_offset_times(traj(), 6) == pytest.approx([0.75, 1.25, 1.75, 2.25, 2.75, 3.25])


def test_the_psychopy_spec_draws_the_same_grating():
    """GratingStim(tex='sin'): texture x-axis along (cos ori, -sin ori) in a y-up frame,
    carrier sin(2 pi (sf * along - phase + 1/2) - pi/2), measured from the stimulus
    position. Evaluated with the spec this package hands PsychoPy, it is the model's."""
    for angle, side, t in [(49.0, "right", 0.4), (-52.0, "left", 1.9), (10.0, "right", 2.7)]:
        tr = traj(angle, side)
        spec = tr.grating_spec(t)
        rng = np.random.default_rng(3)
        pts = np.array([spec["x"], spec["y"]]) + rng.uniform(-0.3, 0.3, size=(80, 2))
        dx, dy = pts[:, 0] - spec["x"], pts[:, 1] - spec["y"]
        o = math.radians(spec["ori"])
        along = dx * math.cos(o) - dy * math.sin(o)
        psychopy = np.sin(2 * math.pi * (tr.sf_cpd * along - spec["phase"] + 0.5) - math.pi / 2)
        assert np.allclose(psychopy, carrier(tr, pts[:, 0], pts[:, 1], t), atol=1e-9)


def test_the_stimulus_clock_starts_on_its_first_frame():
    g = SimulatedDoubleDrift(traj())
    assert not g.started
    g.update(0.5)  # the frame before the stimulus: not its time
    assert g.time_s == 0.0
    for _ in range(3):
        g.update(1 / 120)
    assert g.time_s == pytest.approx(3 / 120)
    assert g.position_dva() == pytest.approx(tuple(g.trajectory.position(3 / 120)))


def test_perceived_path_is_vertical_at_the_illusion_angle():
    tr = traj(48.0, "right")
    pts = tr.perceived_position(np.linspace(0, 3, 50), 48.0)
    assert np.allclose(pts[:, 0], tr.center[0])


@pytest.mark.parametrize("angle", [-70.0, -30.0, 15.0, 49.0, 80.0])
def test_recovered_angle_inverts_a_slope(angle):
    u, _ = path_vectors(angle)
    assert recovered_angle_deg(u[1] / u[0]) == pytest.approx(angle)
