"""Experiment 1, part 2: the saccade task (Lisi & Cavanagh 2015).

The participant fixates a small black dot at the centre of the screen. After 400-600 ms
the double-drift Gabor appears at the middle of its path, 10 dva to the right, and starts
moving back and forth. The fixation dot disappears at one of six times equally spaced along
a full motion cycle, starting at the first path reversal, and the participant makes a
saccade to the moving Gabor. The Gabor is removed as soon as gaze leaves a 2 dva circle
around fixation, so the saccade gets no visual feedback. The path orientations shown are
the ones each participant saw as vertical in the perceptual task (path_angle_right_deg and
path_angle_left_deg), with and without internal motion (the control).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from alhazen import Condition, Duration, Task, TrialPlan, TrialSetup, outcomes
from alhazen.core.events import EventSchema
from alhazen.core.trial import CircleRegion, TrialContext
from alhazen.paradigms.config import SchedulerConfig
from alhazen.task import phases
from alhazen.task.duration import TrialTiming, bounded, jittered, wait
from pydantic import model_validator

from lisi_cavanagh2015.common import (
    PROJECT,
    DoubleDriftParams,
    make_trajectory,
    trajectory_record,
)
from lisi_cavanagh2015.geometry import SIDES, Trajectory, fixation_offset_times


class SaccadeParams(DoubleDriftParams):
    """The saccade task's parameters (configs/task.yaml)."""

    # Per participant: the physical path orientations the perceptual task found to be seen
    # as vertical (the PSEs). The shipped values are the paper's group means.
    path_angle_right_deg: float = 49.0
    path_angle_left_deg: float = -52.0
    n_fix_off_times: int = 6
    saccade_timeout: Duration = Duration(ms=1000)
    landing_settle_speed_dva_s: float = 30.0
    landing_max_wait: Duration = Duration(ms=150)
    landing_window_dva: float = 5.0
    paradigm: SchedulerConfig = SchedulerConfig(n_per_condition=4)

    @model_validator(mode="after")
    def _sane(self) -> SaccadeParams:
        if self.n_fix_off_times < 1:
            raise ValueError("n_fix_off_times must be >= 1")
        if self.paradigm.kind not in ("sequence", "constant"):
            raise ValueError("the saccade task serves a fixed plan: kind sequence or constant")
        return self

    def angle_for(self, side: str) -> float:
        return self.path_angle_right_deg if side == "right" else self.path_angle_left_deg


def gabor_position_at(ctx: TrialContext, traj: Trajectory, event: str) -> tuple[float, float]:
    """Where the Gabor's envelope was on the flip that stamped ``event`` (centred px).
    The Gabor's own clock starts on the GABOR_ON flip, so its time at any later flip is
    the difference of the two stamps."""
    t = float(ctx.record[f"t_{event.lower()}"]) - float(ctx.record["t_gabor_on"])
    p = traj.position(t)
    return ctx.screen.deg2px(float(p[0])), ctx.screen.deg2px(float(p[1]))


class DoubleDriftSaccadesTask(Task):
    name = "double-drift-saccades"
    events = EventSchema(("FIX_ON", "FIX_ACQUIRED", "GABOR_ON", "FIX_OFF", "RESPONSE_ONSET",
                          "LANDED"))
    outcomes = outcomes(
        SACCADE=dict(completed=True, success=True),
        NO_FIXATION=dict(completed=False),
        FIX_BREAK=dict(completed=False),
        NO_SACCADE=dict(completed=False),
    )
    params_model = SaccadeParams

    @classmethod
    def default_params(cls) -> Path:
        return PROJECT / "configs" / "task.yaml"

    def instructions(self) -> str | None:
        return (PROJECT / "instructions.md").read_text(encoding="utf-8")

    def conditions(self, rng: np.random.Generator) -> list[Condition]:
        p: SaccadeParams = self.params  # type: ignore[assignment]
        return [
            Condition({"tilt_side": side, "internal_motion": motion, "start_direction": start})
            for side in SIDES for motion in (True, False) for start in p.start_directions
        ]

    def trial_timing(self, condition: Condition, refresh_rate_hz: float) -> TrialTiming:
        p: SaccadeParams = self.params  # type: ignore[assignment]
        hz = refresh_rate_hz
        probe = make_trajectory(p, angle_deg=0.0, side="right", internal_motion=True,
                                start_direction=p.start_directions[0],
                                rng=np.random.default_rng(0))
        offs = fixation_offset_times(probe, p.n_fix_off_times)
        return TrialTiming([
            wait("acquire fixation", p.acquire_timeout.seconds(hz)),
            jittered("foreperiod", p.foreperiod.seconds(hz), p.foreperiod_jitter.seconds(hz)),
            bounded("Gabor moving with the fixation dot", min(offs), max(offs),
                    "one of the fixation offset times, drawn per trial"),
            wait("saccade latency", p.saccade_timeout.seconds(hz)),
            wait("landing", p.landing_max_wait.seconds(hz)),
        ])

    def build_trial(self, setup: TrialSetup) -> TrialPlan:
        p: SaccadeParams = self.params  # type: ignore[assignment]
        hz = setup.refresh_rate_hz
        cond = setup.condition.params
        side = str(cond["tilt_side"])
        traj = make_trajectory(p, angle_deg=p.angle_for(side), side=side,
                               internal_motion=bool(cond["internal_motion"]),
                               start_direction=str(cond["start_direction"]), rng=setup.rng)
        offs = fixation_offset_times(traj, p.n_fix_off_times)
        k = int(setup.rng.integers(len(offs)))
        o = self.outcomes
        from lisi_cavanagh2015.stimuli import make_dot, make_gabor

        return TrialPlan(
            phases=[
                phases.AcquireFixation(hold_s=p.acquire_hold.seconds(hz),
                                       timeout_s=p.acquire_timeout.seconds(hz),
                                       on_timeout=o["NO_FIXATION"]),
                phases.HoldFixation(duration_s=p.foreperiod.seconds(hz),
                                    jitter_s=p.foreperiod_jitter.seconds(hz),
                                    on_break=o["FIX_BREAK"],
                                    duration_record_key="foreperiod_s"),
                # The Gabor appears and moves; the dot stays until the offset time.
                phases.HoldFixation(duration_s=offs[k], on_break=o["FIX_BREAK"],
                                    concurrent=["gabor"], onset_event="GABOR_ON",
                                    duration_record_key="gabor_lead_s"),
                # The dot is gone: saccade onset is gaze leaving the 2 dva window, and the
                # Gabor goes off with it (it is not drawn in the landing phase).
                phases.StimulusResponse("gabor", depart_region="fixation",
                                        timeout_s=p.saccade_timeout.seconds(hz),
                                        on_timeout=o["NO_SACCADE"], onset_event="FIX_OFF",
                                        response_event="RESPONSE_ONSET",
                                        rt_record_key="saccade_latency_ms"),
                phases.LandingSample(
                    region="landing", on_hit=o["SACCADE"], on_miss=o["SACCADE"],
                    settle_speed_dva_per_s=p.landing_settle_speed_dva_s,
                    max_wait_s=p.landing_max_wait.seconds(hz), depart_region="fixation",
                    reference=lambda ctx: gabor_position_at(ctx, traj, "RESPONSE_ONSET"),
                    stimulus_keys=[]),
            ],
            stimuli={
                "fixation": make_dot(setup.display, setup.screen, p.fix_size_dva, p.fix_color),
                "gabor": make_gabor(setup.display, setup.screen, traj),
            },
            regions={
                "fixation": CircleRegion((0.0, 0.0), setup.screen.deg2px(p.fix_window_dva)),
                "landing": CircleRegion(
                    (setup.screen.deg2px(traj.center[0]), setup.screen.deg2px(traj.center[1])),
                    setup.screen.deg2px(p.landing_window_dva)),
            },
            record={**trajectory_record(traj), "fix_off_index": k, "fix_off_s": offs[k]},
        )

    def score(self, record: dict[str, Any]) -> dict[str, Any]:
        """Derived columns: the Gabor's state at saccade onset, and the saccade vector."""
        out = dict(record)
        t_on, t_sac = out.get("t_gabor_on"), out.get("t_response_onset")
        if t_on is None or t_sac is None:
            return out
        traj = Trajectory(
            angle_deg=float(out["path_angle_deg"]), side=str(out["tilt_side"]),
            internal_motion=bool(out["internal_motion"]),
            start_direction=1 if out["start_direction"] == "up" else -1,
            center=(float(out["path_center_x_dva"]), float(out["path_center_y_dva"])),
            length_dva=float(out["path_length_dva"]), speed_dva_s=float(out["path_speed_dva_s"]),
            tf_hz=float(out["drift_tf_hz"]))
        t = float(t_sac) - float(t_on)
        pos = traj.position(t)
        out["gabor_t_at_onset_s"] = t
        out["gabor_x_at_onset_dva"] = float(pos[0])
        out["gabor_y_at_onset_dva"] = float(pos[1])
        out["gabor_along_at_onset_dva"] = float(traj.along(t))
        out["gabor_direction_at_onset"] = int(traj.direction(t))
        out["drift_sign_at_onset"] = int(traj.drift_sign(t))
        if out.get("endpoint_measured") and "fixation_x_dva" in out:
            out["saccade_dx_dva"] = float(out["endpoint_x_dva"]) - float(out["fixation_x_dva"])
            out["saccade_dy_dva"] = float(out["endpoint_y_dva"]) - float(out["fixation_y_dva"])
        return out

    def simulation(self, seed: int) -> Any:
        from alhazen.modes.simulation import Simulation

        from lisi_cavanagh2015.simulate import autopilot_for

        task, tracker, response = autopilot_for(type(self), self.params, seed,
                                                model=getattr(self, "observer_model", None))
        return Simulation(task=task, tracker=tracker, response=response,
                          describe={"seed": seed, "source": "lisi_cavanagh2015.simulate",
                                    **tracker.describe()})
