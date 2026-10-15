"""Simulated subjects for --mode simulate and the tests.

Both answer from a psychometric function of the paper's form (Eq. 1, p.
4749), p(correct) = 1 - 0.5 exp(-(c/alpha)^beta), with a small lapse rate, so
a rehearsal produces data the analysis notebook can fit, and the fit can be
checked against the planted threshold. Their thresholds are made up for
rehearsal; they are not the paper's results and not anyone's data.

- ``SimulatedObserver`` presses a key after the response cue (human set).
- ``SimulatedMonkey`` is an eye tracker: it looks at the fixation point,
  sometimes breaks fixation, and saccades to the target of the direction it
  chose (monkey set). It learns each trial's condition from the task
  (``RdkDirectionTask.trial_observer``), and event times from tracker
  messages, the same stream a real EDF gets.
"""

from __future__ import annotations

import math
import time
from pathlib import Path
from typing import Any

import numpy as np
from alhazen.core.clock import Clock
from alhazen.core.events import Event
from alhazen.devices.eyetracker.protocol import GazeSample, HostShape
from alhazen.devices.response import ResponseSample
from alhazen.display.screen import Screen
from alhazen.modes.gaze_noise import GazeNoise


def p_correct(coherence_pct: float, alpha_pct: float, beta: float, lapse: float = 0.0) -> float:
    """The paper's Eq. 1 with a lapse rate: chance (0.5) at 0 %."""
    if coherence_pct <= 0:
        return 0.5
    p = 1.0 - 0.5 * math.exp(-((coherence_pct / alpha_pct) ** beta))
    return (1.0 - lapse) * p + lapse * 0.5


class SimulatedObserver:
    """A keyboard subject: reads each trial's condition from TRIAL_START and
    answers after the response cue with a lognormal reaction time."""

    def __init__(
        self,
        keys: tuple[str, str] = ("right", "left"),
        seed: int = 0,
        alpha_pct: float = 8.0,
        beta: float = 1.3,
        lapse: float = 0.02,
        p_no_response: float = 0.01,
        median_rt_s: float = 0.45,
    ) -> None:
        self._keys = {"pref": keys[0], "anti": keys[1]}
        self._rng = np.random.default_rng(seed)
        self._alpha, self._beta, self._lapse = alpha_pct, beta, lapse
        self._p_none = p_no_response
        self._median_rt = median_rt_s
        self._trial: dict[str, Any] = {}
        self._due: float | None = None
        self._key: str | None = None

    def describe(self) -> dict[str, Any]:
        return {"source": "britten1992.simulate.SimulatedObserver", "alpha_pct": self._alpha,
                "beta": self._beta, "lapse": self._lapse, "p_no_response": self._p_none}

    def choose(self, direction: str, coherence_pct: float) -> str:
        right = self._rng.random() < p_correct(coherence_pct, self._alpha, self._beta, self._lapse)
        if coherence_pct <= 0:
            right = self._rng.random() < 0.5
        other = "anti" if direction == "pref" else "pref"
        return direction if right else other

    def on_event(self, event: Event) -> None:
        if event.name == "TRIAL_START":
            self._trial = dict(event.payload)
            self._due = None
        elif event.name == "RESPONSE_CUE" and self._trial:
            if self._rng.random() < self._p_none:
                return
            choice = self.choose(self._trial["direction"], float(self._trial["coherence_pct"]))
            self._key = self._keys[choice]
            rt = float(self._rng.lognormal(math.log(self._median_rt), 0.25))
            self._due = time.monotonic() + rt

    def poll(self) -> ResponseSample:
        if self._due is None or time.monotonic() < self._due:
            return ResponseSample()
        self._due = None
        return ResponseSample(keys=(str(self._key),))


class SimulatedMonkey:
    """An ``EyeTracker`` that fixates, views the dots and reports by saccade.

    Per trial, drawn once at its start: about 2 % never acquire fixation, 5 %
    break it during the hold or the dots, 1 % make no saccade, 1 % saccade
    somewhere that is neither target; the rest choose by the psychometric
    function and saccade to that target with a lognormal latency.
    """

    def __init__(
        self,
        seed: int = 0,
        alpha_pct: float = 10.0,
        beta: float = 1.2,
        lapse: float = 0.02,
        p_no_fixation: float = 0.02,
        p_fixation_break: float = 0.05,
        p_no_saccade: float = 0.01,
        p_stray: float = 0.01,
        median_latency_s: float = 0.22,
        saccade_duration_s: float = 0.04,
        gaze_noise: bool = True,
    ) -> None:
        self._rng = np.random.default_rng(seed)
        (child,) = np.random.SeedSequence(seed).spawn(1)
        self._noise = GazeNoise(np.random.default_rng(child)) if gaze_noise else None
        self._alpha, self._beta, self._lapse = alpha_pct, beta, lapse
        self._p = {"no_fixation": p_no_fixation, "fixation_break": p_fixation_break,
                   "no_saccade": p_no_saccade, "stray": p_stray}
        self._median_latency = median_latency_s
        self._saccade_s = saccade_duration_s
        self._screen: Screen | None = None
        self._clock: Clock | None = None
        self._recording = False
        self._trial: dict[str, Any] | None = None
        self._script: dict[str, Any] = {"kind": "no_fixation"}
        self.messages: list[str] = []

    # what the task tells it ------------------------------------------------
    def note_trial(self, direction: str, coherence_pct: float,
                   targets_dva: dict[str, tuple[float, float]]) -> None:
        self._trial = {"direction": direction, "coherence_pct": float(coherence_pct),
                       "targets_dva": dict(targets_dva)}

    def describe(self) -> dict[str, Any]:
        return {"source": "britten1992.simulate.SimulatedMonkey", "alpha_pct": self._alpha,
                "beta": self._beta, "lapse": self._lapse,
                **{f"p_{k}": v for k, v in self._p.items()},
                "median_latency_s": self._median_latency}

    # the EyeTracker protocol -------------------------------------------------
    def connect(self) -> None:
        return

    def configure(self, screen: Screen, clock: Clock) -> None:
        self._screen, self._clock = screen, clock

    def calibrate(self) -> None:
        return None

    def start_trial(self, trial_index: int, status: str) -> None:
        self._recording = True
        self._script = self._draw_script()

    def stop_trial(self) -> None:
        self._recording = False

    def is_recording(self) -> bool:
        return self._recording

    def send_message(self, text: str) -> None:
        self.messages.append(text)
        now = self._now()
        if text == "fix_on":
            self._script.setdefault("fix_on", now)
        elif text == "stim_on":
            self._script.setdefault("stim_on", now)
        elif text == "targets_on" and "targets_on" not in self._script:
            self._script["targets_on"] = now
            self._decide()

    def draw_host_overlay(self, shapes: list[HostShape]) -> None:
        return

    def get_gaze(self) -> GazeSample | None:
        if self._clock is None or self._screen is None:
            raise RuntimeError("SimulatedMonkey.get_gaze() before configure()")
        now = self._now()
        x, y = self._position_dva(now)
        if self._noise is not None:
            dx, dy = self._noise.offset_dva(now)
            x, y = x + dx, y + dy
        cx, cy = self._screen.deg2px(x), self._screen.deg2px(y)
        gx, gy = self._screen.centered_to_screen(cx, cy)
        return GazeSample(gx=gx, gy=gy, t=now)

    def shutdown(self, recording_destination: Path | None, /) -> None:
        return

    # behaviour -----------------------------------------------------------------
    def _now(self) -> float:
        assert self._clock is not None
        return self._clock.now()

    def _draw_script(self) -> dict[str, Any]:
        roll = float(self._rng.random())
        edges = np.cumsum([self._p["no_fixation"], self._p["fixation_break"],
                           self._p["no_saccade"], self._p["stray"]])
        kind = ["no_fixation", "fixation_break", "no_saccade", "stray"][
            int(np.searchsorted(edges, roll, side="right"))] if roll < edges[-1] else "choice"
        script: dict[str, Any] = {
            "kind": kind,
            "acquire_s": float(self._rng.lognormal(math.log(0.25), 0.3)),
            "break_s": float(self._rng.uniform(0.1, 2.0)),
            "latency_s": float(self._rng.lognormal(math.log(self._median_latency), 0.2)),
            "scatter": (float(self._rng.normal(0, 0.4)), float(self._rng.normal(0, 0.4))),
        }
        return script

    def _decide(self) -> None:
        """The choice and the landing point, decided when the targets appear,
        from the condition the task noted for this trial."""
        s = self._script
        trial = self._trial or {"direction": "pref", "coherence_pct": 0.0,
                                "targets_dva": {"pref": (10.0, 0.0), "anti": (-10.0, 0.0)}}
        c, d = trial["coherence_pct"], trial["direction"]
        right = self._rng.random() < p_correct(c, self._alpha, self._beta, self._lapse)
        if c <= 0:
            right = self._rng.random() < 0.5
        chosen = d if right else ("anti" if d == "pref" else "pref")
        tx, ty = trial["targets_dva"][chosen]
        if s["kind"] == "stray":
            angle = math.atan2(ty, tx) + math.pi / 2
            r = math.hypot(tx, ty)
            tx, ty = r * math.cos(angle), r * math.sin(angle)
        s["landing"] = (tx + s["scatter"][0], ty + s["scatter"][1])
        s["chosen"] = chosen

    def _position_dva(self, now: float) -> tuple[float, float]:
        s = self._script
        away = (6.0, 5.0)
        fix_on = s.get("fix_on")
        if s["kind"] == "no_fixation" or fix_on is None or now - fix_on < s["acquire_s"]:
            return away
        if s["kind"] == "fixation_break" and now - fix_on - s["acquire_s"] >= s["break_s"]:
            return (4.0, -4.0)
        targets_on = s.get("targets_on")
        if targets_on is None or s["kind"] == "no_saccade":
            return (0.0, 0.0)
        flight = now - targets_on - s["latency_s"]
        if flight <= 0:
            return (0.0, 0.0)
        lx, ly = s["landing"]
        if flight >= self._saccade_s:
            return (lx, ly)
        t = flight / self._saccade_s
        k = 10 * t**3 - 15 * t**4 + 6 * t**5  # minimum jerk
        return (k * lx, k * ly)
