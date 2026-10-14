"""Simulated sessions end to end: the run.py command line, and both parameter sets in full."""

from __future__ import annotations

import subprocess
import sys
from collections import Counter

import pandas as pd
import pytest
import yaml
from alhazen.core.events import Event
from conftest import sim_rig

from posner1980.design import composition
from posner1980.simulate import SimulatedObserver
from posner1980.task import PROJECT


def test_run_py_simulate_headless_runs_a_session(tmp_path):
    """The command line as a person types it. Real time passes in this mode, so the
    params are the main set with short durations and one 20-trial block; the full
    design runs below on a fake clock, through the same session builder."""
    params = yaml.safe_load((PROJECT / "configs" / "task.yaml").read_text(encoding="utf-8"))
    params.update(intertrial_min={"ms": 50}, intertrial_max={"ms": 100},
                  cue_target_soa={"ms": 100}, feedback_duration={"ms": 50},
                  response_deadline={"ms": 800})
    params["design"] = {"validity": 0.8, "arrow_fraction": 0.5, "catch_fraction": 0.0,
                        "trials_per_block": 20}
    params["paradigm"]["blocks"] = {"n_blocks": 1, "breaks": False}
    short = tmp_path / "short.yaml"
    short.write_text(yaml.safe_dump(params), encoding="utf-8")
    cmd = [sys.executable, str(PROJECT / "run.py"), "--task", "posner-cueing", "--mode",
           "simulate", "--headless", "--rig", str(sim_rig(tmp_path)), "--params", str(short),
           "--sub", "sim", "--ses", "1", "--seed", "1"]
    done = subprocess.run(cmd, cwd=PROJECT, capture_output=True, text=True, timeout=600)
    assert done.returncode == 0, done.stdout[-3000:] + done.stderr[-3000:]
    df = pd.read_csv(next(tmp_path.rglob("*_trials.csv")))
    assert (df["completed"].astype(str) == "True").sum() == 20


@pytest.mark.parametrize("name", ["tracker", "keyboard"])
def test_a_full_session_serves_every_planned_trial_of_every_block(simulated_runs, name):
    df = pd.read_csv(next(simulated_runs[name].glob("*_trials.csv")))
    done = df[df["completed"].astype(str) == "True"]
    assert len(done) == 320
    comp = composition(80, 0.5, 0.8, 0.25)
    want = Counter({"valid": 2 * comp.valid, "invalid": 2 * comp.invalid,
                    "neutral": 2 * comp.neutral, "catch": 2 * comp.arrow_catch + comp.neutral_catch})
    for _, block in done.groupby("block"):
        assert Counter(block["validity"]) == want
    assert set(done["outcome"]) <= {"DETECTED", "MISS", "CORRECT_REJECTION", "FALSE_ALARM"}
    assert (df["fixation_control"] == ("tracker" if name == "tracker" else "none")).all()


def test_fixation_breaks_happen_only_with_the_tracker_and_are_served_again(simulated_runs):
    tracker = pd.read_csv(next(simulated_runs["tracker"].glob("*_trials.csv")))
    keyboard = pd.read_csv(next(simulated_runs["keyboard"].glob("*_trials.csv")))
    breaks = tracker[tracker["outcome"] == "FIXATION_BREAK"]
    assert len(breaks) > 0 and "FIXATION_BREAK" not in set(keyboard["outcome"])
    # Every broken attempt's slot comes back, in its own block, and completes.
    done = tracker[tracker["completed"].astype(str) == "True"]
    served = set(zip(done["block"], done["slot"], strict=True))
    assert set(zip(breaks["block"], breaks["slot"], strict=True)) <= served
    assert (tracker["attempt"] > 1).any()


@pytest.mark.parametrize("name", ["tracker", "keyboard"])
def test_the_timing_is_the_papers_to_the_frame(simulated_runs, name):
    df = pd.read_csv(next(simulated_runs[name].glob("*_trials.csv")))
    frame = 1 / 60
    reached = df[df["t_target_on"].notna()]
    soa = reached["t_target_on"] - reached["t_cue_on"]
    assert soa.sub(1.0).abs().max() <= frame / 2 + 1e-9
    catch = df[df["t_catch_on"].notna()]
    assert (catch["t_catch_on"] - catch["t_cue_on"]).sub(1.0).abs().max() <= frame / 2 + 1e-9
    iti = df["intertrial_s"].dropna()
    assert iti.between(1.0, 2.0).all() and iti.std() > 0.2
    start = df["t_fix_acquired"] if name == "tracker" else df["t_fix_on"]
    gap = (df["t_cue_on"] - start - df["intertrial_s"]).dropna()
    assert gap.abs().max() <= frame + 1e-9
    hits = df[df["outcome"] == "DETECTED"]
    assert hits["rt_ms"].between(100, 1000).mean() > 0.95


def test_the_simulated_observer_is_blind_to_the_cue(simulated_runs):
    """The rehearsal must not look like Posner's result: no planted cueing effect."""
    df = pd.read_csv(next(simulated_runs["tracker"].glob("*_trials.csv")))
    hits = df[(df["outcome"] == "DETECTED")]
    means = hits.groupby("validity")["rt_ms"].mean()
    assert abs(means["invalid"] - means["valid"]) < 40


def test_the_observer_presses_a_whole_number_of_frames_after_the_target():
    obs = SimulatedObserver(seed=3, p_miss=0.0)
    obs.set_refresh_rate(100.0)
    obs.on_event(Event("TARGET_ON", 0.0, 1))
    polls = 0
    while not obs.poll().keys:
        polls += 1
        assert polls < 200
    assert 15 <= polls <= 100           # 150 ms to 1 s at 100 Hz
    assert obs.poll().keys == ()        # one press, not a held key


def test_the_observer_stays_quiet_on_catch_trials_when_told_to():
    obs = SimulatedObserver(seed=0, p_false_alarm=0.0, p_anticipation=0.0)
    obs.on_event(Event("CUE_ON", 0.0, 1))
    obs.on_event(Event("CATCH_ON", 1.0, 1))
    assert not any(obs.poll().keys for _ in range(200))
