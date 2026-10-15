"""Every task end to end, headless, as `run.py --mode simulate` runs it."""

from __future__ import annotations

import numpy as np
import pandas as pd
import yaml

EXPECTED = {  # task -> completed trials after simulate mode's reduction to 1 per condition
    "equiluminance-speed": 2, "flicker-photometry": 1, "motion-null": 4, "thresholds": 12,
    "attentive-tracking": 16, "speed-match": 9,
}


def trials(root, task):
    return pd.read_csv(next(root.rglob(f"*task-{task}/*_trials.csv")))


def test_every_task_runs_and_writes_its_trials(simulated_data):
    found = {csv.parent.name.split("_task-", 1)[1] for csv in simulated_data.rglob("*_trials.csv")}
    assert found == set(EXPECTED)
    for task, n in EXPECTED.items():
        assert int(trials(simulated_data, task).completed.sum()) == n, task


def test_the_tasks_after_calibration_used_the_subjects_own_k(simulated_data):
    k = trials(simulated_data, "equiluminance-speed")
    expected = float(np.exp(np.log(k.loc[k.outcome == "SET", "k_setting"]).mean()))
    for task in ("motion-null", "thresholds", "attentive-tracking"):
        assert trials(simulated_data, task).k.round(6).unique().tolist() == [round(expected, 6)]
        # The config snapshot records the value used and where it came from.
        snap = next(simulated_data.rglob(f"*task-{task}/config_snapshot.yaml"))
        text = yaml.safe_dump(yaml.safe_load(snap.read_text(encoding="utf-8")))
        assert "geometric mean of 2 settings" in text and "run-01_task-equiluminance-speed" in text


def test_the_simulated_observer_tracks_colour_bars_better_than_chance(simulated_data):
    df = trials(simulated_data, "attentive-tracking")
    assert (df[df.completed].outcome == "CORRECT").mean() > 0.6
