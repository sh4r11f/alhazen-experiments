"""The whole plan of each shipped params file, on simulated time, through alhazen's runner.

scripts/simulate_full.py runs every trial the params describe (168 and 540) with the
simulated subject on a clock that moves one frame per flip, so every recorded time is exact.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

PROJECT = Path(__file__).resolve().parents[1]
FRAME = 1 / 60


@pytest.fixture(scope="module")
def full(tmp_path_factory):
    out = {}
    for task in ("memory-scanning", "memory-scanning-fixed"):
        root = tmp_path_factory.mktemp(task)
        done = subprocess.run([sys.executable, str(PROJECT / "scripts" / "simulate_full.py"),
                               task, str(root)], cwd=PROJECT, capture_output=True, text=True,
                              timeout=600)
        assert done.returncode == 0, done.stdout[-2000:] + done.stderr[-2000:]
        run = next(root.rglob("*_trials.csv")).parent
        out[task] = (pd.read_csv(next(run.glob("*_trials.csv"))),
                     pd.read_csv(next(run.glob("*_events.csv"))))
    return out


def test_experiment_1_runs_its_whole_plan_with_the_papers_timing(full):
    trials, events = full["memory-scanning"]
    assert len(trials) == 168 and list(trials["stage"]).count("test") == 144
    assert trials["completed"].all()
    test = trials[trials["stage"] == "test"]
    assert set(test.groupby(["set_size", "probe_type"]).size()) == {12}
    # Each digit 1.2 s; the last digit plus the 2.0-s delay until the warning.
    t = events.reset_index(drop=True)
    gaps = t["t"].shift(-1) - t["t"]
    item = gaps[(t["event"] == "ITEM_ON") & (t["event"].shift(-1) == "ITEM_ON")]
    last = gaps[(t["event"] == "ITEM_ON") & (t["event"].shift(-1) == "WARNING_ON")]
    assert item.round(6).unique().tolist() == [1.2]
    assert last.round(6).unique().tolist() == [3.2]
    warn = gaps[t["event"] == "WARNING_ON"]
    assert warn.round(6).unique().tolist() == [0.5]


def test_experiment_2_runs_its_whole_plan_with_the_papers_timing(full):
    trials, events = full["memory-scanning-fixed"]
    assert len(trials) == 540
    for part in (1, 2, 3):
        block = trials[(trials["part"] == part) & (trials["stage"] == "test")]
        assert len(block) == 120 and (block["probe_type"] == "positive").sum() == 32
    assert (events["event"] == "SET_ANNOUNCED").sum() == 3
    same_part = trials["part"].shift(-1) == trials["part"]
    gap = (trials["t_probe_on"].shift(-1) - trials["t_response"])[same_part]
    # 3.7 s (paper: p. 653) plus three frames (docs/methods.md, deviations).
    assert gap.round(6).unique().tolist() == [round(3.7 + 3 * FRAME, 6)]
