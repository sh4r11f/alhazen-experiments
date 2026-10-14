"""The analysis helpers the notebook uses."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from moore_fallah2001.analysis import (
    block_table,
    fit_asymptote,
    performance,
    threshold_reduction_pct,
)


def test_the_asymptotic_fit_recovers_a_and_b():
    x = np.arange(1, 16)
    levels = 60.0 - 25.0 * x / (3.0 + x)
    fit = fit_asymptote(levels, start=60.0)
    assert fit.a == pytest.approx(25.0, rel=1e-3)
    assert fit.b == pytest.approx(3.0, rel=1e-2)
    assert fit.threshold_pct == pytest.approx(35.0, rel=1e-3)
    assert fit.converged


def test_a_staircase_still_falling_is_flagged_not_reported():
    levels = 60.0 - 4.0 * np.arange(1, 11)  # a straight line: no asymptote in 10 blocks
    fit = fit_asymptote(levels, start=60.0)
    assert fit.at_bound and not fit.converged


def test_threshold_reduction_matches_the_papers_example():
    # Fig. 2: 30% with stimulation vs 44% without.
    assert threshold_reduction_pct(30.0, 44.0) == pytest.approx(31.818, rel=1e-3)


def test_blocks_and_performance_are_rebuilt_from_trials():
    rows = []
    for block, outs in [(1, ["HIT", "MISS", "CORRECT_REJECTION"]),
                        (2, ["MISS", "MISS", "CORRECT_REJECTION"])]:
        for slot, (tt, out) in enumerate(zip(["blink", "blink", "catch"], outs, strict=True)):
            rows.append({"staircase": "control", "block": block, "dim_pct": 60.0 - 4 * (block - 1),
                         "trial_type": tt, "outcome": out, "completed": True, "rt_ms": 300.0,
                         "slot": slot})
    rows.append({"staircase": "control", "block": 2, "dim_pct": 56.0, "trial_type": "blink",
                 "outcome": "FIX_BREAK", "completed": False, "rt_ms": np.nan, "slot": 0})
    trials = pd.DataFrame(rows)
    blocks = block_table(trials)
    assert list(blocks["block_success"]) == [True, False]
    perf = performance(trials).iloc[0]
    assert perf["n_trials"] == 6
    assert perf["hit_rate"] == pytest.approx(0.25)
    assert perf["pct_correct"] == pytest.approx(100 * 3 / 6)
