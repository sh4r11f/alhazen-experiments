"""The analysis recovers a known, programmed effect (the simulated subject has none)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from raymond1992 import analysis


def synthetic(blink: dict[int, float], control: float = 0.9, fa: float = 0.1,
              target: float = 0.8, n: int = 400, seed: int = 0) -> pd.DataFrame:
    """Two subjects, experimental + control, detection probabilities as given."""
    rng = np.random.default_rng(seed)
    rows = []
    for subject in ("sub-a", "sub-b"):
        for condition in ("experimental", "control"):
            for pos in [None, *range(9)]:
                for _ in range(n):
                    tc = bool(rng.random() < target) if condition == "experimental" else None
                    if pos is None:
                        p = fa
                    elif condition == "experimental":
                        p = blink[pos] if tc else 0.0  # wrong-target trials must be dropped
                    else:
                        p = control
                    rows.append({"subject": subject, "source": subject, "condition": condition,
                                 "completed": True, "practice": False,
                                 "probe_present": pos is not None, "probe_pos": pos,
                                 "probe_reported": bool(rng.random() < p),
                                 "target_correct": tc,
                                 "target_report_pos": 0 if tc else 1})
    return pd.DataFrame(rows)


BLINK = {0: 0.85, 1: 0.8, 2: 0.5, 3: 0.45, 4: 0.5, 5: 0.6, 6: 0.8, 7: 0.85, 8: 0.85}


def test_detection_is_conditioned_on_a_correct_target():
    df = analysis.clean(synthetic(BLINK))
    curve = analysis.group_curve(analysis.detection_by_position(df))
    exp = curve[curve["condition"] == "experimental"].set_index("probe_pos")["mean"]
    ctl = curve[curve["condition"] == "control"].set_index("probe_pos")["mean"]
    for pos, p in BLINK.items():
        assert exp[pos] == pytest.approx(p, abs=0.05)
        assert ctl[pos] == pytest.approx(0.9, abs=0.05)


def test_false_alarms_and_target_errors():
    df = analysis.clean(synthetic(BLINK))
    fa = analysis.false_alarms(df).groupby("condition")["false_alarm_rate"].mean()
    assert fa.to_dict() == pytest.approx({"control": 0.1, "experimental": 0.1}, abs=0.03)
    assert analysis.target_accuracy(df)["p_target_correct"].mean() == pytest.approx(0.8, abs=0.03)
    table = analysis.target_report_positions(df)
    assert set(table.index) == {"probe absent", "probe 0", "probe +1", "probe +2"}
    absent = df[(df["condition"] == "experimental") & ~df["probe_present"]]
    # Every error in this synthetic set is a +1 intrusion.
    assert table.loc["probe absent", "1"] == pytest.approx(1 - absent["target_correct"].mean())
    assert table.loc["probe absent", "0"] == pytest.approx(absent["target_correct"].mean())


def test_practice_and_incomplete_trials_are_excluded():
    df = synthetic(BLINK, n=5)
    df.loc[:9, "practice"] = True
    df.loc[10:19, "completed"] = False
    assert len(analysis.clean(df)) == len(df) - 20
