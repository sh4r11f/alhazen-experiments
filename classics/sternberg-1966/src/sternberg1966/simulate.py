"""The simulated subject for --mode simulate and the tests.

TEMPLATE STARTER: answers F or J at random a fixed delay after each response cue. Replace
it with an observer whose answers depend on the trial (a psychometric function, an RT
distribution), so a rehearsal exercises the analysis as well as the code paths.
"""

from __future__ import annotations

import time

import numpy as np
from alhazen.core.events import Event
from alhazen.devices.response import ResponseSample


class SimulatedObserver:
    def __init__(self, seed: int = 0, delay_s: float = 0.3) -> None:
        self._rng = np.random.default_rng(seed)
        self._delay_s = delay_s
        self._cue_at: float | None = None

    def on_event(self, event: Event) -> None:
        if event.name == "RESPONSE_CUE":
            self._cue_at = time.monotonic()

    def poll(self) -> ResponseSample:
        if self._cue_at is None or time.monotonic() - self._cue_at < self._delay_s:
            return ResponseSample()
        self._cue_at = None
        return ResponseSample(keys=(str(self._rng.choice(["f", "j"])),))
