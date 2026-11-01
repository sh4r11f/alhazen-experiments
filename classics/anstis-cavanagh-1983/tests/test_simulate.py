"""Simulated sessions end to end, headless, as `--mode simulate` runs them (shortened)."""

from __future__ import annotations

import pandas as pd
import pytest
from conftest import fast_params, simulate

RUNS = [
    ("min-motion-constant", "task.yaml",
     {"test_levels_cd_m2": [8.0, 10.0, 12.0],
      "paradigm": {"kind": "constant", "n_per_condition": 1}}),
    ("min-motion-constant", "task-blue-yellow.yaml",
     {"test_levels_cd_m2": [9.0, 11.0], "paradigm": {"kind": "constant", "n_per_condition": 1}}),
    ("min-motion-adjust", "adjust-temporal.yaml",
     {"test_colours": ["green"], "rates_hz": [0.9375, 15.0],
      "paradigm": {"kind": "adjustment", "n_per_condition": 1}}),
    ("min-flicker-adjust", "flicker-grating.yaml",
     {"test_colours": ["blue"], "spatial_freqs_cpd": [5.0],
      "paradigm": {"kind": "adjustment", "n_per_condition": 1}}),
]


@pytest.mark.parametrize("task,name,overrides", RUNS, ids=[r[1] for r in RUNS])
def test_a_simulated_session_runs_and_writes_trials(tmp_path, task, name, overrides):
    done = simulate(tmp_path, task, fast_params(tmp_path, name, **overrides))
    assert done.returncode == 0, done.stdout[-3000:] + done.stderr[-3000:]
    trials = list(tmp_path.rglob("*_trials.csv"))
    assert trials, "no trials.csv written"
    df = pd.read_csv(trials[0])
    assert len(df) > 0 and df["completed"].all()
    assert (df["luminance_basis"].str.contains("UNMEASURED")).all()
