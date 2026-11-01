"""Experiment 1: equating luminance by minimum motion, method of constant stimuli.

Anstis & Cavanagh (1983, p. 157). A 2 x 2 deg square-wave grating at 2.5 c/deg in a dark
surround alternates red/green with dark-yellow/light-yellow in the four-stroke cycle
(stimulus.py) at 5 cycles per second. Green is held at 13.4 cd/m2 and red takes one of a
set of luminances between 8 and 12 cd/m2, each ten times in random order; the observer
reports whether the grating moved left, right or neither. The point of subjective
equality (PSE) is the red luminance at which neither direction prevails.

Here one trial is: the fixation mark alone, then the cycle running until the observer
presses LEFT, RIGHT or DOWN (neither). Each test level is shown five times with the
quarter-cycle steps going rightward and five times leftward (a counterbalancing the
paper does not describe; it lets "red looked lighter" be separated from "said right").
"""

from __future__ import annotations

from typing import Any, Literal

from alhazen import Duration, TrialPlan, TrialSetup, outcomes
from alhazen.core.events import EventSchema
from alhazen.paradigms.base import Condition
from alhazen.paradigms.config import SchedulerConfig
from alhazen.task import phases
from pydantic import Field, model_validator

from anstiscavanagh1983.common import (
    PROJECT,
    DisplayParams,
    EquiluminanceTask,
    grating_geometry,
    michelson,
    timing,
)
from anstiscavanagh1983.phases import Present
from anstiscavanagh1983.render import FixationStim, make_cycle
from anstiscavanagh1983.stimulus import Spec, stroke_luminance

RESPONSE_KEYS = {"left": "MOTION_LEFT", "right": "MOTION_RIGHT", "down": "NO_MOTION"}
MOTION_SIGN = {"left": -1, "right": 1, "down": 0}


class ConstantParams(DisplayParams):
    spatial_freq_cpd: float = Field(2.5, gt=0)
    cycle_hz: float = Field(5.0, gt=0)
    interleave_contrast: float = Field(0.0625, ge=0, lt=1)
    interleave_mix: Literal["additive", "line_dither"] = "additive"
    dither_rows: int = Field(2, ge=1)
    test_levels_cd_m2: list[float] = [8.0 + 0.25 * i for i in range(17)]
    response_timeout: Duration = Duration(ms=10000)
    paradigm: SchedulerConfig = SchedulerConfig(kind="constant", n_per_condition=5)

    @model_validator(mode="after")
    def _levels(self) -> ConstantParams:
        if not self.test_levels_cd_m2 or min(self.test_levels_cd_m2) <= 0:
            raise ValueError("test_levels_cd_m2 must be positive luminances")
        if len(set(self.test_levels_cd_m2)) != len(self.test_levels_cd_m2):
            raise ValueError("test_levels_cd_m2 has repeats")
        return self


def check_spec(spec: Spec, space: Any) -> None:
    """Raise when any stroke of ``spec`` needs a gun outside 0..1."""
    for k in range(spec.strokes):
        space.levels(stroke_luminance(spec, space, k))


class MinMotionConstantTask(EquiluminanceTask):
    name = "min-motion-constant"
    params_model = ConstantParams
    instructions_section = "min-motion-constant"
    events = EventSchema(("FIX_ON", "RESPONSE_CUE", "RESPONSE"))
    outcomes = outcomes(
        MOTION_LEFT=dict(completed=True, success=True),
        MOTION_RIGHT=dict(completed=True, success=True),
        NO_MOTION=dict(completed=True, success=True),
        NO_RESPONSE=dict(completed=False),
    )

    @classmethod
    def default_params(cls):
        return PROJECT / "configs" / "task.yaml"

    def __init__(self, params: Any) -> None:
        super().__init__(params)
        p: ConstantParams = self.params  # type: ignore[assignment]
        space = p.colour_space()
        for level in p.test_levels_cd_m2:  # refused at load, not mid-session
            check_spec(self._spec(level, 1, 0, 8, 8), space)

    def _spec(self, level: float, step: int, offset: int, period: int, size: int) -> Spec:
        p: ConstantParams = self.params  # type: ignore[assignment]
        return Spec("four_stroke", p.test_colour, p.reference_colour, float(level),
                    p.reference_cd_m2, size, period, step, offset, p.interleave_contrast,
                    p.interleave_mix, p.dither_rows)

    def conditions(self, rng):
        p: ConstantParams = self.params  # type: ignore[assignment]
        return [Condition({"test_cd_m2": float(lv), "step": s})
                for lv in p.test_levels_cd_m2 for s in (1, -1)]

    def build_trial(self, setup: TrialSetup) -> TrialPlan:
        p: ConstantParams = self.params  # type: ignore[assignment]
        hz = setup.refresh_rate_hz
        ppd = setup.screen.px_per_deg
        level = float(setup.condition.params["test_cd_m2"])
        step = int(setup.condition.params.get("step", 1))
        period, sf = grating_geometry(ppd, p.spatial_freq_cpd, p.snap_period_to_pixels)
        n_frames, cycle = timing(hz, p.cycle_hz, 4)
        size = max(period, int(round(p.patch_size_dva * ppd)))
        offset = int(setup.rng.integers(0, period))
        spec = self._spec(level, step, offset, period, size)
        space = p.colour_space()
        stim = make_cycle(setup.display, setup.screen, spec, space, p.fix(), n_frames)
        fixation = FixationStim(setup.display, setup.screen, size, ppd, p.fix())
        record = {**self.base_record(p), "task": self.name, "test_cd_m2": level,
                  "step": step, "offset_px": offset, "period_px": period,
                  "spatial_freq_effective_cpd": sf, "cycle_hz_effective": cycle,
                  "frames_per_stroke": n_frames, "interleave_contrast": p.interleave_contrast,
                  "interleave_mix": p.interleave_mix,
                  "test_michelson": michelson(level, p.reference_cd_m2)}
        payload = {"task": self.name, "test_cd_m2": level, "reference_cd_m2": p.reference_cd_m2,
                   "test_colour": p.test_colour, "reference_colour": p.reference_colour,
                   "step": step, "spatial_freq_cpd": sf, "cycle_hz": cycle}
        keys = {k: self.outcomes[v] for k, v in RESPONSE_KEYS.items()}
        return TrialPlan(
            phases=[
                Present(["fixation"], p.fixation_duration.seconds(hz), onset_event="FIX_ON",
                        payload=payload),
                phases.ResponseWindow(keys=keys, timeout_s=p.response_timeout.seconds(hz),
                                      on_timeout=self.outcomes["NO_RESPONSE"],
                                      stimulus_keys=["stimulus"], onset_event="RESPONSE_CUE"),
            ],
            stimuli={"stimulus": stim, "fixation": fixation},
            record=record,
        )

    def score(self, record: dict[str, Any]) -> dict[str, Any]:
        key = record.get("response_key")
        if key in MOTION_SIGN and "step" in record:
            sign = MOTION_SIGN[key]
            record["motion_sign"] = sign
            record["report"] = ("neither" if sign == 0 else
                                "test_lighter" if sign == int(record["step"]) else
                                "reference_lighter")
        return record

    def demo_views(self, setup: Any) -> list[Any]:
        from alhazen.modes.demo import DemoView

        p: ConstantParams = self.params  # type: ignore[assignment]
        ppd = setup.screen.px_per_deg
        period, _ = grating_geometry(ppd, p.spatial_freq_cpd, p.snap_period_to_pixels)
        n_frames, _ = timing(60.0, p.cycle_hz, 4)
        size = max(period, int(round(p.patch_size_dva * ppd)))
        levels = sorted(p.test_levels_cd_m2)
        picks = [(levels[0], "lowest"), (levels[len(levels) // 2], "middle"),
                 (levels[-1], "highest")]
        views = []
        for level, label in picks:
            spec = self._spec(level, 1, 0, period, size)
            stim = make_cycle(setup.display, setup.screen, spec, p.colour_space(), p.fix(),
                              n_frames)
            views.append(DemoView(
                name=f"{p.test_colour} {level:g} cd/m2 ({label})",
                caption=(f"{p.test_colour}/{p.reference_colour} at {level:g} vs "
                         f"{p.reference_cd_m2:g} cd/m2; steps rightward. Assumes 60 Hz."),
                draw=lambda t, s=stim: s.draw()))
        return views
