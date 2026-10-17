"""One simulated session end to end, headless, as `--mode simulate` runs it."""

from __future__ import annotations

import numpy as np
import pandas as pd
from alhazen.core.events import Event
from conftest import N_TRIALS

from rensink1997.simulate import SimulatedObserver

OUTCOMES = {"CORRECT", "MISIDENTIFIED", "NO_DETECTION", "NO_REPORT"}


def test_a_simulated_session_runs_every_scene_once(simulated_run):
    df = pd.read_csv(next(simulated_run.glob("*_trials.csv")))
    assert len(df) == N_TRIALS
    assert df["scene"].is_unique
    assert set(df["outcome"]) <= OUTCOMES
    assert set(df["change_type"]) == {"presence", "color", "location"}
    detected = df[df["outcome"].isin(["CORRECT", "MISIDENTIFIED"])]
    assert len(detected) > 0
    assert (detected["alternations"] > 0).all()
    assert np.allclose(detected["alternations"],
                       detected["rt_ms"] / 1000 / detected["alternation_s"], atol=1e-2)


def test_the_simulated_observer_follows_the_papers_means():
    obs = SimulatedObserver(seed=3)
    for interest in ("central", "marginal"):
        draws = []
        for _ in range(4000):
            obs.on_event(Event("FLICKER_ON", 0.0, 1, {"interest": interest, "cue": "none",
                                                    "blank_frames": 5,
                                                    "alternation_frames": 38}))
            draws.append(obs.detections[-1])
        target = {"central": 7.3, "marginal": 17.1}[interest]
        assert abs(np.mean(draws) / target - 1) < 0.05
    assert obs.mean_alternations("central", "none", 0) == 1.4
    assert obs.mean_alternations("marginal", "valid", 5) < 17.1


def test_the_simulated_observer_presses_space_after_its_drawn_frames():
    obs = SimulatedObserver(seed=0, sigma=1e-6)
    obs.on_event(Event("FLICKER_ON", 0.0, 1, {"interest": "central", "cue": "none",
                                            "blank_frames": 5, "alternation_frames": 10}))
    presses = [obs.poll().keys for _ in range(100)]
    assert presses.index(("space",)) == 72  # 7.3 alternations x 10 frames, counted from 1
    obs.on_event(Event("LOCATION_PROBE", 0.0, 1, {"answer": "3", "keys": ["1", "2", "3", "4"]}))
    keys = [k for _ in range(80) for k in obs.poll().keys]
    assert keys in (["3"], ["1"], ["2"], ["4"])
