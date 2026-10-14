"""One simulated session end to end, headless, as `run.py --mode simulate` runs it."""

from __future__ import annotations

import pandas as pd


def test_a_simulated_session_runs_and_writes_trials(simulated_run):
    done, tmp = simulated_run
    assert done.returncode == 0, done.stdout[-3000:] + done.stderr[-3000:]
    trials = list(tmp.rglob("*_trials.csv"))
    assert trials, "no trials.csv written"
    df = pd.read_csv(trials[0])
    responses = df[df["outcome"].isin(["CORRECT", "INACCURATE"])]
    # one response per location and delay (the rehearsal's one trial per condition)
    assert len(responses.groupby(["cue_angle_deg", "delay_index"])) == 16
    assert responses["endpoint_error_dva"].notna().all()
