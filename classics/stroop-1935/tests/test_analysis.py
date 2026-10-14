"""The paper's measures, on trials whose answer is known."""

from __future__ import annotations

import pandas as pd
import pytest

from stroop1935.analysis import STROOP_1935, interference, item_measures, load_trials, sheet_times


def trials_frame():
    rows = []
    # Block 1: NC, 4 items of 500 ms. Block 2: NCWd, 4 items of 900 ms, one of
    # them an error corrected at 1300 ms and one never corrected.
    for i in range(4):
        rows.append(dict(block=1, phase="test", test="NC", form=1, position=i + 1,
                         outcome="CORRECT", first_correct=True, rt_ms=500.0, rt_correct_ms=500.0))
    rows.append(dict(block=2, phase="test", test="NCWd", form=2, position=1, outcome="CORRECT",
                     first_correct=True, rt_ms=900.0, rt_correct_ms=900.0))
    rows.append(dict(block=2, phase="test", test="NCWd", form=2, position=2, outcome="CORRECTED",
                     first_correct=False, rt_ms=900.0, rt_correct_ms=1300.0))
    rows.append(dict(block=2, phase="test", test="NCWd", form=2, position=3,
                     outcome="UNCORRECTED", first_correct=False, rt_ms=900.0,
                     rt_correct_ms=float("nan")))
    rows.append(dict(block=2, phase="test", test="NCWd", form=2, position=4, outcome="CORRECT",
                     first_correct=True, rt_ms=800.0, rt_correct_ms=800.0))
    rows.append(dict(block=2, phase="practice", test="NCWd", form=0, position=1,
                     outcome="CORRECT", first_correct=True, rt_ms=5000.0, rt_correct_ms=5000.0))
    rows.append(dict(block=2, phase="test", test="NCWd", form=2, position=5,
                     outcome="NO_RESPONSE", first_correct=None, rt_ms=float("nan"),
                     rt_correct_ms=float("nan")))
    return pd.DataFrame(rows)


def test_a_sheet_charges_an_uncorrected_error_twice_the_mean_time_per_item():
    sheets = sheet_times(trials_frame()).set_index("block")
    assert sheets.loc[1, "time_s"] == pytest.approx(2.0)
    assert sheets.loc[1, "per_100_s"] == pytest.approx(50.0)
    mean = (0.9 + 1.3 + 0.8) / 3
    assert sheets.loc[2, "time_s"] == pytest.approx(3.0 + 2 * mean)
    assert sheets.loc[2, "n_items"] == 4  # practice and the missed item are not counted
    assert sheets.loc[2, "n_uncorrected"] == 1 and sheets.loc[2, "n_first_errors"] == 2


def test_interference_is_the_difference_and_its_proportion_of_the_control():
    out = interference(sheet_times(trials_frame())).iloc[0]
    assert out["task"] == "color-naming"
    assert out["D_s"] == pytest.approx(out["interference_per_100_s"] - 50.0)
    assert out["paper_D_over_control"] == pytest.approx(47.0 / 63.3)
    assert STROOP_1935["RCNd"]["mean_s"] - STROOP_1935["RCNb"]["mean_s"] == pytest.approx(2.3)


def test_item_measures_use_right_first_responses():
    m = item_measures(trials_frame()).set_index("test")
    assert m.loc["NCWd", "error_rate"] == pytest.approx(0.5)
    assert m.loc["NCWd", "median_rt_ms"] == pytest.approx(850.0)


def test_a_trials_file_reads_back_with_false_kept_false(tmp_path):
    frame = trials_frame()
    frame.to_csv(tmp_path / "x_trials.csv", index=False)
    back = load_trials(tmp_path)
    assert back["first_correct"].tolist()[:6] == [True] * 5 + [False]
