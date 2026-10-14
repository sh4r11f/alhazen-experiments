"""The simulated searcher, and one simulated session end to end, headless."""

from __future__ import annotations

import subprocess
import sys

import numpy as np
import pandas as pd
import pytest
from alhazen.core.events import Event
from support import short_params_file, sim_rig

from treisman_gelade1980.simulate import MODELS, SimulatedSearcher
from treisman_gelade1980.task import PROJECT


def slope(observer, condition, present, sizes=(1, 5, 15, 30), n=400):
    means = [np.mean([observer.rt_ms(condition, s, present) for _ in range(n)]) for s in sizes]
    return np.polyfit(sizes, means, 1)[0]


def test_conjunction_search_is_serial_and_self_terminating():
    obs = SimulatedSearcher(seed=0)
    neg, pos = slope(obs, "conjunction", False), slope(obs, "conjunction", True)
    assert neg == pytest.approx(MODELS["conjunction"].per_item, rel=0.1)
    assert pos / neg == pytest.approx(0.5, abs=0.08)


def test_feature_search_is_nearly_flat_when_the_target_is_there():
    obs = SimulatedSearcher(seed=1)
    assert abs(slope(obs, "feature", True)) < 8


def test_the_searcher_answers_after_its_rt_with_the_trials_keys():
    clock = [0.0]
    obs = SimulatedSearcher(seed=2, p_miss=0.0, p_false_alarm=0.0, now=lambda: clock[0])
    obs.expect("feature", 5, True, "j", "f", "space")
    obs.on_event(Event("READY_ON", 0.0, 1))
    assert obs.poll().keys == ()
    clock[0] = 0.3
    assert obs.poll().keys == ("space",)
    obs.on_event(Event("ARRAY_ON", 0.3, 1))
    clock[0] = 5.0
    assert obs.poll().keys == ("j",)
    assert obs.poll().keys == ()


def test_a_simulated_session_runs_and_writes_trials(tmp_path):
    cmd = [sys.executable, str(PROJECT / "run.py"), "--task", "feature-conjunction-search",
           "--mode", "simulate", "--headless", "--rig", str(sim_rig(tmp_path)),
           "--params", str(short_params_file(tmp_path, "task-exp2-difficult.yaml")),
           "--sub", "sim", "--ses", "1", "--seed", "1"]
    done = subprocess.run(cmd, cwd=PROJECT, capture_output=True, text=True, timeout=600)
    assert done.returncode == 0, done.stdout[-3000:] + done.stderr[-3000:]
    trials = list(tmp_path.rglob("*_trials.csv"))
    assert trials, "no trials.csv written"
    df = pd.read_csv(trials[0])
    regular = df[df["dummy"] == 0]
    # One card per display size and answer, each completed exactly once.
    done_ok = regular[regular["completed"]]
    assert sorted(done_ok["display_size"].unique()) == [1, 4, 16, 36]
    assert len(done_ok) == 8
    assert (done_ok["rt_ms"] > 0).all()
    assert set(df["outcome"]) <= {"CORRECT", "WRONG", "NO_RESPONSE", "NOT_STARTED"}
