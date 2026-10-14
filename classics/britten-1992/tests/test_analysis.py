"""The analysis functions recover what they are given (Eqs. 1-4 of the paper)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from britten1992.analysis import (
    THRESHOLD_P,
    compare_fits,
    fit_psychometric,
    fit_weibull,
    measured,
    neurometric_fit,
    neurometric_table,
    psychometric_table,
    roc_area,
    weibull,
)

LEVELS = np.array([0.8, 1.6, 3.2, 6.4, 12.8, 25.6, 51.2])


def test_alpha_is_the_82_percent_point_and_zero_is_chance():
    assert weibull(6.1, 6.1, 1.17) == pytest.approx(THRESHOLD_P)
    assert THRESHOLD_P == pytest.approx(0.816, abs=1e-3)
    assert weibull(0.0, 6.1, 1.17) == pytest.approx(0.5)


def test_a_fit_recovers_a_planted_psychometric_function():
    rng = np.random.default_rng(0)
    n = np.full(len(LEVELS), 400)
    k = rng.binomial(n, weibull(LEVELS, 6.1, 1.17))  # the paper's Fig. 4 example
    fit = fit_weibull(LEVELS, k, n)
    assert fit.alpha == pytest.approx(6.1, rel=0.12)
    assert fit.beta == pytest.approx(1.17, rel=0.2)


def test_the_free_asymptote_is_chosen_only_when_it_fits_better():
    rng = np.random.default_rng(1)
    n = np.full(len(LEVELS), 400)
    lapsing = rng.binomial(n, weibull(LEVELS, 6.0, 1.5, delta=0.9))
    assert fit_psychometric(pd.DataFrame({"coherence_pct": LEVELS, "n": n,
                                          "n_correct": lapsing})).equation == 2
    clean = rng.binomial(n, weibull(LEVELS, 6.0, 1.5))
    assert fit_psychometric(pd.DataFrame({"coherence_pct": LEVELS, "n": n,
                                          "n_correct": clean})).equation == 1


def test_roc_area_is_the_ideal_observers_proportion_correct():
    assert roc_area([1, 2, 3], [1, 2, 3]) == pytest.approx(0.5)
    assert roc_area([10, 11], [1, 2]) == 1.0
    assert roc_area([1, 2], [10, 11]) == 0.0


def test_the_comparison_of_two_curves_tells_same_from_different():
    rng = np.random.default_rng(2)
    n = np.full(len(LEVELS), 200)
    a = rng.binomial(n, weibull(LEVELS, 6.0, 1.2))
    b = rng.binomial(n, weibull(LEVELS, 6.0, 1.2))
    c = rng.binomial(n, weibull(LEVELS, 25.0, 1.2))
    assert compare_fits(LEVELS, a, n, b, n)[1] > 0.05
    assert compare_fits(LEVELS, a, n, c, n)[1] < 0.001


def trials_frame():
    rows = []
    rng = np.random.default_rng(3)
    for c in [0.0, *LEVELS]:
        for d in ("pref", "anti"):
            for _ in range(60):
                rate = 20 + (0.6 * c if d == "pref" else -0.3 * c)
                correct = rng.random() < weibull(c, 6.0, 1.3)
                rows.append({"coherence_pct": c, "direction": d, "correction": False,
                             "outcome": "CORRECT" if correct else "WRONG",
                             "spike_count": rng.poisson(max(rate, 1) * 2.0)})
    rows += [{"coherence_pct": 51.2, "direction": "pref", "correction": True, "outcome": "WRONG",
              "spike_count": 0}] * 50
    rows += [{"coherence_pct": 51.2, "direction": "pref", "correction": False,
              "outcome": "FIX_BREAK", "spike_count": 0}] * 50
    return pd.DataFrame(rows)


def test_correction_and_unfinished_trials_are_left_out():
    t = trials_frame()
    assert len(measured(t)) == 8 * 2 * 60
    table = psychometric_table(t)
    assert table.set_index("coherence_pct").loc[51.2, "n"] == 120


def test_a_neurometric_function_rises_from_chance_with_correlation():
    table = neurometric_table(trials_frame())
    assert table.iloc[0]["p_correct"] == pytest.approx(0.5, abs=0.12)
    assert table.iloc[-1]["p_correct"] > 0.99
    fit = neurometric_fit(table)
    assert 0.5 < fit.alpha < 30


def test_the_fit_recovers_the_simulated_observers_planted_threshold():
    from britten1992.simulate import SimulatedObserver

    obs = SimulatedObserver(seed=9, alpha_pct=8.0, beta=1.3, lapse=0.0)
    rows = []
    for c in [0.0, *LEVELS]:
        for d in ("pref", "anti"):
            for _ in range(150):  # ten blocks' worth per cell
                rows.append({"coherence_pct": c, "direction": d, "correction": False,
                             "outcome": "CORRECT" if obs.choose(d, c) == d else "WRONG"})
    fit = fit_psychometric(psychometric_table(pd.DataFrame(rows)))
    assert fit.alpha == pytest.approx(8.0, rel=0.15)
