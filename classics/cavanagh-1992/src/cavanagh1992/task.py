"""Experiment 1's tracking task (Cavanagh 1992, pp. 1563-1564; Fig. 1A, B).

A colour grating (40% colour contrast) and a luminance grating, both eight-cycle
sinusoids, are superimposed in an annulus 4.0 to 8.4 deg from the centre and turn in
opposite directions at 2.0 Hz (0.25 rev/s), the colour grating's direction random on
each trial. The luminance contrast is one of eight values spaced uniformly from 5% to an
upper value set for each observer (25 to 45%).

One trial: the observer fixates the central bull's-eye; a pointer appears beside a pair
of (opposite) bars of the target grating and turns with them for 1.0 s; it goes off and
the observer keeps tracking the pair with attention for 1.5 s; a test pointer appears for
240 ms, aimed at the tracked pair or at an adjacent pair with the same contrast polarity;
the observer reports with a key whether it points at the bars they tracked.

Which grating is the target (colour or luminance bars) is fixed for a session
(``target_grating``): "for half the sessions the pointers indicated color bars as targets
for tracking; for the other half, the pointers indicated luminance bars".
"""

from __future__ import annotations

from typing import Any, Literal

import numpy as np
from alhazen import Duration, TrialPlan, TrialSetup, outcomes
from alhazen.core.events import EventSchema
from alhazen.paradigms.base import Condition
from alhazen.paradigms.config import SchedulerConfig
from pydantic import Field, model_validator

from cavanagh1992.common import PROJECT, CavanaghTask, TrackedDisplayParams, random_phase
from cavanagh1992.phases import Present, ResponseAfter
from cavanagh1992.scene import Component, Pointer, Ring, Scene
from cavanagh1992.stimuli import make_scene_stimulus

TEST_POINTERS = ("tracked", "adjacent")


class AttentiveTrackingTaskParams(TrackedDisplayParams):
    """A tracking session's parameters. Durations resolve to whole frames."""

    target_grating: Literal["color", "luminance"] = "color"
    contrast_min: float = Field(0.05, gt=0)
    contrast_max: float = Field(0.40, gt=0)
    n_contrasts: int = Field(8, ge=2)
    pre_cue: Duration = Duration(ms=500)
    cue_duration: Duration = Duration(ms=1000)
    track_duration: Duration = Duration(ms=1500)
    test_duration: Duration = Duration(ms=240)
    response_timeout: Duration = Duration(ms=4000)
    yes_key: str = "j"
    no_key: str = "f"
    target_polarity: Literal["random", "positive", "negative"] = "random"
    paradigm: SchedulerConfig = SchedulerConfig(kind="sequence", n_per_condition=5)

    @model_validator(mode="after")
    def _contrasts(self) -> AttentiveTrackingTaskParams:
        if not self.contrast_min < self.contrast_max:
            raise ValueError("contrast_min must be below contrast_max")
        if self.yes_key == self.no_key:
            raise ValueError("yes_key and no_key must differ")
        return self

    def luminance_contrasts(self) -> list[float]:
        """The eight (n_contrasts) values, uniformly spaced, rounded to 0.1%."""
        return [round(float(c), 4) for c in
                np.linspace(self.contrast_min, self.contrast_max, self.n_contrasts)]


class AttentiveTrackingTask(CavanaghTask):
    name = "attentive-tracking"
    events = EventSchema(("FIX_ON", "STIM_ON", "POINTER_ON", "POINTER_OFF", "TEST_ON",
                          "RESPONSE_CUE", "RESPONSE"))
    outcomes = outcomes(
        CORRECT=dict(completed=True, success=True),
        WRONG=dict(completed=True, success=False),
        NO_RESPONSE=dict(completed=False),
    )
    params_model = AttentiveTrackingTaskParams
    instructions_section = "attentive-tracking"

    @classmethod
    def default_params(cls):
        return PROJECT / "configs" / "task.yaml"

    def __init__(self, params: Any) -> None:
        super().__init__(params)
        p = self.params
        p.color_model(1.0).check_headroom(p.contrast_max, p.color_contrast)

    def instructions(self) -> str | None:
        from cavanagh1992.common import instructions_for

        return instructions_for(f"attentive-tracking-{self.params.target_grating}")

    def conditions(self, rng: np.random.Generator) -> list[Condition]:
        return [Condition({"luminance_contrast": c, "test_pointer": t})
                for c in self.params.luminance_contrasts() for t in TEST_POINTERS]

    def make_scene(self, setup: TrialSetup, luminance_contrast: float) -> tuple[Scene, dict]:
        """The trial's scene and what was drawn for it (direction, phases, the target)."""
        p: AttentiveTrackingTaskParams = self.params  # type: ignore[assignment]
        rng = setup.rng
        d = int(rng.choice([1, -1]))
        color = Component("color", p.color_contrast, p.n_cycles, p.rate_hz, d, random_phase(rng))
        lum = Component("luminance", luminance_contrast, p.n_cycles, p.rate_hz, -d,
                        random_phase(rng))
        scene = Scene(rings=[Ring(p.annulus_inner_dva, p.annulus_outer_dva, [color, lum])],
                      color=p.color_model(p.k()), bullseye_radius_dva=p.bullseye_radius_dva,
                      bullseye_rings=p.bullseye_rings, pointer_geometry=p.pointer_geometry())
        polarity = {"positive": 1, "negative": -1}.get(p.target_polarity) or int(
            rng.choice([1, -1]))
        target = 0 if p.target_grating == "color" else 1
        index = int(rng.integers(0, p.n_cycles // 2))
        return scene, {"color_direction": d, "target_component": target,
                       "target_polarity": polarity, "target_index": index}

    def build_trial(self, setup: TrialSetup) -> TrialPlan:
        p: AttentiveTrackingTaskParams = self.params  # type: ignore[assignment]
        hz = setup.refresh_rate_hz
        lc = float(setup.condition.params["luminance_contrast"])
        test = setup.condition.params["test_pointer"]
        scene, drawn = self.make_scene(setup, lc)
        # An adjacent pair is one bar of the same polarity to either side, 360/n deg away.
        offset = 0 if test == "tracked" else int(setup.rng.choice([1, -1]))
        tracked = Pointer(0, drawn["target_component"], drawn["target_polarity"],
                          drawn["target_index"])
        probe = Pointer(0, drawn["target_component"], drawn["target_polarity"],
                        drawn["target_index"], offset)
        display = make_scene_stimulus(setup.display, setup.screen, scene)
        fixation = make_scene_stimulus(setup.display, setup.screen, Scene(
            rings=[Ring(p.annulus_inner_dva, p.annulus_outer_dva)], color=scene.color,
            bullseye_radius_dva=p.bullseye_radius_dva, bullseye_rings=p.bullseye_rings,
            pointer_geometry=p.pointer_geometry()))

        def pointer(which: Pointer | None):
            def set_pointer(ctx: Any) -> None:
                scene.pointer = which
            return set_pointer

        is_tracked = offset == 0
        yes, no = self.outcomes["CORRECT"], self.outcomes["WRONG"]
        keys = {p.yes_key: yes if is_tracked else no, p.no_key: no if is_tracked else yes}
        info = {"target_grating": p.target_grating, "luminance_contrast": lc,
                "is_tracked": is_tracked}
        record = {"target_grating": p.target_grating, "luminance_contrast": lc,
                  "color_contrast": p.color_contrast, "test_pointer": test,
                  "test_offset_bars": offset,
                  "test_offset_deg": offset * 360.0 / p.n_cycles, "k": p.k(), **drawn}
        return TrialPlan(
            phases=[
                Present(["fixation"], p.fixation_duration.seconds(hz), onset_event="FIX_ON"),
                Present(["display"], p.pre_cue.seconds(hz), onset_event="STIM_ON"),
                Present(["display"], p.cue_duration.seconds(hz), onset_event="POINTER_ON",
                        on_enter=pointer(tracked)),
                Present(["display"], p.track_duration.seconds(hz), onset_event="POINTER_OFF",
                        on_enter=pointer(None)),
                Present(["display"], p.test_duration.seconds(hz), onset_event="TEST_ON",
                        payload=info, on_enter=pointer(probe)),
                ResponseAfter(keys=keys, timeout_s=p.response_timeout.seconds(hz),
                              on_timeout=self.outcomes["NO_RESPONSE"],
                              stimulus_keys=["display"], on_enter=pointer(None)),
            ],
            stimuli={"display": display, "fixation": fixation},
            record=record,
        )

    def demo_views(self, setup: Any) -> list[Any]:
        from alhazen.task.plan import TrialSetup as TS

        from cavanagh1992.adjust import scene_view

        views = []
        for lc in (self.params.contrast_min, 0.10, self.params.contrast_max):
            fake = TS(cfg=None, screen=setup.screen, display=setup.display,  # type: ignore[arg-type]
                      rng=setup.rng, refresh_rate_hz=60.0, trial_index=1, attempt=1,
                      condition=Condition({}))
            scene, drawn = self.make_scene(fake, lc)
            scene.pointer = Pointer(0, drawn["target_component"], drawn["target_polarity"],
                                    drawn["target_index"])
            views.append(scene_view(setup, scene, f"lum-{lc:.2f}",
                                    f"luminance contrast {lc:.0%}, pointer on the target pair"))
        return views
