"""The simulated subject for --mode simulate and the tests.

Two stand-ins, both seeded so a simulated session replays exactly:

- ``SimulatedObserver``, the hands: presses the response key a simple-RT latency
  after the target appears (an ex-Gaussian, about 290 ms on average), now and then
  misses a target, false-alarms on a catch trial, or presses during the cue period
  (an anticipation). It counts display frames, at the rate the session measured.
- ``SimulatedEye``, the eyes (eye-tracker parameter set only): looks at fixation
  with a little noise, and on a few trials breaks fixation or blinks, so the abort-
  and-serve-again path runs in every rehearsal.

**The observer is blind to the cue on purpose.** Its RT does not depend on whether
a trial is valid, neutral or invalid, so a simulated session shows no cueing effect,
and nothing produced by this folder can be mistaken for Posner's result. The analysis
is checked against tables with a planted effect instead (tests/test_analysis.py).
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np
from alhazen.core.clock import Clock
from alhazen.core.events import Event
from alhazen.devices.eyetracker.protocol import GazeSample, HostShape
from alhazen.devices.response import ResponseSample
from alhazen.display.screen import Screen

from posner1980.task import PosnerCueingTask, PosnerCueingTaskParams


class SimulatedObserver:
    """A ResponseDevice that answers from the task's events (``on_event``)."""

    def __init__(self, seed: int = 0, key: str = "space", rt_mu_s: float = 0.240,
                 rt_sigma_s: float = 0.030, rt_tau_s: float = 0.050,
                 p_miss: float = 0.01, p_false_alarm: float = 0.05,
                 p_anticipation: float = 0.02, refresh_rate_hz: float = 60.0) -> None:
        self._rng = np.random.default_rng(seed)
        self._key = key
        self._mu, self._sigma, self._tau = rt_mu_s, rt_sigma_s, rt_tau_s
        self._p_miss, self._p_fa, self._p_antic = p_miss, p_false_alarm, p_anticipation
        self._hz = refresh_rate_hz
        self._frames_left: int | None = None

    def set_refresh_rate(self, hz: float) -> None:
        """The measured rate, handed over by ``SimulatedPosnerTask`` every trial."""
        self._hz = float(hz)

    def _rt_s(self) -> float:
        return float(self._rng.normal(self._mu, self._sigma) + self._rng.exponential(self._tau))

    def _press_after(self, seconds: float) -> None:
        self._frames_left = max(1, math.ceil(seconds * self._hz))

    def on_event(self, event: Event) -> None:
        name = event.name
        if name in ("TRIAL_START", "TRIAL_END", "FIX_ON"):
            self._frames_left = None
        elif name == "CUE_ON":
            self._frames_left = None
            if self._rng.random() < self._p_antic:
                self._press_after(float(self._rng.uniform(0.15, 0.80)))
        elif name == "TARGET_ON":
            if self._rng.random() >= self._p_miss:
                self._press_after(self._rt_s())
        elif name == "CATCH_ON" and self._rng.random() < self._p_fa:
            self._press_after(self._rt_s())

    def poll(self) -> ResponseSample:
        if self._frames_left is None:
            return ResponseSample()
        self._frames_left -= 1
        if self._frames_left > 0:
            return ResponseSample()
        self._frames_left = None
        return ResponseSample(keys=(self._key,))

    def describe(self) -> dict[str, Any]:
        return {"rt_exgauss_s": [self._mu, self._sigma, self._tau], "p_miss": self._p_miss,
                "p_false_alarm": self._p_fa, "p_anticipation": self._p_antic,
                "cue_effect": "none (the observer ignores the cue)"}


class SimulatedEye:
    """An EyeTracker that fixates, with noise, and sometimes breaks or blinks."""

    def __init__(self, seed: int = 0, noise_dva: float = 0.1, p_break: float = 0.04,
                 p_blink: float = 0.02, break_amplitude_dva: float = 7.0,
                 blink_s: float = 0.15) -> None:
        self._rng = np.random.default_rng(seed + 7919)
        self._noise = noise_dva
        self._p_break, self._p_blink = p_break, p_blink
        self._break_amp = break_amplitude_dva
        self._blink_s = blink_s
        self._screen: Screen | None = None
        self._clock: Clock | None = None
        self._center = (0.0, 0.0)
        self._recording = False
        self._t0 = 0.0
        self._break_at: float | None = None
        self._break_dx = 0.0
        self._blink_at: float | None = None

    # EyeTracker protocol -------------------------------------------------
    def connect(self) -> None:
        return

    def configure(self, screen: Screen, clock: Clock) -> None:
        self._screen, self._clock = screen, clock
        self._center = screen.centered_to_screen(0.0, 0.0)

    def calibrate(self) -> None:
        return None

    def start_trial(self, trial_index: int, status: str) -> None:
        assert self._clock is not None, "configure() first"
        self._recording = True
        self._t0 = self._clock.now()
        rng = self._rng
        self._break_at = float(rng.uniform(0.3, 3.0)) if rng.random() < self._p_break else None
        self._break_dx = self._break_amp * (1 if rng.random() < 0.5 else -1)
        self._blink_at = float(rng.uniform(0.3, 3.0)) if rng.random() < self._p_blink else None

    def stop_trial(self) -> None:
        self._recording = False

    def is_recording(self) -> bool:
        return self._recording

    def send_message(self, text: str) -> None:
        return

    def draw_host_overlay(self, shapes: list[HostShape]) -> None:
        boxes = [s for s in shapes if s.kind == "box"]
        if boxes:
            b = boxes[0]
            self._center = ((b.x1 + b.x2) / 2.0, (b.y1 + b.y2) / 2.0)

    def get_gaze(self) -> GazeSample | None:
        assert self._clock is not None and self._screen is not None, "configure() first"
        now = self._clock.now()
        t = now - self._t0
        if self._blink_at is not None and self._blink_at <= t < self._blink_at + self._blink_s:
            return None
        ppd = self._screen.px_per_deg
        dx = self._break_dx if self._break_at is not None and t >= self._break_at else 0.0
        nx, ny = self._rng.normal(0.0, self._noise, 2)
        return GazeSample(gx=self._center[0] + (dx + nx) * ppd,
                          gy=self._center[1] + ny * ppd, t=now)

    def shutdown(self, recording_destination: Path | None, /) -> None:
        return

    def describe(self) -> dict[str, Any]:
        return {"noise_dva": self._noise, "p_break": self._p_break, "p_blink": self._p_blink}


class SimulatedPosnerTask(PosnerCueingTask):
    """The task as a simulated session runs it: identical trials, and the observer
    is told the measured refresh rate so its latencies are in real seconds."""

    def __init__(self, params: PosnerCueingTaskParams, observer: SimulatedObserver) -> None:
        super().__init__(params)
        self._observer = observer

    def build_trial(self, setup):
        self._observer.set_refresh_rate(setup.refresh_rate_hz)
        return super().build_trial(setup)
