"""One simulated session of each procedure end to end, headless, as `--mode simulate` runs it."""

from __future__ import annotations

import pandas as pd
import pytest


@pytest.mark.parametrize("task", ["memory-scanning", "memory-scanning-fixed"])
def test_a_simulated_session_runs_and_writes_trials(simulated, task):
    code, log = simulated["logs"][task]
    assert code == 0, log[-3000:]
    run = simulated["runs"][task]
    assert run is not None, "no trials.csv written"
    df = pd.read_csv(next(run.glob("*_trials.csv")))
    assert len(df) > 0 and df["completed"].all()
    assert set(df["outcome"]) <= {"CORRECT", "WRONG"}
    assert df["rt_ms"].between(150, 5000).all()


def test_the_varied_set_session_ran_practice_then_test_with_recalls(simulated):
    df = pd.read_csv(next(simulated["runs"]["memory-scanning"].glob("*_trials.csv")))
    assert list(df["stage"]) == ["practice"] * 4 + ["test"] * 4
    assert sorted(df["set_size"].unique()) == [1, 4]
    assert df["recall_committed"].all()
    # The simulated subject recalls what it was shown (up to its 1.4 % recall slips).
    assert (df["recall"].astype(str) == df["series"].astype(str)).mean() >= 0.75
    events = pd.read_csv(next(simulated["runs"]["memory-scanning"].glob("*_events.csv")))
    assert (events["event"] == "ITEM_ON").sum() == df["set_size"].sum()


def test_the_fixed_set_session_announced_each_part_once(simulated):
    run = simulated["runs"]["memory-scanning-fixed"]
    df = pd.read_csv(next(run.glob("*_trials.csv")))
    assert list(df["set_size"]) == [1] * 15 + [4] * 15
    assert (df["probe_type"] == "positive").sum() == 8  # 4 of each part's 15
    events = pd.read_csv(next(run.glob("*_events.csv")))
    assert (events["event"] == "SET_ANNOUNCED").sum() == 2
