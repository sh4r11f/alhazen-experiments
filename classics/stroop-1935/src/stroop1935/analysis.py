"""The original paper's measures, computed from one run's trials file.

Stroop's measure was the time to get through a whole sheet of 100 items, two
sheets per test, and the interference was the difference between the
interference test and its control (reprint p. 17, Tables I and III):

- Experiment 1: RCNd - RCNb (reading words in another ink vs in black);
- Experiment 2: NCWd - NC (naming the ink of words vs of squares), also as a
  proportion of NC (D/NC: 0.74 in the paper).

Here each item is a trial, so a sheet's time is rebuilt from its items: the
time from each item's onset to its right key, summed and scaled to 100 items.
An item whose error was never corrected is charged twice the sheet's mean time
per item, Stroop's rule for Experiment 2 (p. 17). The summed time leaves out
everything between items (eye movements on the printed sheet; the fixation
point and the gap here), so compare ratios and differences with the paper,
not absolute seconds. Trial-level measures (median reaction time of the first
response, error rate) are reported beside it, as modern trial-wise Stroop
tasks do.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

# Stroop (1935), whole group, seconds per 100 items (reprint Tables I and III).
STROOP_1935 = {
    "RCNb": {"mean_s": 41.00, "sd_s": 4.84, "n": 70, "table": "Table I, p. 17"},
    "RCNd": {"mean_s": 43.30, "sd_s": 6.15, "n": 70, "table": "Table I, p. 17"},
    "NC": {"mean_s": 63.3, "sd_s": 10.8, "n": 100, "table": "Table III, p. 18"},
    "NCWd": {"mean_s": 110.3, "sd_s": 18.8, "n": 100, "table": "Table III, p. 18"},
}
PAIRS = {"color-naming": ("NC", "NCWd"), "word-reading": ("RCNb", "RCNd")}
COMPLETED = ("CORRECT", "CORRECTED", "UNCORRECTED", "WRONG")


def load_trials(run: Path | str) -> pd.DataFrame:
    """The trials file of one run folder, with the word column as text."""
    path = next(Path(run).glob("*_trials.csv"))
    trials = pd.read_csv(path, keep_default_na=False, na_values={"rt_ms": [""],
                                                                  "rt_correct_ms": [""]})
    for col in ("rt_ms", "rt_correct_ms"):
        trials[col] = pd.to_numeric(trials[col], errors="coerce")
    # Written as True/False; empty on a trial with no key. Read as text first
    # so "False" can never turn into True.
    truth = {"True": True, "False": False, True: True, False: False}
    trials["first_correct"] = trials["first_correct"].map(truth)
    return trials


def test_items(trials: pd.DataFrame) -> pd.DataFrame:
    """The measured sheet items: phase 'test', completed outcomes only."""
    return trials[(trials["phase"] == "test") & trials["outcome"].isin(COMPLETED)].copy()


def sheet_times(trials: pd.DataFrame) -> pd.DataFrame:
    """One row per sheet (block): its test, form, items, errors and time.

    ``time_s`` sums the items' times to the right key, charging each
    uncorrected item twice the sheet's mean time per corrected item (Stroop's
    Experiment 2 rule); ``per_100_s`` scales it to a 100-item sheet.
    """
    rows = []
    for block, items in test_items(trials).groupby("block"):
        timed = items["rt_correct_ms"].dropna() / 1000.0
        n_uncorrected = int((items["outcome"] == "UNCORRECTED").sum())
        n_wrong = int((items["outcome"] == "WRONG").sum())
        mean_item = float(timed.mean()) if len(timed) else np.nan
        time_s = float(timed.sum()) + 2.0 * mean_item * (n_uncorrected + n_wrong)
        rows.append({
            "block": int(block),
            "test": items["test"].iloc[0],
            "form": int(items["form"].iloc[0]),
            "n_items": len(items),
            "n_first_errors": int((~_right(items)).sum()),
            "n_uncorrected": n_uncorrected + n_wrong,
            "time_s": time_s,
            "per_100_s": time_s * 100.0 / len(items),
        })
    return pd.DataFrame(rows)


def interference(sheets: pd.DataFrame) -> pd.DataFrame:
    """Stroop's comparison for whichever pair of tests the run holds:
    the mean time per 100 items of each test, their difference D and D over
    the control, beside the paper's values."""
    out = []
    for task, (control, test) in PAIRS.items():
        if not {control, test} <= set(sheets["test"]):
            continue
        c = sheets.loc[sheets["test"] == control, "per_100_s"].mean()
        t = sheets.loc[sheets["test"] == test, "per_100_s"].mean()
        pc, pt = STROOP_1935[control]["mean_s"], STROOP_1935[test]["mean_s"]
        out.append({"task": task, "control": control, "interference": test,
                    "control_per_100_s": c, "interference_per_100_s": t, "D_s": t - c,
                    "D_over_control": (t - c) / c, "paper_control_s": pc,
                    "paper_interference_s": pt, "paper_D_s": pt - pc,
                    "paper_D_over_control": (pt - pc) / pc})
    return pd.DataFrame(out)


def item_measures(trials: pd.DataFrame) -> pd.DataFrame:
    """Per test: items, error rate of the first key, and the median and mean
    reaction time of first responses that were right."""
    items = test_items(trials)
    rows = []
    for test, g in items.groupby("test"):
        right = g[_right(g)]["rt_ms"]
        rows.append({"test": test, "n_items": len(g),
                     "error_rate": float((~_right(g)).mean()),
                     "median_rt_ms": float(right.median()), "mean_rt_ms": float(right.mean())})
    return pd.DataFrame(rows)


def _right(items: pd.DataFrame) -> pd.Series:
    """Whether each item's first key was right (False when there was none)."""
    return items["first_correct"].fillna(False).astype(bool)
