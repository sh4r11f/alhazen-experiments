"""The paper's behavioural measures, computed from a run's ``*_trials.csv``.

Funahashi et al. (1989) report the monkeys' behaviour as the distribution of eye positions
after the saccade, for the visually guided saccade task and the ODR task at 3- and 6-s
delays, all cues at 13 deg (p. 333, Fig. 2), and they examine trials with large saccadic
errors (p. 331, Summary 9). The notebook shows the same plot and, per cue location and
delay, the endpoint error and the saccade latency, plus the share of correct responses.

Definitions (columns alhazen writes):

- a **response** is a trial that ended CORRECT or INACCURATE (a saccade left fixation within
  the response period); FIX_BREAK, NO_FIXATION and NO_SACCADE trials made no response;
- **endpoint error**: distance (deg) from the saccade endpoint (``endpoint_x/y_dva``, where
  the eye came to rest) to the cue location (``endpoint_reference_x/y_dva``);
- **direction error**: signed angle (deg) between the endpoint and the cue, seen from the
  saccade's start (``fixation_x/y_dva``), positive counter-clockwise;
- **amplitude gain**: endpoint distance from the start over the cue eccentricity;
- **latency**: ``saccade_latency_ms``, from the go signal (the fixation spot's offset) to the
  frame gaze left the fixation window.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

RESPONSES = ("CORRECT", "INACCURATE")


def load_trials(run: str | Path) -> pd.DataFrame:
    """The trials of one run folder (or a ``*_trials.csv`` path)."""
    path = Path(run)
    if path.is_dir():
        path = next(path.glob("*_trials.csv"))
    return pd.read_csv(path)


def responses(trials: pd.DataFrame) -> pd.DataFrame:
    """Trials with a saccade in the response period and a measured endpoint, with the
    measures in the module docstring added (and ``delay`` rounded to 10 ms)."""
    df = trials[trials["outcome"].isin(RESPONSES)].copy()
    if "endpoint_measured" in df:
        df = df[df["endpoint_measured"].astype(str).str.lower() == "true"]
    if df.empty:
        return df.assign(direction_error_deg=[], amplitude_gain=[], delay=[])
    sx = df.get("fixation_x_dva", pd.Series(0.0, index=df.index)).fillna(0.0)
    sy = df.get("fixation_y_dva", pd.Series(0.0, index=df.index)).fillna(0.0)
    ex, ey = df["endpoint_x_dva"] - sx, df["endpoint_y_dva"] - sy
    cx, cy = df["endpoint_reference_x_dva"] - sx, df["endpoint_reference_y_dva"] - sy
    diff = np.degrees(np.arctan2(ey, ex) - np.arctan2(cy, cx))
    df["direction_error_deg"] = (diff + 180.0) % 360.0 - 180.0
    df["amplitude_gain"] = np.hypot(ex, ey) / np.hypot(cx, cy)
    df["delay"] = df["delay_s"].round(2)
    df["correct"] = df["outcome"] == "CORRECT"
    return df


def summary(df: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    """Per group: responses, share correct, endpoint error and latency."""
    if df.empty:
        return pd.DataFrame()
    g = df.groupby(by)
    return pd.DataFrame({
        "n": g.size(),
        "pct_correct": 100.0 * g["correct"].mean(),
        "endpoint_error_mean_dva": g["endpoint_error_dva"].mean(),
        "endpoint_error_sd_dva": g["endpoint_error_dva"].std(),
        "direction_error_sd_deg": g["direction_error_deg"].std(),
        "amplitude_gain_mean": g["amplitude_gain"].mean(),
        "latency_mean_ms": g["saccade_latency_ms"].mean(),
        "latency_sd_ms": g["saccade_latency_ms"].std(),
    }).round(3)


def outcome_table(trials: pd.DataFrame) -> pd.DataFrame:
    """Every attempt's outcome per delay condition (``delay_index``), FIX_BREAK etc. included."""
    return pd.crosstab(trials["delay_index"], trials["outcome"])
