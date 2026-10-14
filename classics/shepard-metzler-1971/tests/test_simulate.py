"""One simulated session end to end, headless, as `--mode simulate` runs it."""

from __future__ import annotations

import numpy as np
import pandas as pd

from shepard_metzler1971.params import SimulatedSubjectConfig
from shepard_metzler1971.simulate import SimulatedObserver


def test_a_simulated_session_runs_and_writes_every_trial(rehearsal_run):
    df = pd.read_csv(next(rehearsal_run.glob("*_trials.csv")))
    done = df[df["completed"].astype(bool)]
    assert len(done) == 20
    assert set(done["rotation"]) == {"depth", "picture-plane"}
    assert set(done["kind"]) == {"same", "different"}
    assert set(done["outcome"]) <= {"CORRECT", "WRONG"}
    assert (done["rt_ms"] > 0).all()
    # The paper's half second: exact on the fake clock (test_task.py); here a real-time
    # paced display on a shared machine, so only close to it.
    gap = done["t_pair_on"] - done["t_warning_on"]
    assert abs(gap.median() - 0.5) < 0.02 and gap.between(0.45, 0.6).all()


def test_the_simulated_subject_plants_the_papers_pattern():
    obs = SimulatedObserver(SimulatedSubjectConfig(), "j", "f", seed=3)
    rts = {a: np.mean([obs.plan({"kind": "same", "angle_deg": a})[0] for _ in range(4000)])
           for a in (0, 180)}
    assert 0.9 < rts[0] < 1.1
    assert 3.8 < rts[180] < 4.2  # 1 s + 180 deg at 60 deg/s
    diff = np.mean([obs.plan({"kind": "different", "angle_deg": 80})[0] for _ in range(4000)])
    assert 3.6 < diff < 4.0
    keys = [obs.plan({"kind": "same", "angle_deg": 90})[1] for _ in range(4000)]
    assert 0.02 < keys.count("f") / 4000 < 0.05
