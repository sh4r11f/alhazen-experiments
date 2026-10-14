"""The simulated subject for --mode simulate and the tests.

A searcher whose reaction times follow the pattern the paper reports, so a rehearsal gives
the analysis notebook an effect to recover: serial self-terminating search for conjunction
targets (each item costs ``per_item_ms``; a present target is found after a uniformly
random number of items, so the present slope is about half the absent one), and for
feature targets a nearly flat present function with a shallow absent slope. The numbers
are set from the paper's regressions (Table 1, p. 105; Table 2, p. 109). They are a
generative model for software testing, not data, and nothing here is a participant result.

It knows each trial's answer through ``SimulatedSearchTask``, the task subclass simulate
mode runs (alhazen.modes.simulation: a simulated subject whose answers depend on the trial
supplies a task that knows the answer).
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import asdict, dataclass

import numpy as np
from alhazen.core.events import Event
from alhazen.devices.response import ResponseSample

from treisman_gelade1980.task import FeatureConjunctionSearchTask


@dataclass(frozen=True)
class SearchModel:
    """RT model of one condition, in ms. ``serial``: absent = base_absent + per_item * n,
    present = base_present + per_item * k, k uniform on 1..n. Otherwise linear in n."""

    serial: bool
    base_present: float
    base_absent: float
    per_item: float = 0.0  # serial cost per item
    slope_present: float = 0.0  # non-serial
    slope_absent: float = 0.0  # non-serial


# From the paper's fitted intercepts and slopes (Tables 1 and 2). For the serial models
# the per-item cost is the negative slope and the present intercept is set so the mean
# present function matches the paper's intercept.
MODELS = {
    "conjunction": SearchModel(True, base_present=398 - 67.1 / 2, base_absent=397, per_item=67.1),
    "feature": SearchModel(False, base_present=448, base_absent=514, slope_present=3.1,
                           slope_absent=25.1),
    "easy": SearchModel(True, base_present=437 - 39.5 / 2, base_absent=489, per_item=39.5),
    "difficult": SearchModel(True, base_present=453 - 92.4 / 2, base_absent=472, per_item=92.4),
}


class SimulatedSearcher:
    """Presses the ready key soon after the white field appears, and answers each search
    display after a sampled RT, wrong with a small probability."""

    def __init__(self, seed: int = 0, *, noise_cv: float = 0.15, p_miss: float = 0.03,
                 p_false_alarm: float = 0.015, ready_s: float = 0.25,
                 now: Callable[[], float] = time.monotonic) -> None:
        self._rng = np.random.default_rng(seed)
        self._noise_cv = noise_cv
        self._p_miss = p_miss
        self._p_fa = p_false_alarm
        self._ready_s = ready_s
        self._now = now
        self._trial: dict | None = None
        self._due: float | None = None
        self._key: str | None = None

    def describe(self) -> dict:
        return {"noise_cv": self._noise_cv, "p_miss": self._p_miss,
                "p_false_alarm": self._p_fa, "models": {k: asdict(v) for k, v in MODELS.items()}}

    def expect(self, condition: str, display_size: int, present: bool, present_key: str,
               absent_key: str, ready_key: str) -> None:
        """What the next trial asks (called by SimulatedSearchTask.build_trial)."""
        self._trial = dict(condition=condition, n=display_size, present=present,
                           present_key=present_key, absent_key=absent_key, ready_key=ready_key)

    def rt_ms(self, condition: str, n: int, present: bool) -> float:
        m = MODELS[condition]
        if m.serial:
            mean = (m.base_present + m.per_item * int(self._rng.integers(1, n + 1)) if present
                    else m.base_absent + m.per_item * n)
        else:
            mean = (m.base_present + m.slope_present * n if present
                    else m.base_absent + m.slope_absent * n)
        return float(max(150.0, mean * (1.0 + self._noise_cv * self._rng.standard_normal())))

    def on_event(self, event: Event) -> None:
        if self._trial is None:
            return
        t = self._trial
        if event.name == "READY_ON":
            self._due, self._key = self._now() + self._ready_s, t["ready_key"]
        elif event.name == "ARRAY_ON":
            wrong = self._rng.random() < (self._p_miss if t["present"] else self._p_fa)
            says_present = t["present"] != wrong
            self._key = t["present_key"] if says_present else t["absent_key"]
            self._due = self._now() + self.rt_ms(t["condition"], t["n"], t["present"]) / 1000.0

    def poll(self) -> ResponseSample:
        if self._due is None or self._now() < self._due:
            return ResponseSample()
        key, self._due, self._key = self._key, None, None
        return ResponseSample(keys=(key,)) if key else ResponseSample()


class SimulatedSearchTask(FeatureConjunctionSearchTask):
    """The task as simulate mode runs it: identical trials, plus telling the simulated
    searcher what each trial asks."""

    def __init__(self, params, observer: SimulatedSearcher) -> None:
        super().__init__(params)
        self._observer = observer

    def build_trial(self, setup):
        plan = super().build_trial(setup)
        c = setup.condition.params
        p = self.params
        self._observer.expect(str(c["condition"]), int(c["display_size"]),
                              bool(c["target_present"]), p.present_key, p.absent_key, p.ready_key)
        return plan
