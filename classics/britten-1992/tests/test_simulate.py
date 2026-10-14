"""One simulated session of each parameter set, end to end, as `--mode simulate` runs it."""

from __future__ import annotations

import json

import pandas as pd


def trials(run):
    return pd.read_csv(next(run.glob("*_trials.csv")), keep_default_na=False, na_values=[""])


def test_the_human_session_serves_every_cell_and_records_the_answers(simulated_runs):
    df = trials(simulated_runs["human"])
    done = df[df["completed"]]
    assert len(done) == 16  # reduced to one trial per cell
    assert set(zip(done["direction"], done["coherence_pct"], strict=True)) == {
        (d, c) for d in ("pref", "anti") for c in (0.0, 0.8, 1.6, 3.2, 6.4, 12.8, 25.6, 51.2)}
    assert set(done["outcome"]) <= {"CORRECT", "WRONG"}
    assert done["rt_ms"].gt(0).all()
    assert set(done["choice"]) <= {"pref", "anti"}
    assert (df["subject_kind"] == "human").all()


def test_the_monkey_session_is_paid_and_saccades_land_on_a_target(simulated_runs):
    df = trials(simulated_runs["monkey"])
    done = df[df["completed"] & ~df["correction"]]
    assert len(done) == 16
    correct = done[done["outcome"] == "CORRECT"]
    assert correct["rewarded"].astype(str).str.lower().eq("true").all()
    assert done["endpoint_measured"].all()
    assert (done["endpoint_x_dva"].abs() > 7).all()  # targets are 10 deg either side
    assert (df["subject_kind"] == "monkey").all()


def test_each_trial_records_the_seed_that_replays_its_dots(simulated_runs):
    for run in simulated_runs.values():
        df = trials(run)
        assert df["stimulus_seed"].nunique() == len(df)
        assert df["signal_dt_ms"].eq(50.0).all()  # 45 ms at 60 Hz


def test_the_session_record_says_who_and_what_was_simulated(simulated_runs):
    for kind, run in simulated_runs.items():
        session = json.loads((run / "session.json").read_text(encoding="utf-8"))
        assert kind in json.dumps(session)
