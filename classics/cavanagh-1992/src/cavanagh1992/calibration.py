"""Equiluminance, set by the observer: the k every colour stimulus is drawn with.

``equiluminance-speed`` is the paper's own criterion (p. 1563, note 10): "the relative
modulations of red and green were set to approximate equiluminance with the use of a
minimum apparent speed criterion". The colour grating alone turns at 2.0 Hz and the
observer moves k until it looks slowest.

``flicker-photometry`` is heterochromatic flicker photometry, the common alternative
(NOT the paper's criterion): the annulus alternates between the red-weighted and the
green-weighted state of the same colour modulation, and the observer moves k until the
flicker is least. Offered because it is faster to set and familiar; a session reads
whichever ``equiluminance.method`` names.

Both record ``k_setting`` (green-to-red luminance modulation ratio, 1 = photometric).
"""

from __future__ import annotations

import dataclasses

from alhazen import TrialSetup
from alhazen.paradigms.base import Condition
from alhazen.paradigms.config import SchedulerConfig
from pydantic import Field, model_validator

from cavanagh1992.adjust import AdjustParams, AdjustTask, Knob, field_scene
from cavanagh1992.common import SETTING_COLUMN, PROJECT, log_uniform, random_phase
from cavanagh1992.scene import Component, Ring


class EquiluminanceParams(AdjustParams):
    k_start_range: tuple[float, float] = (0.6, 1.6)
    k_step: float = Field(1.02, gt=1.0)
    k_limits: tuple[float, float] = (0.25, 4.0)
    paradigm: SchedulerConfig = SchedulerConfig(kind="adjustment", n_per_condition=3)

    @model_validator(mode="after")
    def _ranges(self) -> EquiluminanceParams:
        lo, hi = self.k_limits
        a, b = self.k_start_range
        if not 0 < lo <= a < b <= hi:
            raise ValueError("need 0 < k_limits[0] <= k_start_range[0] < k_start_range[1] <= k_limits[1]")
        return self


class FlickerParams(EquiluminanceParams):
    flicker_hz: float = Field(15.0, gt=0)
    paradigm: SchedulerConfig = SchedulerConfig(kind="adjustment", n_per_condition=6)


class _KTask(AdjustTask):
    def check_display(self) -> None:
        p = self.params
        for k in p.k_limits:
            p.color_model(k).check_headroom(0.0, p.color_contrast)

    def _k_knob(self, setup: TrialSetup, comp: Component, record: dict) -> Knob:
        p = self.params
        ring = Ring(p.annulus_inner_dva, p.annulus_outer_dva, [comp])
        scene = field_scene(p, [ring], 1.0)
        scene.rings = [ring]  # the field scene's geometry, with the component in its ring
        state = {"k": log_uniform(setup.rng, *p.k_start_range)}

        def get() -> float:
            return state["k"]

        def set_(k: float) -> None:
            state["k"] = k
            # The colour model is immutable; swap in one with the new k.
            scene.color = dataclasses.replace(scene.color, k=k)

        set_(state["k"])
        return Knob(scene=scene, get=get, set_=set_, step=p.k_step, scale="log",
                    lo=p.k_limits[0], hi=p.k_limits[1], record=record, value_key=SETTING_COLUMN)


class EquiluminanceSpeedTask(_KTask):
    name = "equiluminance-speed"
    params_model = EquiluminanceParams
    instructions_section = "equiluminance-speed"

    @classmethod
    def default_params(cls):
        return PROJECT / "configs" / "equiluminance-speed.yaml"

    def conditions(self, rng):
        return [Condition({"direction": d}) for d in (1, -1)]

    def knob(self, setup: TrialSetup) -> Knob:
        p = self.params
        d = int(setup.condition.params.get("direction", 1))
        comp = Component("color", p.color_contrast, p.n_cycles, p.rate_hz, d,
                         random_phase(setup.rng))
        return self._k_knob(setup, comp, {"direction": d, "color_contrast": p.color_contrast,
                                          "rate_hz": p.rate_hz})


class FlickerPhotometryTask(_KTask):
    name = "flicker-photometry"
    params_model = FlickerParams
    instructions_section = "flicker-photometry"

    @classmethod
    def default_params(cls):
        return PROJECT / "configs" / "flicker-photometry.yaml"

    def knob(self, setup: TrialSetup) -> Knob:
        p = self.params
        # Locked to whole frames: half a cycle is the nearest whole number of frames.
        half = max(1, round(setup.refresh_rate_hz / (2.0 * p.flicker_hz)))
        effective = setup.refresh_rate_hz / (2.0 * half)
        comp = Component("color", p.color_contrast, 0, effective)
        return self._k_knob(setup, comp, {"flicker_hz": effective,
                                          "color_contrast": p.color_contrast})
