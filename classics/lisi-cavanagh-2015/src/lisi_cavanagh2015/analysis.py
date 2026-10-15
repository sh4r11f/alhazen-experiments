"""The paper's measures, from a run's ``*_trials.csv`` (used by notebooks/analysis.ipynb).

Lisi & Cavanagh (2015), Supplemental Experimental Procedures, Analysis, Experiment 1:

- **Perceptual task.** For each participant and drift pairing, the point of subjective
  verticality is the mean of a cumulative Gaussian fitted by maximum likelihood to the
  proportion of "right" reports as a function of the physical path orientation.
- **Saccade task.** Trials with latencies under 100 ms or over 600 ms are excluded. A
  multivariate linear model per participant predicts the horizontal and vertical saccade
  amplitudes from the Gabor's coordinates at saccade onset, the condition (control vs
  double-drift) and their interactions. Its predictions along the Gabor's path are regressed
  vertical-on-horizontal, and the slope gives the path orientation "seen" by the saccades;
  double-drift minus control is the effect of the internal motion.
- **Orthogonal landing error** (double-drift trials): each landing's signed distance from
  the physical path, compared between leftward and rightward internal drift at saccade
  onset, and regressed on the Gabor's position along the path.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import norm

from lisi_cavanagh2015.geometry import path_vectors, recovered_angle_deg

LATENCY_MIN_MS = 100.0  # paper: Results, Exp. 1
LATENCY_MAX_MS = 600.0  # paper: Results, Exp. 1


# --------------------------------------------------------------------------------------
# Perceptual task
# --------------------------------------------------------------------------------------
@dataclass(frozen=True)
class PsychometricFit:
    mu: float  # the PSE: the orientation reported "right" half the time
    sigma: float
    n: int


def fit_cumulative_gaussian(x: Iterable[float], right: Iterable[bool]) -> PsychometricFit:
    """Maximum-likelihood cumulative Gaussian, P(right) = Phi((x - mu) / sigma)."""
    x = np.asarray(list(x), dtype=float)
    y = np.asarray(list(right), dtype=bool)
    if len(x) < 3:
        raise ValueError("need at least three trials to fit a psychometric function")

    def nll(theta: np.ndarray) -> float:
        mu, log_sigma = theta
        p = norm.cdf((x - mu) / math.exp(log_sigma))
        p = np.clip(p, 1e-9, 1 - 1e-9)
        return -float(np.sum(np.where(y, np.log(p), np.log1p(-p))))

    start = np.array([float(np.median(x)), math.log(max(float(np.std(x)), 1.0))])
    best = minimize(nll, start, method="Nelder-Mead",
                    options={"xatol": 1e-4, "fatol": 1e-6, "maxiter": 4000})
    return PsychometricFit(mu=float(best.x[0]), sigma=float(math.exp(best.x[1])), n=len(x))


def perceptual_pse(trials: pd.DataFrame) -> pd.DataFrame:
    """One row per drift pairing: the PSE (deg), the slope sigma and the trial count."""
    done = trials[trials["outcome"].isin(["REPORTED_RIGHT", "REPORTED_LEFT"])]
    rows = []
    for side, g in done.groupby("tilt_side"):
        fit = fit_cumulative_gaussian(g["path_angle_deg"], g["outcome"] == "REPORTED_RIGHT")
        rows.append({"tilt_side": side, "pse_deg": fit.mu, "sigma_deg": fit.sigma, "n": fit.n})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------------------
# Saccade task
# --------------------------------------------------------------------------------------
def usable_saccades(trials: pd.DataFrame) -> pd.DataFrame:
    """Completed saccades with a measured, settled landing and a latency in 100-600 ms."""
    df = trials[trials["outcome"] == "SACCADE"].copy()
    df = df[df["endpoint_measured"].astype(bool)]
    if "endpoint_settled" in df:
        df = df[df["endpoint_settled"].astype(bool)]
    lat = df["saccade_latency_ms"].astype(float)
    return df[(lat >= LATENCY_MIN_MS) & (lat <= LATENCY_MAX_MS)]


def _design(x: np.ndarray, y: np.ndarray, dd: np.ndarray) -> np.ndarray:
    return np.column_stack([np.ones_like(x), x, y, dd, dd * x, dd * y])


def recover_orientations(sacc: pd.DataFrame, n_points: int = 21) -> pd.DataFrame:
    """The path orientation targeted by the saccades, per tilt and condition.

    The two-step analysis of the paper: one multivariate linear model (both amplitudes,
    predictors: Gabor x and y at onset, condition, condition x coordinates) per
    participant; its predictions along each physical path, regressed vertical on
    horizontal; the angle of that line from vertical (clockwise positive)."""
    if sacc.empty:
        return pd.DataFrame()
    x = sacc["gabor_x_at_onset_dva"].to_numpy(float)
    y = sacc["gabor_y_at_onset_dva"].to_numpy(float)
    dd = sacc["internal_motion"].astype(bool).to_numpy(float)
    amps = sacc[["saccade_dx_dva", "saccade_dy_dva"]].to_numpy(float)
    X = _design(x, y, dd)
    coef, *_ = np.linalg.lstsq(X, amps, rcond=None)
    fitted = X @ coef
    ss_res = ((amps - fitted) ** 2).sum(axis=0)
    ss_tot = ((amps - amps.mean(axis=0)) ** 2).sum(axis=0)
    r2 = 1.0 - ss_res / np.where(ss_tot > 0, ss_tot, np.nan)
    rows = []
    for side, g in sacc.groupby("tilt_side"):
        angle = float(g["path_angle_deg"].iloc[0])
        cx, cy = float(g["path_center_x_dva"].iloc[0]), float(g["path_center_y_dva"].iloc[0])
        half = float(g["path_length_dva"].iloc[0]) / 2.0
        u, _ = path_vectors(angle)
        s = np.linspace(-half, half, n_points)
        px, py = cx + s * u[0], cy + s * u[1]
        for motion in (False, True):
            pred = _design(px, py, np.full_like(px, float(motion))) @ coef
            slope = np.polyfit(pred[:, 0], pred[:, 1], 1)[0]
            rows.append({"tilt_side": side, "condition": "double-drift" if motion else "control",
                         "physical_deg": angle, "recovered_deg": recovered_angle_deg(slope),
                         "n": int((g["internal_motion"].astype(bool) == motion).sum()),
                         "r2_dx": float(r2[0]), "r2_dy": float(r2[1])})
    return pd.DataFrame(rows)


def internal_motion_effect(orientations: pd.DataFrame) -> pd.DataFrame:
    """Double-drift minus control recovered orientation, per tilt (paper Figure 1F)."""
    if orientations.empty:
        return pd.DataFrame()
    wide = orientations.pivot(index="tilt_side", columns="condition", values="recovered_deg")
    out = (wide["double-drift"] - wide["control"]).rename("effect_deg").reset_index()
    return out.merge(wide.reset_index(), on="tilt_side")


def orthogonal_errors(sacc: pd.DataFrame) -> pd.DataFrame:
    """Double-drift trials with each landing's signed distance from the physical path
    (positive = right of it, along +n) and the drift direction at onset."""
    dd = sacc[sacc["internal_motion"].astype(bool)].copy()
    if dd.empty:
        return dd
    err = []
    for _, r in dd.iterrows():
        _, n = path_vectors(float(r["path_angle_deg"]))
        err.append((float(r["endpoint_x_dva"]) - float(r["path_center_x_dva"])) * n[0]
                   + (float(r["endpoint_y_dva"]) - float(r["path_center_y_dva"])) * n[1])
    dd["orthogonal_error_dva"] = err
    dd["drift_at_onset"] = np.where(dd["drift_sign_at_onset"].astype(float) > 0, "rightward",
                                    "leftward")
    return dd


def orthogonal_shift(errs: pd.DataFrame) -> dict[str, float]:
    """Rightward minus leftward drift mean orthogonal error (paper: 0.67 dva), and the
    slope of the error along the path for each tilt (paper: not different from 0)."""
    out: dict[str, float] = {}
    if errs.empty:
        return out
    means = errs.groupby("drift_at_onset")["orthogonal_error_dva"].mean()
    if {"rightward", "leftward"} <= set(means.index):
        out["rightward_minus_leftward_dva"] = float(means["rightward"] - means["leftward"])
    for side, g in errs.groupby("tilt_side"):
        if len(g) >= 4:
            # error ~ 1 + position along the path + drift direction at onset (Figure S2B)
            X = np.column_stack([np.ones(len(g)), g["gabor_along_at_onset_dva"].astype(float),
                                 g["drift_sign_at_onset"].astype(float)])
            beta, *_ = np.linalg.lstsq(X, g["orthogonal_error_dva"].astype(float), rcond=None)
            out[f"slope_along_path_{side}"] = float(beta[1])
    return out
