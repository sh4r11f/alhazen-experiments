"""The analysis recovers what a planted observer was given (hirisblake1992.analysis)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from hirisblake1992 import analysis
from hirisblake1992.simulate import SimulatedObserver, p_choose_test

LEVELS = [-20.0, -10.0, 0.0, 10.0, 20.0, 30.0, 40.0, 50.0, 60.0]


def synthetic(n_per_level=200, shift=40.0, sigma=10.0, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for mode, s in (("unidirectional", shift), ("random", 0.0)):
        for lvl in LEVELS:
            p = p_choose_test(lvl, 40.0, s, sigma)
            for chose in rng.random(n_per_level) < p:
                rows.append({"adapt_mode": mode, "test_signal_pct": lvl,
                             "outcome": "CHOSE_TEST" if chose else "CHOSE_REFERENCE"})
    rows.append({"adapt_mode": "random", "test_signal_pct": 0.0, "outcome": "NO_RESPONSE"})
    return pd.DataFrame(rows)


def test_the_probit_fit_recovers_the_planted_pse_and_spread():
    df = synthetic()
    adapted = analysis.fit_mode(df, "unidirectional")
    control = analysis.fit_mode(df, "random")
    assert adapted.pse == pytest.approx(0.0, abs=1.5)
    assert control.pse == pytest.approx(40.0, abs=1.5)
    assert adapted.sigma == pytest.approx(10.0, rel=0.15)
    assert control.n == 9 * 200  # the NO_RESPONSE trial is not a measurement


def test_aftereffect_strength_is_the_pse_difference_with_an_interval():
    out = analysis.aftereffect_strength(synthetic(n_per_level=60), n_boot=100)
    assert out["aftereffect_pct"] == pytest.approx(40.0, abs=4.0)
    lo, hi = out["aftereffect_ci95"]
    assert lo < out["aftereffect_pct"] < hi


def test_the_table_counts_choices_per_level():
    tab = analysis.psychometric_table(synthetic(n_per_level=10))
    assert set(tab["adapt_mode"]) == {"unidirectional", "random"}
    assert (tab["n"] == 10).all() and (tab["k"] <= tab["n"]).all()


def test_the_simulated_observer_has_no_aftereffect_without_adaptation():
    obs = SimulatedObserver(seed=1, lapse=0.0)
    assert obs.shift_for("random") == 0.0 and obs.shift_for("unidirectional") == 40.0
    assert np.mean([obs.choose(40.0, "random") for _ in range(4000)]) == pytest.approx(0.5,
                                                                                      abs=0.03)
    assert np.mean([obs.choose(0.0, "unidirectional") for _ in range(4000)]) == pytest.approx(
        0.5, abs=0.03)
