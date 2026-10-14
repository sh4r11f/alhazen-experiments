"""The monkey's training trials (Britten et al., 1992, p. 4748).

"Each animal was trained on a sequence of tasks leading up to the two-choice
task ... (1) fixation, (2) fixation followed by a saccade to a single target,
(3) saccade to a single target in the presence of random dot patterns, and (4)
choosing between two saccade targets based on the direction of motion in the
random dot pattern", first at 100 % correlation, then down to threshold.

Steps 1-3 are this task, ``rdk-direction-training``, named by the ladder
(configs/training-britten.yaml) by import path so it stays off run.py's menus.
Steps 4 and 5 are the experiment's own task. Nothing here changes the
experiment's trial or its data.
"""

from __future__ import annotations

from typing import Any, Literal

from alhazen import CircleRegion, TrialPlan, TrialSetup, outcomes
from alhazen.core.trial import Outcome, TrialContext
from alhazen.task import phases

from britten1992.task import OUTCOME_SPECS, RdkDirectionTask, RdkDirectionTaskParams


class RdkTrainingParams(RdkDirectionTaskParams):
    """The monkey file's parameters, and which training trial runs."""

    training_stage: Literal["fixate", "single-target", "single-target-dots"] = "fixate"


class EndWith:
    """End the trial with ``outcome`` at once: what a held fixation earns."""

    name = "end_with"

    def __init__(self, outcome: Outcome) -> None:
        self._outcome = outcome

    def on_enter(self, ctx: TrialContext) -> None:
        return

    def on_frame(self, ctx: TrialContext) -> Outcome:
        return ctx.end_undrawn(self._outcome)


class RdkTrainingTask(RdkDirectionTask):
    name = "rdk-direction-training"
    outcomes = outcomes(
        **OUTCOME_SPECS,
        FIXATION_HELD=dict(completed=True, success=True),
    )
    params_model = RdkTrainingParams

    def instructions(self) -> str | None:
        return None  # a monkey reads nothing

    def build_trial(self, setup: TrialSetup) -> TrialPlan:
        p: RdkTrainingParams = self.params  # type: ignore[assignment]
        plan = super().build_trial(setup)  # the experiment's trial: its stimuli and record
        direction = setup.condition.params["direction"]
        record = dict(plan.record, training_stage=p.training_stage)
        if p.training_stage == "fixate":
            hz = setup.refresh_rate_hz
            o = self.outcomes
            return TrialPlan(
                phases=[
                    phases.AcquireFixation(hold_s=p.acquire_hold.seconds(hz),
                                           timeout_s=p.acquire_timeout.seconds(hz),
                                           on_timeout=o["NO_FIXATION"]),
                    phases.HoldFixation(duration_s=p.stimulus_duration.seconds(hz),
                                        on_break=o["FIX_BREAK"],
                                        duration_record_key="stimulus_hold_s"),
                    EndWith(o["FIXATION_HELD"]),
                ],
                stimuli={"fixation": plan.stimuli["fixation"]},
                regions={"fixation": CircleRegion((0.0, 0.0),
                                                  setup.screen.deg2px(p.fix_window_dva))},
                record=record,
            )
        stimuli: dict[str, Any] = {k: v for k, v in plan.stimuli.items() if k != "targets"}
        return self._saccade_trial(
            setup, direction, stimuli, record,
            show_dots=p.training_stage == "single-target-dots",
            shown_targets=(direction,),
        )
