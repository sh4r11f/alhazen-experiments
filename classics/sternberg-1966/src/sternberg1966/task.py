"""Sternberg memory scanning: what a trial is made of.

TEMPLATE STARTER: a fixation point, then a target left or right, answered with F or J.
Replace it with the original paradigm (docs/methods.md is the specification).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from alhazen import Condition, Duration, SubjectParams, Task, TrialPlan, TrialSetup, outcomes
from alhazen.core.events import EventSchema
from alhazen.paradigms.config import SchedulerConfig
from alhazen.stimuli.fixation import make_fixation
from alhazen.task import phases

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]


class MemoryScanningTaskParams(SubjectParams):
    """A session's parameters. Durations resolve to whole frames at the measured rate."""

    fix_size_dva: float = 0.3
    target_size_dva: float = 1.0
    target_ecc_dva: float = 5.0
    fixation_duration: Duration = Duration(ms=500)
    response_timeout: Duration = Duration(ms=2000)
    iti: Duration = Duration(ms=1000)
    paradigm: SchedulerConfig = SchedulerConfig(n_per_condition=10)


class MemoryScanningTask(Task):
    name = "memory-scanning"
    events = EventSchema(("FIX_ON", "TARGET_ON", "RESPONSE_CUE", "RESPONSE"))
    outcomes = outcomes(
        CORRECT=dict(completed=True, success=True),
        WRONG=dict(completed=True, success=False),
        NO_RESPONSE=dict(completed=False),
    )
    params_model = MemoryScanningTaskParams

    @classmethod
    def default_params(cls) -> Path:
        return PROJECT / "configs" / "task.yaml"

    def instructions(self) -> str | None:
        return (PROJECT / "instructions.md").read_text(encoding="utf-8")

    def conditions(self, rng: np.random.Generator) -> list[Condition]:
        return [Condition({"side": side}) for side in ("left", "right")]

    def build_trial(self, setup: TrialSetup) -> TrialPlan:
        p: MemoryScanningTaskParams = self.params  # type: ignore[assignment]
        hz = setup.refresh_rate_hz
        side = setup.condition.params["side"]
        x = setup.screen.deg2px(p.target_ecc_dva) * (-1 if side == "left" else 1)
        correct, wrong = self.outcomes["CORRECT"], self.outcomes["WRONG"]
        keys = {
            "f": correct if side == "left" else wrong,
            "j": correct if side == "right" else wrong,
        }
        return TrialPlan(
            phases=[
                phases.Feedback(
                    ["fixation"], p.fixation_duration.seconds(hz), onset_event="FIX_ON"
                ),
                phases.ResponseWindow(keys=keys, timeout_s=p.response_timeout.seconds(hz),
                                      on_timeout=self.outcomes["NO_RESPONSE"],
                                      stimulus_keys=["fixation", "target"]),
            ],
            stimuli={
                "fixation": make_fixation(setup.display, setup.screen, p.fix_size_dva),
                "target": make_fixation(
                    setup.display, setup.screen, p.target_size_dva, pos=(x, 0.0)
                ),
            },
            record={"side": side},
        )

    def simulation(self, seed: int):
        from alhazen.modes.simulation import Simulation

        from sternberg1966.simulate import SimulatedObserver

        return Simulation(response=SimulatedObserver(seed=seed),
                          describe={"seed": seed, "source": "sternberg1966.simulate"})
