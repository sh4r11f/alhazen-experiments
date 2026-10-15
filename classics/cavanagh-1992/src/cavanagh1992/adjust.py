"""The method-of-adjustment tasks share one trial shape: the bull's-eye on the mean
field, then the stimulus, with a knob (scroll wheel or up/down arrows) on one setting
until SPACE commits it. Each task says what the stimulus is and what the knob turns.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
from alhazen import Duration, TrialPlan, TrialSetup, outcomes
from alhazen.core.events import EventSchema
from alhazen.modes.demo import DemoView

from cavanagh1992.common import CavanaghParams, CavanaghTask, PointerParams
from cavanagh1992.phases import KnobAdjustment, Present
from cavanagh1992.scene import PointerGeometry, Ring, Scene
from cavanagh1992.stimuli import make_scene_stimulus

ADJUST_OUTCOMES = outcomes(
    SET=dict(completed=True, success=True),
    TIMEOUT=dict(completed=False),
)
ADJUST_EVENTS = EventSchema(("FIX_ON", "ADJUST_START", "RESPONSE"))


class AdjustParams(CavanaghParams):
    adjust_timeout: Duration = Duration(ms=60000)


@dataclass
class Knob:
    """What the knob turns: the scene it drives, how to read and write the setting,
    and the step and limits."""

    scene: Scene
    get: Any
    set_: Any
    step: float
    scale: str
    lo: float
    hi: float
    record: dict[str, Any] = field(default_factory=dict)
    value_key: str = "setting"


def field_scene(p: CavanaghParams, rings: list[Ring], k: float = 1.0) -> Scene:
    """The same rings with nothing in them: the mean field and the bull's-eye."""
    return Scene(rings=[Ring(r.inner_dva, r.outer_dva) for r in rings], color=p.color_model(k),
                 bullseye_radius_dva=p.bullseye_radius_dva, bullseye_rings=p.bullseye_rings,
                 pointer_geometry=_pointer_geometry(p))


def _pointer_geometry(p: CavanaghParams) -> PointerGeometry:
    pp = getattr(p, "pointer", PointerParams())
    return PointerGeometry(pp.inner_dva, pp.outer_dva, pp.width_inner_dva, pp.width_outer_dva)


class AdjustTask(CavanaghTask):
    events = ADJUST_EVENTS
    outcomes = ADJUST_OUTCOMES

    def knob(self, setup: TrialSetup) -> Knob:
        raise NotImplementedError

    def check_display(self) -> None:
        """Refuse, when the task is built, settings this display cannot show."""

    def __init__(self, params: Any) -> None:
        super().__init__(params)
        self.check_display()

    def build_trial(self, setup: TrialSetup) -> TrialPlan:
        p = self.params
        hz = setup.refresh_rate_hz
        knob = self.knob(setup)
        stimulus = make_scene_stimulus(setup.display, setup.screen, knob.scene)
        fixation = make_scene_stimulus(setup.display, setup.screen,
                                       field_scene(p, knob.scene.rings, knob.scene.color.k))
        payload = {"task": self.name, **knob.record}
        return TrialPlan(
            phases=[
                Present(["fixation"], p.fixation_duration.seconds(hz), onset_event="FIX_ON"),
                KnobAdjustment(knob.get, knob.set_, step=knob.step, scale=knob.scale,
                               lo=knob.lo, hi=knob.hi, stimulus_keys=["stimulus"],
                               on_commit=self.outcomes["SET"], on_timeout=self.outcomes["TIMEOUT"],
                               timeout_s=p.adjust_timeout.seconds(hz),
                               value_record_key=knob.value_key, start_payload=payload),
            ],
            stimuli={"stimulus": stimulus, "fixation": fixation},
            record=dict(knob.record),
        )

    def demo_views(self, setup: Any) -> list[Any]:
        from alhazen.paradigms.base import Condition
        from alhazen.task.plan import TrialSetup as TS

        conds = self.conditions(setup.rng) or [Condition({})]
        fake = TS(cfg=None, screen=setup.screen, display=setup.display, rng=setup.rng,  # type: ignore[arg-type]
                  refresh_rate_hz=60.0, trial_index=1, attempt=1, condition=conds[0])
        knob = self.knob(fake)
        return [scene_view(setup, knob.scene, self.name, self.instructions_section)]


def scene_view(setup: Any, scene: Scene, name: str, caption: str) -> Any:
    stim = make_scene_stimulus(setup.display, setup.screen, scene)
    last = {"t": 0.0}

    def draw(t: float) -> None:
        dt = max(0.0, t - last["t"]) if t >= last["t"] else 0.0
        last["t"] = t
        stim.update(dt)
        stim.draw()

    return DemoView(name=name, caption=caption, draw=draw)


def directions() -> list[int]:
    return [1, -1]


def rng_direction(rng: np.random.Generator) -> int:
    return int(rng.choice([1, -1]))
