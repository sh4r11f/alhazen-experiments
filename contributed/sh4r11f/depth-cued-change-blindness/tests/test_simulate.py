"""One simulated session end to end, headless, as `--mode simulate` runs it."""

from __future__ import annotations

import numpy as np
import pandas as pd
from alhazen.core.events import Event
from conftest import N_TRIALS

from depthcb.simulate import SimulatedObserver

OUTCOMES = {"CORRECT", "MISIDENTIFIED", "NO_DETECTION", "NO_REPORT"}


def test_a_simulated_session_runs_every_cell_with_its_cues(simulated_run):
    df = pd.read_csv(next(simulated_run.glob("*_trials.csv")))
    assert len(df) == N_TRIALS
    assert df["scene"].is_unique
    assert set(df["outcome"]) <= OUTCOMES
    counts = df.groupby(["plane", "change_type", "cue"]).size()
    assert (counts == 1).all() and len(counts) == 12
    valid = df[df["cue"] == "valid"]
    invalid = df[df["cue"] == "invalid"]
    assert (valid["cued_plane"] == valid["plane"]).all()
    assert (invalid["cued_plane"] != invalid["plane"]).all()
    assert set(df["cue_word"]) == {"NEAR", "FAR"}
    detected = df[df["outcome"].isin(["CORRECT", "MISIDENTIFIED"])]
    assert len(detected) > 0
    assert np.allclose(detected["alternations"],
                       detected["rt_ms"] / 1000 / detected["alternation_s"], atol=1e-2)
    for planes in df["probe_planes"]:
        assert sorted(planes.split(",")) == ["far", "far", "near", "near"]


def test_the_simulated_observer_uses_its_stated_means():
    obs = SimulatedObserver(seed=3)
    for plane, cue, target in [("near", "valid", 4.2), ("far", "invalid", 13.5)]:
        draws = []
        for _ in range(4000):
            obs.on_event(Event("FLICKER_ON", 0.0, 1, {"plane": plane, "cue": cue,
                                                    "alternation_frames": 38}))
            draws.append(obs.detections[-1])
        assert abs(np.mean(draws) / target - 1) < 0.05


def test_the_simulated_observer_presses_space_after_its_drawn_frames():
    obs = SimulatedObserver(seed=0, sigma=1e-6)
    obs.on_event(Event("FLICKER_ON", 0.0, 1, {"plane": "near", "cue": "none",
                                            "alternation_frames": 10}))
    presses = [obs.poll().keys for _ in range(100)]
    assert presses.index(("space",)) == 69  # 7 alternations x 10 frames, counted from 1
