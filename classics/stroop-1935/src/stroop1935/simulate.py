"""The simulated subject for ``--mode simulate`` and the tests.

It answers the way the design expects a subject to, so a rehearsal exercises
the analysis as well as the code: each item's reaction time is drawn from a
log-normal around a per-test median, it sometimes presses the competing
colour's key first and then corrects itself, now and then leaves an error
uncorrected, and rarely presses nothing at all (so the re-serve path runs).

The medians are Stroop's whole-sheet means divided by 100 (reprint pp. 17-18:
RCNb 41.0 s, RCNd 43.3 s, NC 63.3 s, NCWd 110.3 s per 100 items). They are
placeholders that give the simulated data the paper's ordering, NOT a
prediction of key-press reaction times, which nobody has measured with this
folder. A simulated session is software verification only.

How it learns the trial: the substituted task (``autopilot``) hands each
trial's record to ``prepare`` in ``build_trial``, and the RESPONSE_CUE event
(the stimulus flip) starts the clock, as alhazen's mbri experiment does.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

import numpy as np
from alhazen.core.events import Event
from alhazen.devices.response import ResponseSample

# Median seconds per item, from Stroop's sheet times (see the module docstring).
MEDIAN_S = {"NC": 0.633, "NCWd": 1.103, "RCNb": 0.410, "RCNd": 0.433}
# Chance the first key is wrong, per test (errors were few in the paper).
P_ERROR = {"NC": 0.02, "NCWd": 0.07, "RCNb": 0.01, "RCNd": 0.02}
SIGMA = 0.25  # log-normal spread of reaction times
P_LAPSE = 0.01  # no key at all: the item is served again
P_UNCORRECTED = 0.10  # of errors, left uncorrected until the deadline
CORRECTION_S = (0.25, 0.45)  # from the wrong key to the right one


class SimulatedObserver:
    def __init__(self, seed: int = 0, now: Callable[[], float] = time.perf_counter) -> None:
        self._rng = np.random.default_rng(seed)
        self._now = now
        self._trial: dict[str, Any] | None = None
        self._keys: tuple[str, ...] = ()
        self._queue: list[tuple[float, str]] = []

    def describe(self) -> dict[str, Any]:
        return {"source": "stroop1935.simulate", "median_s": MEDIAN_S, "p_error": P_ERROR,
                "sigma": SIGMA, "p_lapse": P_LAPSE, "p_uncorrected": P_UNCORRECTED,
                "note": "medians are Stroop's sheet means / 100, not a key-RT prediction"}

    def prepare(self, record: dict[str, Any], test: str, keys: tuple[str, ...]) -> None:
        """What the next trial asks for: its record, its test and the bound keys."""
        self._trial = {**record, "test": test}
        self._keys = keys
        self._queue = []

    def on_event(self, event: Event) -> None:
        if event.name != "RESPONSE_CUE" or self._trial is None:
            return
        trial, self._trial = self._trial, None
        t0 = self._now()
        if self._rng.random() < P_LAPSE:
            return
        test = trial["test"]
        rt = float(MEDIAN_S[test] * np.exp(SIGMA * self._rng.standard_normal()))
        correct = trial["correct_key"]
        if self._rng.random() < P_ERROR[test]:
            wrong = trial.get("competing_key") or str(
                self._rng.choice([k for k in self._keys if k != correct]))
            self._queue.append((t0 + rt, wrong))
            if self._rng.random() >= P_UNCORRECTED:
                self._queue.append((t0 + rt + float(self._rng.uniform(*CORRECTION_S)), correct))
        else:
            self._queue.append((t0 + rt, correct))

    def poll(self) -> ResponseSample:
        if not self._queue:
            return ResponseSample()
        now = self._now()
        due = [k for t, k in self._queue if t <= now]
        self._queue = [(t, k) for t, k in self._queue if t > now]
        return ResponseSample(keys=tuple(due))


class _Autopilot:
    """Mixed in before a Stroop task class: tells the observer each trial."""

    _observer: SimulatedObserver

    def build_trial(self, setup):  # type: ignore[no-untyped-def]
        plan = super().build_trial(setup)  # type: ignore[misc]
        keys = tuple(self.params.keys.values())  # type: ignore[attr-defined]
        self._observer.prepare(plan.record, setup.condition.params["test"], keys)
        return plan


def autopilot(task: Any, observer: SimulatedObserver) -> Any:
    """``task`` rebuilt as a subclass that keeps ``observer`` informed."""
    base = type(task)
    cls = type(f"{base.__name__}Autopilot", (_Autopilot, base), {"_observer": observer})
    return cls(task.params)
