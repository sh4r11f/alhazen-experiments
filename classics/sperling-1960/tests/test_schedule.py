"""The order trials are served in, and the arrays they show."""

from __future__ import annotations

from collections import Counter
from itertools import groupby

import numpy as np
import pytest
from alhazen.config.loader import load_params
from alhazen.core.engine import TrialResult
from alhazen.core.trial import Outcome

from sperling1960.materials import CUE_EVENTS, MATERIALS, draw_array
from sperling1960.schedule import SeriesSchedule, build_plan
from sperling1960.task import PROJECT, PartialReportTask, PartialReportTaskParams

DONE = Outcome("REPORTED", completed=True)
MISSED = Outcome("NO_RESPONSE", completed=False)


def main_task():
    return PartialReportTask(load_params(PROJECT / "configs" / "task.yaml",
                                         PartialReportTaskParams))


def serve_all(source, fail_at=()):
    served = []
    while (cond := source.next()) is not None:
        served.append(cond)
        outcome = MISSED if len(served) in fail_at else DONE
        source.record(cond, TrialResult(outcome=outcome, record={}))
    return served


def blocks(served):
    return [list(g) for _, g in groupby(served, key=lambda c: c.params["block"])]


def test_the_main_plan_is_four_alternating_series_of_six_delay_blocks():
    task = main_task()
    served = serve_all(task.make_source(task.params, np.random.default_rng(1)))
    assert len(served) == 6 * 4 * (2 + 6)
    bs = blocks(served)
    delays = [b[0].params["delay_s"] for b in bs]
    asc = [-0.10, 0.0, 0.15, 0.30, 0.50, 1.0]
    assert delays == asc + asc[::-1] + asc + asc[::-1]  # ascending first (paper p. 10)
    for b in bs:
        assert [c.params["sample"] for c in b] == [True, True] + [False] * 6
        tests = Counter(c.params["cued_row"] for c in b if not c.params["sample"])
        assert tests == {0: 2, 1: 2, 2: 2}  # rows balanced within each block
    per_delay = Counter(c.params["delay_s"] for c in served if not c.params["sample"])
    assert set(per_delay.values()) == {24}  # at least 20 per delay (paper p. 8)


def test_a_missed_trial_comes_back_inside_its_own_block():
    task = main_task()
    served = serve_all(task.make_source(task.params, np.random.default_rng(1)), fail_at={5, 8})
    # Trial 5 (block 0) and trial 8 (the last of block 0) both missed: block 0 grows by two.
    assert [len(b) for b in blocks(served)][:2] == [10, 8]
    assert len(served) == 6 * 4 * 8 + 2


def test_the_duration_estimate_counts_the_plan():
    task = main_task()
    plan = task.duration_schedule(task.params, np.random.default_rng(0))
    assert plan.n_trials == 192
    timing = task.trial_timing(plan.conditions()[0], 60.0)
    assert timing.min_s > 0.5


def test_a_whole_report_plan_has_one_block_per_material():
    plan = build_plan(report="whole", materials=["3/3", "4/4"], delays=[], n_series=1,
                      first_series="ascending", samples_per_block=2, test_per_block=15,
                      rng=np.random.default_rng(0))
    assert len(plan) == 2 * 17
    assert {c.params["cued_row"] for c in plan} == {None}


@pytest.mark.parametrize("name", sorted(MATERIALS))
def test_arrays_have_the_materials_shape(name):
    m = MATERIALS[name]
    rng = np.random.default_rng(3)
    for _ in range(200):
        rows = draw_array(m, "BDFGJKLMNQSTVWXYZ", "0123456789", rng)
        assert len(rows) == m.n_rows and all(len(r) == m.n_cols for r in rows)
        for r in rows:
            n_digits = sum(ch.isdigit() for ch in r)
            assert n_digits == (2 if m.letters_and_numbers else 0)  # paper p. 4
            assert all(ch.isdigit() or ch in "BDFGJKLMNQSTVWXYZ" for ch in r)
    assert len(CUE_EVENTS[m.n_rows]) == m.n_rows


def test_letters_are_drawn_with_replacement():
    # The paper's information values are n x log2(21) bits (p. 4): independent draws, so a
    # card can repeat a letter (its Fig. 2 shows LQDKKJ).
    rng = np.random.default_rng(0)
    rows = [draw_array(MATERIALS["4/4"], "BDFGJKLMNQSTVWXYZ", "0123456789", rng) for _ in range(300)]
    assert any(len(set(r)) < len(r) for card in rows for r in card)


def test_build_plan_with_a_series_order_starting_descending():
    plan = build_plan(report="partial", materials=["3/3"], delays=[0.0, 0.5, 1.0], n_series=2,
                      first_series="descending", samples_per_block=0, test_per_block=2,
                      rng=np.random.default_rng(0))
    assert [c.params["delay_s"] for c in plan] == [1.0, 1.0, 0.5, 0.5, 0.0, 0.0,
                                                    0.0, 0.0, 0.5, 0.5, 1.0, 1.0]
    assert isinstance(SeriesSchedule(plan).remaining(), int)
