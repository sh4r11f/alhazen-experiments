"""The simulated subject for --mode simulate and the tests: an eye that does the ODR task.

It satisfies alhazen's ``EyeTracker`` protocol (the autopilot's gaze source). It learns
where the fixation spot and the cue are from the trial's own regions (the operator overlay
the runner hands every tracker), and when to move from the task's events: ``fix_off`` (the
go signal) releases the eye. It never sees the trial's condition.

Each trial is decided once, in ``start_trial``, from a seeded generator:

- **fixation break**: leaves fixation at a random time in the first few seconds; on a
  short-delay trial that time may fall after the go signal, and then it is a normal trial;
- **no saccade**: stays at fixation after the go signal (NO_SACCADE);
- **wrong location**: a saccade to a neighbouring or the opposite cue location
  (INACCURATE), the large errors the paper examined;
- **blink**: the tracker loses the eye briefly after the go signal;
- **normal**: after a lognormal latency (median 0.25 s), a saccade that lands at the cue
  location scaled by an amplitude gain (0.95) plus Gaussian scatter (1.0 deg).

The eye is never still: alhazen's ``GazeNoise`` adds drift, microsaccades and tracker
noise to every sample.

What it deliberately does NOT do is depend on the delay or the cue location: every cell
gets the same latency and scatter distributions. A rehearsal therefore tests that the
pipeline and the notebook work; it previews no result. Any delay or location effect in
simulated data is noise.
"""

from __future__ import annotations

import logging
import math
from pathlib import Path

import numpy as np
from alhazen.core.clock import Clock
from alhazen.devices.eyetracker.protocol import GazeSample, HostShape
from alhazen.display.screen import Screen
from alhazen.modes.gaze_noise import GazeNoise

log = logging.getLogger(__name__)


class SimulatedSubject:
    """An automated ODR subject (module docstring)."""

    def __init__(
        self,
        seed: int | None = None,
        median_latency_s: float = 0.25,
        latency_spread_s: float = 0.06,
        amplitude_gain: float = 0.95,
        landing_scatter_dva: float = 1.0,
        p_fixation_break: float = 0.05,
        p_no_saccade: float = 0.03,
        p_wrong_location: float = 0.05,
        p_blink: float = 0.03,
        gaze_noise: bool = True,
    ) -> None:
        self._rng = np.random.default_rng(seed)
        self._noise: GazeNoise | None = None
        if gaze_noise:
            # Its own generator (alhazen's GazeNoise explains why), spawned from the seed.
            (child,) = np.random.SeedSequence(seed).spawn(1)
            self._noise = GazeNoise(np.random.default_rng(child))
        self._median_latency_s = median_latency_s
        self._latency_spread_s = latency_spread_s
        self._amplitude_gain = amplitude_gain
        self._landing_scatter_dva = landing_scatter_dva
        self._p_fixation_break = p_fixation_break
        self._p_no_saccade = p_no_saccade
        self._p_wrong_location = p_wrong_location
        self._p_blink = p_blink
        self._screen: Screen | None = None
        self._clock: Clock | None = None
        self._recording = False
        self._fixation = (0.0, 0.0)  # screen px, y down
        self._target = (0.0, 0.0)
        self._plan = _Plan("still")

    # -- EyeTracker protocol -------------------------------------------------------

    def connect(self) -> None:
        return

    def configure(self, screen: Screen, clock: Clock) -> None:
        self._screen = screen
        self._clock = clock

    def calibrate(self) -> None:
        log.info("simulated subject: nothing to calibrate")

    def start_trial(self, trial_index: int, status: str) -> None:
        self._recording = True
        self._plan = self._draw()
        self._plan.started_s = self._now()

    def stop_trial(self) -> None:
        self._recording = False

    def is_recording(self) -> bool:
        return self._recording

    def send_message(self, text: str) -> None:
        if text == "fix_off":
            self._plan.released_s = self._now()

    def get_gaze(self) -> GazeSample | None:
        if self._clock is None:
            raise RuntimeError("SimulatedSubject.get_gaze() before configure()")
        now = self._now()
        aim = self._aim(now)
        if aim is None:
            return None
        if self._noise is not None:
            assert self._screen is not None
            dx, dy = self._noise.offset_dva(now)
            aim = (aim[0] + dx * self._screen.px_per_deg, aim[1] - dy * self._screen.px_per_deg)
        return GazeSample(gx=aim[0], gy=aim[1], t=now)

    def draw_host_overlay(self, shapes: list[HostShape]) -> None:
        boxes = [s for s in shapes if s.kind == "box"]
        if boxes:
            self._fixation = _centre(boxes[0])
            self._target = _centre(boxes[-1])

    def shutdown(self, recording_destination: Path | None, /) -> None:
        return

    def describe(self) -> dict:
        return {
            "median_latency_s": self._median_latency_s,
            "latency_spread_s": self._latency_spread_s,
            "amplitude_gain": self._amplitude_gain,
            "landing_scatter_dva": self._landing_scatter_dva,
            "p_fixation_break": self._p_fixation_break,
            "p_no_saccade": self._p_no_saccade,
            "p_wrong_location": self._p_wrong_location,
            "p_blink": self._p_blink,
            "depends_on_delay_or_location": False,
            "gaze_noise": self._noise.describe() if self._noise is not None else "none",
        }

    # -- behaviour ---------------------------------------------------------------

    def _now(self) -> float:
        assert self._clock is not None
        return self._clock.now()

    def _draw(self) -> _Plan:
        roll = self._rng.random()
        edges = np.cumsum([self._p_fixation_break, self._p_no_saccade, self._p_wrong_location])
        if roll < edges[0]:
            return _Plan("fixation_break", break_after_s=float(self._rng.uniform(0.3, 4.0)))
        latency = float(self._rng.lognormal(np.log(self._median_latency_s),
                                            self._latency_spread_s / self._median_latency_s))
        blink_at = float(self._rng.uniform(0.0, 0.2)) if self._rng.random() < self._p_blink else None
        if roll < edges[1]:
            return _Plan("no_saccade")
        rotation = 0.0
        if roll < edges[2]:
            rotation = float(self._rng.choice([-90.0, -45.0, 45.0, 90.0, 180.0]))
        scatter = self._rng.normal(0.0, self._landing_scatter_dva, size=2)
        return _Plan("saccade", latency_s=latency, rotation_deg=rotation,
                     scatter_dva=(float(scatter[0]), float(scatter[1])), blink_at_s=blink_at,
                     blink_for_s=float(self._rng.uniform(0.04, 0.10)))

    def _aim(self, now: float) -> tuple[float, float] | None:
        plan = self._plan
        if plan.kind == "fixation_break" and plan.released_s is None:
            if now - plan.started_s >= plan.break_after_s:
                return (self._fixation[0] + 300.0, self._fixation[1] + 200.0)
            return self._fixation
        if plan.released_s is None:
            return self._fixation
        since = now - plan.released_s
        if plan.blink_at_s is not None and plan.blink_at_s <= since < plan.blink_at_s + plan.blink_for_s:
            return None
        if plan.kind in ("no_saccade", "still") or since < plan.latency_s:
            return self._fixation
        return self._landing()

    def _landing(self) -> tuple[float, float]:
        """The cue vector from fixation, rotated (a wrong-location trial), scaled by the
        gain, plus scatter; in screen px (y down, so degrees' y is subtracted)."""
        assert self._screen is not None
        plan = self._plan
        vx, vy = self._target[0] - self._fixation[0], self._target[1] - self._fixation[1]
        a = math.radians(plan.rotation_deg)
        # Rotating in screen coordinates (y down) by -a is a counter-clockwise turn on screen.
        rx = vx * math.cos(a) + vy * math.sin(a)
        ry = -vx * math.sin(a) + vy * math.cos(a)
        ppd = self._screen.px_per_deg
        return (self._fixation[0] + self._amplitude_gain * rx + plan.scatter_dva[0] * ppd,
                self._fixation[1] + self._amplitude_gain * ry - plan.scatter_dva[1] * ppd)


class _Plan:
    __slots__ = ("kind", "latency_s", "rotation_deg", "scatter_dva", "break_after_s",
                 "blink_at_s", "blink_for_s", "started_s", "released_s")

    def __init__(self, kind: str, latency_s: float = 0.0, rotation_deg: float = 0.0,
                 scatter_dva: tuple[float, float] = (0.0, 0.0), break_after_s: float = 0.0,
                 blink_at_s: float | None = None, blink_for_s: float = 0.0) -> None:
        self.kind = kind
        self.latency_s = latency_s
        self.rotation_deg = rotation_deg
        self.scatter_dva = scatter_dva
        self.break_after_s = break_after_s
        self.blink_at_s = blink_at_s
        self.blink_for_s = blink_for_s
        self.started_s = 0.0
        self.released_s: float | None = None


def _centre(box: HostShape) -> tuple[float, float]:
    return ((box.x1 + box.x2) / 2.0, (box.y1 + box.y2) / 2.0)
