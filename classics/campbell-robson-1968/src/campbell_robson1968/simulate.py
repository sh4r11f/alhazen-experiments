"""Simulated observers for ``--mode simulate`` and the tests.

A TOY, not data. Its contrast sensitivity follows a log-parabola in log frequency
(peak 200 at 4 c/deg, 3 octaves full width at half height; the form of Lesmes et al.,
2010, with made-up numbers chosen only to give thresholds in a realistic range). It
detects a grating from the contrast of its FUNDAMENTAL alone, so for a square wave it is
4/pi more sensitive than for a sine wave at every frequency BY CONSTRUCTION: a simulated
session can check that the analysis recovers a planted ratio, never the paper's claim.

- ``SimulatedObserver`` (csf-2ifc): learns the trial from the FIX_ON payload, answers
  after the response cue from a Weibull psychometric function (2AFC, guess 0.5,
  lapse 0.01, slope 3.5) with a lognormal reaction time.
- ``SimulatedAdjuster`` (csf-adjustment): from ADJUST_START, turns the knob down or up
  one arrow press at a time toward its threshold times a lognormal setting error
  (SD 0.08 log10 units), then presses SPACE.
"""

from __future__ import annotations

import math
import time
from typing import Any

import numpy as np
from alhazen.core.events import Event
from alhazen.devices.response import ResponseSample

PEAK_SENSITIVITY = 200.0
PEAK_SF = 4.0
BANDWIDTH_OCT = 3.0
SLOPE = 3.5
LAPSE = 0.01


def toy_sensitivity(sf_cpd: float) -> float:
    beta = math.log10(2.0**BANDWIDTH_OCT)
    z = (math.log10(sf_cpd) - math.log10(PEAK_SF)) / (beta / 2.0)
    return 10.0 ** (math.log10(PEAK_SENSITIVITY) - math.log10(2.0) * z * z)


def p_correct_2afc(
    contrast: float, threshold: float, slope: float = SLOPE, lapse: float = LAPSE
) -> float:
    """Weibull in log10 units, the form alhazen's QUEST+ uses (log10 scale)."""
    if contrast <= 0:
        return 0.5
    x = math.log10(contrast) - math.log10(threshold)
    return 0.5 + (0.5 - lapse) * (1.0 - math.exp(-(10.0 ** (slope * x))))


class SimulatedObserver:
    def __init__(
        self,
        seed: int = 0,
        keys: tuple[str, str] = ("f", "j"),
        p_no_response: float = 0.01,
        median_rt_s: float = 0.4,
    ) -> None:
        self._rng = np.random.default_rng(seed)
        self._keys = keys
        self._p_none = p_no_response
        self._median_rt = median_rt_s
        self._trial: dict[str, Any] = {}
        self._due: float | None = None
        self._key: str | None = None

    def describe(self) -> dict[str, Any]:
        return {
            "source": "campbell_robson1968.simulate.SimulatedObserver",
            "toy": True,
            "peak_sensitivity": PEAK_SENSITIVITY,
            "peak_sf_cpd": PEAK_SF,
            "bandwidth_octaves": BANDWIDTH_OCT,
            "slope": SLOPE,
            "lapse": LAPSE,
            "detects": "fundamental only",
        }

    def choose(self, info: dict[str, Any]) -> str:
        threshold = 1.0 / toy_sensitivity(float(info["sf_cpd"]))
        effective = float(info["fundamental_contrast"])
        right = self._rng.random() < p_correct_2afc(effective, threshold)
        signal = int(info["signal_interval"])
        return self._keys[signal - 1] if right else self._keys[2 - signal]

    def on_event(self, event: Event) -> None:
        if event.name == "FIX_ON":
            self._trial = dict(event.payload)
            self._due = None
        elif event.name == "RESPONSE_CUE" and self._trial:
            if self._rng.random() < self._p_none:
                return
            self._key = self.choose(self._trial)
            self._due = time.monotonic() + float(
                self._rng.lognormal(math.log(self._median_rt), 0.25)
            )

    def poll(self) -> ResponseSample:
        if self._due is None or time.monotonic() < self._due:
            return ResponseSample()
        self._due = None
        return ResponseSample(keys=(str(self._key),))


class SimulatedAdjuster:
    def __init__(
        self, seed: int = 0, setting_sd_log10: float = 0.08, press_every_s: float = 0.03
    ) -> None:
        self._rng = np.random.default_rng(seed)
        self._sd = setting_sd_log10
        self._every = press_every_s
        self._queue: list[str] = []
        self._next = 0.0

    def describe(self) -> dict[str, Any]:
        return {
            "source": "campbell_robson1968.simulate.SimulatedAdjuster",
            "toy": True,
            "peak_sensitivity": PEAK_SENSITIVITY,
            "peak_sf_cpd": PEAK_SF,
            "bandwidth_octaves": BANDWIDTH_OCT,
            "setting_sd_log10": self._sd,
        }

    def plan(self, payload: dict[str, Any]) -> list[str]:
        threshold = 1.0 / toy_sensitivity(float(payload["sf_cpd"]))
        if payload.get("waveform") == "square":
            threshold /= 4.0 / math.pi
        target = threshold * 10.0 ** float(self._rng.normal(0.0, self._sd))
        target = min(max(target, float(payload["lo"])), float(payload["hi"]))
        n = int(
            round(math.log(target / float(payload["value"])) / math.log(float(payload["step"])))
        )
        return ["up" if n > 0 else "down"] * abs(n) + ["space"]

    def on_event(self, event: Event) -> None:
        if event.name == "ADJUST_START":
            self._queue = self.plan(dict(event.payload))
            self._next = time.monotonic() + 0.2

    def poll(self) -> ResponseSample:
        if not self._queue or time.monotonic() < self._next:
            return ResponseSample()
        self._next = time.monotonic() + self._every
        return ResponseSample(keys=(self._queue.pop(0),))
