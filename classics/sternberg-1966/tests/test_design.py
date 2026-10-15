"""The design rules: what each trial contains and how sessions are scheduled."""

from __future__ import annotations

from collections import Counter

import numpy as np
import pytest
from alhazen.config.loader import load_params
from alhazen.errors import ConfigError

from sternberg1966 import design
from sternberg1966.simulate import SimulatedObserver
from sternberg1966.task import (
    PROJECT,
    FixedSetMemoryScanningTask,
    FixedSetParams,
    MemoryScanningTask,
    VariedSetParams,
)


def varied_task():
    return MemoryScanningTask(load_params(PROJECT / "configs" / "task.yaml", VariedSetParams))


def fixed_task():
    return FixedSetMemoryScanningTask(
        load_params(PROJECT / "configs" / "task-fixed-set.yaml", FixedSetParams))


def served(source):
    out = []
    while (c := source.next()) is not None:
        out.append((c, source.take_block_break()))
        from alhazen.core.engine import TrialResult
        from alhazen.core.trial import Outcome
        source.record(c, TrialResult(outcome=Outcome("OK", completed=True), record={}))
    return out


# ------------------------------------------------------------ experiment 1


def test_varied_set_probe_probabilities_are_the_papers():
    """Each series digit is the probe with p = 1/(2s), each other digit 1/(2(10 - s))."""
    rng = np.random.default_rng(1)
    s, n = 3, 30000
    position_hits = Counter()
    for i in range(n):
        t = design.varied_set_trial(s, positive=i % 2 == 0, rng=rng)
        assert len(set(t.series)) == s and (t.probe in t.series) == t.positive
        if t.positive:
            position_hits[t.probe_position] += 1
    # Given a positive trial every serial position is equally likely: 1/s each.
    for k in range(1, s + 1):
        assert position_hits[k] / (n / 2) == pytest.approx(1 / s, abs=0.015)


def test_varied_set_digits_are_uniform():
    rng = np.random.default_rng(2)
    counts = Counter(d for _ in range(20000) for d in design.varied_set_trial(1, True, rng).series)
    assert min(counts.values()) / max(counts.values()) > 0.9 and len(counts) == 10


def test_a_set_size_without_a_spare_digit_is_refused():
    with pytest.raises(ValueError):
        design.varied_set_trial(10, False, np.random.default_rng(0))


def test_the_varied_set_session_is_24_practice_then_144_test_balanced_over_cells():
    task = varied_task()
    trials = served(task.make_source(task.params, np.random.default_rng(0)))
    stages = [c.params["stage"] for c, _ in trials]
    assert stages == ["practice"] * 24 + ["test"] * 144
    for stage, per_cell in (("practice", 2), ("test", 12)):
        cells = Counter((c.params["set_size"], c.params["probe_type"])
                        for c, _ in trials if c.params["stage"] == stage)
        assert len(cells) == 12 and set(cells.values()) == {per_cell}
    assert sum(1 for _, brk in trials if brk) == 1  # one rest, between practice and test


def test_the_varied_set_order_is_random_and_seeded():
    task = varied_task()
    a = [c.params for c, _ in served(task.make_source(task.params, np.random.default_rng(5)))]
    b = [c.params for c, _ in served(task.make_source(task.params, np.random.default_rng(5)))]
    c = [c.params for c, _ in served(task.make_source(task.params, np.random.default_rng(6)))]
    assert a == b and a != c


# ------------------------------------------------------------ experiment 2


def test_roles_partition_the_digits_and_the_population_has_the_papers_frequencies():
    roles = design.assign_roles(np.random.default_rng(3))
    pop = design.population(roles)
    assert len(pop) == 15
    freq = Counter(cell.digit for cell in pop)
    for role, copies in design.ROLE_COPIES.items():
        for digit in roles[role]:
            assert freq[digit] == copies
    # The positive set is 4/15 of the population whatever its size (paper: p. 653).
    for s in (1, 2, 4):
        positive = design.positive_set(roles, s)
        assert len(positive) == s
        assert sum(cell.digit in positive for cell in pop) == 4
    sets = [set(design.positive_set(roles, s)) for s in (1, 2, 4)]
    assert not (sets[0] & sets[1] or sets[0] & sets[2] or sets[1] & sets[2])


def test_a_bad_role_assignment_is_refused():
    with pytest.raises(ValueError):
        design.population({"x": (1,), "y": (2, 3), "z": (4, 5, 6, 7), "w": (8, 9, 9)})


def test_the_fixed_set_session_is_three_parts_of_60_practice_and_120_test():
    task = fixed_task()
    trials = served(task.make_source(task.params, np.random.default_rng(0)))
    assert len(trials) == 3 * 180
    parts = [c.params["part"] for c, _ in trials]
    assert parts == [1] * 180 + [2] * 180 + [3] * 180
    sizes = {c.params["part"]: c.params["set_size"] for c, _ in trials}
    assert sorted(sizes.values()) == [1, 2, 4]
    for part in (1, 2, 3):
        block = [c.params for c, _ in trials if c.params["part"] == part]
        assert [b["stage"] for b in block] == ["practice"] * 60 + ["test"] * 120
        test = [b for b in block if b["stage"] == "test"]
        positives = sum(b["probe_type"] == "positive" for b in test)
        assert positives == 32  # 4/15 of 120
        assert all((str(b["probe_digit"]) in b["positive_set"]) == (b["probe_type"] == "positive")
                   for b in block)
        assert len({b["positive_set"] for b in block}) == 1
    assert sum(1 for _, brk in trials if brk) == 5  # after each block but the last


def test_part_order_can_be_fixed_or_shortened():
    task = FixedSetMemoryScanningTask(fixed_task().params.model_copy(update={"part_order": [4, 1]}))
    trials = served(task.make_source(task.params, np.random.default_rng(0)))
    assert [c.params["set_size"] for c, _ in trials[::180]] == [4, 1]


@pytest.mark.parametrize("bad", [[], [1, 1], [3], [1, 2, 4, 2]])
def test_a_bad_part_order_is_refused(bad):
    data = fixed_task().params.model_dump()
    data["part_order"] = bad
    with pytest.raises(ValueError):
        FixedSetParams.model_validate(data)


def test_the_37_second_interval_must_add_up():
    data = fixed_task().params.model_dump()
    data["iti"] = {"ms": 2000}
    with pytest.raises(ValueError, match="3.7 s"):
        FixedSetParams.model_validate(data)
    data["iti"] = {"frames": 162}
    with pytest.raises(ValueError, match="in ms"):
        FixedSetParams.model_validate(data)


@pytest.mark.parametrize("update", [
    {"positive_key": "f"}, {"positive_key": "p"}, {"negative_key": "5"},
    {"negative_key": "return"}, {"warning_symbol": "7"}, {"subject_kind": "monkey"},
    {"set_sizes": [1, 1]}, {"set_sizes": [0, 2]}, {"set_sizes": [10]},
    {"paradigm": {"kind": "constant", "n_per_condition": 2}}])
def test_bad_params_are_refused(update):
    data = varied_task().params.model_dump()
    data.update(update)
    with pytest.raises(ValueError):
        VariedSetParams.model_validate(data)


def test_the_launch_estimate_counts_the_papers_trials():
    for task, n, breaks in ((varied_task(), 168, 1), (fixed_task(), 540, 5)):
        schedule = task.duration_schedule(task.params, np.random.default_rng(0))
        assert schedule.n_trials == n and schedule.breaks == breaks
        timing = task.trial_timing(schedule.conditions()[0], 60.0)
        assert timing.min_s > 0


def test_a_rehearsal_shrinks_both_blocks():
    from alhazen.modes.rehearsal import shrink_params

    for task in (varied_task(), fixed_task()):
        params, reductions = shrink_params(task.params)
        assert {r.where for r in reductions} == {"practice.n_per_condition",
                                                 "paradigm.n_per_condition"}
        type(task)(params)


def test_the_rehearsal_of_the_fixed_set_keeps_its_interval_rule():
    with pytest.raises((ValueError, ConfigError)):
        FixedSetParams.model_validate({**fixed_task().params.model_dump(),
                                       "warning_duration": {"ms": 900}})


# ------------------------------------------------------------ the simulated subject


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def ev(name, **payload):
    from alhazen.core.events import Event

    return Event(name=name, t=0.0, trial_index=1, payload=payload)


def test_the_simulated_subject_answers_from_memory_and_recalls():
    clock = Clock()
    obs = SimulatedObserver(seed=0, p_error=0.0, p_recall_error=0.0, clock=clock)
    for position, digit in enumerate((3, 8, 1), start=1):
        obs.on_event(ev("ITEM_ON", position=position, digit=digit))
    obs.on_event(ev("PROBE_DIGIT", digit=8))
    clock.t = 5.0
    assert obs.poll().keys == ("j",)
    obs.on_event(ev("PROBE_DIGIT", digit=4))
    clock.t = 10.0
    assert obs.poll().keys == ("f",)
    obs.on_event(ev("RECALL_ON"))
    clock.t = 20.0
    assert obs.poll().keys == ("3", "8", "1", "return")
    obs.on_event(ev("SET_ANNOUNCED", digits=[2, 9], part=1))
    clock.t = 30.0
    assert obs.poll().keys == ("space",)
    assert obs.memory == [2, 9]


def test_the_simulated_subjects_rt_follows_its_linear_model():
    obs = SimulatedObserver(seed=1, intercept_ms=400, slope_ms=40)
    means = [np.mean([obs.rt_ms(s) for _ in range(4000)]) for s in (1, 6)]
    assert means[0] == pytest.approx(440, abs=6) and means[1] == pytest.approx(640, abs=6)
