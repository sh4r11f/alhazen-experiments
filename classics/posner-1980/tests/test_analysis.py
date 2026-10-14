"""The paper's measures, checked on tables with a known, planted answer."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from posner1980 import analysis


def planted(valid=250.0, neutral=265.0, invalid=300.0, n=40, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for validity, mean in (("valid", valid), ("neutral", neutral), ("invalid", invalid)):
        for rt in rng.normal(mean, 1e-9, n):
            rows.append(dict(validity=validity, outcome="DETECTED", completed=True, rt_ms=rt))
    rows += [dict(validity="valid", outcome="DETECTED", completed=True, rt_ms=40.0)]  # fast guess
    rows += [dict(validity="neutral", outcome="MISS", completed=True, rt_ms=np.nan)]
    rows += [dict(validity="catch", outcome="CORRECT_REJECTION", completed=True, rt_ms=np.nan)] * 9
    rows += [dict(validity="catch", outcome="FALSE_ALARM", completed=True, rt_ms=230.0)]
    rows += [dict(validity="valid", outcome="ANTICIPATION", completed=False, rt_ms=np.nan)] * 2
    rows += [dict(validity="invalid", outcome="FIXATION_BREAK", completed=False, rt_ms=np.nan)] * 3
    return pd.DataFrame(rows)


def test_benefit_and_cost_are_measured_against_neutral():
    cb = analysis.costs_and_benefits(planted())
    assert cb["benefit_ms"] == pytest.approx(15.0)
    assert cb["cost_ms"] == pytest.approx(35.0)
    assert cb["validity_effect_ms"] == pytest.approx(50.0)


def test_fast_guesses_are_left_out_of_the_means():
    table = analysis.rt_by_condition(planted())
    assert table.loc["valid", "count"] == 40
    assert table.loc["valid", "mean"] == pytest.approx(250.0)
    assert list(table.index) == ["valid", "neutral", "invalid"]


def test_the_response_summary_counts_what_a_simple_rt_design_must_report():
    s = analysis.response_summary(planted())
    assert s["false_alarm_rate"] == pytest.approx(0.1)
    assert s["miss_rate"] == pytest.approx(1 / 122)
    assert (s["fast_guesses"], s["anticipations"], s["fixation_breaks"]) == (1, 2, 3)


def test_incomplete_attempts_never_enter_the_rts():
    df = planted()
    df.loc[df["outcome"] == "ANTICIPATION", "rt_ms"] = 1.0
    assert analysis.rt_by_condition(df).loc["valid", "count"] == 40
