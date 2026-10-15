"""The paper's measures from one or more runs' *_trials.csv (used by the notebook).

Raymond, Shapiro & Arnell (1992), Experiment 2 (p. 853):

- probe detection by the probe's relative serial position (0..+8), for the experimental
  condition "using only those trials in which subjects identified the target correctly",
  and for the control condition over all trials (Figure 3A);
- false-alarm rate (an X reported on probe-absent trials) per condition;
- target-identification errors in the experimental condition: the relative serial
  position of the letter reported as the target, for probe-absent trials and trials
  with the probe at 0, +1 and +2 (Figure 3B).

Practice trials and trials that did not complete are excluded. Group values are means of
per-subject values, as the paper's group means were.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import numpy as np
import pandas as pd

POSITIONS = tuple(range(9))
REPORT_BINS = (-2, -1, 0, 1, 2)

# What the paper reports for Experiment 2 (pp. 853-854), for comparison only.
PAPER = {
    "control_detection_min": 0.85,  # "85% or better of trials for all probe serial positions"
    "experimental_detection_dip": "below 60% for probes 180-450 ms after the target (+2..+5)",
    "false_alarms": {"experimental": 0.126, "control": 0.113},
    "target_errors_probe_absent": 0.22,
    "plus1_share_of_errors_probe_absent": 0.50,
}


def _truthy(series: pd.Series) -> pd.Series:
    return series.map(lambda v: str(v).strip().lower() in ("true", "1", "1.0"))


def load_trials(runs: Iterable[Path | str]) -> pd.DataFrame:
    """Every *_trials.csv under the given run folders, one subject id per file."""
    frames = []
    for run in runs:
        for path in sorted(Path(run).rglob("*_trials.csv")):
            df = pd.read_csv(path)
            df["source"] = path.name
            df["subject"] = path.name.split("_")[0]
            frames.append(df)
    if not frames:
        raise FileNotFoundError(f"no *_trials.csv under {list(runs)}")
    return pd.concat(frames, ignore_index=True)


def clean(trials: pd.DataFrame) -> pd.DataFrame:
    """Completed, non-practice trials, with boolean columns made boolean."""
    df = trials.copy()
    for col in ("completed", "practice", "probe_present", "probe_reported", "target_correct",
                "probe_correct"):
        if col in df:
            df[col] = _truthy(df[col])
    return df[df["completed"] & ~df["practice"]].copy()


def detection_by_position(df: pd.DataFrame) -> pd.DataFrame:
    """P(probe reported | probe at position k), per subject and condition.

    Experimental trials count only when the target was identified correctly."""
    present = df[df["probe_present"]].copy()
    exp = present["condition"] == "experimental"
    present = present[~exp | present["target_correct"]]
    present["probe_pos"] = present["probe_pos"].astype(int)
    return (present.groupby(["subject", "condition", "probe_pos"])["probe_reported"]
            .agg(["mean", "size"]).rename(columns={"mean": "p_detect", "size": "n"})
            .reset_index())


def group_curve(by_subject: pd.DataFrame) -> pd.DataFrame:
    """Group mean (and SEM across subjects) of the per-subject detection curves."""
    g = by_subject.groupby(["condition", "probe_pos"])["p_detect"]
    out = g.agg(["mean", "count", "std"]).reset_index()
    out["sem"] = out["std"] / np.sqrt(out["count"])
    return out.rename(columns={"count": "n_subjects"}).drop(columns="std")


def false_alarms(df: pd.DataFrame) -> pd.DataFrame:
    """P(X reported | no X), per subject and condition (all probe-absent trials)."""
    absent = df[~df["probe_present"]]
    return (absent.groupby(["subject", "condition"])["probe_reported"].mean()
            .rename("false_alarm_rate").reset_index())


def target_accuracy(df: pd.DataFrame) -> pd.DataFrame:
    exp = df[df["condition"] == "experimental"]
    return exp.groupby("subject")["target_correct"].mean().rename("p_target_correct").reset_index()


def target_report_positions(df: pd.DataFrame) -> pd.DataFrame:
    """Figure 3B: P(the letter reported as the target was at relative position r), for
    probe-absent trials and probe at 0, +1, +2; anything else is 'other'."""
    exp = df[df["condition"] == "experimental"].copy()
    trial_type = np.where(~exp["probe_present"], "probe absent",
                          "probe " + exp["probe_pos"].fillna(-99).astype(int).map("{:+d}".format))
    exp["trial_type"] = pd.Series(trial_type, index=exp.index).str.replace("probe +0", "probe 0")
    exp = exp[exp["trial_type"].isin(["probe absent", "probe 0", "probe +1", "probe +2"])]
    pos = pd.to_numeric(exp["target_report_pos"], errors="coerce")
    exp["report_bin"] = [str(int(v)) if v == v and int(v) in REPORT_BINS else "other"
                         for v in pos]
    counts = exp.groupby(["trial_type", "report_bin"]).size().unstack(fill_value=0)
    for col in [str(b) for b in REPORT_BINS] + ["other"]:
        if col not in counts:
            counts[col] = 0
    counts = counts[[str(b) for b in REPORT_BINS] + ["other"]]
    return counts.div(counts.sum(axis=1), axis=0)


def timing_summary(trials: pd.DataFrame) -> pd.DataFrame:
    """The frame timing the runs actually used (refresh rate, letter, ISI, SOA)."""
    cols = ["refresh_hz", "letter_frames", "isi_frames", "letter_ms", "isi_ms", "soa_ms"]
    return trials[cols].drop_duplicates().reset_index(drop=True)
