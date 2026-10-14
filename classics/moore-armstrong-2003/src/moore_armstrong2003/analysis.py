"""The paper's measures, computed from a run's files: the trial-level checks any session
can answer, and the neural measures, which need a recording this folder does not make.

Two kinds of input:

- ``*_trials.csv``: one row per attempt, with the flip-stamped event times
  (``t_vis_on``, ``t_stim_trigger`` / ``t_control_mark``, ``t_vis_off``) on the session
  clock. Enough for the design and timing checks below, and for the behavioural check
  the paper implies (subthreshold stimulation should not break fixation).
- spike times of the recorded V4 neuron, ON THE SESSION CLOCK: a CSV with a ``t_s``
  column (seconds), produced by aligning the lab's recording to the session with the
  sync pulses (alhazen's ``align_run``). Without it the neural measures cannot be
  computed, and nothing here pretends otherwise.

The neural measures follow the paper (p. 371): the visual-onset activity is the rate in
the 400 ms after the display appears; the stimulation effect is the rate in the 70 ms
window that starts when the train ends, stimulation minus control. Activity during the
train itself is never used (the paper excluded it: the stimulation artefact). On a
control trial the same window is taken after CONTROL_MARK plus the train's duration, so
the two conditions are measured at the same moment.

``synthetic_spikes_for_testing`` makes a Poisson spike train for exercising this code in
the tests. It is not data and carries no stimulation effect unless a test asks for one.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np
import pandas as pd

RF_ORDER = ["none", "orthogonal", "preferred"]  # the paper's Ø, np, p


@dataclass(frozen=True)
class Windows:
    """The measurement windows, in seconds (from the params file's ``analysis`` block)."""

    visual_onset_s: float = 0.400  # paper: p. 371
    post_train_s: float = 0.070  # paper: p. 371
    train_s: float = 0.050  # the session's stimulation.train_ms
    baseline_s: float = 0.300  # ASSUMED: the paper's baseline window is not stated


def mark_time(trials: pd.DataFrame) -> pd.Series:
    """The trigger moment of every trial: STIM_TRIGGER's flip on a stimulation trial,
    CONTROL_MARK's on a control trial (NaN when the trial ended before it)."""
    stim = trials.get("t_stim_trigger", pd.Series(np.nan, index=trials.index))
    ctrl = trials.get("t_control_mark", pd.Series(np.nan, index=trials.index))
    return stim.where(trials["stimulation"] == "stim", ctrl)


def realised_timing(trials: pd.DataFrame) -> pd.DataFrame:
    """Per completed trial: when the trigger went out after the bars appeared, and how
    long the bars were up, as the display's flips stamped them (ms)."""
    done = trials[trials["outcome"] == "COMPLETED"].copy()
    done["trigger_after_vis_on_ms"] = (mark_time(done) - done["t_vis_on"]) * 1000.0
    done["stimulus_on_ms"] = (done["t_vis_off"] - done["t_vis_on"]) * 1000.0
    return done[["trial_index", "display", "stimulation", "trigger_after_vis_on_ms",
                 "stimulus_on_ms"]]


def completed_counts(trials: pd.DataFrame) -> pd.DataFrame:
    """Completed trials per display condition and stimulation condition."""
    done = trials[trials["outcome"] == "COMPLETED"]
    return done.pivot_table(index="display", columns="stimulation", values="trial_index",
                            aggfunc="count", fill_value=0)


def break_after_trigger(trials: pd.DataFrame) -> pd.DataFrame:
    """Of the trials that reached the trigger moment, the fraction that ended with a
    fixation break after it, by stimulation condition. Subthreshold stimulation (p. 372)
    should leave stim and control alike; an excess on stim trials is the sign of evoked
    saccades, i.e. a current too close to the movement threshold."""
    reached = trials[mark_time(trials).notna()]
    out = reached.groupby("stimulation")["outcome"].agg(
        n_reached="count", n_broke=lambda s: int((s == "BROKE_FIX_AFTER_TRIGGER").sum()))
    out["p_broke"] = out["n_broke"] / out["n_reached"]
    return out


def _count(spikes: np.ndarray, start: float, stop: float) -> int:
    return int(np.searchsorted(spikes, stop, "left") - np.searchsorted(spikes, start, "left"))


def trial_rates(trials: pd.DataFrame, spike_times_s: np.ndarray, w: Windows) -> pd.DataFrame:
    """Per completed trial, the firing rate (spikes/s) in the paper's windows."""
    spikes = np.sort(np.asarray(spike_times_s, dtype=float))
    done = trials[trials["outcome"] == "COMPLETED"].copy()
    mark = mark_time(done)
    rows = []
    for (_, row), t_mark in zip(done.iterrows(), mark, strict=True):
        on = float(row["t_vis_on"])
        start = float(t_mark) + w.train_s
        rows.append({
            "trial_index": row["trial_index"],
            "rf_stimulus": row["rf_stimulus"],
            "distracter": row["distracter_stimulus"] != "none",
            "stimulation": row["stimulation"],
            "baseline_rate": _count(spikes, on - w.baseline_s, on) / w.baseline_s,
            "onset_rate": _count(spikes, on, on + w.visual_onset_s) / w.visual_onset_s,
            "post_train_rate": _count(spikes, start, start + w.post_train_s) / w.post_train_s,
        })
    return pd.DataFrame(rows)


def stimulation_effect(rates: pd.DataFrame, by_distracter: bool = False) -> pd.DataFrame:
    """The paper's Fig. 2c / Fig. 3 quantities for one neuron: per RF condition (and per
    distracter condition when asked), the visual-onset activity and the stimulation
    effect, mean post-train rate on stimulation trials minus control trials, with its
    standard error (unpaired: the paper's single-neuron pairing is not described).
    ``onset_norm`` divides the onset activity by the response to the preferred stimulus
    presented alone, as Fig. 3 normalises each neuron."""
    keys = ["rf_stimulus", "distracter"] if by_distracter else ["rf_stimulus"]
    out = []
    pref_alone = rates[(rates["rf_stimulus"] == "preferred") & ~rates["distracter"]]
    norm = pref_alone["onset_rate"].mean() if len(pref_alone) else np.nan
    for key, g in rates.groupby(keys):
        s = g.loc[g["stimulation"] == "stim", "post_train_rate"]
        c = g.loc[g["stimulation"] == "control", "post_train_rate"]
        diff = s.mean() - c.mean() if len(s) and len(c) else np.nan
        sem = (np.sqrt(s.var(ddof=1) / len(s) + c.var(ddof=1) / len(c))
               if len(s) > 1 and len(c) > 1 else np.nan)
        key = key if isinstance(key, tuple) else (key,)
        out.append({**dict(zip(keys, key, strict=True)), "n_stim": len(s), "n_control": len(c),
                    "onset_rate": g["onset_rate"].mean(),
                    "onset_norm": g["onset_rate"].mean() / norm if norm else np.nan,
                    "effect": diff, "effect_sem": sem})
    df = pd.DataFrame(out)
    df["rf_stimulus"] = pd.Categorical(df["rf_stimulus"], RF_ORDER, ordered=True)
    return df.sort_values(keys).reset_index(drop=True)


def synthetic_spikes_for_testing(
    trials: pd.DataFrame,
    rng: np.random.Generator,
    w: Windows,
    *,
    baseline_hz: float = 8.0,
    driven_hz: Mapping[str, float] | None = None,
    stim_gain_hz: float = 0.0,
) -> np.ndarray:
    """A Poisson spike train on the session clock, for TESTING THIS CODE ONLY: a rate of
    ``baseline_hz`` outside the bars, ``driven_hz[rf_stimulus]`` while they are up, plus
    ``stim_gain_hz`` in the post-train window of stimulation trials (default 0: no
    effect). Not a model of V4 and not a result."""
    driven = dict(driven_hz or {"none": 8.0, "orthogonal": 20.0, "preferred": 48.0})
    t0 = float(np.nanmin(trials["t_trial_start"])) - 1.0
    t1 = float(np.nanmax(trials["t_trial_end"])) + 1.0
    segments = [(t0, t1, baseline_hz)]
    done = trials[trials["outcome"] == "COMPLETED"]
    for (_, row), t_mark in zip(done.iterrows(), mark_time(done), strict=True):
        extra = driven[row["rf_stimulus"]] - baseline_hz
        segments.append((float(row["t_vis_on"]), float(row["t_vis_off"]), extra))
        if row["stimulation"] == "stim" and stim_gain_hz:
            start = float(t_mark) + w.train_s
            segments.append((start, start + w.post_train_s, stim_gain_hz))
    spikes = [rng.uniform(a, b, rng.poisson(max(rate, 0.0) * (b - a))) for a, b, rate in segments]
    return np.sort(np.concatenate(spikes))
