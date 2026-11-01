"""Thresholds and contrast sensitivity from a run's trials table.

- **csf-2ifc.** Per cell (waveform x spatial frequency), every completed trial (CORRECT or
  WRONG) enters a maximum-likelihood fit of the psychometric function QUEST+ assumed:
  p(correct) = 0.5 + (0.5 - lapse) (1 - exp(-10^(slope (x - t)))), x = log10 contrast,
  lapse fixed at 0.01, t and slope free (grid search). The threshold is 10^t, the
  contrast at which p = 0.5 + 0.49 (1 - 1/e) = 0.81; the sensitivity is 1 / threshold.
  x is the REALISED contrast of the drawn image (``contrast_realised``), floored at
  1e-4 when the drawn image had none. Confidence intervals: percentile bootstrap over
  trials.
- **csf-adjustment.** Per cell, the committed settings (SET): the threshold is their
  geometric mean (mean of log10 contrast; the paper reports means with a standard error
  under 10%, p. 553, without saying on which scale), with the standard error in log10
  units and as a percentage.
- **Square / sine.** Where both waveforms were measured at a frequency, the sensitivity
  ratio square / sine, against 4 / pi = 1.273 (the paper's prediction when only the
  fundamental counts, p. 555).

Nothing here knows the paper's numbers; it reports what the data say.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

LAPSE = 0.01
P_THRESHOLD = 0.5 + (0.5 - LAPSE) * (1.0 - math.exp(-1.0))
FOUR_OVER_PI = 4.0 / math.pi
CONTRAST_FLOOR = 1e-4
T_GRID = np.round(np.arange(-4.0, 0.3001, 0.01), 4)
SLOPE_GRID = np.geomspace(0.5, 15.0, 48)


def load_runs(runs: list[str | Path] | str | Path) -> pd.DataFrame:
    """Every ``*_trials.csv`` in the given run folders, with a ``run`` column."""
    if isinstance(runs, (str, Path)):
        runs = [runs]
    frames = []
    for run in runs:
        for f in sorted(Path(run).glob("*_trials.csv")):
            df = pd.read_csv(f)
            df["run"] = Path(run).name
            frames.append(df)
    if not frames:
        raise FileNotFoundError(f"no *_trials.csv in {runs}")
    return pd.concat(frames, ignore_index=True)


def p_correct(x: np.ndarray, t: np.ndarray, slope: np.ndarray) -> np.ndarray:
    return 0.5 + (0.5 - LAPSE) * (1.0 - np.exp(-np.power(10.0, slope * (x - t))))


@dataclass(frozen=True)
class Fit:
    log_threshold: float
    slope: float
    loglik: float
    n: int

    @property
    def threshold(self) -> float:
        return 10.0**self.log_threshold

    @property
    def sensitivity(self) -> float:
        return 1.0 / self.threshold


def fit_2afc(x: np.ndarray, correct: np.ndarray) -> Fit:
    """Grid maximum likelihood over (t, slope); x in log10 contrast, correct in {0, 1}."""
    x = np.asarray(x, float)
    k = np.asarray(correct, float)
    if x.shape != k.shape or not len(x):
        raise ValueError("x and correct must be equal-length and non-empty")
    p = p_correct(x[None, None, :], T_GRID[:, None, None], SLOPE_GRID[None, :, None])
    p = np.clip(p, 1e-9, 1 - 1e-9)
    ll = (k * np.log(p) + (1 - k) * np.log(1 - p)).sum(axis=2)
    i, j = np.unravel_index(int(np.argmax(ll)), ll.shape)
    return Fit(float(T_GRID[i]), float(SLOPE_GRID[j]), float(ll[i, j]), int(len(x)))


def detection_trials(trials: pd.DataFrame) -> pd.DataFrame:
    t = trials[trials["outcome"].isin(["CORRECT", "WRONG"])].copy()
    if "contrast_realised" in t:
        c = t["contrast_realised"].astype(float)
    else:
        c = t["contrast_requested"].astype(float)
    t["x"] = np.log10(np.clip(c, CONTRAST_FLOOR, None))
    t["correct"] = (t["outcome"] == "CORRECT").astype(int)
    return t


def csf_table(trials: pd.DataFrame, n_boot: int = 200, seed: int = 0) -> pd.DataFrame:
    """One row per cell: trials, threshold, sensitivity and bootstrap 95% intervals."""
    t = detection_trials(trials)
    rng = np.random.default_rng(seed)
    rows = []
    for (waveform, sf), g in t.groupby(["waveform", "sf_cpd"]):
        x, k = g["x"].to_numpy(), g["correct"].to_numpy()
        fit = fit_2afc(x, k)
        boot = []
        for _ in range(n_boot):
            idx = rng.integers(0, len(x), len(x))
            boot.append(fit_2afc(x[idx], k[idx]).log_threshold)
        lo, hi = np.percentile(boot, [2.5, 97.5]) if boot else (np.nan, np.nan)
        rows.append(
            {
                "waveform": waveform,
                "sf_cpd": float(sf),
                "n_trials": fit.n,
                "p_correct": float(k.mean()),
                "threshold": fit.threshold,
                "threshold_ci_low": 10.0**lo,
                "threshold_ci_high": 10.0**hi,
                "sensitivity": fit.sensitivity,
                "sensitivity_ci_low": 10.0**-hi,
                "sensitivity_ci_high": 10.0**-lo,
                "slope": fit.slope,
                "n_below_code_step": int((g.get("n_codes", pd.Series(dtype=float)) <= 1).sum()),
            }
        )
    return pd.DataFrame(rows).sort_values(["waveform", "sf_cpd"]).reset_index(drop=True)


def square_sine_ratio(table: pd.DataFrame) -> pd.DataFrame:
    """Sensitivity ratio square / sine where both were measured, with 4/pi beside it."""
    s = table.pivot(index="sf_cpd", columns="waveform", values="sensitivity")
    if not {"sine", "square"} <= set(s.columns):
        return pd.DataFrame(columns=["sf_cpd", "ratio", "predicted"])
    out = (s["square"] / s["sine"]).dropna().rename("ratio").reset_index()
    out["predicted"] = FOUR_OVER_PI
    return out


def adjustment_table(trials: pd.DataFrame) -> pd.DataFrame:
    t = trials[trials["outcome"] == "SET"].copy()
    col = "contrast_realised" if "contrast_realised" in t else "setting"
    t["x"] = np.log10(np.clip(t[col].astype(float), CONTRAST_FLOOR, None))
    rows = []
    for (waveform, sf), g in t.groupby(["waveform", "sf_cpd"]):
        x = g["x"].to_numpy()
        se = float(x.std(ddof=1) / math.sqrt(len(x))) if len(x) > 1 else float("nan")
        thr = 10.0 ** float(x.mean())
        rows.append(
            {
                "waveform": waveform,
                "sf_cpd": float(sf),
                "n_settings": int(len(x)),
                "threshold": thr,
                "sensitivity": 1.0 / thr,
                "se_log10": se,
                "se_percent": (10.0**se - 1.0) * 100.0 if se == se else float("nan"),
            }
        )
    return pd.DataFrame(rows).sort_values(["waveform", "sf_cpd"]).reset_index(drop=True)


def realised_timing(trials: pd.DataFrame) -> pd.DataFrame:
    """Realised phase durations (ms) from the flip stamps each phase's onset event left in
    the record, next to the frames asked for: interval 1, gap, interval 2."""
    need = ["t_interval1_on", "t_isi_on", "t_interval2_on", "t_response_cue"]
    t = trials[trials["outcome"].isin(["CORRECT", "WRONG"])]
    if not set(need) <= set(t.columns):
        return pd.DataFrame()
    return (
        pd.DataFrame(
            {
                "interval1_ms": (t["t_isi_on"] - t["t_interval1_on"]) * 1000.0,
                "isi_ms": (t["t_interval2_on"] - t["t_isi_on"]) * 1000.0,
                "interval2_ms": (t["t_response_cue"] - t["t_interval2_on"]) * 1000.0,
            }
        )
        .describe()
        .T
    )
