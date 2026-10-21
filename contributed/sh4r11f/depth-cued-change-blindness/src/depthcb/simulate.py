"""The simulated subject for --mode simulate and the tests.

It exists so a rehearsal exercises the task and the analysis. It is NOT data, and its
numbers are invented, not taken from any study:

- Detection: alternations before SPACE ~ lognormal with mean 7 (near-plane changes) or
  9 (far-plane changes), times a cue factor: valid 0.6, neutral or no cue 1.0, invalid 1.5.
  Past the time limit it never presses.
- Report: after ~0.6 s it presses the correct box with probability ``p_location`` and the
  correct change type with ``p_type``, otherwise another listed key.

It counts frames (one ``poll`` per frame) from the task's events, so its timing does not
depend on how fast the machine runs.
"""

from __future__ import annotations

import numpy as np
from alhazen.core.events import Event
from alhazen.devices.response import ResponseSample

MEAN_ALTERNATIONS = {"near": 7.0, "far": 9.0}
CUE_FACTOR = {"valid": 0.6, "neutral": 1.0, "none": 1.0, "invalid": 1.5}


class SimulatedObserver:
    def __init__(self, seed: int = 0, sigma: float = 0.5, p_location: float = 0.97,
                 p_type: float = 0.98, report_frames: int = 36) -> None:
        self._rng = np.random.default_rng(seed)
        self._sigma = sigma
        self._p_location = p_location
        self._p_type = p_type
        self._report_frames = report_frames
        self._countdown: int | None = None
        self._key: str | None = None
        self.detections: list[float] = []  # drawn alternations, for tests

    @staticmethod
    def mean_alternations(plane: str, cue: str) -> float:
        return MEAN_ALTERNATIONS.get(plane, 8.0) * CUE_FACTOR.get(cue, 1.0)

    def _arm(self, frames: float, key: str) -> None:
        self._countdown = max(1, int(round(frames)))
        self._key = key

    def on_event(self, event: Event) -> None:
        pl = event.payload or {}
        if event.name == "FLICKER_ON":
            mean = self.mean_alternations(pl.get("plane", ""), pl.get("cue", "none"))
            mu = np.log(mean) - self._sigma**2 / 2  # lognormal with this mean
            n = float(self._rng.lognormal(mu, self._sigma))
            self.detections.append(n)
            self._arm(n * float(pl.get("alternation_frames", 38)), "space")
        elif event.name in ("LOCATION_PROBE", "TYPE_PROBE"):
            p = self._p_location if event.name == "LOCATION_PROBE" else self._p_type
            keys = list(pl.get("keys", []))
            answer = pl.get("answer")
            if self._rng.random() < p or len(keys) < 2:
                key = answer
            else:
                key = str(self._rng.choice([k for k in keys if k != answer]))
            self._arm(self._report_frames + self._rng.integers(-8, 9), key)
        elif event.name in ("TRIAL_END", "TRIAL_START"):
            self._countdown, self._key = None, None

    def poll(self) -> ResponseSample:
        if self._countdown is None:
            return ResponseSample()
        self._countdown -= 1
        if self._countdown > 0:
            return ResponseSample()
        key, self._countdown, self._key = self._key, None, None
        return ResponseSample(keys=(key,)) if key else ResponseSample()
