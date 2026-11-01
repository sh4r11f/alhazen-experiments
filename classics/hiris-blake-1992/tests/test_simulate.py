"""One simulated session of each parameter set, end to end, as `--mode simulate` runs it."""

from __future__ import annotations

import json

import pandas as pd


def trials(run):
    return pd.read_csv(next(run.glob("*_trials.csv")), keep_default_na=False, na_values=[""])


LEVELS = {-20.0, -10.0, 0.0, 10.0, 20.0, 30.0, 40.0, 50.0, 60.0}


def test_each_session_serves_every_level_and_records_a_choice(simulated_runs):
    for kind, mode in (("adapted", "unidirectional"), ("control", "random")):
        df = trials(simulated_runs[kind])
        done = df[df["completed"]]
        assert len(done) == 9  # reduced to one trial per level
        assert set(done["test_signal_pct"]) == LEVELS
        assert set(done["outcome"]) <= {"CHOSE_TEST", "CHOSE_REFERENCE"}
        assert set(done["chose_test"]) <= {0, 1}
        assert (done["adapt_mode"] == mode).all()
        assert done["rt_ms"].gt(0).all()


def test_only_the_first_trial_gets_the_initial_adaptation(simulated_runs):
    for run in simulated_runs.values():
        df = trials(run)
        kinds = list(df["adaptation_kind"])
        assert kinds[0] == "initial" and set(kinds[1:]) == {"top-up"}
        assert df["adaptation_s"].iloc[0] > df["adaptation_s"].iloc[1]


def test_each_trial_records_the_realised_motion_and_four_seeds(simulated_runs):
    for run in simulated_runs.values():
        df = trials(run)
        assert df["update_frames"].eq(3).all()  # 0.0957 deg at ~2 deg/s on 60 Hz
        assert df["speed_dva_s"].round(3).eq(1.914).all()
        seeds = df[[c for c in df if c.startswith("seed_")]]
        assert seeds.shape[1] == 4 and seeds.notna().all().all()
        assert df["reference_signal_pct"].eq(40.0).all()


def test_the_session_record_names_the_simulated_observer(simulated_runs):
    for run in simulated_runs.values():
        session = json.loads((run / "session.json").read_text(encoding="utf-8"))
        assert session["mode"] == "simulate"
        log = (run / "session.log").read_text(encoding="utf-8")
        assert "hirisblake1992.simulate.SimulatedObserver" in log
