"""The paper's measure, computed from runs' trials tables (Hiris & Blake, 1992, Fig. 1).

- **Psychometric function** (Fig. 1 Lower, p. 9026): proportion of trials on which the
  adapted (variable) display was judged more coherently downward, against its signed
  signal percentage (+ downward, the aftereffect's direction; - upward). The paper
  fitted these "by probit analysis"; here a cumulative normal is fitted by maximum
  likelihood: ``p = Phi((x - pse) / sigma)``. ``pse`` is the point of subjective
  equality with the reference display (40 % downward), ``sigma`` the spread (the
  paper compared slopes between conditions).
- **Aftereffect strength** in units of real motion signal: ``pse(control) -
  pse(adapted)``. After RDVN adaptation the two displays match when both hold 40 %
  (PSE about 40); after upward adaptation the paper's PSE was about 0 %, i.e. the
  aftereffect seen in RDVN matched 40 % real downward signal.
- A percentile **bootstrap** over trials (resampled within each level) gives an interval
  for each PSE and for the difference.

Only completed choices (CHOSE_TEST / CHOSE_REFERENCE) enter.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import optimize, stats


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


def measured(trials: pd.DataFrame) -> pd.DataFrame:
    """Completed choices, with ``chose_test`` as 0/1."""
    t = trials[trials["outcome"].isin(["CHOSE_TEST", "CHOSE_REFERENCE"])].copy()
    t["chose_test"] = (t["outcome"] == "CHOSE_TEST").astype(int)
    return t


def psychometric_table(trials: pd.DataFrame) -> pd.DataFrame:
    """Per adaptation mode and signed level: trials, test choices, proportion."""
    t = measured(trials)
    g = t.groupby(["adapt_mode", "test_signal_pct"])["chose_test"]
    out = g.agg(n="count", k="sum").reset_index()
    out["p_test"] = out["k"] / out["n"]
    return out


@dataclass(frozen=True)
class ProbitFit:
    pse: float
    sigma: float
    n: int
    loglik: float

    def p(self, x: np.ndarray | float) -> np.ndarray:
        return stats.norm.cdf((np.asarray(x, dtype=float) - self.pse) / self.sigma)


def fit_probit(x: np.ndarray, k: np.ndarray, n: np.ndarray) -> ProbitFit:
    """Maximum-likelihood cumulative normal through binomial counts ``k`` of ``n`` at
    levels ``x``."""
    x, k, n = (np.asarray(a, dtype=float) for a in (x, k, n))
    if n.sum() == 0:
        raise ValueError("no trials to fit")

    def nll(theta: np.ndarray) -> float:
        mu, log_sigma = theta
        p = stats.norm.cdf((x - mu) / np.exp(log_sigma))
        p = np.clip(p, 1e-9, 1 - 1e-9)
        return -float(np.sum(k * np.log(p) + (n - k) * np.log(1 - p)))

    span = max(float(np.ptp(x)), 1.0)
    starts = [(float(np.average(x, weights=n)), np.log(span / 4)),
              (float(np.median(x)), np.log(span / 8)), (float(x.mean()), np.log(span / 2))]
    best = None
    for start in starts:
        res = optimize.minimize(nll, np.array(start), method="Nelder-Mead",
                                options={"xatol": 1e-6, "fatol": 1e-9, "maxiter": 4000})
        if best is None or res.fun < best.fun:
            best = res
    assert best is not None
    mu, log_sigma = best.x
    return ProbitFit(pse=float(mu), sigma=float(np.exp(log_sigma)), n=int(n.sum()),
                     loglik=-float(best.fun))


def fit_mode(trials: pd.DataFrame, adapt_mode: str) -> ProbitFit:
    tab = psychometric_table(trials)
    tab = tab[tab["adapt_mode"] == adapt_mode]
    if tab.empty:
        raise ValueError(f"no completed trials with adapt_mode {adapt_mode!r}")
    return fit_probit(tab["test_signal_pct"].to_numpy(), tab["k"].to_numpy(),
                      tab["n"].to_numpy())


def bootstrap_pse(trials: pd.DataFrame, adapt_mode: str, n_boot: int = 200,
                  seed: int = 0) -> np.ndarray:
    """PSEs of ``n_boot`` refits, trials resampled with replacement within each level."""
    rng = np.random.default_rng(seed)
    t = measured(trials)
    t = t[t["adapt_mode"] == adapt_mode]
    groups = [(lvl, g["chose_test"].to_numpy()) for lvl, g in t.groupby("test_signal_pct")]
    out = np.empty(n_boot)
    for b in range(n_boot):
        x, k, n = [], [], []
        for lvl, choices in groups:
            draw = rng.choice(choices, size=len(choices), replace=True)
            x.append(lvl)
            k.append(draw.sum())
            n.append(len(draw))
        out[b] = fit_probit(np.array(x), np.array(k), np.array(n)).pse
    return out


def aftereffect_strength(trials: pd.DataFrame, n_boot: int = 200, seed: int = 0) -> dict:
    """PSE per mode and the aftereffect (control PSE minus adapted PSE), in % signal,
    with 95 % percentile bootstrap intervals."""
    out: dict = {}
    boots = {}
    for mode in ("unidirectional", "random"):
        try:
            fit = fit_mode(trials, mode)
        except ValueError:
            continue
        boots[mode] = bootstrap_pse(trials, mode, n_boot=n_boot, seed=seed)
        lo, hi = np.percentile(boots[mode], [2.5, 97.5])
        out[mode] = {"pse": fit.pse, "sigma": fit.sigma, "n": fit.n,
                     "pse_ci95": (float(lo), float(hi))}
    if "unidirectional" in out and "random" in out:
        diff = boots["random"] - boots["unidirectional"]
        lo, hi = np.percentile(diff, [2.5, 97.5])
        out["aftereffect_pct"] = out["random"]["pse"] - out["unidirectional"]["pse"]
        out["aftereffect_ci95"] = (float(lo), float(hi))
    return out
