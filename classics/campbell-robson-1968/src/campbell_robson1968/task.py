"""Contrast detection by two-interval forced choice (the modern behavioural version).

One trial: the corner marks show two observation intervals in turn; a stationary grating
is in one of them (chosen at random), the other shows only the uniform field at the same
mean luminance. The observer presses F if the grating was in the first interval and J if
in the second. QUEST+ (alhazen's, one estimator per cell) picks each trial's contrast;
the analysis fits a Weibull function to every completed trial of each cell and reports
the threshold and its reciprocal, the contrast sensitivity.

Campbell & Robson measured thresholds by adjustment (``adjust.py`` is that task); this
one changes the method to a criterion-free forced choice, a deviation stated in
docs/methods.md.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from alhazen import Condition, Duration, Task, TrialPlan, TrialSetup, outcomes
from alhazen.core.events import EventSchema
from alhazen.paradigms.config import QuestConfig, SchedulerConfig
from alhazen.stimuli.fixation import make_fixation
from alhazen.task import phases

from campbell_robson1968.common import (
    PROJECT,
    CampbellRobsonParams,
    cells,
    check_geometry,
)
from campbell_robson1968.grating import GratingSpec
from campbell_robson1968.phases import Present
from campbell_robson1968.stimuli import make_grating, make_marks, make_mean_field, to_signed

__all__ = ["PROJECT", "Csf2ifcParams", "Csf2ifcTask"]

KEYS = ("f", "j")  # first interval, second interval


class Csf2ifcParams(CampbellRobsonParams):
    interval_duration: Duration = Duration(ms=1000)
    isi: Duration = Duration(ms=500)
    response_timeout: Duration = Duration(ms=5000)
    feedback_duration: Duration = Duration(ms=200)
    paradigm: SchedulerConfig = SchedulerConfig(
        kind="questplus",
        quest=QuestConfig(
            parameter="log_contrast",
            intensities=[-3.0, -2.0, -1.0, 0.0],
            thresholds=[-2.0],
            interleave_by="cell",
            scale="log10",
            lower_asymptotes=[0.5],
            lapse_rates=[0.01],
        ),
    )


class Csf2ifcTask(Task):
    name = "csf-2ifc"
    events = EventSchema(
        ("FIX_ON", "INTERVAL1_ON", "ISI_ON", "INTERVAL2_ON", "RESPONSE_CUE", "RESPONSE")
    )
    outcomes = outcomes(
        CORRECT=dict(completed=True, success=True),
        WRONG=dict(completed=True, success=False),
        NO_RESPONSE=dict(completed=False),
    )
    params_model = Csf2ifcParams

    def __init__(self, params: Csf2ifcParams) -> None:
        super().__init__(params)
        q = params.paradigm.quest
        if params.paradigm.kind == "questplus" and (q is None or q.interleave_by != "cell"):
            raise ValueError("the QUEST+ block must interleave by 'cell'")
        if q is not None and max(q.intensities) > 0.0:
            raise ValueError("QUEST+ intensities are log10 contrast and must be <= 0")
        self._cells = cells(params)
        self._geometry: dict[str, float] | None = None

    @classmethod
    def default_params(cls) -> Path:
        return PROJECT / "configs" / "task.yaml"

    def instructions(self) -> str | None:
        return (PROJECT / "instructions.md").read_text(encoding="utf-8")

    def conditions(self, rng: np.random.Generator) -> list[Condition]:
        return [Condition({"cell": name}) for name in self._cells]

    def build_trial(self, setup: TrialSetup) -> TrialPlan:
        p: Csf2ifcParams = self.params  # type: ignore[assignment]
        hz = setup.refresh_rate_hz
        screen = setup.screen
        if self._geometry is None:  # every cell, on the first trial, before anything is drawn
            self._geometry = check_geometry(p, screen.px_per_deg, screen.width_px, screen.height_px)
        cell = str(setup.condition.params["cell"])
        waveform, sf = self._cells[cell]
        log_c = float(setup.condition.params["log_contrast"])
        contrast = float(min(10.0**log_c, 1.0 / p.quantised_mean() - 1.0))
        rng = setup.rng
        signal = int(rng.integers(1, 3))
        phase = float(rng.uniform(0.0, 360.0)) if p.random_phase else 0.0
        seed = int(rng.integers(0, 2**31 - 1))
        mean = p.quantised_mean()
        spec = GratingSpec(
            sf_cpd=sf,
            contrast=contrast,
            field_dva=p.field_dva,
            mean=mean,
            phase_deg=phase,
            orientation_deg=p.orientation_deg,
            waveform=waveform,
        )
        grating = make_grating(
            setup.display, screen, spec, bits=p.display_bits, dither=p.dither, seed=seed
        )
        realised = grating.realised
        o = self.outcomes
        correct_key = KEYS[signal - 1]
        keys = {k: (o["CORRECT"] if k == correct_key else o["WRONG"]) for k in KEYS}
        base = ["field", "fixation"]
        shown = {
            1: ["field", "grating", "marks", "fixation"]
            if signal == 1
            else ["field", "marks", "fixation"],
            2: ["field", "grating", "marks", "fixation"]
            if signal == 2
            else ["field", "marks", "fixation"],
        }
        info = {
            "cell": cell,
            "sf_cpd": sf,
            "waveform": waveform,
            "signal_interval": signal,
            "contrast": realised.contrast,
            "fundamental_contrast": realised.fundamental_contrast,
        }
        record: dict[str, Any] = {
            "cell": cell,
            "sf_cpd": sf,
            "waveform": waveform,
            "log_contrast": log_c,
            "contrast_requested": contrast,
            "signal_interval": signal,
            "correct_key": correct_key,
            "phase_deg": phase,
            "orientation_deg": p.orientation_deg,
            "field_dva": p.field_dva,
            "mean_luminance": mean,
            "display_bits": p.display_bits,
            "dither": p.dither,
            "noise_seed": seed,
            "px_per_deg": screen.px_per_deg,
            "interval_frames": int(round(p.interval_duration.seconds(hz) * hz)),
            "isi_frames": int(round(p.isi.seconds(hz) * hz)),
            **realised.as_record(),
        }
        return TrialPlan(
            phases=[
                Present(base, p.fixation_duration.seconds(hz), onset_event="FIX_ON", payload=info),
                Present(shown[1], p.interval_duration.seconds(hz), onset_event="INTERVAL1_ON"),
                Present(base, p.isi.seconds(hz), onset_event="ISI_ON"),
                Present(shown[2], p.interval_duration.seconds(hz), onset_event="INTERVAL2_ON"),
                phases.ResponseWindow(
                    keys=keys,
                    timeout_s=p.response_timeout.seconds(hz),
                    on_timeout=o["NO_RESPONSE"],
                    stimulus_keys=base,
                    onset_event="RESPONSE_CUE",
                ),
                phases.TrialFeedback(
                    verdict=lambda ctx: bool(ctx.outcome is not None and ctx.outcome.success),
                    then=lambda ctx: ctx.outcome or o["NO_RESPONSE"],
                    duration_s=p.feedback_duration.seconds(hz),
                    stimulus_key="fixation",
                    keep_drawing=("field",),
                ),
            ],
            stimuli={
                "field": make_mean_field(setup.display, screen, mean),
                "grating": grating,
                "marks": make_marks(
                    setup.display,
                    screen,
                    field_dva=p.field_dva,
                    gap_dva=p.marks_gap_dva,
                    arm_dva=p.marks_arm_dva,
                    width_dva=p.marks_width_dva,
                    luminance=p.marks_luminance,
                ),
                "fixation": make_fixation(
                    setup.display, screen, p.fix_size_dva, fill_color=to_signed(p.fix_luminance)
                ),
            },
            record=record,
        )

    def demo_views(self, setup: Any) -> list[Any]:
        from campbell_robson1968.demo import grating_views

        return grating_views(self.params, setup)

    def simulation(self, seed: int):
        from alhazen.modes.simulation import Simulation

        from campbell_robson1968.simulate import SimulatedObserver

        obs = SimulatedObserver(seed=seed)
        return Simulation(response=obs, describe=obs.describe())
