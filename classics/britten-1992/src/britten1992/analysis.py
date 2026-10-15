"""The paper's measures, computed from a run's trials table (Britten et al., 1992).

- **Psychometric function** (p. 4749): proportion correct against correlation,
  fitted by maximum likelihood with Quick's Weibull form (Eq. 1)
  ``p = 1 - 0.5 exp(-(c/alpha)^beta)``; ``alpha`` is the threshold (82 %
  correct) and ``beta`` the slope. Where Eq. 1 fits badly because of errors at
  the highest levels, Eq. 2 frees the asymptote ``delta``:
  ``p = delta - (delta - 0.5) exp(-(c/alpha)^beta)``; the paper used Eq. 2 when
  it fitted significantly better (p. 4750).
- **Neurometric function** (pp. 4750-4752): for each correlation, the area
  under the ROC of a neuron's spike counts on preferred- versus null-direction
  trials (the neuron against its "antineuron"), fitted with Eq. 1.
- **Comparing two functions** (p. 4753, Eq. 3): ``-2 ln`` of the likelihood of
  one joint Weibull over that of two separate ones, chi-square with 2 df.

Only completed trials (CORRECT / WRONG) outside correction trials enter, as in
the paper (pp. 4747-4748). At 0 % a trial's "correct" answer is its nominal
direction, so proportion correct there is chance by construction.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import optimize, stats

THRESHOLD_P = 1.0 - 0.5 * math.exp(-1.0)  # 0.816: Eq. 1 at c = alpha


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
    """The trials the paper analysed: completed choices, correction trials dropped."""
    keep = trials["outcome"].isin(["CORRECT", "WRONG"])
    if "correction" in trials:
        keep &= ~trials["correction"].astype(str).str.lower().eq("true")
    return trials[keep].copy()


def psychometric_table(trials: pd.DataFrame) -> pd.DataFrame:
    """Per correlation level: trials, correct choices, proportion correct."""
    t = measured(trials)
    g = t.groupby("coherence_pct")["outcome"]
    n_correct = g.apply(lambda s: int((s == "CORRECT").sum()))
    table = pd.DataFrame({"n": g.size(), "n_correct": n_correct})
    table["p_correct"] = table["n_correct"] / table["n"]
    return table.reset_index()


def weibull(c: np.ndarray | float, alpha: float, beta: float, delta: float = 1.0) -> np.ndarray:
    """Eq. 2 of the paper (Eq. 1 when delta = 1): chance (0.5) at c = 0."""
    c = np.asarray(c, dtype=float)
    return delta - (delta - 0.5) * np.exp(-((np.clip(c, 0, None) / alpha) ** beta))


@dataclass(frozen=True)
class WeibullFit:
    alpha: float  # threshold, in the units of c (82 % correct under Eq. 1)
    beta: float  # slope
    delta: float  # asymptote (1.0 for Eq. 1)
    loglik: float
    n_trials: int
    equation: int  # 1 or 2

    def predict(self, c: np.ndarray | float) -> np.ndarray:
        return weibull(c, self.alpha, self.beta, self.delta)


def _nll(
    theta: np.ndarray, c: np.ndarray, k: np.ndarray, n: np.ndarray, free_delta: bool
) -> float:
    alpha, beta = math.exp(theta[0]), math.exp(theta[1])
    delta = 0.5 + 0.5 / (1.0 + math.exp(-theta[2])) if free_delta else 1.0
    p = np.clip(weibull(c, alpha, beta, delta), 1e-9, 1 - 1e-9)
    return -float(np.sum(k * np.log(p) + (n - k) * np.log(1 - p)))


def fit_weibull(c, k, n, *, free_asymptote: bool = False) -> WeibullFit:
    """Maximum-likelihood Weibull fit to ``k`` correct of ``n`` at levels ``c``."""
    c, k, n = (np.asarray(x, dtype=float) for x in (c, k, n))
    if c.shape != k.shape or c.shape != n.shape or not len(c):
        raise ValueError("c, k and n must be equal-length, non-empty")
    if np.any(k > n) or np.any(k < 0):
        raise ValueError("need 0 <= k <= n")
    positive = c[c > 0]
    lo, hi = (positive.min(), positive.max()) if len(positive) else (1.0, 10.0)
    best = None
    for a0 in np.geomspace(lo, hi, 6):
        for b0 in (0.8, 1.5, 3.0):
            start = [math.log(a0), math.log(b0)] + ([2.0] if free_asymptote else [])
            res = optimize.minimize(_nll, start, args=(c, k, n, free_asymptote),
                                    method="Nelder-Mead",
                                    options={"xatol": 1e-6, "fatol": 1e-9, "maxiter": 4000})
            if best is None or res.fun < best.fun:
                best = res
    assert best is not None
    alpha, beta = math.exp(best.x[0]), math.exp(best.x[1])
    delta = 0.5 + 0.5 / (1.0 + math.exp(-best.x[2])) if free_asymptote else 1.0
    equation = 2 if free_asymptote else 1
    return WeibullFit(alpha, beta, delta, -float(best.fun), int(n.sum()), equation)


def fit_psychometric(table: pd.DataFrame, x: str = "coherence_pct") -> WeibullFit:
    """Eq. 1, or Eq. 2 when freeing the asymptote improves the fit significantly
    (likelihood ratio, chi-square with 1 df, p < 0.05), as on p. 4750."""
    args = (table[x], table["n_correct"], table["n"])
    eq1 = fit_weibull(*args)
    eq2 = fit_weibull(*args, free_asymptote=True)
    if 2 * (eq2.loglik - eq1.loglik) > stats.chi2.ppf(0.95, 1):
        return eq2
    return eq1


def roc_area(pref: np.ndarray, null: np.ndarray) -> float:
    """Area under the ROC of two response distributions: P(pref > null) +
    P(pref == null) / 2, the ideal observer's proportion correct (p. 4752)."""
    pref, null = np.asarray(pref, float), np.asarray(null, float)
    if not len(pref) or not len(null):
        raise ValueError("both distributions need at least one response")
    greater = (pref[:, None] > null[None, :]).mean()
    ties = (pref[:, None] == null[None, :]).mean()
    return float(greater + 0.5 * ties)


def neurometric_table(trials: pd.DataFrame, count: str = "spike_count") -> pd.DataFrame:
    """Per correlation level: ROC area of ``count`` on pref- vs anti-direction
    trials, as proportion correct, with the trial numbers behind it."""
    t = measured(trials)
    rows = []
    for c, g in t.groupby("coherence_pct"):
        pref = g.loc[g["direction"] == "pref", count].to_numpy()
        anti = g.loc[g["direction"] == "anti", count].to_numpy()
        if len(pref) and len(anti):
            rows.append({"coherence_pct": c, "p_correct": roc_area(pref, anti),
                         "n_pref": len(pref), "n_anti": len(anti)})
    return pd.DataFrame(rows)


def neurometric_fit(table: pd.DataFrame) -> WeibullFit:
    """Eq. 1 fitted to ROC areas, weighted by the trials behind each (N/2 per
    level, Eq. 4: two measures, neuron and antineuron, per comparison)."""
    n = ((table["n_pref"] + table["n_anti"]) / 2.0).round()
    k = (table["p_correct"] * n).round()
    return fit_weibull(table["coherence_pct"], k, n)


def compare_fits(c, k1, n1, k2, n2) -> tuple[float, float]:
    """Eq. 3: lambda = -2 ln(L(single curve) / L(two curves)), chi-square with
    2 df. Returns (lambda, p)."""
    c = np.asarray(c, float)
    joint = fit_weibull(np.r_[c, c], np.r_[k1, k2], np.r_[n1, n2])
    lam = -2.0 * (joint.loglik - fit_weibull(c, k1, n1).loglik - fit_weibull(c, k2, n2).loglik)
    lam = max(lam, 0.0)
    return lam, float(stats.chi2.sf(lam, 2))
