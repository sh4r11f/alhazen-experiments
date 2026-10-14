"""The simulated subject for --mode simulate and the tests.

It answers the way the paper's subjects did on average, so a rehearsal exercises the
analysis as well as the code: for a "same" pair the reaction time grows linearly with
the angular difference (intercept + angle / rate), for a "different" pair it is longer
on average, both with lognormal scatter, and it presses the wrong key a few percent of
the time (more at large angles). The numbers come from params.simulated_subject; the
main parameter set plants the paper's own results (about 1 s at 0 deg, about 60 deg/s,
3.8 s for "different" pairs, 3.2% errors overall). Planted values are what a rehearsal
can recover, not a prediction about real subjects.

It learns what each trial is from TRIAL_START, whose payload is the trial's condition,
and starts its clock on PAIR_ON, the flip that showed the pair. It times itself on the
session clock when it is given one (a FakeClock session in simulated time,
scripts/simulate_sessions.py), else on the host's monotonic clock, which is what
`run.py --mode simulate` paces against.
"""

from __future__ import annotations

import time
from collections.abc import Callable

import numpy as np
from alhazen.core.events import Event
from alhazen.devices.response import ResponseSample

from shepard_metzler1971.params import SimulatedSubjectConfig


class SimulatedObserver:
    def __init__(self, cfg: SimulatedSubjectConfig, same_key: str, different_key: str,
                 seed: int = 0, now: Callable[[], float] = time.monotonic) -> None:
        self._now = now
        self._cfg = cfg
        self._keys = {"same": same_key, "different": different_key}
        self._rng = np.random.default_rng(seed)
        self._condition: dict = {}
        self._due: float | None = None
        self._key: str | None = None

    def plan(self, condition: dict) -> tuple[float, str]:
        """(reaction time in s, key) for one trial: the model, separate from the clock."""
        cfg = self._cfg
        angle = float(condition.get("angle_deg", 0.0))
        if condition.get("kind") == "same":
            mean = cfg.intercept_s + angle / cfg.rate_deg_per_s
        else:
            mean = cfg.different_mean_s
        # lognormal with this mean: median = mean * exp(-sd^2 / 2)
        rt = float(mean * np.exp(cfg.rt_log_sd * self._rng.standard_normal()
                                 - cfg.rt_log_sd ** 2 / 2))
        p_error = cfg.error_rate_at_0 + (cfg.error_rate_at_180 - cfg.error_rate_at_0) * angle / 180
        answer = condition.get("kind", "same")
        if self._rng.random() < p_error:
            answer = "different" if answer == "same" else "same"
        return rt, self._keys[answer]

    def on_event(self, event: Event) -> None:
        if event.name == "TRIAL_START":
            self._condition = dict(event.payload or {})
            self._due = None
        elif event.name == "PAIR_ON":
            rt, self._key = self.plan(self._condition)
            self._due = self._now() + rt

    def poll(self) -> ResponseSample:
        if self._due is None or self._now() < self._due:
            return ResponseSample()
        self._due = None
        return ResponseSample(keys=(self._key,))
