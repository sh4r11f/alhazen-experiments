"""The simulated subject for --mode simulate and the tests.

It remembers what it was shown (the series in experiment 1, the announced positive set in
experiment 2), answers the test digit from that memory, and types the series back at the
recall. Its reaction time is the paper's own linear fit, intercept + slope x s, plus
ex-Gaussian noise; its error rates are the paper's (1.3 % wrong lever and 1.4 % imperfect
recall in experiment 1, p. 652). So a rehearsal exercises the analysis on data with the
shape the paper reported. Recovering those numbers from simulated data checks the pipeline;
it is NOT a replication of the result.
"""

from __future__ import annotations

import time
from typing import Any

import numpy as np
from alhazen.core.events import Event
from alhazen.devices.response import ResponseSample


class SimulatedObserver:
    def __init__(
        self,
        seed: int = 0,
        positive_key: str = "j",
        negative_key: str = "f",
        intercept_ms: float = 397.2,
        slope_ms: float = 37.9,
        sd_ms: float = 50.0,
        tau_ms: float = 80.0,
        p_error: float = 0.013,
        p_recall_error: float = 0.014,
        read_s: float = 0.6,
        type_s: float = 0.15,
        clock: Any = time.monotonic,
    ) -> None:
        self._rng = np.random.default_rng(seed)
        self._keys = {True: positive_key, False: negative_key}
        self.intercept_ms, self.slope_ms = intercept_ms, slope_ms
        self.sd_ms, self.tau_ms = sd_ms, tau_ms
        self.p_error, self.p_recall_error = p_error, p_recall_error
        self._read_s, self._type_s = read_s, type_s
        self._now = clock
        self.memory: list[int] = []
        self._queue: list[tuple[float, str]] = []

    def describe(self) -> dict[str, float]:
        return {"intercept_ms": self.intercept_ms, "slope_ms": self.slope_ms,
                "sd_ms": self.sd_ms, "tau_ms": self.tau_ms, "p_error": self.p_error,
                "p_recall_error": self.p_recall_error}

    def _press(self, after_s: float, key: str) -> None:
        self._queue.append((self._now() + after_s, key))
        self._queue.sort()

    def rt_ms(self, set_size: int) -> float:
        """One reaction time: mean intercept + slope x s, normal plus exponential spread."""
        noise = self._rng.normal(0.0, self.sd_ms) + self._rng.exponential(self.tau_ms) - self.tau_ms
        return max(150.0, self.intercept_ms + self.slope_ms * set_size + noise)

    def on_event(self, event: Event) -> None:
        payload = event.payload or {}
        if event.name == "ITEM_ON":
            if payload["position"] == 1:
                self.memory = []
            self.memory.append(int(payload["digit"]))
        elif event.name == "SET_ANNOUNCED":
            self.memory = [int(d) for d in payload["digits"]]
            self._press(self._read_s, "space")
        elif event.name == "PROBE_DIGIT":
            positive = int(payload["digit"]) in self.memory
            if self._rng.random() < self.p_error:
                positive = not positive
            self._press(self.rt_ms(len(self.memory)) / 1000.0, self._keys[positive])
        elif event.name == "RECALL_ON":
            typed = [str(d) for d in self.memory]
            if typed and self._rng.random() < self.p_recall_error:
                i = int(self._rng.integers(len(typed)))
                typed[i] = str((int(typed[i]) + 1) % 10)
            for i, key in enumerate([*typed, "return"], start=1):
                self._press(self._read_s + i * self._type_s, key)

    def poll(self) -> ResponseSample:
        now = self._now()
        due = [key for t, key in self._queue if t <= now]
        self._queue = [(t, key) for t, key in self._queue if t > now]
        return ResponseSample(keys=tuple(due))
