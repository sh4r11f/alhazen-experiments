"""One simulated session end to end, headless, as `--mode simulate` runs it."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from shepard_metzler1971.params import SimulatedSubjectConfig
from shepard_metzler1971.simulate import SimulatedObserver

PROJECT = Path(__file__).resolve().parents[1]


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


def test_a_whole_200_trial_block_of_the_main_set_in_simulated_time(tmp_path):
    """scripts/simulate_sessions.py: the main parameter set on alhazen's FakeClock."""
    done = subprocess.run(
        [sys.executable, str(PROJECT / "scripts" / "simulate_sessions.py"), "--out",
         str(tmp_path), "--subjects", "sim", "--sessions", "3"],
        cwd=PROJECT, capture_output=True, text=True, timeout=600)
    assert done.returncode == 0, done.stdout[-2000:] + done.stderr[-2000:]
    df = pd.read_csv(next(tmp_path.rglob("*_trials.csv")))
    assert len(df) == 200 and df["completed"].all()
    assert set(df["session"]) == {3} and df["block_type"].nunique() == 1
    assert (df["kind"] == "same").sum() == 100
    # simulated time is exact: the warning precedes the pair by 30 frames at 60 Hz
    assert np.allclose(df["t_pair_on"] - df["t_warning_on"], 0.5, atol=1e-6)
