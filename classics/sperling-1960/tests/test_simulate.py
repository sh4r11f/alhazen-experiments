"""One simulated session end to end, headless, as `--mode simulate` runs it."""

from __future__ import annotations

import pandas as pd


def test_a_simulated_session_runs_and_writes_scored_trials(simulated_run):
    df = pd.read_csv(next(simulated_run.glob("*_trials.csv")))
    # 4 delays x 2 series x (1 sample + 1 test trial: simulate mode serves one per block)
    assert len(df) >= 16
    assert set(df["outcome"]) <= {"REPORTED", "NO_RESPONSE", "NO_START"}
    done = df[df["outcome"] == "REPORTED"]
    assert len(done) == 16
    assert done["n_correct"].between(0, 4).all()
    assert (done["letters_available"] == done["n_correct"] * 3).all()
    # Whole frames: 3 at 60 Hz, and the flip stamps say so.
    assert (done["exposure_frames"] == 3).all()
    # On a loaded machine a simulated display can flip late; the flag says so per trial.
    assert (done["exposure_ms_measured"] > 49).all()
    late = done["exposure_ms_measured"] - done["exposure_ms_planned"] >= 500 / 60
    assert (done["exposure_ok"] == ~late).all()
    assert set(done["delay_s"]) == {-0.10, 0.0, 0.30, 1.0}
    events = pd.read_csv(next(simulated_run.glob("*_events.csv")))
    assert {"ARRAY_ON", "ARRAY_OFF", "REPORT_ON", "RESPONSE"} <= set(events["event"])
