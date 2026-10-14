"""One simulated session end to end, headless, as `--mode simulate` runs it."""

from __future__ import annotations

import pandas as pd

from moore_armstrong2003 import analysis


def read(run, suffix):
    return pd.read_csv(next(run.glob(f"*_{suffix}.csv")))


def test_a_simulated_session_completes_every_condition(simulated_run):
    trials = read(simulated_run, "trials")
    counts = analysis.completed_counts(trials)
    assert counts.shape == (6, 2), counts  # six displays x stim/control
    assert (counts >= 1).all().all(), counts  # simulate reduces n_per_condition to 1
    assert set(trials["subject_kind"]) == {"monkey"}


def test_the_trigger_goes_out_only_on_stimulation_trials(simulated_run):
    trials = read(simulated_run, "trials")
    events = read(simulated_run, "events")
    name_col = "event" if "event" in events.columns else "name"
    stim_trials = set(trials.loc[trials["stimulation"] == "stim", "trial_index"])
    ctrl_trials = set(trials.loc[trials["stimulation"] == "control", "trial_index"])
    fired = set(events.loc[events[name_col] == "STIM_TRIGGER", "trial_index"])
    marked = set(events.loc[events[name_col] == "CONTROL_MARK", "trial_index"])
    assert fired and fired <= stim_trials
    assert marked and marked <= ctrl_trials


def test_realised_timing_is_the_papers(simulated_run):
    trials = read(simulated_run, "trials")
    t = analysis.realised_timing(trials)
    frame_ms = 1000 / 60
    # 200-500 ms after the bars appear and 1.5-2 s of bars (p. 371, p. 373), to the frame
    # (the simulated display paces on the wall clock, so allow one frame of slack).
    assert t["trigger_after_vis_on_ms"].between(200 - frame_ms, 500 + frame_ms).all(), t
    assert t["stimulus_on_ms"].between(1500 - frame_ms, 2000 + frame_ms).all(), t


def test_only_completed_trials_are_paid(simulated_run):
    trials = read(simulated_run, "trials")
    paid = trials["rewarded"].fillna(False).astype(bool)
    assert (trials.loc[paid, "outcome"] == "COMPLETED").all()
