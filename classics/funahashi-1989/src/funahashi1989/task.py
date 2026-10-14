"""The oculomotor delayed-response (ODR) task of Funahashi, Bruce & Goldman-Rakic (1989).

One trial, as the paper's Methods describe it (J Neurophysiol 61: 331-349, pp. 332-333;
docs/methods.md is the specification and cites each number):

1. a small white fixation spot appears at the centre; the subject looks at it and holds
   fixation for the fixation period (0.75 s);
2. a filled white square, the cue, flashes for 0.5 s at one of eight locations 13 deg from
   fixation, 45 deg apart, while fixation is held;
3. the delay (1.5, 3 or 6 s here; the paper used 3 s, 6 s, or mixtures of 1.5/3/6 s):
   fixation is still held and nothing else is on the screen;
4. the fixation spot goes off: that is the go signal. Within the 0.5-s response period
   the subject makes a saccade to where the cue had been;
5. a saccade whose endpoint falls within a 6-deg-diameter window around the cue location
   is correct (a monkey is paid juice for it).

Leaving fixation before the go signal ends the trial as FIX_BREAK; no departure within
the response period is NO_SACCADE; a saccade that lands outside the window is INACCURATE.
Values the paper does not state are marked ASSUMED in configs/task.yaml.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np
from alhazen import (
    CircleRegion,
    Condition,
    ConfigError,
    Duration,
    SubjectParams,
    Task,
    TrialPlan,
    TrialSetup,
    outcomes,
)
from alhazen.core.events import EventSchema
from alhazen.paradigms.config import SchedulerConfig
from alhazen.stimuli.base import NullStimulus
from alhazen.stimuli.fixation import make_fixation
from alhazen.task import duration as timing
from alhazen.task import phases
from pydantic import field_validator, model_validator

from funahashi1989.stimuli import make_square

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]

# The events of one trial, in the order they happen. A rig file may map any of them to a
# sync line (configs/rig-gaze-example.yaml) so a recording system can align to them.
EVENTS = ("FIX_ON", "FIX_ACQUIRED", "CUE_ON", "CUE_OFF", "FIX_OFF", "SACCADE_ONSET", "LANDED")


class OdrParams(SubjectParams):
    """A session's parameters. Durations resolve to whole frames at the measured rate.

    Defaults are the paper's values where it states them; configs/task.yaml is the file a
    session runs and says, line by line, which values are the paper's and which are assumed.
    """

    # --- stimuli ----------------------------------------------------------------------
    fix_size_dva: float = 0.1
    fix_color: tuple[float, float, float] = (1.0, 1.0, 1.0)
    cue_size_dva: float = 0.7
    cue_color: tuple[float, float, float] = (1.0, 1.0, 1.0)
    cue_ecc_dva: float = 13.0
    cue_angles_deg: list[float] = [0.0, 45.0, 90.0, 135.0, 180.0, 225.0, 270.0, 315.0]

    # --- gaze windows (radii) ---------------------------------------------------------
    fix_window_dva: float = 1.5
    target_window_dva: float = 3.0

    # --- timing -----------------------------------------------------------------------
    acquire_timeout: Duration = Duration(ms=2000)
    fixation_period: Duration = Duration(ms=750)
    cue_duration: Duration = Duration(ms=500)
    delays: list[Duration] = [Duration(ms=1500), Duration(ms=3000), Duration(ms=6000)]
    response_period: Duration = Duration(ms=500)
    landing_settle_speed_dva_s: float = 30.0
    landing_max_wait: Duration = Duration(ms=150)
    iti: Duration = Duration(ms=5000)

    paradigm: SchedulerConfig = SchedulerConfig(n_per_condition=5)

    @field_validator("cue_angles_deg", "delays")
    @classmethod
    def _not_empty(cls, value: list) -> list:
        if not value:
            raise ValueError("needs at least one entry")
        return value

    @model_validator(mode="after")
    def _windows_make_sense(self) -> OdrParams:
        for name in ("fix_size_dva", "cue_size_dva", "cue_ecc_dva", "fix_window_dva",
                     "target_window_dva", "landing_settle_speed_dva_s"):
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} must be > 0")
        # A target window that reached the fixation window would credit a saccade that
        # never left fixation (LandingSample refuses it too, but only mid-session).
        if self.cue_ecc_dva - self.target_window_dva <= self.fix_window_dva:
            raise ValueError(
                f"the target window (radius {self.target_window_dva} deg at "
                f"{self.cue_ecc_dva} deg) overlaps the fixation window (radius "
                f"{self.fix_window_dva} deg): shrink a window or move the cue out"
            )
        return self


def cue_position_dva(ecc_dva: float, angle_deg: float) -> tuple[float, float]:
    """Where a cue at this eccentricity and polar angle is, in degrees from fixation.

    Polar angle counts counter-clockwise from the right horizontal meridian, with y up:
    0 = right, 90 = up, 180 = left, 270 = down.
    """
    a = math.radians(angle_deg)
    return (ecc_dva * math.cos(a), ecc_dva * math.sin(a))


def check_fits_on_screen(params: OdrParams, screen: Any) -> None:
    """Refuse a rig whose screen cannot show every cue (the paper's CRT spanned 48 x 38
    deg; a common monitor at 57 cm spans about 50 x 29)."""
    half_w = screen.px2deg(screen.width_px / 2.0)
    half_h = screen.px2deg(screen.height_px / 2.0)
    half_cue = params.cue_size_dva / 2.0
    for angle in params.cue_angles_deg:
        x, y = cue_position_dva(params.cue_ecc_dva, angle)
        if abs(x) + half_cue > half_w or abs(y) + half_cue > half_h:
            raise ConfigError(
                f"the cue at {angle:g} deg ({x:.1f}, {y:.1f} deg) does not fit on this screen, "
                f"which reaches {half_w:.1f} deg left/right and {half_h:.1f} deg up/down of "
                f"its centre. Move the subject closer, use a larger screen, or lower "
                f"cue_ecc_dva (and list it as a deviation)"
            )


class OculomotorDelayedResponseTask(Task):
    """The ODR trial (module docstring)."""

    name = "oculomotor-delayed-response"
    events = EventSchema(EVENTS)
    outcomes = outcomes(
        CORRECT=dict(completed=True, success=True),
        # A saccade was made in time and landed outside the window. Completed, so it is
        # kept and not re-served: the paper examined such error trials.
        INACCURATE=dict(completed=True, success=False),
        NO_FIXATION=dict(completed=False),
        FIX_BREAK=dict(completed=False),
        NO_SACCADE=dict(completed=False),
    )
    params_model = OdrParams

    @classmethod
    def default_params(cls) -> Path:
        return PROJECT / "configs" / "task.yaml"

    def instructions(self) -> str | None:
        return (PROJECT / "instructions.md").read_text(encoding="utf-8")

    def conditions(self, rng: np.random.Generator) -> list[Condition]:
        p: OdrParams = self.params  # type: ignore[assignment]
        return [
            Condition({"cue_angle_deg": float(angle), "delay_index": i})
            for angle in p.cue_angles_deg
            for i in range(len(p.delays))
        ]

    # ------------------------------------------------------------------------------
    # One trial
    # ------------------------------------------------------------------------------

    def _geometry(self, setup: TrialSetup) -> tuple[float, tuple[float, float], dict, dict]:
        """The cue angle, its centred-px position, the stimuli and the regions both the
        memory trial and the training trials share."""
        p: OdrParams = self.params  # type: ignore[assignment]
        screen = setup.screen
        check_fits_on_screen(p, screen)
        angle = float(setup.condition.params["cue_angle_deg"])
        x_dva, y_dva = cue_position_dva(p.cue_ecc_dva, angle)
        pos = (screen.deg2px(x_dva), screen.deg2px(y_dva))
        stimuli = {
            "fixation": make_fixation(setup.display, screen, p.fix_size_dva, tuple(p.fix_color),
                                      (0.0, 0.0)),
            "cue": make_square(setup.display, screen, p.cue_size_dva, tuple(p.cue_color), pos),
            # The response period shows nothing: the fixation spot's absence is the go
            # signal, and the cue is gone.
            "blank": NullStimulus("blank"),
        }
        # Declared fixation first and target last: the operator's overlay draws them in
        # this order, and the simulated subject reads them in it (simulate.py).
        regions = {
            "fixation": CircleRegion((0.0, 0.0), screen.deg2px(p.fix_window_dva)),
            "target": CircleRegion(pos, screen.deg2px(p.target_window_dva)),
        }
        return angle, pos, stimuli, regions

    def _base_record(self, angle: float) -> dict[str, Any]:
        p: OdrParams = self.params  # type: ignore[assignment]
        x, y = cue_position_dva(p.cue_ecc_dva, angle)
        return {
            "cue_angle_deg": angle,
            "cue_ecc_dva": p.cue_ecc_dva,
            "cue_x_dva": x,
            "cue_y_dva": y,
            "fix_window_dva": p.fix_window_dva,
            "target_window_dva": p.target_window_dva,
        }

    def _response_phases(self, hz: float, stimulus_key: str) -> list:
        """Go signal, saccade, landing: shared by the memory and the visually guided trial."""
        p: OdrParams = self.params  # type: ignore[assignment]
        return [
            phases.StimulusResponse(
                stimulus_key=stimulus_key,
                depart_region="fixation",
                timeout_s=p.response_period.seconds(hz),
                on_timeout=self.outcomes["NO_SACCADE"],
                # This phase never draws the fixation spot: its first flip is the go signal,
                # and the latency is measured from that flip.
                onset_event="FIX_OFF",
                response_event="SACCADE_ONSET",
                rt_record_key="saccade_latency_ms",
            ),
            # Where the saccade came to rest: the first new gaze sample slower than the
            # settle speed (a stand-in for the paper's velocity-based saccade detection),
            # judged against the window around the cue location.
            phases.LandingSample(
                region="target",
                on_hit=self.outcomes["CORRECT"],
                on_miss=self.outcomes["INACCURATE"],
                settle_speed_dva_per_s=p.landing_settle_speed_dva_s,
                max_wait_s=p.landing_max_wait.seconds(hz),
                onset_event="SACCADE_ONSET",
                depart_region="fixation",
                stimulus_keys=[stimulus_key],
            ),
        ]

    def build_trial(self, setup: TrialSetup) -> TrialPlan:
        p: OdrParams = self.params  # type: ignore[assignment]
        hz = setup.refresh_rate_hz
        angle, _, stimuli, regions = self._geometry(setup)
        delay_index = int(setup.condition.params["delay_index"])
        delay = p.delays[delay_index]
        return TrialPlan(
            phases=[
                phases.AcquireFixation(
                    timeout_s=p.acquire_timeout.seconds(hz),
                    on_timeout=self.outcomes["NO_FIXATION"],
                    onset_event="FIX_ON",
                    acquired_event="FIX_ACQUIRED",
                ),
                phases.HoldFixation(
                    duration_s=p.fixation_period.seconds(hz),
                    on_break=self.outcomes["FIX_BREAK"],
                    duration_record_key="fixation_period_s",
                ),
                phases.HoldFixation(
                    duration_s=p.cue_duration.seconds(hz),
                    on_break=self.outcomes["FIX_BREAK"],
                    concurrent=["cue"],
                    onset_event="CUE_ON",
                    duration_record_key="cue_duration_s",
                ),
                phases.HoldFixation(
                    duration_s=delay.seconds(hz),
                    on_break=self.outcomes["FIX_BREAK"],
                    onset_event="CUE_OFF",
                    duration_record_key="delay_s",
                ),
                *self._response_phases(hz, "blank"),
            ],
            stimuli=stimuli,
            regions=regions,
            record={**self._base_record(angle), "delay_index": delay_index,
                    "trial_kind": "memory"},
        )

    def trial_timing(self, condition: Condition, refresh_rate_hz: float) -> Any:
        """For --estimate-duration: the phases above, with their caps."""
        p: OdrParams = self.params  # type: ignore[assignment]
        hz = refresh_rate_hz
        delay = p.delays[int(condition.params["delay_index"])]
        return timing.TrialTiming([
            timing.wait("fixation acquired", p.acquire_timeout.seconds(hz)),
            timing.fixed("fixation period", p.fixation_period.seconds(hz)),
            timing.fixed("cue", p.cue_duration.seconds(hz)),
            timing.fixed("delay", delay.seconds(hz)),
            timing.wait("saccade", p.response_period.seconds(hz)),
            timing.wait("landing", p.landing_max_wait.seconds(hz)),
        ])

    def simulation(self, seed: int):
        from alhazen.modes.simulation import Simulation

        from funahashi1989.simulate import SimulatedSubject

        subject = SimulatedSubject(seed=seed)
        return Simulation(tracker=subject, describe={"seed": seed,
                                                     "source": "funahashi1989.simulate",
                                                     **subject.describe()})
