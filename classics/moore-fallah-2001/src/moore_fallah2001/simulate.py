"""The simulated subject for --mode simulate and the end-to-end tests.

Two stand-ins, each driven only by what the session tells it:

- ``FixatingEye`` (alhazen's EyeTracker protocol) looks at the fixation point
  with alhazen's GazeNoise (drift, microsaccades, tracker noise) and, on a
  small fraction of trials, looks away at a random moment: a fixation break,
  so the re-serve path runs in every rehearsal.
- ``SimulatedObserver`` (a ResponseDevice) presses the response key after a
  dimming with a probability that grows with its magnitude (a Weibull
  psychometric function of % Michelson contrast), at a log-normal reaction
  time, and now and then presses at a random moment (false alarms and early
  responses).

What it deliberately does not do is respond to stimulation. STIM_TRIGGER
reaches it like any other event and changes nothing: the paper's effect is a
property of frontal-eye-field neurons that no simulation here has, so the
stimulation and control staircases of a simulated session converge on the
same threshold. That is the honest result of a pipeline test, not a failed
replication.
"""

from __future__ import annotations

import math
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, ClassVar

import numpy as np
from alhazen.core.clock import Clock
from alhazen.core.events import Event
from alhazen.devices.eyetracker.protocol import GazeSample, HostShape
from alhazen.devices.response import ResponseSample
from alhazen.display.screen import Screen
from alhazen.modes.gaze_noise import GazeNoise


def p_detect(dim_pct: float, threshold_pct: float, slope: float, guess: float,
             lapse: float) -> float:
    """Weibull probability of detecting a dimming of ``dim_pct`` (% Michelson)."""
    core = 1.0 - math.exp(-((max(dim_pct, 0.0) / threshold_pct) ** slope))
    return guess + (1.0 - guess - lapse) * core


class SimulatedObserver:
    DEFAULTS: ClassVar[dict[str, float]] = {
        "threshold_pct": 30.0, "slope": 3.0, "guess": 0.0, "lapse": 0.04,
        "rt_median_s": 0.33, "rt_sigma": 0.22, "p_spontaneous_press": 0.05,
    }

    def __init__(self, seed: int = 0, key: str = "space",
                 now: Callable[[], float] = time.monotonic, **overrides: float) -> None:
        cfg = {**self.DEFAULTS, **overrides}
        unknown = set(cfg) - set(self.DEFAULTS)
        if unknown:
            raise TypeError(f"unknown observer settings: {sorted(unknown)}")
        self._cfg = cfg
        self._rng = np.random.default_rng(seed)
        self._key = key
        self._now = now
        self._press_at: float | None = None

    def on_event(self, event: Event) -> None:
        c = self._cfg
        if event.name == "TARGET_ON":
            self._press_at = None
            if self._rng.random() < c["p_spontaneous_press"]:
                self._press_at = self._now() + float(self._rng.uniform(0.15, 2.0))
        elif event.name == "DIM_ON":
            dim = float(event.payload.get("dim_pct", 0.0))
            if self._rng.random() < p_detect(dim, c["threshold_pct"], c["slope"], c["guess"],
                                             c["lapse"]):
                rt = float(c["rt_median_s"] * math.exp(c["rt_sigma"] * self._rng.standard_normal()))
                at = self._now() + rt
                self._press_at = at if self._press_at is None else min(self._press_at, at)
        elif event.name in ("RESPONSE", "TRIAL_END"):
            self._press_at = None

    def poll(self) -> ResponseSample:
        if self._press_at is None or self._now() < self._press_at:
            return ResponseSample()
        self._press_at = None
        return ResponseSample(keys=(self._key,))


class FixatingEye:
    DEFAULTS: ClassVar[dict[str, float]] = {"p_fixation_break": 0.03}

    def __init__(self, seed: int = 0, p_fixation_break: float = 0.03,
                 gaze_noise: bool = True) -> None:
        self._rng = np.random.default_rng(seed)
        (child,) = np.random.SeedSequence(seed).spawn(1)
        self._noise = GazeNoise(np.random.default_rng(child)) if gaze_noise else None
        self._p_break = p_fixation_break
        self._screen: Screen | None = None
        self._clock: Clock | None = None
        self._fixation = (0.0, 0.0)
        self._recording = False
        self._break_at: float | None = None

    def connect(self) -> None:
        return

    def configure(self, screen: Screen, clock: Clock) -> None:
        self._screen, self._clock = screen, clock
        self._fixation = (screen.width_px / 2.0, screen.height_px / 2.0)

    def calibrate(self) -> None:
        return None

    def start_trial(self, trial_index: int, status: str) -> None:
        self._recording = True
        assert self._clock is not None
        self._break_at = None
        if self._rng.random() < self._p_break:
            self._break_at = self._clock.now() + float(self._rng.uniform(0.4, 2.2))

    def stop_trial(self) -> None:
        self._recording = False

    def is_recording(self) -> bool:
        return self._recording

    def send_message(self, text: str) -> None:
        return

    def get_gaze(self) -> GazeSample | None:
        if self._clock is None or self._screen is None:
            raise RuntimeError("FixatingEye.get_gaze() before configure()")
        now = self._clock.now()
        x, y = self._fixation
        if self._break_at is not None and now >= self._break_at:
            x += 6.0 * self._screen.px_per_deg  # a look away, well outside any fixation window
        if self._noise is not None:
            dx, dy = self._noise.offset_dva(now)
            x, y = x + dx * self._screen.px_per_deg, y + dy * self._screen.px_per_deg
        return GazeSample(gx=x, gy=y, t=now)

    def draw_host_overlay(self, shapes: list[HostShape]) -> None:
        boxes = [s for s in shapes if s.kind == "box"]
        if boxes:  # the fixation window is the task's first (only) region
            b = boxes[0]
            self._fixation = ((b.x1 + b.x2) / 2.0, (b.y1 + b.y2) / 2.0)

    def shutdown(self, recording_destination: Path | None, /) -> None:
        return

    def describe(self) -> dict[str, Any]:
        return {"p_fixation_break": self._p_break, "gaze_noise": self._noise is not None}
