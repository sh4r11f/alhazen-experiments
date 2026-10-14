"""The original paper's measures, from a run's ``*_trials.csv``.

Posner (1980, Fig. 2, p. 7) reports mean simple RT for valid, neutral and invalid
trials and reads the cueing effect as a **benefit** (neutral minus valid) and a
**cost** (invalid minus neutral). Those are computed here, together with what a
simple-RT design needs to be trusted: the false-alarm rate on catch trials, misses,
anticipations and (eye-tracker set) the attempts lost to fixation breaks.

The notebook (notebooks/analysis.ipynb) calls these; tests/test_analysis.py checks
them on tables with a planted effect.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

CONDITIONS = ("valid", "neutral", "invalid")
# ASSUMED (not in the paper): RTs this short are anticipations, not detections.
MIN_RT_MS = 100.0


def load_trials(run: str | Path) -> pd.DataFrame:
    """The trials table of one run folder (or the CSV itself)."""
    run = Path(run)
    path = run if run.suffix == ".csv" else next(run.glob("*_trials.csv"))
    return pd.read_csv(path)


def _completed(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["completed"].astype(str) == "True"]


def detection_rts(df: pd.DataFrame, min_rt_ms: float = MIN_RT_MS) -> pd.DataFrame:
    """Completed target trials with a detection, fast guesses removed."""
    done = _completed(df)
    hits = done[(done["outcome"] == "DETECTED") & done["validity"].isin(CONDITIONS)]
    return hits[hits["rt_ms"] >= min_rt_ms]


def rt_by_condition(df: pd.DataFrame, min_rt_ms: float = MIN_RT_MS) -> pd.DataFrame:
    """Mean, median, SD and count of detection RT per cue condition (Fig. 2's measure)."""
    rts = detection_rts(df, min_rt_ms)
    table = rts.groupby("validity")["rt_ms"].agg(["mean", "median", "std", "count"])
    return table.reindex(list(CONDITIONS))


def costs_and_benefits(df: pd.DataFrame, min_rt_ms: float = MIN_RT_MS) -> dict[str, float]:
    """Benefit = neutral - valid, cost = invalid - neutral, in ms (positive = as Posner found)."""
    m = rt_by_condition(df, min_rt_ms)["mean"]
    return {"benefit_ms": float(m["neutral"] - m["valid"]),
            "cost_ms": float(m["invalid"] - m["neutral"]),
            "validity_effect_ms": float(m["invalid"] - m["valid"])}


def _rate(rows: pd.DataFrame, outcome: str) -> float:
    return float((rows["outcome"] == outcome).mean()) if len(rows) else float("nan")


def response_summary(df: pd.DataFrame, min_rt_ms: float = MIN_RT_MS) -> dict[str, float]:
    """Catch-trial false alarms, misses, fast guesses, and the attempts served again."""
    done = _completed(df)
    catch = done[done["validity"] == "catch"]
    targets = done[done["validity"].isin(CONDITIONS)]
    hits = targets[targets["outcome"] == "DETECTED"]
    return {
        "completed_trials": int(len(done)),
        "catch_trials": int(len(catch)),
        "false_alarm_rate": _rate(catch, "FALSE_ALARM"),
        "target_trials": int(len(targets)),
        "miss_rate": _rate(targets, "MISS"),
        "fast_guesses": int((hits["rt_ms"] < min_rt_ms).sum()),
        "anticipations": int((df["outcome"] == "ANTICIPATION").sum()),
        "fixation_breaks": int((df["outcome"] == "FIXATION_BREAK").sum()),
        "no_fixation": int((df["outcome"] == "NO_FIXATION").sum()),
    }


def fixation_breaks_by_period(df: pd.DataFrame) -> pd.Series:
    """Where each fixation break happened: before the cue, during the cue, or after the
    target time. Read from which onsets the attempt reached."""
    breaks = df[df["outcome"] == "FIXATION_BREAK"]

    def period(row) -> str:
        if pd.isna(row.get("t_cue_on")):
            return "inter-trial interval"
        if pd.isna(row.get("t_target_on")) and pd.isna(row.get("t_catch_on")):
            return "cue period"
        return "detection window"

    return breaks.apply(period, axis=1).value_counts()
