"""The simulated subject for --mode simulate and the tests.

It answers the way the paper's observers did on average, so a rehearsal exercises the
analysis as well as the code paths. It is NOT data: its numbers are the paper's means fed
back in, and nothing it produces says anything about change blindness.

- Detection: the number of alternations before it presses SPACE is drawn from a
  lognormal whose mean is the paper's (p. 370): 7.3 for central and 17.1 for marginal
  interests with blanks, 1.4 with no blanks; a valid cue divides the mean by 2.5, an
  invalid one multiplies it by 1.1 (Exp. 3, Fig. 3c, read qualitatively). Intermediate
  interests get the geometric mean of the two. Past the time limit it simply never presses.
- Report: after ~0.6 s it presses the correct box with probability ``p_location`` and the
  correct change type with ``p_type``, otherwise another listed key.

It counts frames (one ``poll`` per frame) from the events the task emits, so its timing
does not depend on how fast the machine runs.
"""

from __future__ import annotations

import numpy as np
from alhazen.core.events import Event
from alhazen.devices.response import ResponseSample

MEAN_ALTERNATIONS = {"central": 7.3, "marginal": 17.1}
NO_BLANK_ALTERNATIONS = 1.4
CUE_FACTOR = {"none": 1.0, "valid": 1 / 2.5, "invalid": 1.1}


class SimulatedObserver:
    def __init__(self, seed: int = 0, sigma: float = 0.6, p_location: float = 0.97,
                 p_type: float = 0.98, report_frames: int = 36) -> None:
        self._rng = np.random.default_rng(seed)
        self._sigma = sigma
        self._p_location = p_location
        self._p_type = p_type
        self._report_frames = report_frames
        self._countdown: int | None = None
        self._key: str | None = None
        self.detections: list[float] = []  # drawn alternations, for tests

    def mean_alternations(self, interest: str, cue: str, blank_frames: int) -> float:
        if blank_frames == 0:
            base = NO_BLANK_ALTERNATIONS
        elif interest in MEAN_ALTERNATIONS:
            base = MEAN_ALTERNATIONS[interest]
        else:
            base = float(np.sqrt(MEAN_ALTERNATIONS["central"] * MEAN_ALTERNATIONS["marginal"]))
        return base * CUE_FACTOR.get(cue, 1.0)

    def _arm(self, frames: float, key: str) -> None:
        self._countdown = max(1, int(round(frames)))
        self._key = key

    def on_event(self, event: Event) -> None:
        pl = event.payload or {}
        if event.name == "FLICKER_ON":
            mean = self.mean_alternations(pl.get("interest", ""), pl.get("cue", "none"),
                                          int(pl.get("blank_frames", 1)))
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
