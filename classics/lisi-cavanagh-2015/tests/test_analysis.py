"""The analysis recovers what a simulated observer was built to do, from synthetic trials
made with the same stimulus geometry (no session needed): the PSE of a known psychometric
function, no saccade orientation effect for an observer aiming at the physical path, a large
one for an observer aiming at the perceived path, and the constant local shift."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from lisi_cavanagh2015 import analysis as A
from lisi_cavanagh2015.geometry import Trajectory
from lisi_cavanagh2015.simulate import ObserverModel, landing_dva


def synthetic_saccades(model, n=800, seed=0, angles=(48.0, -48.0)):
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(n):
        side = "right" if i % 2 else "left"
        motion = bool((i // 2) % 2)
        start = 1 if (i // 4) % 2 else -1
        tr = Trajectory(angle_deg=angles[0] if side == "right" else angles[1], side=side,
                        internal_motion=motion, start_direction=start)
        t = 0.75 + 0.5 * rng.integers(6) + rng.normal(0.24, 0.04)
        x, y = landing_dva(tr, t, model, rng)
        p = tr.position(t)
        rows.append({
            "outcome": "SACCADE", "endpoint_measured": True, "endpoint_settled": True,
            "saccade_latency_ms": float(rng.uniform(150, 400)), "tilt_side": side,
            "internal_motion": motion, "path_angle_deg": tr.angle_deg,
            "path_center_x_dva": 10.0, "path_center_y_dva": 0.0, "path_length_dva": 3.0,
            "gabor_x_at_onset_dva": p[0], "gabor_y_at_onset_dva": p[1],
            "gabor_along_at_onset_dva": float(tr.along(t)),
            "drift_sign_at_onset": int(tr.drift_sign(t)),
            "endpoint_x_dva": x, "endpoint_y_dva": y, "saccade_dx_dva": x, "saccade_dy_dva": y,
        })
    return pd.DataFrame(rows)


def test_the_cumulative_gaussian_recovers_a_known_pse():
    rng = np.random.default_rng(0)
    x = rng.uniform(-80, 80, 600)
    right = x + rng.normal(0, 9, x.size) > 37.0
    fit = A.fit_cumulative_gaussian(x, right)
    assert fit.mu == pytest.approx(37.0, abs=2.0)
    assert fit.sigma == pytest.approx(9.0, abs=3.0)


def test_saccades_to_the_physical_path_show_no_orientation_effect():
    eff = A.internal_motion_effect(A.recover_orientations(
        A.usable_saccades(synthetic_saccades(ObserverModel(target="physical")))))
    assert (eff["effect_deg"].abs() < 5).all(), eff
    assert ((eff["control"] - np.sign(eff["control"]) * 48).abs() < 6).all()


def test_saccades_to_the_perceived_path_show_the_illusion():
    eff = A.internal_motion_effect(A.recover_orientations(
        A.usable_saccades(synthetic_saccades(ObserverModel(target="perceived")))))
    right = eff.set_index("tilt_side")
    assert right.loc["right", "effect_deg"] < -30  # rotated toward vertical
    assert right.loc["left", "effect_deg"] > 30


def test_the_local_shift_is_recovered_and_does_not_grow_along_the_path():
    errs = A.orthogonal_errors(A.usable_saccades(synthetic_saccades(ObserverModel(), n=1600)))
    shift = A.orthogonal_shift(errs)
    assert shift["rightward_minus_leftward_dva"] == pytest.approx(0.66, abs=0.12)
    assert abs(shift["slope_along_path_left"]) < 0.12
    assert abs(shift["slope_along_path_right"]) < 0.12


def test_latency_exclusions_follow_the_paper():
    df = synthetic_saccades(ObserverModel(), n=20)
    df.loc[0, "saccade_latency_ms"] = 99.0
    df.loc[1, "saccade_latency_ms"] = 601.0
    df.loc[2, "saccade_latency_ms"] = 100.0
    df.loc[3, "saccade_latency_ms"] = 600.0
    kept = A.usable_saccades(df)
    assert 0 not in kept.index and 1 not in kept.index
    assert 2 in kept.index and 3 in kept.index
