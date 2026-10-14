"""Experiment 1's adjustment measures (p. 1563 and notes 6 and 9; Fig. 1C).

``motion-null``: the colour grating (40%) and the luminance grating turn in opposite
directions; the observer sets the luminance contrast at which the global rotation is
nulled, "without paying attention to the individual features of the two gratings".

``thresholds``: the luminance contrast at which the drifting (2.0 Hz) luminance grating
is just noticed (presence) or its direction just seen (direction), alone and with the
40% colour grating superimposed, and the colour contrast at which the colour grating
alone is just visible. Each threshold is the mean of four settings, "starting twice from
suprathreshold values and twice from subthreshold values".
"""

from __future__ import annotations

from typing import Literal

from alhazen import TrialSetup
from alhazen.paradigms.base import Condition
from alhazen.paradigms.config import SchedulerConfig
from pydantic import Field

from cavanagh1992.adjust import AdjustParams, AdjustTask, Knob
from cavanagh1992.common import PROJECT, TrackedDisplayParams, random_phase
from cavanagh1992.scene import Component, Ring, Scene


class _AdjustOnDisplay(AdjustParams, TrackedDisplayParams):
    contrast_step: float = Field(1.03, gt=1.0)
    contrast_limits: tuple[float, float] = (0.0005, 0.45)
    start_above: float = 0.30
    start_below: float = 0.01


class MotionNullParams(_AdjustOnDisplay):
    paradigm: SchedulerConfig = SchedulerConfig(kind="adjustment", n_per_condition=1,
                                                shuffle=False)


class ThresholdParams(_AdjustOnDisplay):
    criterion: Literal["presence", "direction"] = "presence"
    start_above: float = 0.20
    start_below: float = 0.001
    contrast_step: float = Field(1.05, gt=1.0)
    paradigm: SchedulerConfig = SchedulerConfig(kind="adjustment", n_per_condition=1,
                                                shuffle=False)


def _scene(p: TrackedDisplayParams, comps: list[Component]) -> Scene:
    return Scene(rings=[Ring(p.annulus_inner_dva, p.annulus_outer_dva, comps)],
                 color=p.color_model(p.k()), bullseye_radius_dva=p.bullseye_radius_dva,
                 bullseye_rings=p.bullseye_rings, pointer_geometry=p.pointer_geometry())


def _contrast_knob(p: _AdjustOnDisplay, scene: Scene, comp: Component, start: str,
                   record: dict, value_key: str) -> Knob:
    comp.contrast = p.start_above if start == "above" else p.start_below

    def get() -> float:
        return comp.contrast

    def set_(c: float) -> None:
        comp.contrast = c

    return Knob(scene=scene, get=get, set_=set_, step=p.contrast_step, scale="log",
                lo=p.contrast_limits[0], hi=p.contrast_limits[1],
                record={**record, "start": start}, value_key=value_key)


class MotionNullTask(AdjustTask):
    name = "motion-null"
    params_model = MotionNullParams
    instructions_section = "motion-null"

    @classmethod
    def default_params(cls):
        return PROJECT / "configs" / "motion-null.yaml"

    def check_display(self) -> None:
        p = self.params
        p.color_model(1.0).check_headroom(p.contrast_limits[1], p.color_contrast)

    def conditions(self, rng):
        return [Condition({"start": s, "direction": d})
                for s in ("above", "below") for d in (1, -1)]

    def knob(self, setup: TrialSetup) -> Knob:
        p = self.params
        d = int(setup.condition.params["direction"])
        color = Component("color", p.color_contrast, p.n_cycles, p.rate_hz, d,
                          random_phase(setup.rng))
        lum = Component("luminance", 0.0, p.n_cycles, p.rate_hz, -d, random_phase(setup.rng))
        return _contrast_knob(p, _scene(p, [color, lum]), lum, setup.condition.params["start"],
                              {"color_direction": d, "color_contrast": p.color_contrast,
                               "k": p.k()}, "null_contrast")


# The cells of Fig. 1C plus note 9's colour threshold, in the paper's order: the
# luminance grating alone, then with the colour grating superimposed; colour alone
# (presence only: the paper gives no colour direction threshold).
CELLS = {
    "presence": [("luminance", "none"), ("luminance", "color"), ("color", "none")],
    "direction": [("luminance", "none"), ("luminance", "color")],
}
STARTS = ("above", "below", "above", "below")


class ThresholdTask(AdjustTask):
    name = "thresholds"
    params_model = ThresholdParams
    instructions_section = "thresholds"

    @classmethod
    def default_params(cls):
        return PROJECT / "configs" / "thresholds-presence.yaml"

    def instructions(self):
        from cavanagh1992.common import instructions_for

        return instructions_for(f"thresholds-{self.params.criterion}")

    def check_display(self) -> None:
        p = self.params
        p.color_model(1.0).check_headroom(p.contrast_limits[1], p.color_contrast)
        p.color_model(1.0).check_headroom(0.0, p.contrast_limits[1])

    def conditions(self, rng):
        return [Condition({"grating": g, "mask": m, "start": s, "setting": i + 1})
                for g, m in CELLS[self.params.criterion] for i, s in enumerate(STARTS)]

    def knob(self, setup: TrialSetup) -> Knob:
        p = self.params
        c = setup.condition.params
        d = int(setup.rng.choice([1, -1]))
        test = Component(c["grating"], 0.0, p.n_cycles, p.rate_hz, d, random_phase(setup.rng))
        comps = [test]
        if c["mask"] == "color":
            comps.append(Component("color", p.color_contrast, p.n_cycles, p.rate_hz, -d,
                                   random_phase(setup.rng)))
        record = {"criterion": p.criterion, "grating": c["grating"], "mask": c["mask"],
                  "setting_number": c["setting"], "direction": d, "k": p.k()}
        return _contrast_knob(p, _scene(p, comps), test, c["start"], record, "threshold")
