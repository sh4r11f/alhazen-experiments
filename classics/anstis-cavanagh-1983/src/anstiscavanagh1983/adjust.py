"""Experiments 2 and 3: minimum motion and minimum flicker by adjustment.

Anstis & Cavanagh (1983, pp. 157-161). Each colour (red, green, blue) is matched to an
achromatic grey of 13.6 cd/m2. Minimum motion: the four-stroke cycle with test/grey bars
interleaved with light and dark "pink" (the mixture of the two) at 12.5% contrast, at
15 cycles per second (one TV frame per grating) over 0.625-5 c/deg (Experiment 2), or at
2.5 c/deg over 0.9375-15 Hz (Experiment 3). Minimum flicker: a square-wave grating whose
bars swap between the two colours (two-stroke counterphase, 15 Hz: two TV frames each),
and the standard 2-deg uniform field flickering between them. "The subject adjusted the
luminance of the coloured bars by means of a joystick control until he saw minimum
motion or minimum flicker ... six readings were taken for each datum point" (p. 159).

Here the knob is the scroll wheel or the up/down arrow keys (multiplicative steps on the
test luminance), SPACE commits a setting, and each condition is set three times with
the quarter-cycle steps going rightward and three times leftward.
"""

from __future__ import annotations

import itertools
from typing import Any, Literal

from alhazen import Duration, TrialPlan, TrialSetup, outcomes
from alhazen.core.events import EventSchema
from alhazen.paradigms.base import Condition
from alhazen.paradigms.config import SchedulerConfig
from pydantic import Field, model_validator

from anstiscavanagh1983.color import ColourSpace
from anstiscavanagh1983.common import (
    PROJECT,
    Colour,
    DisplayParams,
    EquiluminanceTask,
    grating_geometry,
    log_uniform,
    timing,
)
from anstiscavanagh1983.phases import KnobAdjustment, Present
from anstiscavanagh1983.render import FixationStim, make_cycle
from anstiscavanagh1983.stimulus import Spec

SETTING = "test_cd_m2"


def max_test_cd(space: ColourSpace, test: str, ref: str, ref_cd: float, contrast: float,
                with_mixture: bool, mix: str = "additive") -> float:
    """The highest test luminance every stroke can show: the test bar itself and, for the
    four-stroke cycle, the light mixture bar. With ``additive`` mixing a light bar is
    (1 + c) * (test + reference) / 2 on every pixel; with ``line_dither`` its test-colour
    rows carry the test colour itself scaled by (1 + c) (stimulus.stroke_luminance), so
    the cap is lower by that factor."""
    st, sr, mx = space.shares(test), space.shares(ref), space.photometry.max_cd_m2
    hi = float("inf")
    for g in range(3):
        if st[g] > 0:
            hi = min(hi, mx[g] / st[g])
            if with_mixture:
                if mix == "line_dither":
                    hi = min(hi, mx[g] / ((1.0 + contrast) * st[g]))
                else:
                    hi = min(hi, (2.0 * mx[g] / (1.0 + contrast) - sr[g] * ref_cd) / st[g])
    return hi


class AdjustParams(DisplayParams):
    reference_colour: Colour = "grey"
    reference_cd_m2: float = Field(13.6, gt=0)
    test_colours: list[Colour] = ["red", "green", "blue"]
    spatial_freqs_cpd: list[float] = [0.625, 1.25, 2.5, 5.0]
    rates_hz: list[float] = [15.0]
    start_range: tuple[float, float] = (0.7, 1.3)
    step_factor: float = Field(1.01, gt=1.0)
    limits: tuple[float, float] = (0.25, 4.0)
    adjust_timeout: Duration = Duration(ms=60000)
    paradigm: SchedulerConfig = SchedulerConfig(kind="adjustment", n_per_condition=3)

    @model_validator(mode="after")
    def _ranges(self) -> AdjustParams:
        lo, hi = self.limits
        a, b = self.start_range
        if not 0 < lo <= a < b <= hi:
            raise ValueError("need 0 < limits[0] <= start_range[0] < start_range[1] <= limits[1]")
        if self.reference_colour in self.test_colours:
            raise ValueError("reference_colour must not be one of test_colours")
        return self


class MotionAdjustParams(AdjustParams):
    interleave_contrast: float = Field(0.125, ge=0, lt=1)
    interleave_mix: Literal["additive", "line_dither"] = "additive"
    dither_rows: int = Field(2, ge=1)


class FlickerAdjustParams(AdjustParams):
    field: Literal["uniform", "counterphase"] = "uniform"


ADJUST_EVENTS = EventSchema(("FIX_ON", "ADJUST_START", "RESPONSE"))
ADJUST_OUTCOMES = outcomes(SET=dict(completed=True, success=True), TIMEOUT=dict(completed=False))


class _AdjustBase(EquiluminanceTask):
    events = ADJUST_EVENTS
    outcomes = ADJUST_OUTCOMES
    layout: str = "four_stroke"

    def _mixture(self) -> bool:
        return self.layout == "four_stroke"

    def _contrast(self) -> float:
        return float(getattr(self.params, "interleave_contrast", 0.0))

    def _mix(self) -> str:
        return str(getattr(self.params, "interleave_mix", "additive"))

    def _range(self, colour: str) -> tuple[float, float]:
        """Knob limits for ``colour``, in cd/m2: the params' limits times the reference,
        capped by what the display can show."""
        p: AdjustParams = self.params  # type: ignore[assignment]
        cap = max_test_cd(p.colour_space(), colour, p.reference_colour, p.reference_cd_m2,
                          self._contrast(), self._mixture(), self._mix())
        lo, hi = p.limits[0] * p.reference_cd_m2, min(p.limits[1] * p.reference_cd_m2, cap)
        if hi < p.start_range[1] * p.reference_cd_m2:
            raise ValueError(
                f"this display reaches {colour} only up to {cap:.2f} cd/m2 here, below the top "
                f"of start_range ({p.start_range[1] * p.reference_cd_m2:.2f}); lower "
                f"reference_cd_m2 or the contrast, or use a brighter display")
        return lo, hi

    def __init__(self, params: Any) -> None:
        super().__init__(params)
        p: AdjustParams = self.params  # type: ignore[assignment]
        for c in p.test_colours:
            self._range(c)
        p.colour_space().levels(p.colour_space().gun_luminance(p.reference_colour,
                                                                p.reference_cd_m2))
        if self._mixture() and self._mix() == "line_dither":
            # The reference rows of a light line-dither bar are the reference at (1 + c).
            p.colour_space().levels(p.colour_space().gun_luminance(
                p.reference_colour, p.reference_cd_m2 * (1.0 + self._contrast())))

    def conditions(self, rng):
        p: AdjustParams = self.params  # type: ignore[assignment]
        sfs = p.spatial_freqs_cpd if self.layout != "uniform" else [0.0]
        return [Condition({"test_colour": c, "spatial_freq_cpd": float(sf),
                           "rate_hz": float(r), "step": s})
                for c, sf, r, s in itertools.product(p.test_colours, sfs, p.rates_hz, (1, -1))]

    def build_trial(self, setup: TrialSetup) -> TrialPlan:
        p: AdjustParams = self.params  # type: ignore[assignment]
        hz = setup.refresh_rate_hz
        ppd = setup.screen.px_per_deg
        cond = setup.condition.params
        colour = str(cond.get("test_colour", p.test_colours[0]))
        sf_req = float(cond.get("spatial_freq_cpd", p.spatial_freqs_cpd[0]))
        rate = float(cond.get("rate_hz", p.rates_hz[0]))
        step = int(cond.get("step", 1))
        strokes = 4 if self.layout == "four_stroke" else 2
        if self.layout == "uniform":
            period, sf = 4, 0.0
        else:
            period, sf = grating_geometry(ppd, sf_req, p.snap_period_to_pixels)
        n_frames, cycle = timing(hz, rate, strokes)
        size = max(period, int(round(p.patch_size_dva * ppd)))
        offset = int(setup.rng.integers(0, period))
        lo, hi = self._range(colour)
        start = min(hi, max(lo, log_uniform(setup.rng, *(f * p.reference_cd_m2
                                                           for f in p.start_range))))
        space = p.colour_space()
        spec = Spec(self.layout, colour, p.reference_colour, start,  # type: ignore[arg-type]
                    p.reference_cd_m2, size, period, step, offset, self._contrast(),
                    getattr(p, "interleave_mix", "additive"), getattr(p, "dither_rows", 2),
                    disc=self.layout == "uniform")
        stim = make_cycle(setup.display, setup.screen, spec, space, p.fix(), n_frames)
        fixation = FixationStim(setup.display, setup.screen, size, ppd, p.fix())
        state = {"v": start}

        def get() -> float:
            return state["v"]

        def set_(v: float) -> None:
            state["v"] = v
            stim.set_spec(stim.spec.with_test(v))

        record = {**self.base_record(p), "task": self.name, "test_colour": colour,
                  "layout": self.layout, "step": step, "offset_px": offset,
                  "period_px": period if self.layout != "uniform" else None,
                  "spatial_freq_cpd": sf_req, "spatial_freq_effective_cpd": sf,
                  "rate_hz": rate, "cycle_hz_effective": cycle, "frames_per_stroke": n_frames,
                  "interleave_contrast": self._contrast()}
        payload = {"task": self.name, "test_colour": colour,
                   "reference_colour": p.reference_colour,
                   "reference_cd_m2": p.reference_cd_m2, "spatial_freq_cpd": sf,
                   "rate_hz": cycle, "layout": self.layout}
        return TrialPlan(
            phases=[
                Present(["fixation"], p.fixation_duration.seconds(hz), onset_event="FIX_ON",
                        payload=payload),
                KnobAdjustment(get, set_, step=p.step_factor, scale="log", lo=lo, hi=hi,
                               stimulus_keys=["stimulus"], on_commit=self.outcomes["SET"],
                               on_timeout=self.outcomes["TIMEOUT"],
                               timeout_s=p.adjust_timeout.seconds(hz),
                               value_record_key=SETTING, start_payload=payload),
            ],
            stimuli={"stimulus": stim, "fixation": fixation},
            record=record,
        )

    def demo_views(self, setup: Any) -> list[Any]:
        from alhazen.modes.demo import DemoView

        p: AdjustParams = self.params  # type: ignore[assignment]
        ppd = setup.screen.px_per_deg
        views = []
        for colour in p.test_colours:
            if self.layout == "uniform":
                period = 4
            else:
                period, _ = grating_geometry(ppd, p.spatial_freqs_cpd[0], p.snap_period_to_pixels)
            strokes = 4 if self.layout == "four_stroke" else 2
            n_frames, _ = timing(60.0, p.rates_hz[0], strokes)
            size = max(period, int(round(p.patch_size_dva * ppd)))
            spec = Spec(self.layout, colour, p.reference_colour,  # type: ignore[arg-type]
                        p.reference_cd_m2, p.reference_cd_m2, size, period, 1, 0,
                        self._contrast(), getattr(p, "interleave_mix", "additive"),
                        getattr(p, "dither_rows", 2), disc=self.layout == "uniform")
            stim = make_cycle(setup.display, setup.screen, spec, p.colour_space(), p.fix(),
                              n_frames)
            views.append(DemoView(
                name=f"{colour} vs {p.reference_colour}",
                caption=(f"{self.name}: {colour} at {p.reference_cd_m2:g} cd/m2 against "
                         f"{p.reference_colour} {p.reference_cd_m2:g} cd/m2. Assumes 60 Hz."),
                draw=lambda t, s=stim: s.draw()))
        return views


class MinMotionAdjustTask(_AdjustBase):
    name = "min-motion-adjust"
    params_model = MotionAdjustParams
    instructions_section = "min-motion-adjust"
    layout = "four_stroke"

    @classmethod
    def default_params(cls):
        return PROJECT / "configs" / "adjust-spatial.yaml"


class MinFlickerAdjustTask(_AdjustBase):
    name = "min-flicker-adjust"
    params_model = FlickerAdjustParams
    instructions_section = "min-flicker-adjust"

    @classmethod
    def default_params(cls):
        return PROJECT / "configs" / "flicker-uniform.yaml"

    def __init__(self, params: Any) -> None:
        self.layout = "uniform" if params.field == "uniform" else "counterphase"
        super().__init__(params)
