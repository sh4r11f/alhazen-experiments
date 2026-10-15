"""The measures recover what was put in, on synthetic spike trains (not data)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from moore_armstrong2003 import analysis


def fake_trials(n=40, seed=0):
    """Completed trials on a regular clock: 3 RF conditions x stim/control."""
    rng = np.random.default_rng(seed)
    rows, t = [], 10.0
    for i in range(n):
        rf = ["none", "orthogonal", "preferred"][i % 3]
        stim = "stim" if (i // 3) % 2 else "control"
        on = t + 1.0
        mark = on + rng.uniform(0.2, 0.5)
        rows.append({"trial_index": i + 1, "outcome": "COMPLETED", "rf_stimulus": rf,
                     "distracter_stimulus": "preferred" if i % 2 else "none",
                     "display": f"rf-{rf}", "stimulation": stim, "t_trial_start": t,
                     "t_vis_on": on, "t_vis_off": on + 1.75,
                     "t_stim_trigger": mark if stim == "stim" else np.nan,
                     "t_control_mark": mark if stim == "control" else np.nan,
                     "t_trial_end": on + 1.8})
        t += 4.0
    return pd.DataFrame(rows)


def effect(gain, n=600, seed=1):
    trials = fake_trials(n)
    w = analysis.Windows()
    spikes = analysis.synthetic_spikes_for_testing(trials, np.random.default_rng(seed), w,
                                                   stim_gain_hz=gain)
    return analysis.stimulation_effect(analysis.trial_rates(trials, spikes, w))


def test_no_injected_effect_gives_none():
    e = effect(0.0)
    assert (e["effect"].abs() < 4 * e["effect_sem"]).all(), e


def test_an_injected_effect_is_recovered():
    e = effect(30.0)
    assert e["effect"].to_numpy() == pytest.approx([30.0] * 3, abs=12.0), e


def test_onset_activity_is_normalised_to_the_preferred_stimulus_alone():
    e = effect(0.0)
    assert e.loc[e["rf_stimulus"] == "preferred", "onset_norm"].iloc[0] == pytest.approx(1, abs=.1)


def test_the_post_train_window_skips_the_train():
    trials = fake_trials(3)
    w = analysis.Windows()
    row = trials.iloc[1]
    mark = row["t_stim_trigger"] if row["stimulation"] == "stim" else row["t_control_mark"]
    during_train = np.array([mark + 0.01, mark + 0.02])  # inside the 50-ms train
    rates = analysis.trial_rates(trials, during_train, w)
    assert (rates["post_train_rate"] == 0).all()


def test_breaks_after_the_trigger_are_counted_by_condition():
    trials = fake_trials(6)
    trials.loc[trials.index[-1], "outcome"] = "BROKE_FIX_AFTER_TRIGGER"
    out = analysis.break_after_trigger(trials)
    assert out["n_broke"].sum() == 1
