"""Scheduling: the paper's block and its correction trials (pp. 4747-4748)."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
from alhazen.config.loader import load_params

from britten1992.task import PROJECT, CorrectionTrials, RdkDirectionTask, RdkDirectionTaskParams

CORRECT = SimpleNamespace(outcome=SimpleNamespace(completed=True, success=True))
WRONG = SimpleNamespace(outcome=SimpleNamespace(completed=True, success=False))
BREAK = SimpleNamespace(outcome=SimpleNamespace(completed=False, success=False))


def task(name):
    return RdkDirectionTask(load_params(PROJECT / "configs" / name, RdkDirectionTaskParams))


def drain(source, answer):
    served = []
    while (c := source.next()) is not None:
        served.append(c.params)
        source.record(c, answer(c.params))
        assert len(served) < 5000
    return served


def test_a_block_is_15_per_direction_per_level_in_random_order():
    t = task("task-monkey.yaml")
    served = drain(t.make_source(t.params, np.random.default_rng(1)), lambda p: CORRECT)
    assert len(served) == 15 * 2 * 8
    cells = {(p["direction"], p["coherence_pct"]) for p in served}
    assert len(cells) == 16
    assert served[:16] != sorted(served[:16], key=lambda p: (p["coherence_pct"], p["direction"]))


def test_a_trial_without_a_choice_is_served_again():
    t = task("task-monkey.yaml")
    failed = {"n": 0}

    def answer(p):
        if failed["n"] < 5:
            failed["n"] += 1
            return BREAK
        return CORRECT

    served = drain(t.make_source(t.params, np.random.default_rng(2)), answer)
    assert len(served) == 240 + 5


def test_three_errors_on_one_direction_start_correction_trials_until_it_is_chosen():
    source = CorrectionTrials(_Fixed([("pref", 12.8)] * 6 + [("anti", 12.8)] * 4),
                              after_errors=3, coherences_pct=[0.0, 6.4, 12.8], coherence_pct=None,
                              rng=np.random.default_rng(3))
    log = []
    wrong_corrections = 2
    while (c := source.next()) is not None:
        p = c.params
        log.append((p["direction"], p["correction"]))
        if p["correction"]:
            result = WRONG if wrong_corrections else CORRECT
            wrong_corrections -= 1 if not p.get("_") else 0
        else:
            result = WRONG if p["direction"] == "pref" else CORRECT
        source.record(c, result)
    # three wrong pref trials, then pref correction trials (two wrong, one right)
    assert log[:3] == [("pref", False)] * 3
    assert log[3:6] == [("pref", True)] * 3
    assert log[6:9] == [("pref", False)] * 3
    # the planned trials were all served despite the corrections
    assert sum(1 for _, corr in log if not corr) == 10
    assert all(c > 0 for c in [6.4, 12.8])


def test_zero_correlation_errors_do_not_count_toward_a_streak():
    source = CorrectionTrials(_Fixed([("pref", 0.0)] * 5), after_errors=3,
                              coherences_pct=[0.0, 6.4], coherence_pct=None,
                              rng=np.random.default_rng(4))
    served = drain(source, lambda p: WRONG)
    assert not any(p["correction"] for p in served)


def test_correction_trials_use_non_zero_levels():
    source = CorrectionTrials(_Fixed([("anti", 6.4)] * 3 + [("pref", 6.4)]), after_errors=3,
                              coherences_pct=[0.0, 3.2, 6.4], coherence_pct=None,
                              rng=np.random.default_rng(5))
    served = drain(source, lambda p: WRONG if not p["correction"] else CORRECT)
    corrections = [p for p in served if p["correction"]]
    assert corrections and all(p["coherence_pct"] in (3.2, 6.4) for p in corrections)


def test_the_human_set_has_no_correction_trials():
    t = task("task.yaml")
    assert not isinstance(t.make_source(t.params, np.random.default_rng(6)), CorrectionTrials)
    assert isinstance(task("task-monkey.yaml").make_source(
        task("task-monkey.yaml").params, np.random.default_rng(6)), CorrectionTrials)


def test_the_duration_estimate_counts_the_planned_block():
    t = task("task-monkey.yaml")
    plan = t.duration_schedule(t.params, np.random.default_rng(0))
    assert plan.n_trials == 240 and "correction" in plan.note
    assert t.trial_timing(t.conditions(np.random.default_rng(0))[0], 120.0) is not None


class _Fixed:
    """A planned queue of (direction, coherence) that re-serves nothing."""

    def __init__(self, cells):
        from alhazen.paradigms.base import Condition

        self._q = [Condition({"direction": d, "coherence_pct": c, "correction": False})
                   for d, c in cells]

    def next(self):
        return self._q.pop(0) if self._q else None

    def record(self, condition, result):
        return

    def remaining(self):
        return len(self._q)

    def summary(self):
        return None
