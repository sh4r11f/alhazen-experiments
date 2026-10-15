"""Moore & Fallah (2001): detect a brief dimming of a peripheral target among
flashing distractors, with an optional microstimulation trigger before it.

A trial (docs/methods.md, Procedure):

1. the fixation point appears; gaze must enter and stay in the fixation
   window (AcquireFixation);
2. the target appears inside or outside the movement field, distractors
   flash elsewhere every 32 ms, and on a blink trial the target dims for
   32–48 ms at a random time 500–1300 ms after it appeared. On a stimulation
   trial a STIM_TRIGGER event goes out one stimulation-onset asynchrony
   before the (would-be) dimming, for the rig to map to a TTL line
   (DimmingWatch);
3. the subject presses the response key within the response window after a
   dimming, or holds off for the whole catch trial.

The luminance change is titrated by the paper's simultaneous block staircase
(staircase.py), one staircase per condition (stimulation, control).
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Literal

import numpy as np
from alhazen import CircleRegion, Condition, Duration, SubjectParams, Task, TrialPlan, TrialSetup
from alhazen import outcomes as declare_outcomes
from alhazen.config.models import Model, whole_frames
from alhazen.core.events import EventSchema
from alhazen.paradigms.base import TrialSource
from alhazen.task import phases
from alhazen.task.duration import (
    PlannedSchedule,
    Schedule,
    TrialTiming,
    fixed,
    uniform,
    wait,
)
from pydantic import BaseModel, model_validator

from moore_fallah2001 import geometry
from moore_fallah2001.luminance import Photometry, dimmed_luminance, to_rgb
from moore_fallah2001.phases import DimmingWatch, WatchPlan
from moore_fallah2001.staircase import BLINK, CATCH, BlockRule, BlockStaircases
from moore_fallah2001.stimuli import Layered, make_background, make_fixation_point, make_square

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]


class FieldParams(Model):
    """Where the target goes: the movement field, or a location outside it."""

    movement_field_dva: tuple[float, float]
    target_field: Literal["inside", "outside"] = "inside"
    outside_rotation_deg: float = 90.0


class StimulationParams(Model):
    """The microstimulation seam. Only ``enabled`` and ``soa`` change what the
    task does (whether, and when, STIM_TRIGGER is emitted). The rest is the
    paper's train, recorded with every session so the record says what the
    lab's stimulator was meant to deliver; this software never drives it."""

    enabled: bool = False
    soa: Duration = Duration(ms=175)
    train: Duration = Duration(ms=100)
    pulse_width_ms: float = 0.2
    pulse_rate_hz: float = 200.0
    biphasic: bool = True
    max_fraction_of_movement_threshold: float = 0.5
    # Per session, entered by the lab after mapping the site; None = not entered.
    current_ua: float | None = None
    movement_threshold_ua: float | None = None


class StaircaseParams(Model):
    start_pct: float
    step_pct: float
    min_pct: float
    n_blocks: int
    blink_per_block: int = 2
    catch_per_block: int = 1

    @model_validator(mode="after")
    def _valid(self) -> StaircaseParams:
        if not 0 < self.min_pct <= self.start_pct < 100:
            raise ValueError("need 0 < min_pct <= start_pct < 100 (% Michelson contrast)")
        if self.step_pct <= 0 or self.n_blocks < 1:
            raise ValueError("step_pct must be > 0 and n_blocks >= 1")
        return self


class TargetDimmingDetectionTaskParams(SubjectParams):
    """A session's parameters. Durations resolve to whole frames at the measured rate."""

    photometry: Photometry
    background_cd_m2: float = 1.0
    target_cd_m2: float = 26.0
    distractor_cd_m2: float = 26.0
    fixation_cd_m2: float = 26.0
    fix_size_dva: float = 0.5
    fix_window_radius_dva: float = 1.5
    fix_acquire_timeout: Duration = Duration(ms=2000)
    fix_acquire_hold: Duration = Duration(ms=200)
    target_area_deg2: float = 0.75
    distractor_area_deg2: float = 0.55
    distractor_flash: Duration = Duration(ms=16)
    distractor_period: Duration = Duration(ms=32)
    distractor_exclusion_dva: float = 3.5
    distractor_fixation_clearance_dva: float = 1.5
    dim_onset_min: Duration = Duration(ms=500)
    dim_onset_max: Duration = Duration(ms=1300)
    dim_duration_min: Duration = Duration(ms=32)
    dim_duration_max: Duration = Duration(ms=48)
    response_window: Duration = Duration(ms=800)
    min_rt: Duration = Duration(ms=100)
    catch_duration: Duration = Duration(ms=2100)
    response_key: str = "space"
    field: FieldParams
    stimulation: StimulationParams = StimulationParams()
    staircase: StaircaseParams
    iti: Duration = Duration(ms=1000)

    @model_validator(mode="after")
    def _consistent(self) -> TargetDimmingDetectionTaskParams:
        ms = _ms
        if self.subject_kind is not None and self.subject_kind.value == "human" \
                and self.stimulation.enabled:
            raise ValueError(
                "stimulation.enabled is a monkey procedure; a human file must say false")
        checks = [
            ((self.dim_onset_min,), (self.dim_onset_max,),
             "dim_onset_min must be <= dim_onset_max"),
            ((self.dim_duration_min,), (self.dim_duration_max,),
             "dim_duration_min must be <= dim_duration_max"),
            ((self.dim_onset_max, self.response_window), (self.catch_duration,),
             "catch_duration must cover the latest dimming plus the response window"),
            ((self.distractor_flash,), (self.distractor_period,),
             "distractor_flash must be shorter than distractor_period"),
        ]
        if self.stimulation.enabled:
            checks.append(((self.stimulation.soa,), (self.dim_onset_min,),
                           "the stimulation-onset asynchrony is longer than the earliest dimming"))
        for small, large, message in checks:
            a, b = [ms(d) for d in small], [ms(d) for d in large]
            # Frame-valued durations depend on the refresh rate; checked at the rig instead.
            if None not in a and None not in b and sum(a) > sum(b):  # type: ignore[arg-type]
                raise ValueError(message)
        if self.distractor_flash == self.distractor_period:
            raise ValueError("distractor_flash must be shorter than distractor_period")
        return self

    @property
    def conditions_labels(self) -> dict[str, dict[str, bool]]:
        if self.stimulation.enabled:
            return {"stim": {"stimulation": True}, "control": {"stimulation": False}}
        return {"control": {"stimulation": False}}


class TargetDimmingDetectionTask(Task):
    name = "target-dimming-detection"
    events = EventSchema((
        "FIX_ON", "FIX_ACQUIRED", "TARGET_ON", "STIM_TRIGGER", "DIM_ON", "DIM_OFF", "RESPONSE",
    ))
    outcomes = declare_outcomes(
        HIT=dict(completed=True, success=True),
        MISS=dict(completed=True, success=False),
        EARLY_RESPONSE=dict(completed=True, success=False),
        FALSE_ALARM=dict(completed=True, success=False),
        CORRECT_REJECTION=dict(completed=True, success=True),
        FIX_BREAK=dict(completed=False),
        NO_FIXATION=dict(completed=False),
    )
    params_model = TargetDimmingDetectionTaskParams

    @classmethod
    def default_params(cls) -> Path:
        return PROJECT / "configs" / "task.yaml"

    def instructions(self) -> str | None:
        return (PROJECT / "instructions.md").read_text(encoding="utf-8")

    # -- scheduling --------------------------------------------------------

    def make_source(self, params: BaseModel, rng: np.random.Generator) -> TrialSource:
        p: TargetDimmingDetectionTaskParams = params  # type: ignore[assignment]
        s = p.staircase
        return BlockStaircases(
            p.conditions_labels, parameter="dim_pct", start=s.start_pct, step=s.step_pct,
            min_value=s.min_pct, n_blocks=s.n_blocks, rng=rng,
            rule=BlockRule(n_blink=s.blink_per_block, n_catch=s.catch_per_block),
        )

    def duration_schedule(self, params: BaseModel, rng: np.random.Generator) -> Schedule:
        p: TargetDimmingDetectionTaskParams = params  # type: ignore[assignment]
        s = p.staircase
        block = []
        for label, fields in p.conditions_labels.items():
            for trial_type, n in ((BLINK, s.blink_per_block), (CATCH, s.catch_per_block)):
                block += [Condition({**fields, "staircase": label, "trial_type": trial_type,
                                     "slot": i}) for i in range(n)]
        return PlannedSchedule(
            blocks=(tuple(block * s.n_blocks),), breaks=0,
            note="every staircase runs n_blocks blocks; trials lost to a fixation break are "
                 "served again within their block and are not counted here",
        )

    def trial_timing(self, condition: Condition, refresh_rate_hz: float) -> TrialTiming | None:
        p: TargetDimmingDetectionTaskParams = self.params  # type: ignore[assignment]
        hz = refresh_rate_hz
        spans = [
            wait("fixation acquisition", p.fix_acquire_timeout.seconds(hz),
                 basis="fix_acquire_timeout"),
            fixed("fixation hold", p.fix_acquire_hold.seconds(hz), basis="fix_acquire_hold"),
        ]
        if condition.params.get("trial_type") == CATCH:
            spans.append(fixed("catch trial", p.catch_duration.seconds(hz), basis="catch_duration"))
        else:
            spans += [
                uniform("wait for the dimming", p.dim_onset_min.seconds(hz),
                        p.dim_onset_max.seconds(hz), basis="dim_onset_min..dim_onset_max"),
                wait("response window", p.response_window.seconds(hz), basis="response_window"),
            ]
        return TrialTiming(spans)

    # -- one trial -----------------------------------------------------------

    def build_trial(self, setup: TrialSetup) -> TrialPlan:
        p: TargetDimmingDetectionTaskParams = self.params  # type: ignore[assignment]
        hz = setup.refresh_rate_hz
        period = 1.0 / hz
        screen, rng = setup.screen, setup.rng
        cond = setup.condition.params
        blink = cond["trial_type"] == BLINK
        stimulation = bool(cond.get("stimulation", False))
        dim_pct = float(cond["dim_pct"])

        half_w = screen.px2deg(screen.width_px / 2.0)
        half_h = screen.px2deg(screen.height_px / 2.0)
        target_side = math.sqrt(p.target_area_deg2)
        distractor_side = math.sqrt(p.distractor_area_deg2)
        tx, ty = geometry.target_location(p.field.movement_field_dva, p.field.target_field,
                                          p.field.outside_rotation_deg)
        geometry.check_on_screen((tx, ty), target_side / 2, half_w, half_h, "target")

        # The timeline, in whole frames from the flip before the target's first frame.
        lo = whole_frames(p.dim_onset_min.seconds(hz), period)
        hi = whole_frames(p.dim_onset_max.seconds(hz), period)
        dim_frame = int(rng.integers(lo, hi + 1))
        dlo = max(1, whole_frames(p.dim_duration_min.seconds(hz), period))
        dhi = max(dlo, whole_frames(p.dim_duration_max.seconds(hz), period))
        dim_frames = int(rng.integers(dlo, dhi + 1))
        soa_frames = whole_frames(p.stimulation.soa.seconds(hz), period)
        stim_frame = dim_frame - soa_frames if stimulation else None
        flash = max(1, whole_frames(p.distractor_flash.seconds(hz), period))
        cycle = max(flash + 1, whole_frames(p.distractor_period.seconds(hz), period))
        last = whole_frames(max(p.catch_duration.seconds(hz),
                                p.dim_onset_max.seconds(hz) + p.response_window.seconds(hz)),
                            period)
        n_cycles = last // cycle + 2
        spots = geometry.distractor_positions(
            rng, n_cycles, half_w=half_w, half_h=half_h, half_side=distractor_side / 2,
            target=(tx, ty), exclusion_radius=p.distractor_exclusion_dva,
            fixation_clearance=p.distractor_fixation_clearance_dva)

        phot = p.photometry
        target_rgb = to_rgb(p.target_cd_m2, phot)
        dimmed_cd = dimmed_luminance(p.target_cd_m2, dim_pct)
        dimmed_rgb = to_rgb(dimmed_cd, phot)
        deg = screen.deg2px
        plan = WatchPlan(
            blink=blink, dim_frame=dim_frame, dim_frames=dim_frames, stim_frame=stim_frame,
            response_window_s=p.response_window.seconds(hz), min_rt_s=p.min_rt.seconds(hz),
            catch_duration_s=p.catch_duration.seconds(hz), target_color=target_rgb,
            dimmed_color=dimmed_rgb, flash_frames=flash, cycle_frames=cycle,
            distractor_px=tuple((deg(x), deg(y)) for x, y in spots),
        )
        o = self.outcomes
        watch = DimmingWatch(
            plan, hit=o["HIT"], miss=o["MISS"], early=o["EARLY_RESPONSE"],
            false_alarm=o["FALSE_ALARM"], correct_rejection=o["CORRECT_REJECTION"],
            fix_break=o["FIX_BREAK"], response_key=p.response_key,
            stim_payload={"soa_frames": soa_frames,
                          "train_ms": p.stimulation.train.seconds(hz) * 1000},
            dim_payload={"dim_pct": dim_pct, "dim_frames": dim_frames},
        )
        display = setup.display
        stimuli = {
            "background": make_background(display, screen, to_rgb(p.background_cd_m2, phot)),
            "fixation": make_fixation_point(display, screen, p.fix_size_dva,
                                            to_rgb(p.fixation_cd_m2, phot)),
            "target": make_square(display, screen, target_side, target_rgb,
                                  (deg(tx), deg(ty)), "target"),
            "distractor": make_square(display, screen, distractor_side,
                                      to_rgb(p.distractor_cd_m2, phot), (0.0, 0.0), "distractor"),
        }
        # The paper's display is the 1 cd/m² background for the whole trial (alhazen's
        # window is mid-grey), so fixation acquisition draws the point over it too.
        stimuli["fixation_on_background"] = Layered(stimuli["background"], stimuli["fixation"])
        acquire = phases.AcquireFixation(
            fixation_key="fixation_on_background", region="fixation",
            hold_s=p.fix_acquire_hold.seconds(hz), timeout_s=p.fix_acquire_timeout.seconds(hz),
            on_timeout=o["NO_FIXATION"],
        )
        mf = p.field.movement_field_dva
        return TrialPlan(
            phases=[acquire, watch],
            stimuli=stimuli,
            regions={"fixation": CircleRegion((0.0, 0.0), deg(p.fix_window_radius_dva))},
            record={
                "target_field": p.field.target_field,
                "target_x_dva": tx, "target_y_dva": ty,
                "mf_x_dva": float(mf[0]), "mf_y_dva": float(mf[1]),
                "dim_onset_ms": dim_frame * period * 1000.0,
                "dim_duration_ms": dim_frames * period * 1000.0 if blink else None,
                "planned_soa_ms": soa_frames * period * 1000.0 if stimulation else None,
                "dimmed_cd_m2": dimmed_cd,
                "stim_current_ua": p.stimulation.current_ua if stimulation else None,
            },
        )

    def score(self, record: dict) -> dict:
        """The realised stimulation-onset asynchrony, from the two flip stamps."""
        stim, dim = record.get("t_stim_trigger"), record.get("t_dim_on")
        if stim is not None and dim is not None:
            record["realised_soa_ms"] = (dim - stim) * 1000.0
        return record

    def simulation(self, seed: int):
        from alhazen.modes.simulation import Simulation

        from moore_fallah2001.simulate import FixatingEye, SimulatedObserver

        p: TargetDimmingDetectionTaskParams = self.params  # type: ignore[assignment]
        return Simulation(
            tracker=FixatingEye(seed=seed),
            response=SimulatedObserver(seed=seed, key=p.response_key),
            describe={"seed": seed, "source": "moore_fallah2001.simulate",
                      **SimulatedObserver.DEFAULTS, **FixatingEye.DEFAULTS},
        )


def _ms(d: Duration) -> float | None:
    """A millisecond Duration's value, or None for one given in frames."""
    return d.ms
