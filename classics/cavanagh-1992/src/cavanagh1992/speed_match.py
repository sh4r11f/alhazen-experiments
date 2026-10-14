"""Experiment 2 (p. 1564, Fig. 2): the apparent speed of a colour grating.

The outer ring holds only the colour grating (40%, 0.5 Hz), which carries a luminance
contrast that varies from trial to trial (positive: red more luminous than green). The
inner ring holds a 15% luminance grating turning the opposite way at a rate the observer
adjusts until it matches the outer ring: either the overall impression of motion
(``global``) or the rate of a pair of bars tracked with attention (``tracking``),
switching attention between the rings as often as needed.
"""

from __future__ import annotations

from typing import Literal

from alhazen import Duration, TrialSetup
from alhazen.paradigms.base import Condition
from alhazen.paradigms.config import SchedulerConfig
from pydantic import Field, model_validator

from cavanagh1992.adjust import AdjustParams, AdjustTask, Knob
from cavanagh1992.common import PROJECT, TrackedDisplayParams, log_uniform, random_phase
from cavanagh1992.scene import Component, Ring, Scene


class SpeedMatchParams(AdjustParams, TrackedDisplayParams):
    judgment: Literal["global", "tracking"] = "global"
    outer_rate_hz: float = Field(0.5, gt=0)
    comparison_contrast: float = Field(0.15, gt=0)
    comparison_cycles: int = Field(8, ge=1)
    inner_ring_dva: tuple[float, float] = (1.6, 3.6)
    luminance_contrasts: tuple[float, ...] = (-0.20, -0.15, -0.10, -0.05, 0.0, 0.05, 0.10,
                                              0.15, 0.20)
    luminance_reference: Literal["photometric", "observer"] = "photometric"
    rate_start_range: tuple[float, float] = (0.2, 1.0)
    rate_step: float = Field(1.03, gt=1.0)
    rate_limits: tuple[float, float] = (0.05, 3.0)
    adjust_timeout: Duration = Duration(ms=120000)
    paradigm: SchedulerConfig = SchedulerConfig(kind="adjustment", n_per_condition=3)

    @model_validator(mode="after")
    def _inner_ring_fits(self) -> SpeedMatchParams:
        a, b = self.inner_ring_dva
        if not self.bullseye_radius_dva <= a < b <= self.annulus_inner_dva:
            raise ValueError("inner_ring_dva must lie between the bull's-eye and the annulus")
        if self.luminance_reference == "observer" and self.equiluminance.source == "photometric":
            raise ValueError("luminance_reference observer needs equiluminance.source "
                             "calibration or fixed: the observer's k is the reference")
        return self


class SpeedMatchTask(AdjustTask):
    name = "speed-match"
    params_model = SpeedMatchParams
    instructions_section = "speed-match"

    @classmethod
    def default_params(cls):
        return PROJECT / "configs" / "speed-global.yaml"

    def instructions(self):
        from cavanagh1992.common import instructions_for

        return instructions_for(f"speed-match-{self.params.judgment}")

    def check_display(self) -> None:
        p = self.params
        p.color_model(1.0).check_headroom(max(map(abs, p.luminance_contrasts)), p.color_contrast)

    def conditions(self, rng):
        return [Condition({"luminance_contrast": c}) for c in self.params.luminance_contrasts]

    def knob(self, setup: TrialSetup) -> Knob:
        p = self.params
        lc = float(setup.condition.params["luminance_contrast"])
        d = int(setup.rng.choice([1, -1]))
        phase = random_phase(setup.rng)
        k = 1.0 if p.luminance_reference == "photometric" else p.k()
        # The luminance contrast rides on the colour grating, in phase with its red bars.
        outer = [Component("color", p.color_contrast, p.n_cycles, p.outer_rate_hz, d, phase),
                 Component("luminance", lc, p.n_cycles, p.outer_rate_hz, d, phase)]
        comparison = Component("luminance", p.comparison_contrast, p.comparison_cycles,
                               log_uniform(setup.rng, *p.rate_start_range), -d,
                               random_phase(setup.rng))
        scene = Scene(rings=[Ring(p.annulus_inner_dva, p.annulus_outer_dva, outer),
                             Ring(*p.inner_ring_dva, [comparison])],
                      color=p.color_model(k), bullseye_radius_dva=p.bullseye_radius_dva,
                      bullseye_rings=p.bullseye_rings, pointer_geometry=p.pointer_geometry())

        def get() -> float:
            return comparison.rate_hz

        def set_(hz: float) -> None:
            comparison.rate_hz = hz

        record = {"judgment": p.judgment, "luminance_contrast": lc, "outer_rate_hz":
                  p.outer_rate_hz, "outer_direction": d, "luminance_reference":
                  p.luminance_reference, "k": k}
        return Knob(scene=scene, get=get, set_=set_, step=p.rate_step, scale="log",
                    lo=p.rate_limits[0], hi=p.rate_limits[1], record=record,
                    value_key="matched_rate_hz")
