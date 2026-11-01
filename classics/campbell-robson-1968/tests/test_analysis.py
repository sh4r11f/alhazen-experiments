"""The analysis recovers a planted observer: QUEST+ (alhazen's estimator, this folder's
grid) drives the toy observer offline, without the real-time session loop."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest
from alhazen.config.loader import load_params
from alhazen.paradigms.questplus import QuestPlusEstimator

from campbell_robson1968 import analysis
from campbell_robson1968.common import PROJECT
from campbell_robson1968.simulate import p_correct_2afc, toy_sensitivity
from campbell_robson1968.task import Csf2ifcParams


def synthetic(cells, n_trials, seed=0):
    p = load_params(PROJECT / "configs" / "task.yaml", Csf2ifcParams)
    q = p.paradigm.quest
    rng = np.random.default_rng(seed)
    rows = []
    for waveform, sf in cells:
        est = QuestPlusEstimator(
            q.intensities, q.thresholds, q.slopes, q.lower_asymptotes, q.lapse_rates, scale="log10"
        )
        thr = 1 / toy_sensitivity(sf)
        for _ in range(n_trials):
            x = est.next_intensity()
            c = 10**x
            eff = c * (4 / math.pi if waveform == "square" else 1.0)
            ok = bool(rng.random() < p_correct_2afc(eff, thr))
            est.add_response(x, ok)
            rows.append(
                {
                    "waveform": waveform,
                    "sf_cpd": sf,
                    "contrast_realised": c,
                    "n_codes": 50,
                    "outcome": "CORRECT" if ok else "WRONG",
                }
            )
    return pd.DataFrame(rows)


def test_fit_recovers_planted_thresholds():
    cells = [("sine", f) for f in (0.5, 2.0, 8.0)]
    table = analysis.csf_table(synthetic(cells, 120), n_boot=30)
    for _, row in table.iterrows():
        planted = toy_sensitivity(row["sf_cpd"])
        assert row["sensitivity"] == pytest.approx(planted, rel=0.35)
        assert row["sensitivity_ci_low"] <= row["sensitivity"] <= row["sensitivity_ci_high"]


def test_square_sine_ratio_is_reported_against_4_over_pi():
    cells = [(w, 1.0) for w in ("sine", "square")]
    table = analysis.csf_table(synthetic(cells, 150, seed=2), n_boot=0)
    ratio = analysis.square_sine_ratio(table)
    assert list(ratio["sf_cpd"]) == [1.0]
    assert ratio["predicted"].iloc[0] == pytest.approx(1.2732, abs=1e-4)
    assert ratio["ratio"].iloc[0] == pytest.approx(4 / math.pi, rel=0.35)


def test_threshold_point_and_fit_shape():
    assert analysis.P_THRESHOLD == pytest.approx(0.5 + 0.49 * (1 - math.exp(-1)))
    x = np.array([-2.0] * 50 + [-1.0] * 50)
    k = np.array([0] * 25 + [1] * 25 + [1] * 50)
    fit = analysis.fit_2afc(x, k)
    assert -2.0 < fit.log_threshold <= -1.0


def test_adjustment_threshold_is_the_geometric_mean():
    df = pd.DataFrame(
        {
            "outcome": ["SET"] * 4 + ["TIMEOUT"],
            "waveform": "sine",
            "sf_cpd": 2.0,
            "contrast_realised": [0.01, 0.04, 0.01, 0.04, 0.5],
        }
    )
    t = analysis.adjustment_table(df)
    assert t["threshold"].iloc[0] == pytest.approx(0.02)
    assert t["n_settings"].iloc[0] == 4
