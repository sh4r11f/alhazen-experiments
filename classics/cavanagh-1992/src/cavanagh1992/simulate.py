"""The simulated observer for --mode simulate and the tests.

A toy observer whose answers depend on the trial, shaped after the paper's figures so a
rehearsal exercises the analysis: tracking accuracy after Fig. 1B (observer T.W.: colour
bars tracked near-perfectly until the luminance grating is strong, luminance bars barely
above chance until two to four times the motion-null contrast), thresholds and the null
after Fig. 1C, apparent speed after Fig. 2. Its numbers are a model of a model: they are
NOT data, and a simulated session is not a replication.

It never reads the stimulus. It learns what each trial asks from the events the task
emits (``TEST_ON`` carries whether the test pointer is on the tracked pair; the
``ADJUST_START`` payload carries the condition, the starting value and the knob's
step), keeps track of where its own turns have moved the knob, and presses keys or turns
the wheel after a reaction delay.
"""

from __future__ import annotations

import math
import time
from typing import Any

import numpy as np
from alhazen.core.events import Event
from alhazen.devices.response import ResponseSample

# The observer's "true" values; each seed jitters them.
TRUE = {
    "k": 1.0,                 # green-to-red modulation ratio at equiluminance
    "null_contrast": 0.08,    # Fig. 1B/C: 5-10%, ~9% for T.W.
    "lum_presence": 0.0040,   # Fig. 1C: isolated luminance thresholds ~0.4%
    "lum_direction": 0.0045,
    "mask_factor": 4.5,       # "rose by a factor of 4 or 5" with the colour grating
    "color_presence": 0.02,   # note 9: 40% is about 20x the colour threshold
    "lum_tracking_threshold": 0.30,  # Fig. 1B: 75% at ~2-4x the null contrast
    "speed_minimum_at": -0.05,       # Fig. 2: global match lowest near -10% (P.C.), +3% (I.M.)
}


class SimulatedObserver:
    def __init__(self, seed: int = 0, delay_s: float = 0.35) -> None:
        self._rng = np.random.default_rng(seed)
        jitter = lambda sd: float(math.exp(self._rng.normal(0.0, sd)))  # noqa: E731
        self.k_true = TRUE["k"] * jitter(0.06)
        self.null = TRUE["null_contrast"] * jitter(0.15)
        self.track_thr = TRUE["lum_tracking_threshold"] * jitter(0.1)
        self.l0 = TRUE["speed_minimum_at"] + float(self._rng.normal(0.0, 0.03))
        self._delay = delay_s
        self._answer: str | None = None
        self._cue_at: float | None = None
        self._pending_test: dict | None = None
        self._knob: dict | None = None

    def describe(self) -> dict[str, Any]:
        return {"k_true": round(self.k_true, 4), "null_contrast": round(self.null, 4),
                "lum_tracking_threshold": round(self.track_thr, 4),
                "speed_minimum_at": round(self.l0, 4)}

    # -- the models ---------------------------------------------------------------
    def p_correct(self, target: str, contrast: float) -> float:
        if target == "color":
            return 0.5 + 0.48 / (1.0 + (contrast / 0.37) ** 6)
        return 0.5 + 0.48 * (1.0 - math.exp(-((contrast / self.track_thr) ** 4)))

    def setpoint(self, info: dict) -> float:
        task = info["task"]
        if task in ("equiluminance-speed", "flicker-photometry"):
            return self.k_true
        if task == "motion-null":
            return self.null
        if task == "thresholds":
            if info["grating"] == "color":
                return TRUE["color_presence"]
            base = TRUE["lum_presence" if info["criterion"] == "presence" else "lum_direction"]
            return base * (TRUE["mask_factor"] if info["mask"] == "color" else 1.0)
        if task == "speed-match":
            off = float(info["luminance_contrast"]) - self.l0
            if info["judgment"] == "global":
                ratio = 1.5 - 1.2 * math.exp(-(off**2) / (2 * 0.06**2))
            else:
                ratio = 1.2 - 0.15 * math.exp(-(off**2) / (2 * 0.1**2))
            return float(info["outer_rate_hz"]) * ratio
        raise ValueError(f"no model for task {task!r}")

    # -- the device ---------------------------------------------------------------
    def on_event(self, event: Event) -> None:
        if event.name == "TEST_ON":
            self._pending_test = dict(event.payload)
        elif event.name == "RESPONSE_CUE" and self._pending_test is not None:
            info, self._pending_test = self._pending_test, None
            right = self._rng.random() < self.p_correct(info["target_grating"],
                                                       float(info["luminance_contrast"]))
            says_yes = info["is_tracked"] == right
            self._answer = "j" if says_yes else "f"
            self._cue_at = time.monotonic() + float(self._rng.uniform(0.0, 0.3))
        elif event.name == "ADJUST_START":
            info = dict(event.payload)
            target = self.setpoint(info) * float(math.exp(self._rng.normal(0.0, 0.08)))
            self._knob = {**info, "target": min(max(target, info["lo"]), info["hi"]),
                          "t0": time.monotonic(), "settled": None}
        elif event.name in ("RESPONSE", "TRIAL_END"):
            self._knob = None if event.name == "TRIAL_END" else self._knob

    def poll(self) -> ResponseSample:
        now = time.monotonic()
        if self._answer is not None and self._cue_at is not None and now - self._cue_at >= self._delay:
            key, self._answer, self._cue_at = self._answer, None, None
            return ResponseSample(keys=(key,))
        knob = self._knob
        if knob is None or now - knob["t0"] < self._delay:
            return ResponseSample()
        v, target, step = knob["value"], knob["target"], knob["step"]
        n = round(math.log(target / v) / math.log(step)) if knob["scale"] == "log" else round(
            (target - v) / step)
        if n == 0:
            if knob["settled"] is None:
                knob["settled"] = now
            if now - knob["settled"] >= 0.15:
                self._knob = None
                return ResponseSample(keys=("space",))
            return ResponseSample()
        notch = int(max(-3, min(3, n)))
        nv = v * step**notch if knob["scale"] == "log" else v + step * notch
        knob["value"] = min(max(nv, knob["lo"]), knob["hi"])
        return ResponseSample(wheel=float(notch))
