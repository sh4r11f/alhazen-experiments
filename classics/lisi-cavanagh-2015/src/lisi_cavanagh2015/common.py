"""What both tasks share: the stimulus parameters, the trial's Trajectory, and the
fixation-controlled response window the perceptual task needs.

Every default here is the paper's value or the value in configs/; the params files are what
a session runs with, and docs/methods.md says where each number comes from.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import numpy as np
from alhazen import Duration, SubjectParams
from alhazen.core.trial import Outcome, TrialContext
from alhazen.task import phases
from pydantic import field_validator

from lisi_cavanagh2015.geometry import Trajectory

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]

BLACK = (-1.0, -1.0, -1.0)
START = {"up": 1, "down": -1}


class DoubleDriftParams(SubjectParams):
    """The stimulus and the fixation control, common to both tasks."""

    # Documentation of the display the paper used; not set by software (the window is the
    # gamma-linearised display's mid-grey). docs/methods.md, Deviations.
    background_cd_m2: float = 5.3
    fix_size_dva: float = 0.2
    fix_color: tuple[float, float, float] = BLACK
    fix_window_dva: float = 2.0
    path_center_dva: tuple[float, float] = (10.0, 0.0)
    path_length_dva: float = 3.0
    path_speed_dva_s: float = 2.0
    gabor_sf_cpd: float = 2.0
    gabor_sigma_dva: float = 0.1
    gabor_contrast: float = 1.0
    drift_tf_hz: float = 3.0
    start_directions: list[Literal["up", "down"]] = ["up", "down"]
    carrier_phase: Literal["random"] | float = "random"
    acquire_timeout: Duration = Duration(ms=5000)
    acquire_hold: Duration = Duration(ms=100)
    foreperiod: Duration = Duration(ms=500)
    foreperiod_jitter: Duration = Duration(ms=100)
    iti: Duration = Duration(ms=500)

    @field_validator("start_directions")
    @classmethod
    def _some_direction(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("start_directions needs at least one of up, down")
        return v

    @field_validator("gabor_contrast")
    @classmethod
    def _contrast(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("gabor_contrast is a Michelson contrast, 0..1")
        return v


def make_trajectory(p: DoubleDriftParams, *, angle_deg: float, side: str,
                    internal_motion: bool, start_direction: str,
                    rng: np.random.Generator) -> Trajectory:
    """This trial's stimulus from the params, the condition and the trial's rng."""
    phase0 = float(rng.uniform(0.0, 1.0)) if p.carrier_phase == "random" else float(
        p.carrier_phase)
    return Trajectory(
        angle_deg=float(angle_deg), side=side, internal_motion=bool(internal_motion),
        start_direction=START[start_direction],
        center=(float(p.path_center_dva[0]), float(p.path_center_dva[1])),
        length_dva=p.path_length_dva, speed_dva_s=p.path_speed_dva_s, sf_cpd=p.gabor_sf_cpd,
        tf_hz=p.drift_tf_hz, sigma_dva=p.gabor_sigma_dva, contrast=p.gabor_contrast,
        phase0_cycles=phase0,
    )


def trajectory_record(traj: Trajectory) -> dict[str, object]:
    """The columns that let an analysis rebuild the trial's stimulus exactly."""
    return {
        "path_angle_deg": traj.angle_deg,
        "tilt_side": traj.side,
        "internal_motion": traj.internal_motion,
        "start_direction": "up" if traj.start_direction > 0 else "down",
        "carrier_phase0": traj.phase0_cycles,
        "path_center_x_dva": traj.center[0],
        "path_center_y_dva": traj.center[1],
        "path_length_dva": traj.length_dva,
        "path_speed_dva_s": traj.speed_dva_s,
        "drift_tf_hz": traj.tf_hz,
    }


class FixatedResponseWindow(phases.ResponseWindow):
    """alhazen's ResponseWindow with fixation control: the trial ends as ``on_break`` on
    the first frame gaze is not verifiably inside ``region`` (a look away or a blink, by
    alhazen's blink rule), before any key on that frame is read. The paper's perceptual
    task: "trials in which participant shifted gaze away from the fixation point or
    blinked before giving the response were immediately aborted and repeated"."""

    name = "fixated_response_window"

    def __init__(self, *args: object, region: str = "fixation",
                 on_break: Outcome | None = None, **kwargs: object) -> None:
        if on_break is None:
            raise ValueError("FixatedResponseWindow needs an on_break outcome")
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        self._region = region
        self._on_break = on_break

    def on_frame(self, ctx: TrialContext) -> str | Outcome:
        if not ctx.regions[self._region].contains(ctx.inputs.gaze):
            return self._on_break
        return super().on_frame(ctx)
