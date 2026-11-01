"""Contrast threshold by adjustment: the paper's own method (Campbell & Robson, 1968, p. 553).

"For making measurements of contrast threshold the modulating voltage was switched on and
off at 0.5 c/s so that the pattern was periodically introduced and removed without any
change in the mean luminance ... Contrast thresholds were determined by the subject
adjusting the contrast of a grating of a given spatial frequency until the pattern was
barely detectable. Either five or ten observations were made for each threshold."

One trial is one setting: the field at its mean (corner marks show where it is), then the
grating switching on and off (on for half of each 2-s cycle) while the observer turns the
contrast with the up/down arrow keys or a scroll wheel, and presses SPACE when it is
barely detectable. The setting and the realised contrast of the image shown at that
setting are recorded.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from alhazen import Condition, Duration, Task, TrialPlan, TrialSetup, outcomes
from alhazen.core.events import EventSchema
from alhazen.paradigms.config import SchedulerConfig

from campbell_robson1968.common import PROJECT, CampbellRobsonParams, cells, check_geometry
from campbell_robson1968.grating import GratingSpec
from campbell_robson1968.phases import KnobAdjustment, Present
from campbell_robson1968.stimuli import FlickerGrating, make_grating, make_marks, make_mean_field


class CsfAdjustmentParams(CampbellRobsonParams):
    flicker_period: Duration = Duration(ms=2000)
    flicker_on: Duration = Duration(ms=1000)
    knob_step_log10: float = 0.05
    contrast_min: float = 0.0005
    contrast_max: float = 0.9
    start_log10_min: float = -2.0
    start_log10_max: float = -0.5
    adjust_timeout: Duration = Duration(ms=120000)
    paradigm: SchedulerConfig = SchedulerConfig(kind="adjustment", n_per_condition=5)


class CsfAdjustmentTask(Task):
    name = "csf-adjustment"
    events = EventSchema(("FIX_ON", "ADJUST_START", "RESPONSE"))
    outcomes = outcomes(
        SET=dict(completed=True, success=True),
        TIMEOUT=dict(completed=False),
    )
    params_model = CsfAdjustmentParams

    def __init__(self, params: CsfAdjustmentParams) -> None:
        super().__init__(params)
        if not params.flicker_on.ms or not params.flicker_period.ms:
            raise ValueError("flicker_on and flicker_period are given in ms")
        if not 0 < params.flicker_on.ms < params.flicker_period.ms:
            raise ValueError("flicker_on must be shorter than flicker_period")
        if not 0 < params.contrast_min < params.contrast_max <= 1.0 / params.quantised_mean() - 1:
            raise ValueError("need 0 < contrast_min < contrast_max <= what the mean allows")
        self._cells = cells(params)
        self._geometry: dict[str, float] | None = None

    @classmethod
    def default_params(cls) -> Path:
        return PROJECT / "configs" / "adjustment.yaml"

    def instructions(self) -> str | None:
        return (PROJECT / "instructions-adjustment.md").read_text(encoding="utf-8")

    def conditions(self, rng: np.random.Generator) -> list[Condition]:
        return [Condition({"cell": name}) for name in self._cells]

    def build_trial(self, setup: TrialSetup) -> TrialPlan:
        p: CsfAdjustmentParams = self.params  # type: ignore[assignment]
        hz = setup.refresh_rate_hz
        screen = setup.screen
        if self._geometry is None:
            self._geometry = check_geometry(p, screen.px_per_deg, screen.width_px, screen.height_px)
        cell = str(setup.condition.params["cell"])
        waveform, sf = self._cells[cell]
        rng = setup.rng
        start = float(10.0 ** rng.uniform(p.start_log10_min, p.start_log10_max))
        start = min(max(start, p.contrast_min), p.contrast_max)
        phase = float(rng.uniform(0.0, 360.0)) if p.random_phase else 0.0
        seed = int(rng.integers(0, 2**31 - 1))
        mean = p.quantised_mean()
        spec = GratingSpec(
            sf_cpd=sf,
            contrast=start,
            field_dva=p.field_dva,
            mean=mean,
            phase_deg=phase,
            orientation_deg=p.orientation_deg,
            waveform=waveform,
        )
        on_frames = max(1, int(round(p.flicker_on.seconds(hz) * hz)))
        period_frames = max(on_frames + 1, int(round(p.flicker_period.seconds(hz) * hz)))
        flicker = FlickerGrating(
            make_grating(
                setup.display, screen, spec, bits=p.display_bits, dither=p.dither, seed=seed
            ),
            on_frames,
            period_frames,
        )

        def extra() -> dict[str, Any]:
            return {
                "contrast_set": flicker.contrast,
                **flicker.realised.as_record(),
                "frames_grating_on": flicker.frames_on,
                "frames_shown": flicker.frame,
            }

        o = self.outcomes
        record = {
            "cell": cell,
            "sf_cpd": sf,
            "waveform": waveform,
            "phase_deg": phase,
            "orientation_deg": p.orientation_deg,
            "field_dva": p.field_dva,
            "mean_luminance": mean,
            "display_bits": p.display_bits,
            "dither": p.dither,
            "noise_seed": seed,
            "px_per_deg": screen.px_per_deg,
            "flicker_on_frames": on_frames,
            "flicker_period_frames": period_frames,
        }
        return TrialPlan(
            phases=[
                Present(
                    ["field", "marks"],
                    p.fixation_duration.seconds(hz),
                    onset_event="FIX_ON",
                    payload={"cell": cell, "sf_cpd": sf, "waveform": waveform},
                ),
                KnobAdjustment(
                    lambda: flicker.contrast,
                    flicker.set_contrast,
                    step=10.0**p.knob_step_log10,
                    lo=p.contrast_min,
                    hi=p.contrast_max,
                    stimulus_keys=["field", "flicker", "marks"],
                    on_commit=o["SET"],
                    on_timeout=o["TIMEOUT"],
                    timeout_s=p.adjust_timeout.seconds(hz),
                    value_record_key="setting",
                    extra_record=extra,
                    start_payload={"cell": cell, "sf_cpd": sf, "waveform": waveform},
                ),
            ],
            stimuli={
                "field": make_mean_field(setup.display, screen, mean),
                "flicker": flicker,
                "marks": make_marks(
                    setup.display,
                    screen,
                    field_dva=p.field_dva,
                    gap_dva=p.marks_gap_dva,
                    arm_dva=p.marks_arm_dva,
                    width_dva=p.marks_width_dva,
                    luminance=p.marks_luminance,
                ),
            },
            record=record,
        )

    def demo_views(self, setup: Any) -> list[Any]:
        from campbell_robson1968.demo import grating_views

        return grating_views(self.params, setup)

    def simulation(self, seed: int):
        from alhazen.modes.simulation import Simulation

        from campbell_robson1968.simulate import SimulatedAdjuster

        obs = SimulatedAdjuster(seed=seed)
        return Simulation(response=obs, describe=obs.describe())
