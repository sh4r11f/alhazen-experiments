"""The designs as the paper gives them: 384 saccade trials in 12 blocks of 32, every cell
balanced; 240 perceptual trials over four randomly interleaved staircases in 6 blocks."""

from __future__ import annotations

from collections import Counter

import numpy as np
from alhazen.config.loader import load_params
from alhazen.core.engine import TrialResult
from alhazen.core.trial import Outcome

from lisi_cavanagh2015.perception import STAIRCASE_KEY, RandomInterleavedQuest
from lisi_cavanagh2015.task import (
    PROJECT,
    DoubleDriftPerceptionTask,
    DoubleDriftSaccadesTask,
    PerceptionParams,
    SaccadeParams,
)

DONE = Outcome("REPORTED_RIGHT", completed=True, success=True)
ABORT = Outcome("FIX_BREAK", completed=False)


def drain(source, outcome_for=lambda c, i: DONE, limit=5000):
    served = []
    for i in range(limit):
        c = source.next()
        if c is None:
            break
        served.append(c)
        source.record(c, TrialResult(outcome=outcome_for(c, i), record={}))
    return served


def test_the_saccade_session_is_384_trials_in_12_balanced_blocks():
    task = DoubleDriftSaccadesTask(load_params(PROJECT / "configs" / "task.yaml", SaccadeParams))
    served = drain(task.make_source(task.params, np.random.default_rng(0)))
    assert len(served) == 384
    cells = Counter((c.params["tilt_side"], c.params["internal_motion"], c.params["start_direction"])
                    for c in served)
    assert len(cells) == 8 and set(cells.values()) == {48}
    blocks = Counter(c.params["block"] for c in served)
    assert len(blocks) == 12 and set(blocks.values()) == {32}


def test_the_perceptual_session_is_240_trials_over_four_staircases_in_6_blocks():
    task = DoubleDriftPerceptionTask(
        load_params(PROJECT / "configs" / "task-perception.yaml", PerceptionParams))
    served = drain(task.make_source(task.params, np.random.default_rng(0)))
    assert len(served) == 240
    per = Counter(c.params[STAIRCASE_KEY] for c in served)
    assert per == {"left-1": 60, "left-2": 60, "right-1": 60, "right-2": 60}
    assert Counter(c.params["block"] for c in served) == {b: 40 for b in range(1, 7)}
    assert all(c.params["tilt_side"] == c.params[STAIRCASE_KEY].split("-")[0] for c in served)


def test_staircases_are_picked_at_random_not_in_turn():
    task = DoubleDriftPerceptionTask(
        load_params(PROJECT / "configs" / "task-perception.yaml", PerceptionParams))
    served = drain(task.make_source(task.params, np.random.default_rng(5)))
    order = [c.params[STAIRCASE_KEY] for c in served[:40]]
    # Round-robin would repeat a fixed cycle of four; random order does not.
    assert order[:4] * 10 != order
    assert any(order[i] == order[i + 1] for i in range(39))


def test_an_aborted_trial_is_served_again_at_once_with_the_same_orientation():
    p = load_params(PROJECT / "configs" / "task-perception.yaml", PerceptionParams)
    task = DoubleDriftPerceptionTask(p)
    levels = [dict(c.params) for c in task.conditions(np.random.default_rng(0))]
    src = RandomInterleavedQuest(p.paradigm.quest, levels, np.random.default_rng(1),
                                 task.score_trial)
    aborted = {3, 4, 10}
    served = drain(src, lambda c, i: ABORT if i in aborted else DONE)
    for i in aborted:
        assert served[i + 1].params == served[i].params
    assert len(served) == 240 + len(aborted)


def test_the_staircase_titrates_right_reports():
    """Fed a simulated observer whose right-tilt PSE is +45 deg, the right staircases
    present orientations near it."""
    p = load_params(PROJECT / "configs" / "task-perception.yaml", PerceptionParams)
    task = DoubleDriftPerceptionTask(p)
    rng = np.random.default_rng(7)
    src = task.make_source(p, np.random.default_rng(2))

    def observer(c, i):
        pse = 45.0 if c.params["tilt_side"] == "right" else -45.0
        right = c.params["path_angle_deg"] + rng.normal(0, 6) > pse
        return DONE if right else Outcome("REPORTED_LEFT", completed=True, success=False)

    served = drain(src, observer)
    late = [c.params["path_angle_deg"] for c in served[120:] if c.params["tilt_side"] == "right"]
    assert abs(np.median(late) - 45.0) < 12
