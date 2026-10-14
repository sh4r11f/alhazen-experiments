"""The paper's measures, from a run's trials.csv (and its paradigm.csv).

- Luminance-change threshold per staircase (p. 1274): "the least-square fit
  of 10–25 blocks of staircase data with an asymptotic function
  y = ax/(b + x), where a is the threshold (at 66.7% performance) and b is the
  block number at half threshold". The function rises from 0 at block 0, so y
  cannot be the staircase level itself, which starts high and falls. It is
  read here as the staircase's PROGRESS, y = start − level after block x, and
  the threshold as start − a. That reading is ASSUMED (docs/methods.md); the
  fitted a is reported too.
- Threshold reduction with stimulation (Fig. 3 legend, p. 1275):
  (1 − threshold_stim / threshold_control) × 100.
- Performance (% correct) on stimulation and control trials, the paper's
  first measure (p. 1275), and hit and false-alarm rates.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

GOOD = {"blink": "HIT", "catch": "CORRECT_REJECTION"}


def load_run(run_dir: str | Path) -> tuple[pd.DataFrame, pd.DataFrame | None]:
    run_dir = Path(run_dir)
    trials = pd.read_csv(next(run_dir.glob("*_trials.csv")))
    para = next(run_dir.glob("*_paradigm.csv"), None)
    return trials, (pd.read_csv(para) if para is not None else None)


def completed(trials: pd.DataFrame) -> pd.DataFrame:
    """Trials that produced a measurement (fixation breaks are served again)."""
    return trials[trials["completed"].astype(bool)].copy()


def block_table(trials: pd.DataFrame, n_blink: int = 2, n_catch: int = 1,
                min_hits: int = 1) -> pd.DataFrame:
    """Each staircase's blocks, rebuilt from the trials alone: the level, the
    hits and held catches, and the block's verdict. Independent of the
    scheduler's own paradigm.csv, so the two can be checked against each other."""
    done = completed(trials)
    rows = []
    for (label, block), g in done.groupby(["staircase", "block"], sort=True):
        hits = int((g.query("trial_type == 'blink'")["outcome"] == "HIT").sum())
        held = int((g.query("trial_type == 'catch'")["outcome"] == "CORRECT_REJECTION").sum())
        n_b = int((g["trial_type"] == "blink").sum())
        n_c = int((g["trial_type"] == "catch").sum())
        rows.append({"staircase": label, "block": int(block),
                     "dim_pct": float(g["dim_pct"].iloc[0]),
                     "blink_hits": hits, "n_blink": n_b, "catch_correct": held, "n_catch": n_c,
                     "complete": n_b == n_blink and n_c == n_catch,
                     "block_success": hits >= min_hits and held == n_catch})
    return pd.DataFrame(rows)


@dataclass(frozen=True)
class AsymptoteFit:
    a: float  # asymptotic progress (% contrast below the start)
    b: float  # block number at half the asymptote
    start: float
    sse: float
    n_blocks: int
    # True when the best b lies on the edge of the searched range: the staircase has not
    # levelled off within its blocks (it is still falling, or never moved), so a and the
    # threshold are extrapolations, not estimates. The paper fitted staircases that had.
    at_bound: bool = False

    @property
    def threshold_pct(self) -> float:
        return self.start - self.a

    @property
    def converged(self) -> bool:
        return not self.at_bound and 0.0 <= self.threshold_pct <= self.start

    def progress(self, x: np.ndarray) -> np.ndarray:
        return self.a * x / (self.b + x)


def fit_asymptote(levels: np.ndarray, start: float,
                  b_grid: np.ndarray | None = None) -> AsymptoteFit:
    """Least-squares fit of y = a x / (b + x) to a staircase's progress.

    ``levels[i]`` is the level the staircase stood at AFTER block i + 1 (the
    level its next block ran at). For each b on a log grid the best a is
    closed-form (linear least squares), so the fit has no starting values to
    get wrong. b is searched from 0.01 to 10 × the number of blocks; a best b on
    either edge is flagged (``at_bound``) rather than reported as a threshold.
    """
    levels = np.asarray(levels, dtype=float)
    if levels.size < 2:
        raise ValueError("an asymptotic fit needs at least two blocks")
    x = np.arange(1, levels.size + 1, dtype=float)
    y = start - levels
    grid = np.geomspace(1e-2, 10.0 * levels.size, 2001) if b_grid is None else b_grid
    best = None
    for b in grid:
        f = x / (b + x)
        a = float(f @ y / (f @ f))
        sse = float(((y - a * f) ** 2).sum())
        if best is None or sse < best[2]:
            best = (a, float(b), sse)
    assert best is not None
    at_bound = bool(np.isclose(best[1], grid[0]) or np.isclose(best[1], grid[-1]))
    return AsymptoteFit(a=best[0], b=best[1], start=float(start), sse=best[2],
                        n_blocks=int(levels.size), at_bound=at_bound)


def thresholds(paradigm: pd.DataFrame, start: float) -> dict[str, AsymptoteFit]:
    """One fit per staircase, from the scheduler's per-block levels."""
    out = {}
    for label, g in paradigm.sort_values("block").groupby("staircase"):
        out[str(label)] = fit_asymptote(g["next_dim_pct"].to_numpy(), start)
    return out


def threshold_reduction_pct(stim_threshold: float, control_threshold: float) -> float:
    """(1 − contrast_stim / contrast_control) × 100: positive = lower with stimulation."""
    return (1.0 - stim_threshold / control_threshold) * 100.0


def performance(trials: pd.DataFrame) -> pd.DataFrame:
    """% correct, hit rate and false-alarm rate per staircase."""
    done = completed(trials)
    rows = []
    for label, g in done.groupby("staircase"):
        blink, catch = g.query("trial_type == 'blink'"), g.query("trial_type == 'catch'")
        correct = (g["outcome"] == g["trial_type"].map(GOOD)).mean()
        rows.append({
            "staircase": label, "n_trials": len(g),
            "pct_correct": 100.0 * correct,
            "hit_rate": (blink["outcome"] == "HIT").mean() if len(blink) else np.nan,
            "early_rate": (blink["outcome"] == "EARLY_RESPONSE").mean() if len(blink) else np.nan,
            "false_alarm_rate": (
                (catch["outcome"] == "FALSE_ALARM").mean() if len(catch) else np.nan),
            "median_rt_ms": blink.loc[blink["outcome"] == "HIT", "rt_ms"].median(),
        })
    return pd.DataFrame(rows)
