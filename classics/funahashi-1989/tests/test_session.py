"""Whole sessions of the full design (8 locations x 3 delays, the paper's 5-s ITI) through
alhazen's builder with the simulated subject's eye, in simulated time."""

from __future__ import annotations

from collections import Counter

import pytest
from alhazen.config.loader import load_params
from conftest import PROJECT, run_session

from funahashi1989.task import OculomotorDelayedResponseTask, OdrParams

RESPONSES = {"CORRECT", "INACCURATE"}


def one_per_condition(file: str) -> OdrParams:
    p = load_params(PROJECT / "configs" / file, OdrParams)
    values = p.model_dump(mode="json")
    values["paradigm"] = {**values["paradigm"], "n_per_condition": 1, "blocks": None}
    return OdrParams.model_validate(values)


@pytest.fixture(scope="module")
def human(tmp_path_factory):
    task = OculomotorDelayedResponseTask(one_per_condition("task.yaml"))
    return run_session(task, tmp_path_factory.mktemp("human") / "data")


@pytest.fixture(scope="module")
def monkey(tmp_path_factory):
    task = OculomotorDelayedResponseTask(one_per_condition("task-monkey.yaml"))
    return run_session(task, tmp_path_factory.mktemp("monkey") / "data", reward=True, seed=5)


def test_every_condition_gets_exactly_one_response(human):
    rows, _ = human
    done = Counter((float(r["cue_angle_deg"]), int(r["delay_index"]))
                   for r in rows if r["outcome"] in RESPONSES)
    assert len(done) == 24 and set(done.values()) == {1}
    # a trial that made no response is served again, so attempts >= 24
    assert len(rows) >= 24


def test_recorded_epochs_are_the_papers(human):
    rows, _ = human
    for r in rows:
        if r["outcome"] in RESPONSES:
            assert float(r["fixation_period_s"]) == pytest.approx(0.75)
            assert float(r["cue_duration_s"]) == pytest.approx(0.5)
            assert float(r["delay_s"]) == pytest.approx([1.5, 3.0, 6.0][int(r["delay_index"])])
            assert float(r["saccade_latency_ms"]) <= 500 + 1000 / 60


def test_a_human_session_pays_nothing(human):
    rows, card = human
    assert card["subject_kind"] == "human" or card.get("subject", {}).get("kind") == "human"
    assert not any(r.get("rewarded") == "True" for r in rows)


def test_a_monkey_session_pays_exactly_the_correct_trials(monkey):
    rows, _ = monkey
    correct = [r["trial_index"] for r in rows if r["outcome"] == "CORRECT"]
    assert correct
    assert [r["trial_index"] for r in rows if r.get("rewarded") == "True"] == correct
