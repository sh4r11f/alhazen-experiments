"""The simulated observer for --mode simulate and the tests.

It answers from a model of the paper's measurement: the adapted display's downward signal
looks stronger by a fixed aftereffect shift (in % signal) after unidirectional adaptation
and by nothing after RDVN adaptation, and the observer picks the display that looks more
coherently downward, with Gaussian decision noise and a small lapse rate:

    p(choose test) = lapse / 2 + (1 - lapse) * Phi((test% + shift - reference%) / sigma)

so the PSE is ``reference% - shift`` and the analysis can be checked against it. The
default shift, 40 %, is planted to resemble the paper's reported match (RDVN after
adaptation matched 40 % real signal, p. 9026); sigma and the lapse rate are made up. None
of it is anyone's data.
"""

from __future__ import annotations

import math
import time
from typing import Any

import numpy as np
from alhazen.core.events import Event
from alhazen.devices.response import ResponseSample


def p_choose_test(test_pct: float, reference_pct: float, shift_pct: float, sigma_pct: float,
                  lapse: float = 0.0) -> float:
    """Probability of judging the test display more coherently downward."""
    z = (test_pct + shift_pct - reference_pct) / sigma_pct
    phi = 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))
    return lapse / 2.0 + (1.0 - lapse) * phi


class SimulatedObserver:
    """Reads each trial's condition from TRIAL_START and answers after the response cue
    with a lognormal reaction time."""

    def __init__(self, test_key: str = "left", reference_key: str = "right",
                 reference_pct: float = 40.0, seed: int = 0, shift_pct: float = 40.0,
                 sigma_pct: float = 10.0, lapse: float = 0.02, p_no_response: float = 0.0,
                 median_rt_s: float = 0.6) -> None:
        self._keys = {True: test_key, False: reference_key}
        self._ref = reference_pct
        self._rng = np.random.default_rng(seed)
        self._shift, self._sigma, self._lapse = shift_pct, sigma_pct, lapse
        self._p_none = p_no_response
        self._median_rt = median_rt_s
        self._trial: dict[str, Any] = {}
        self._due: float | None = None
        self._key: str | None = None

    def describe(self) -> dict[str, Any]:
        return {"source": "hirisblake1992.simulate.SimulatedObserver",
                "shift_pct_after_unidirectional_adaptation": self._shift,
                "sigma_pct": self._sigma, "lapse": self._lapse,
                "p_no_response": self._p_none, "planted": True}

    def shift_for(self, adapt_mode: str) -> float:
        return self._shift if adapt_mode == "unidirectional" else 0.0

    def choose(self, test_pct: float, adapt_mode: str) -> bool:
        p = p_choose_test(test_pct, self._ref, self.shift_for(adapt_mode), self._sigma,
                          self._lapse)
        return bool(self._rng.random() < p)

    def on_event(self, event: Event) -> None:
        if event.name == "TRIAL_START":
            self._trial = dict(event.payload)
            self._due = None
        elif event.name == "RESPONSE_CUE" and self._trial:
            if self._rng.random() < self._p_none:
                return
            chose_test = self.choose(float(self._trial["test_signal_pct"]),
                                     str(self._trial.get("adapt_mode", "unidirectional")))
            self._key = self._keys[chose_test]
            rt = float(self._rng.lognormal(math.log(self._median_rt), 0.25))
            self._due = time.monotonic() + rt

    def poll(self) -> ResponseSample:
        if self._due is None or time.monotonic() < self._due:
            return ResponseSample()
        self._due = None
        return ResponseSample(keys=(str(self._key),))
