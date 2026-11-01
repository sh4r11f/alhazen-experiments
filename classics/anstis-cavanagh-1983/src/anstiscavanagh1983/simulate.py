"""The simulated observer for --mode simulate and the tests.

A toy observer whose answers depend on the trial, shaped after the paper's numbers so a
rehearsal exercises the analysis. Its "true" equiluminant test luminance for each pair is
the reference times a ratio near the paper's (red vs 13.4 cd/m2 green: PSEs of 9.54 and
10.47 cd/m2, p. 157; blue vs 7.9 cd/m2 yellow: 10.5 and 9.41; colours vs 13.6 cd/m2 grey:
the flicker matches of p. 159), with red's efficiency rising and blue's falling with
spatial frequency (Fig. 3). These numbers are a model of a model: NOT data, and a
simulated session is not a replication. The observer also knows nothing about the
display: it answers in the cd/m2 the task reports, whatever the photometry file says.

Constant stimuli: an ordered-probit observer on log luminance. Let d = ln(L / PSE) + e,
e ~ N(0, sigma). It reports motion consistent with "test lighter" when d > delta,
"reference lighter" when d < -delta, and "neither" otherwise (the paper's indifference
band, p. 157). The direction it reports on the screen is that times the trial's step.

It never reads pixels. It learns each trial from the FIX_ON / ADJUST_START payloads.
"""

from __future__ import annotations

import math
import time
from typing import Any

import numpy as np
from alhazen.core.events import Event
from alhazen.devices.response import ResponseSample

# (test, reference) -> PSE / reference luminance at 2.5 c/deg (toy values, see above).
RATIO = {
    ("red", "green"): 10.0 / 13.4,
    ("blue", "yellow"): 9.95 / 7.9,
    ("red", "grey"): 12.4 / 13.6,
    ("green", "grey"): 14.7 / 13.6,
    ("blue", "grey"): 12.6 / 13.6,
}
# Change of ln(ratio) per octave of spatial frequency (Fig. 3: red's luminous efficiency
# rises with spatial frequency, so its PSE falls; blue's falls, so its PSE rises).
SF_SLOPE = {"red": -0.05, "green": 0.0, "blue": 0.06}


class SimulatedObserver:
    def __init__(self, seed: int = 0, delay_s: float = 0.4, sigma: float = 0.025,
                 delta: float = 0.03) -> None:
        self._rng = np.random.default_rng(seed)
        self.bias = float(self._rng.normal(0.0, 0.04))  # this observer's ln-ratio offset
        self.sigma, self.delta = sigma, delta
        self._delay = delay_s
        self._info: dict | None = None
        self._answer: str | None = None
        self._cue_at: float | None = None
        self._knob: dict | None = None

    def describe(self) -> dict[str, Any]:
        return {"ln_ratio_offset": round(self.bias, 4), "sigma_ln": self.sigma,
                "delta_ln": self.delta, "model": "toy ordered probit; not data"}

    def pse(self, info: dict) -> float:
        test, ref = info["test_colour"], info["reference_colour"]
        ratio = RATIO.get((test, ref), 1.0)
        sf = float(info.get("spatial_freq_cpd") or 2.5)
        octaves = math.log2(sf / 2.5) if sf > 0 else 0.0
        ln = math.log(ratio) + SF_SLOPE.get(test, 0.0) * octaves + self.bias
        return float(info["reference_cd_m2"]) * math.exp(ln)

    def report(self, info: dict) -> str:
        d = math.log(float(info["test_cd_m2"]) / self.pse(info)) + self._rng.normal(0, self.sigma)
        if abs(d) <= self.delta:
            return "down"
        lighter = 1 if d > 0 else -1
        return "right" if lighter * int(info["step"]) > 0 else "left"

    def on_event(self, event: Event) -> None:
        if event.name == "FIX_ON":
            self._info = dict(event.payload)
        elif event.name == "RESPONSE_CUE" and self._info is not None:
            self._answer = self.report(self._info)
            self._cue_at = time.monotonic() + float(self._rng.uniform(0.0, 0.3))
        elif event.name == "ADJUST_START":
            info = dict(event.payload)
            target = self.pse(info) * math.exp(self._rng.normal(0.0, 0.02))
            self._knob = {**info, "target": min(max(target, info["lo"]), info["hi"]),
                          "t0": time.monotonic(), "settled": None}
        elif event.name == "TRIAL_END":
            self._knob = None

    def poll(self) -> ResponseSample:
        now = time.monotonic()
        if self._answer is not None and self._cue_at is not None \
                and now - self._cue_at >= self._delay:
            key, self._answer, self._cue_at = self._answer, None, None
            return ResponseSample(keys=(key,))
        knob = self._knob
        if knob is None or now - knob["t0"] < self._delay:
            return ResponseSample()
        v, target, step = knob["value"], knob["target"], knob["step"]
        n = round(math.log(target / v) / math.log(step))
        if n == 0:
            if knob["settled"] is None:
                knob["settled"] = now
            if now - knob["settled"] >= 0.15:
                self._knob = None
                return ResponseSample(keys=("space",))
            return ResponseSample()
        notch = int(max(-5, min(5, n)))
        knob["value"] = min(max(v * step**notch, knob["lo"]), knob["hi"])
        return ResponseSample(wheel=float(notch))
