"""The simulated observer for --mode simulate, the tests and the analysis check.

It is a development tool, never a subject: the numbers it produces show that the software
and the analysis do what docs/methods.md says, and nothing about people.

Both tasks are gaze-contingent from the first frame, so the observer is an eye tracker (and,
for the perceptual task, a pair of hands) that follows the trial the task built: the tasks
are subclassed to publish each plan, as alhazen's own experiments do, and the observer
reads the Gabor's clock from it.

- **Perceptual task.** The observer sees the path rotated toward vertical by
  ``illusion_deg`` (with internal motion), adds Gaussian noise, and presses the right arrow
  when the seen path leans right of vertical, after viewing for 1-3.5 s.
- **Saccade task.** A latency after the fixation dot goes off, the eye jumps to the Gabor's
  position at saccade onset (``target="physical"``, what the paper found) or to where the
  perceived path would put it (``target="perceived"``, the paper's hypothesis 2), with an
  undershoot, a constant shift of ``drift_shift_dva`` in the direction of the internal drift
  at onset (the paper's small local effect) and more scatter along the saccade than across.

Each trial also draws a behaviour, so every outcome branch turns up in a rehearsal: a
fixation never acquired, a look away before the dot goes off, a blink, no saccade, no key.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
from alhazen.devices.eyetracker.protocol import GazeSample, HostShape
from alhazen.devices.response import ResponseSample
from alhazen.errors import ConfigError
from alhazen.modes.gaze_noise import GazeNoise
from alhazen.task.plan import TrialPlan, TrialSetup

from lisi_cavanagh2015.geometry import path_vectors, side_sign
from lisi_cavanagh2015.perception import DoubleDriftPerceptionTask
from lisi_cavanagh2015.saccade import DoubleDriftSaccadesTask


@dataclass(frozen=True)
class ObserverModel:
    """What the simulated observer does. The defaults are chosen to look like the paper's
    group results (perceived-vertical tilt about 50 deg, latency about 240 ms, a 0.3 dva
    local shift), so the notebook has something realistic to compute; they are not data."""

    illusion_deg: float = 48.0
    perceptual_noise_deg: float = 8.0
    view_s: tuple[float, float] = (1.0, 3.5)
    latency_mean_s: float = 0.24
    latency_sd_s: float = 0.05
    saccade_gain: float = 0.93
    radial_sd_dva: float = 0.45
    tangential_sd_dva: float = 0.25
    drift_shift_dva: float = 0.33
    target: str = "physical"  # or "perceived"
    p_no_fixation: float = 0.02
    p_fix_break: float = 0.04
    p_no_saccade: float = 0.02
    p_no_response: float = 0.01
    p_blink: float = 0.03
    gaze_noise: bool = True

    def __post_init__(self) -> None:
        if self.target not in ("physical", "perceived"):
            raise ValueError("target is 'physical' or 'perceived'")


class _PublishesPlan:
    """A real task that keeps the trial it built last, for the observer to read."""

    def __init__(self, params: Any) -> None:
        super().__init__(params)  # type: ignore[call-arg]
        self.current_plan: TrialPlan | None = None

    def build_trial(self, setup: TrialSetup) -> TrialPlan:
        plan = super().build_trial(setup)  # type: ignore[misc]
        self.current_plan = plan
        return plan


class AutopilotPerceptionTask(_PublishesPlan, DoubleDriftPerceptionTask):
    """The perceptual task, publishing each trial to the observer."""


class AutopilotSaccadeTask(_PublishesPlan, DoubleDriftSaccadesTask):
    """The saccade task, publishing each trial to the observer."""


def autopilot_for(task_class: type, params: Any, seed: int,
                  model: ObserverModel | None = None) -> tuple[Any, Any, Any]:
    """(task, tracker, response) for a simulated session of ``task_class``."""
    model = model or ObserverModel()
    if issubclass(task_class, DoubleDriftPerceptionTask):
        task: Any = AutopilotPerceptionTask(params)
        tracker = SimulatedEye(task, seed=seed, model=model, saccades=False)
        return task, tracker, SimulatedHands(task, seed=seed + 1, model=model)
    if issubclass(task_class, DoubleDriftSaccadesTask):
        task = AutopilotSaccadeTask(params)
        return task, SimulatedEye(task, seed=seed, model=model, saccades=True), None
    raise ConfigError(f"no simulated observer for {task_class.__name__}")


class SimulatedEye:
    """An alhazen EyeTracker that looks where the observer model says."""

    def __init__(self, task: Any, *, seed: int, model: ObserverModel, saccades: bool) -> None:
        self._task = task
        self._model = model
        self._saccades = saccades
        self._rng = np.random.default_rng(seed)
        (child,) = np.random.SeedSequence(seed).spawn(1)
        self._noise_rng = np.random.default_rng(child)
        self._noise: GazeNoise | None = GazeNoise(self._noise_rng) if model.gaze_noise else None
        self._screen: Any = None
        self._clock: Any = None
        self._recording = False
        self._plan: TrialPlan | None = None
        self._behaviour = "normal"
        self._latency_s = 0.24
        self._break_frac = 0.5
        self._blink: tuple[float, float] | None = None
        self._landing: tuple[float, float] | None = None
        self._t0 = 0.0
        self.sent_messages: list[str] = []

    # -- EyeTracker protocol -----------------------------------------------------
    def connect(self) -> None:
        return

    def configure(self, screen: Any, clock: Any) -> None:
        self._screen, self._clock = screen, clock
        if self._noise is not None:
            self._noise = GazeNoise(self._noise_rng)

    def calibrate(self) -> None:
        return

    def start_trial(self, trial_index: int, status: str) -> None:
        m = self._model
        self._recording = True
        self._plan = self._task.current_plan
        self._t0 = self._clock.now() if self._clock is not None else 0.0
        self._landing = None
        names = ["no_fixation", "fix_break", "no_saccade", "normal"]
        p = [m.p_no_fixation, m.p_fix_break, m.p_no_saccade if self._saccades else 0.0]
        weights = [*p, 1.0 - sum(p)]
        self._behaviour = str(self._rng.choice(names, p=weights))
        self._latency_s = float(np.clip(self._rng.normal(m.latency_mean_s, m.latency_sd_s),
                                        0.08, 0.9))
        self._break_frac = float(self._rng.uniform(0.2, 0.8))
        if self._rng.random() < m.p_blink:
            start = float(self._rng.uniform(0.3, 2.5))
            self._blink = (start, start + float(self._rng.uniform(0.08, 0.2)))
        else:
            self._blink = None

    def stop_trial(self) -> None:
        self._recording = False

    def is_recording(self) -> bool:
        return self._recording

    def send_message(self, text: str) -> None:
        self.sent_messages.append(text)

    def draw_host_overlay(self, shapes: list[HostShape]) -> None:
        return

    def shutdown(self, recording_destination: Path | None, /) -> None:
        return

    def get_gaze(self) -> GazeSample | None:
        now = self._clock.now()
        if self._blink is not None and self._blink[0] <= now - self._t0 <= self._blink[1]:
            return None
        x, y = self._aim_dva()
        if self._noise is not None:
            dx, dy = self._noise.offset_dva(now)
            x, y = x + dx, y + dy
        gx, gy = self._screen.centered_to_screen(self._screen.deg2px(x), self._screen.deg2px(y))
        return GazeSample(gx=gx, gy=gy, t=now)

    def describe(self) -> dict[str, Any]:
        return {"observer": asdict(self._model)}

    # -- where to look -------------------------------------------------------------
    def _aim_dva(self) -> tuple[float, float]:
        away = (-8.0, 6.0)  # far outside the 2 dva fixation window
        plan = self._plan
        if plan is None or self._behaviour == "no_fixation":
            return away
        gabor = plan.stimuli.get("gabor")
        if gabor is None or not gabor.started:
            return (0.0, 0.0)
        t = float(gabor.time_s)
        if self._saccades:
            fix_off = float(plan.record["fix_off_s"])
            if self._behaviour == "fix_break" and t >= self._break_frac * fix_off:
                return away
            if self._behaviour == "no_saccade" or t < fix_off + self._latency_s:
                return (0.0, 0.0)
            if self._landing is None:
                self._landing = self._land(gabor.trajectory, t)
            return self._landing
        if self._behaviour == "fix_break" and t >= self._break_frac * 2.0:
            return away
        return (0.0, 0.0)

    def _land(self, traj: Any, t: float) -> tuple[float, float]:
        return landing_dva(traj, t, self._model, self._rng)


def landing_dva(traj: Any, t: float, model: ObserverModel,
                rng: np.random.Generator) -> tuple[float, float]:
    """Where the simulated saccade lands, for a saccade starting at Gabor time t (from
    fixation at the origin): the physical or perceived position at onset, scaled by the
    gain, shifted along the drift direction at onset, scattered more along the saccade
    (radial) than across it."""
    target = (traj.perceived_position(t, model.illusion_deg) if model.target == "perceived"
              else traj.position(t))
    v = np.asarray(target, dtype=float)
    radial = v / (float(np.hypot(*v)) or 1.0)
    tangential = np.array([-radial[1], radial[0]])
    _, n = path_vectors(traj.angle_deg)
    landing = (model.saccade_gain * v + model.drift_shift_dva * float(traj.drift_sign(t)) * n
               + rng.normal(0.0, model.radial_sd_dva) * radial
               + rng.normal(0.0, model.tangential_sd_dva) * tangential)
    return float(landing[0]), float(landing[1])


class SimulatedHands:
    """Arrow-key reports for the perceptual task."""

    def __init__(self, task: Any, *, seed: int, model: ObserverModel) -> None:
        self._task = task
        self._model = model
        self._rng = np.random.default_rng(seed)
        self._plan: TrialPlan | None = None
        self._key: str | None = None
        self._view_s = 2.0

    def poll(self) -> ResponseSample:
        plan = self._task.current_plan
        if plan is not self._plan:
            self._new_trial(plan)
        if plan is None or self._key is None:
            return ResponseSample()
        gabor = plan.stimuli.get("gabor")
        if gabor is None or not gabor.started or gabor.time_s < self._view_s:
            return ResponseSample()
        return ResponseSample(keys=(self._key,))

    def _new_trial(self, plan: TrialPlan | None) -> None:
        m = self._model
        self._plan = plan
        self._view_s = float(self._rng.uniform(*m.view_s))
        if plan is None or self._rng.random() < m.p_no_response:
            self._key = None
            return
        rec = plan.record
        seen = (float(rec["path_angle_deg"]) - side_sign(str(rec["tilt_side"])) * m.illusion_deg
                + self._rng.normal(0.0, m.perceptual_noise_deg))
        p = self._task.params
        self._key = p.right_key if seen > 0 or (seen == 0 and self._rng.random() < 0.5) \
            else p.left_key


def perceived_vertical_deg(side: str, model: ObserverModel | None = None) -> float:
    """The physical path angle this observer sees as vertical (its true PSE)."""
    model = model or ObserverModel()
    return side_sign(side) * model.illusion_deg


__all__ = ["ObserverModel", "SimulatedEye", "SimulatedHands", "autopilot_for", "landing_dva",
           "perceived_vertical_deg"]
