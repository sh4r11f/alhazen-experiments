"""One simulated session end to end, headless, as `--mode simulate` runs it."""

from __future__ import annotations

import pandas as pd

from moore_fallah2001.analysis import block_table


def test_a_simulated_session_runs_both_staircases_to_their_last_block(simulated_run):
    trials = pd.read_csv(next(simulated_run.glob("*_trials.csv")))
    paradigm = pd.read_csv(next(simulated_run.glob("*_paradigm.csv")))
    assert set(trials["staircase"]) == {"stim", "control"}
    assert len(paradigm) == 4  # 2 staircases x 2 blocks
    done = trials[trials["completed"]]
    assert len(done) == 12  # 2 blocks x 2 staircases x (2 blink + 1 catch)
    assert set(trials["outcome"]) <= {"HIT", "MISS", "EARLY_RESPONSE", "FALSE_ALARM",
                                      "CORRECT_REJECTION", "FIX_BREAK", "NO_FIXATION"}


def test_the_scheduler_and_the_trials_agree_on_every_block(simulated_run):
    trials = pd.read_csv(next(simulated_run.glob("*_trials.csv")))
    paradigm = pd.read_csv(next(simulated_run.glob("*_paradigm.csv")))
    rebuilt = block_table(trials).sort_values(["staircase", "block"]).reset_index(drop=True)
    para = paradigm.sort_values(["staircase", "block"]).reset_index(drop=True)
    assert list(rebuilt["block_success"]) == list(para["block_success"])
    assert list(rebuilt["dim_pct"]) == list(para["dim_pct"])


def test_stimulation_triggers_go_out_only_on_the_stimulation_staircase(simulated_run):
    events = pd.read_csv(next(simulated_run.glob("*_events.csv")))
    trials = pd.read_csv(next(simulated_run.glob("*_trials.csv")))
    stim_trials = set(trials.loc[trials["staircase"] == "stim", "trial_index"])
    fired = set(events.loc[events["event"] == "STIM_TRIGGER", "trial_index"])
    assert fired and fired <= stim_trials
    hits = trials[(trials["staircase"] == "stim") & trials["realised_soa_ms"].notna()]
    assert (hits["realised_soa_ms"] > 150).all()
