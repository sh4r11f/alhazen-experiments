"""Short simulated sessions end to end, headless, as `--mode simulate` runs them."""

from __future__ import annotations

import pandas as pd

from campbell_robson1968 import analysis


def test_2ifc_session_writes_every_cell_with_realised_values(simulated_runs):
    df = pd.read_csv(next(simulated_runs["2ifc"].glob("*_trials.csv")))
    done = df[df["outcome"].isin(["CORRECT", "WRONG"])]
    assert set(done["cell"]) == {"sine-0.5", "sine-1", "sine-2", "sine-4", "sine-8"}
    assert (done.groupby("cell").size() >= 6).all()
    for col in (
        "contrast_requested",
        "contrast_realised",
        "fundamental_contrast_realised",
        "signal_interval",
        "phase_deg",
        "noise_seed",
        "px_per_cycle",
        "t_interval1_on",
        "t_interval2_on",
        "t_response_cue",
    ):
        assert col in df, col
    assert set(done["signal_interval"]) <= {1, 2}
    assert (done["px_per_cycle"] >= 4).all()


def test_square_session_interleaves_both_waveforms(simulated_runs):
    df = pd.read_csv(next(simulated_runs["square"].glob("*_trials.csv")))
    assert set(df["waveform"].dropna()) == {"sine", "square"}
    sq = df[df["waveform"] == "square"]
    ratio = sq["fundamental_contrast_realised"] / sq["contrast_realised"]
    assert ((ratio - 4 / 3.14159265).abs() < 0.05).all()


def test_adjustment_session_writes_settings(simulated_runs):
    df = pd.read_csv(next(simulated_runs["adjustment"].glob("*_trials.csv")))
    sets = df[df["outcome"] == "SET"]
    # simulate mode rehearses one setting per cell (alhazen shrinks n_per_condition to 1)
    assert set(sets["cell"]) == {"sine-0.5", "sine-1", "sine-2", "sine-4", "sine-8"}
    table = analysis.adjustment_table(df)
    assert len(table) == 5 and (table["sensitivity"] > 1).all()
