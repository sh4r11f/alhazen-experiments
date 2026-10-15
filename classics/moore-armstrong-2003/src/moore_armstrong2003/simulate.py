"""The simulated monkey for --mode simulate and the tests: a fixating eye, nothing more.

It satisfies alhazen's ``EyeTracker`` protocol and stands in for the tracker. Every
trial it either looks at the fixation point (with alhazen's ``GazeNoise``: drift,
microsaccades, tracker noise) and keeps looking, or does one of the things a real
fixating monkey does, so every outcome branch is exercised in a rehearsal:

- never looks (NO_FIXATION);
- breaks fixation at a random moment (BROKE_FIX_BASELINE / BROKE_FIX_STIMULUS);
- blinks (a ``None`` sample, which the blink rule counts as a break);
- on a STIM_TRIGGER only, makes a saccade away (``p_evoked_saccade``): the failure a
  current too close to the movement threshold would produce, BROKE_FIX_AFTER_TRIGGER.

It knows nothing about V4 and produces no spikes. What it deliberately does NOT do is
produce the paper's result, or any neural signal at all: this folder records no neural
data, and a simulated neuron that showed the predicted enhancement would only show that
it had been written to.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from alhazen.core.clock import Clock
from alhazen.devices.eyetracker.protocol import GazeSample, HostShape
from alhazen.display.screen import Screen
from alhazen.modes.gaze_noise import GazeNoise

log = logging.getLogger(__name__)


@dataclass
class _Plan:
    """One trial's behaviour, drawn once in start_trial."""

    acquire_after_s: float | None  # None: never looks
    break_after_s: float | None  # from fixation acquired; None: holds to the end
    blink_after_s: float | None
    evoked_saccade: bool
    started_s: float = 0.0
    stim_at_s: float | None = None


class SimulatedMonkey:
    def __init__(
        self,
        seed: int | None = None,
        *,
        acquire_latency_s: float = 0.25,
        p_no_fixation: float = 0.03,
        p_break: float = 0.05,
        p_blink: float = 0.02,
        p_evoked_saccade: float = 0.05,
        gaze_noise: bool = True,
    ) -> None:
        self._rng = np.random.default_rng(seed)
        (child,) = np.random.SeedSequence(seed).spawn(1)
        self._noise = GazeNoise(np.random.default_rng(child)) if gaze_noise else None
        self._settings = {
            "acquire_latency_s": acquire_latency_s,
            "p_no_fixation": p_no_fixation,
            "p_break": p_break,
            "p_blink": p_blink,
            "p_evoked_saccade": p_evoked_saccade,
            "gaze_noise": gaze_noise,
        }
        self._screen: Screen | None = None
        self._clock: Clock | None = None
        self._recording = False
        self._plan = _Plan(None, None, None, False)

    # -- EyeTracker protocol ------------------------------------------------------

    def connect(self) -> None:
        return

    def configure(self, screen: Screen, clock: Clock) -> None:
        self._screen = screen
        self._clock = clock

    def calibrate(self) -> None:
        log.info("simulated monkey: nothing to calibrate")
        return None

    def start_trial(self, trial_index: int, status: str) -> None:
        s, r = self._settings, self._rng
        looks = r.random() >= s["p_no_fixation"]
        self._plan = _Plan(
            acquire_after_s=float(r.gamma(4.0, s["acquire_latency_s"] / 4.0)) if looks else None,
            # Somewhere in the first ~3 s of holding: baseline or stimulus period.
            break_after_s=float(r.uniform(0.05, 3.0)) if r.random() < s["p_break"] else None,
            blink_after_s=float(r.uniform(0.05, 3.0)) if r.random() < s["p_blink"] else None,
            evoked_saccade=bool(r.random() < s["p_evoked_saccade"]),
            started_s=self._now(),
        )
        self._recording = True

    def stop_trial(self) -> None:
        self._recording = False

    def is_recording(self) -> bool:
        return self._recording

    def send_message(self, text: str) -> None:
        # The task's events arrive lowercased. Only the trigger matters: a monkey
        # cannot see a control mark, and a subthreshold train evokes no saccade except
        # on the trials this subject is set to fail.
        if text == "stim_trigger":
            self._plan.stim_at_s = self._now()

    def get_gaze(self) -> GazeSample | None:
        if self._clock is None or self._screen is None:
            raise RuntimeError("SimulatedMonkey.get_gaze() before configure()")
        now = self._now()
        centre = (self._screen.width_px / 2.0, self._screen.height_px / 2.0)
        away = (centre[0] + self._screen.deg2px(8.0), centre[1])
        plan, t = self._plan, now - self._plan.started_s
        if plan.acquire_after_s is None or t < plan.acquire_after_s:
            return GazeSample(gx=away[0], gy=away[1], t=now)
        held = t - plan.acquire_after_s
        blink = plan.blink_after_s
        if blink is not None and blink <= held < blink + 0.12:
            return None
        if plan.break_after_s is not None and held >= plan.break_after_s:
            return GazeSample(gx=away[0], gy=away[1], t=now)
        if plan.evoked_saccade and plan.stim_at_s is not None and now - plan.stim_at_s > 0.06:
            return GazeSample(gx=away[0], gy=centre[1] + self._screen.deg2px(6.0), t=now)
        x, y = centre
        if self._noise is not None:
            dx, dy = self._noise.offset_dva(now)
            x, y = x + dx * self._screen.px_per_deg, y + dy * self._screen.px_per_deg
        return GazeSample(gx=x, gy=y, t=now)

    def draw_host_overlay(self, shapes: list[HostShape]) -> None:
        return  # the fixation point is always at the centre of the screen

    def shutdown(self, recording_destination: Path | None, /) -> None:
        return

    def describe(self) -> dict:
        return dict(self._settings)

    def _now(self) -> float:
        assert self._clock is not None
        return self._clock.now()
