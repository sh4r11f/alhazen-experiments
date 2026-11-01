"""The paper's measures from a run's trials, used by notebooks/analysis.ipynb and the tests.

Experiment 1 (constant stimuli, p. 157, Fig. 2): per test luminance, the percentage of
"left", "right" and "neither" reports; the point of subjective equality (PSE), the test
luminance at which neither direction prevails; and the width of the "neither" band
("the number of 'neither' responses fell to one-half maximum when the contrast of the
red/green grating deviated from its equiluminous value by 1.6%").

The paper read its PSEs off the plotted functions and does not say how. Two estimates
are offered, both labelled as this folder's choice (docs/methods.md):

- ``pse_crossing``: model-free; where P(test lighter) - P(reference lighter) crosses 0,
  by linear interpolation between adjacent levels.
- ``fit_ordered_probit``: maximum likelihood of the three-category model the simulated
  observer uses (on ln luminance: a PSE, a noise sigma and an indifference half-width
  delta), by grid search then coordinate refinement (numpy only).

"Test lighter" means motion reported in the direction of the quarter-cycle steps (Fig. 1:
red lighter than green -> red bars jump to the light bars a quarter cycle ahead).

Experiments 2-3 (adjustment): mean, SD, SE and n of the settings per condition, and the
luminous efficiency of each colour relative to its standard (uniform-field) flicker
match, Fig. 3-4's ordinate: flicker setting / motion setting.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

SIGN = {"left": -1, "right": 1, "down": 0}


def load_trials(run: Path | str) -> pd.DataFrame:
    frames = [pd.read_csv(p) for p in sorted(Path(run).glob("*_trials.csv"))]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def code_reports(df: pd.DataFrame) -> pd.DataFrame:
    """Completed constant-stimuli trials with ``motion_sign`` (screen: +1 right) and
    ``report`` (test_lighter / reference_lighter / neither)."""
    d = df[df["completed"].astype(bool)].copy() if "completed" in df else df.copy()
    d = d[d["response_key"].isin(list(SIGN))]
    d["motion_sign"] = d["response_key"].map(SIGN).astype(int)
    rel = d["motion_sign"] * d["step"].astype(int)
    d["report"] = np.where(rel > 0, "test_lighter",
                           np.where(rel < 0, "reference_lighter", "neither"))
    return d


def constant_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Per test luminance: n and proportions of left / right / neither and of
    test-lighter / reference-lighter reports, plus the colour grating's Michelson
    luminance contrast (test - reference) / (test + reference) in the file's units."""
    d = code_reports(df)
    g = d.groupby("test_cd_m2")
    out = pd.DataFrame({
        "n": g.size(),
        "p_left": g["response_key"].apply(lambda s: float((s == "left").mean())),
        "p_right": g["response_key"].apply(lambda s: float((s == "right").mean())),
        "p_neither": g["report"].apply(lambda s: float((s == "neither").mean())),
        "p_test_lighter": g["report"].apply(lambda s: float((s == "test_lighter").mean())),
        "p_reference_lighter": g["report"].apply(
            lambda s: float((s == "reference_lighter").mean())),
    }).reset_index()
    ref = float(d["reference_cd_m2"].iloc[0]) if len(d) else float("nan")
    out["contrast"] = (out["test_cd_m2"] - ref) / (out["test_cd_m2"] + ref)
    return out


def pse_crossing(summary: pd.DataFrame) -> float:
    """Test luminance where P(test lighter) - P(reference lighter) crosses zero, by linear
    interpolation. With several crossings, the one nearest the middle of the levels.
    NaN when the difference never changes sign."""
    s = summary.sort_values("test_cd_m2")
    x = s["test_cd_m2"].to_numpy(float)
    y = (s["p_test_lighter"] - s["p_reference_lighter"]).to_numpy(float)
    roots = []
    for i in range(len(x) - 1):
        if y[i] == 0:
            roots.append(x[i])
        elif y[i] * y[i + 1] < 0:
            roots.append(x[i] + (x[i + 1] - x[i]) * (-y[i]) / (y[i + 1] - y[i]))
    if len(x) and y[-1] == 0:
        roots.append(x[-1])
    if not roots:
        return float("nan")
    mid = 0.5 * (x[0] + x[-1])
    return float(min(roots, key=lambda r: abs(r - mid)))


def neither_half_max(summary: pd.DataFrame) -> tuple[float, float, float]:
    """(lower, upper, peak): the test luminances on either side of the "neither" peak where
    P(neither) falls to half its maximum (linear interpolation; NaN where it does not)."""
    s = summary.sort_values("test_cd_m2")
    x = s["test_cd_m2"].to_numpy(float)
    y = s["p_neither"].to_numpy(float)
    if not len(y) or y.max() <= 0:
        return float("nan"), float("nan"), float("nan")
    i = int(np.argmax(y))
    half = y[i] / 2.0

    def walk(rng):
        for j in rng:
            k = j + (1 if rng.step < 0 else -1)
            if y[j] <= half < y[k] or y[j] < half <= y[k]:
                return float(x[j] + (x[k] - x[j]) * (half - y[j]) / (y[k] - y[j]))
        return float("nan")

    lower = walk(range(i - 1, -1, -1))
    upper = walk(range(i + 1, len(x)))
    return lower, upper, float(x[i])


def indifference_contrast(summary: pd.DataFrame, pse: float) -> float:
    """Half the width of the half-maximum "neither" band, as the change in the colour
    grating's Michelson contrast from its value at the PSE: the paper's "deviated from
    its equiluminous value by 1.6%" (its exact definition is not given; this reading is
    ASSUMED, docs/methods.md)."""
    lo, hi, _ = neither_half_max(summary)
    if not (math.isfinite(lo) and math.isfinite(hi) and math.isfinite(pse)):
        return float("nan")
    # contrast(L) = (L - R) / (L + R); R recovered from the summary's own column.
    row = summary.iloc[0]
    R = float(row["test_cd_m2"]) * (1 - row["contrast"]) / (1 + row["contrast"])
    c = lambda L: (L - R) / (L + R)  # noqa: E731
    return float(0.5 * (abs(c(hi) - c(pse)) + abs(c(pse) - c(lo))))


def _nll(mu: float, sigma: float, delta: float, x: np.ndarray, cat: np.ndarray) -> float:
    from math import erf, sqrt

    phi = np.vectorize(lambda z: 0.5 * (1.0 + erf(z / sqrt(2.0))))
    up = 1.0 - phi((delta - (x - mu)) / sigma)  # P(test lighter)
    down = phi((-delta - (x - mu)) / sigma)  # P(reference lighter)
    mid = 1.0 - up - down
    p = np.where(cat > 0, up, np.where(cat < 0, down, mid))
    return float(-np.sum(np.log(np.clip(p, 1e-12, 1.0))))


def fit_ordered_probit(df: pd.DataFrame) -> dict[str, float]:
    """Maximum-likelihood (PSE, sigma, delta) on ln test luminance. Returns pse_cd_m2,
    sigma_ln, delta_ln, nll, n. A coarse grid then three rounds of coordinate refinement;
    adequate for three parameters and a few hundred trials, not a general optimiser."""
    d = code_reports(df)
    if d.empty:
        return {"pse_cd_m2": float("nan"), "sigma_ln": float("nan"),
                "delta_ln": float("nan"), "nll": float("nan"), "n": 0}
    x = np.log(d["test_cd_m2"].to_numpy(float))
    cat = d["report"].map({"test_lighter": 1, "reference_lighter": -1, "neither": 0}).to_numpy()
    mus = np.linspace(x.min() - 0.1, x.max() + 0.1, 41)
    sigmas = np.geomspace(0.005, 0.5, 15)
    deltas = np.concatenate([[0.0], np.geomspace(0.002, 0.3, 14)])
    best = min(((_nll(m, s, dl, x, cat), m, s, dl) for m in mus for s in sigmas
                for dl in deltas), key=lambda t: t[0])
    nll, m, s, dl = best
    for scale in (0.25, 0.06, 0.015):
        for _ in range(3):
            m = min((m + k * scale * 0.2 for k in range(-5, 6)),
                    key=lambda v: _nll(v, s, dl, x, cat))
            s = min((max(1e-4, s * math.exp(k * scale)) for k in range(-5, 6)),
                    key=lambda v: _nll(m, v, dl, x, cat))
            dl = min((max(0.0, dl + k * scale * 0.05) for k in range(-5, 6)),
                     key=lambda v: _nll(m, s, v, x, cat))
    return {"pse_cd_m2": float(math.exp(m)), "sigma_ln": float(s), "delta_ln": float(dl),
            "nll": _nll(m, s, dl, x, cat), "n": int(len(d))}


def adjust_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Committed settings per (task, layout, test colour, spatial frequency, rate):
    n, mean, SD and SE of the test luminance, the reference luminance, and
    ``ratio`` = mean setting / reference."""
    d = df[df["outcome"] == "SET"].copy()
    keys = [k for k in ("task", "layout", "test_colour", "reference_colour",
                        "spatial_freq_cpd", "rate_hz") if k in d]
    g = d.groupby(keys)["test_cd_m2"]
    out = pd.DataFrame({"n": g.size(), "mean_cd_m2": g.mean(), "sd_cd_m2": g.std(ddof=1)})
    out["se_cd_m2"] = out["sd_cd_m2"] / np.sqrt(out["n"])
    out = out.reset_index()
    ref = d.groupby(keys)["reference_cd_m2"].first().reset_index(drop=True)
    out["reference_cd_m2"] = ref.to_numpy()
    out["ratio"] = out["mean_cd_m2"] / out["reference_cd_m2"]
    return out


def relative_efficiency(motion: pd.DataFrame, uniform_flicker: pd.DataFrame) -> pd.DataFrame:
    """Fig. 3-4's ordinate: each colour's luminous efficiency relative to its standard
    uniform-field flicker match = uniform-flicker setting / setting (a colour that needs
    less luminance to match grey is relatively more efficient). Both inputs are
    ``adjust_summary`` tables against the same reference."""
    flick = uniform_flicker.set_index("test_colour")["mean_cd_m2"]
    out = motion.copy()
    out["relative_efficiency"] = out["test_colour"].map(flick) / out["mean_cd_m2"]
    return out
