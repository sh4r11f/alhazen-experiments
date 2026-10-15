"""The analysis measures on hand-made rows."""

from __future__ import annotations

import pandas as pd
import pytest

from funahashi1989 import analysis


def rows():
    base = dict(cue_angle_deg=0.0, delay_s=3.0, delay_index=1, endpoint_measured=True,
                endpoint_reference_x_dva=13.0, endpoint_reference_y_dva=0.0,
                fixation_x_dva=0.0, fixation_y_dva=0.0, saccade_latency_ms=250.0,
                target_window_dva=3.0)
    return pd.DataFrame([
        {**base, "trial_index": 1, "outcome": "CORRECT", "endpoint_x_dva": 12.0,
         "endpoint_y_dva": 1.0, "endpoint_error_dva": 2 ** 0.5},
        {**base, "trial_index": 2, "outcome": "INACCURATE", "endpoint_x_dva": 0.0,
         "endpoint_y_dva": 13.0, "endpoint_error_dva": 13 * 2 ** 0.5},
        {**base, "trial_index": 3, "outcome": "FIX_BREAK", "endpoint_x_dva": None,
         "endpoint_y_dva": None, "endpoint_error_dva": None},
    ])


def test_only_responses_are_measured_and_the_direction_error_is_signed():
    r = analysis.responses(rows())
    assert list(r["trial_index"]) == [1, 2]
    assert r["direction_error_deg"].iloc[1] == pytest.approx(90.0)
    assert r["amplitude_gain"].iloc[1] == pytest.approx(1.0)


def test_the_summary_counts_correct_responses_by_delay():
    s = analysis.summary(analysis.responses(rows()), ["delay"])
    assert s.loc[3.0, "n"] == 2 and s.loc[3.0, "pct_correct"] == pytest.approx(50.0)
