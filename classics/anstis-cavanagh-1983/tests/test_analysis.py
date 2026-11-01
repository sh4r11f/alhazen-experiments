"""The analysis recovers what the simulated observer was given (software check only)."""

from __future__ import annotations

import pandas as pd
import pytest

from anstiscavanagh1983 import analysis as A
from anstiscavanagh1983.simulate import SimulatedObserver


def synthetic(n=20, seed=4):
    obs = SimulatedObserver(seed=seed)
    rows = []
    for level in [8.0 + 0.25 * i for i in range(17)]:
        for step in (1, -1):
            for _ in range(n):
                info = dict(test_colour="red", reference_colour="green", reference_cd_m2=13.4,
                            test_cd_m2=level, step=step, spatial_freq_cpd=2.5)
                rows.append(dict(test_cd_m2=level, step=step, response_key=obs.report(info),
                                 completed=True, reference_cd_m2=13.4))
    true = obs.pse(dict(test_colour="red", reference_colour="green", reference_cd_m2=13.4,
                        spatial_freq_cpd=2.5))
    return pd.DataFrame(rows), true


def test_reports_are_coded_relative_to_the_step():
    df = pd.DataFrame({"test_cd_m2": [9, 9, 9, 9], "step": [1, -1, 1, -1],
                       "response_key": ["right", "right", "down", "left"],
                       "completed": [True] * 4, "reference_cd_m2": [13.4] * 4})
    assert list(A.code_reports(df)["report"]) == [
        "test_lighter", "reference_lighter", "neither", "test_lighter"]


def test_pse_estimates_recover_the_simulated_value():
    df, true = synthetic()
    summ = A.constant_summary(df)
    assert A.pse_crossing(summ) == pytest.approx(true, rel=0.02)
    fit = A.fit_ordered_probit(df)
    assert fit["pse_cd_m2"] == pytest.approx(true, rel=0.02)
    assert fit["sigma_ln"] == pytest.approx(0.025, rel=0.4)
    assert fit["delta_ln"] == pytest.approx(0.03, rel=0.4)
    lo, hi, peak = A.neither_half_max(summ)
    assert lo < true < hi
    assert 0 < A.indifference_contrast(summ, A.pse_crossing(summ)) < 0.05


def test_adjustment_summary_and_relative_efficiency():
    motion = pd.DataFrame({"outcome": ["SET"] * 4, "task": ["min-motion-adjust"] * 4,
                           "layout": ["four_stroke"] * 4, "test_colour": ["red"] * 4,
                           "reference_colour": ["grey"] * 4, "spatial_freq_cpd": [2.5] * 4,
                           "rate_hz": [15.0] * 4, "test_cd_m2": [12.0, 12.2, 11.8, 12.0],
                           "reference_cd_m2": [13.6] * 4})
    s = A.adjust_summary(motion)
    assert s["mean_cd_m2"].iloc[0] == pytest.approx(12.0) and s["n"].iloc[0] == 4
    flick = s.assign(mean_cd_m2=[12.6])
    eff = A.relative_efficiency(s, flick)
    assert eff["relative_efficiency"].iloc[0] == pytest.approx(12.6 / 12.0)
