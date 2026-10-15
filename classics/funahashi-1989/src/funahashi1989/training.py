"""The ODR task's training variant: the first two rungs of the monkey's ladder.

The paper says only that training lasted "usually 3-4 mo" before the monkey was
"proficient on the oculomotor delayed-response task" (p. 332); it does not describe the
steps. The ladder in configs/training-odr.yaml is therefore ASSUMED as a whole
(docs/methods.md): it follows the usual route to a memory-guided saccade.

1. **fixate** (this task, ``training.mode: fixate``): the fixation spot alone, acquired
   and held for the fixation period. Pays FIXATION_HELD.
2. **visual** (this task, ``training.mode: visual``): a visually guided saccade. After the
   fixation period the spot goes off and the square appears at one of the eight locations
   on the same flip; saccade to it. Pays CORRECT.
3. **short delay**: the experiment's own trial with short delays (overrides only).
4. **full**: the experiment's own trial, as the monkey file says.

This task is named by the ladder by import path and is not in run.py's TASKS (alhazen's
training-mode contract: a training task's params accept every experiment file, so it must
not be a candidate for "which task is this file for").
"""

from __future__ import annotations

from typing import Any, Literal

import numpy as np
from alhazen import Condition, TrialPlan, TrialSetup, outcomes
from alhazen.config.models import Model
from alhazen.task import duration as timing
from alhazen.task import phases

from funahashi1989.task import OculomotorDelayedResponseTask, OdrParams


class TrainingStage(Model):
    """Which training trial runs."""

    mode: Literal["fixate", "visual"] = "fixate"


class OdrTrainingParams(OdrParams):
    """The experiment's parameters and the stage's ``training`` block."""

    training: TrainingStage = TrainingStage()


class OdrTrainingTask(OculomotorDelayedResponseTask):
    """A fixation hold, or a visually guided saccade (module docstring)."""

    name = "oculomotor-delayed-response-training"
    params_model = OdrTrainingParams
    outcomes = outcomes(
        FIXATION_HELD=dict(completed=True, success=True),
        CORRECT=dict(completed=True, success=True),
        INACCURATE=dict(completed=True, success=False),
        NO_FIXATION=dict(completed=False),
        FIX_BREAK=dict(completed=False),
        NO_SACCADE=dict(completed=False),
    )

    def instructions(self) -> None:
        """A monkey reads nothing."""
        return None

    def conditions(self, rng: np.random.Generator) -> list[Condition]:
        """The eight cue locations; a training trial has no delay."""
        p: OdrParams = self.params  # type: ignore[assignment]
        return [Condition({"cue_angle_deg": float(a), "delay_index": -1})
                for a in p.cue_angles_deg]

    def build_trial(self, setup: TrialSetup) -> TrialPlan:
        p: OdrTrainingParams = self.params  # type: ignore[assignment]
        hz = setup.refresh_rate_hz
        angle, _, stimuli, regions = self._geometry(setup)
        mode = p.training.mode
        fixate = [
            phases.AcquireFixation(
                timeout_s=p.acquire_timeout.seconds(hz),
                on_timeout=self.outcomes["NO_FIXATION"],
                onset_event="FIX_ON",
                acquired_event="FIX_ACQUIRED",
            ),
            phases.HoldFixation(
                duration_s=p.fixation_period.seconds(hz),
                on_break=self.outcomes["FIX_BREAK"],
                duration_record_key="fixation_period_s",
            ),
        ]
        if mode == "fixate":
            # The last frame of the hold ends the trial as held.
            plan_phases = [*fixate, _End(self.outcomes["FIXATION_HELD"])]
        else:
            # Visually guided: the square appears on the flip the spot goes off.
            plan_phases = [*fixate, *self._response_phases(hz, "cue")]
        return TrialPlan(
            phases=plan_phases,
            stimuli=stimuli,
            regions=regions,
            record={**self._base_record(angle), "delay_index": -1,
                    "trial_kind": f"training-{mode}", "training_mode": mode},
        )

    def trial_timing(self, condition: Condition, refresh_rate_hz: float) -> Any:
        p: OdrTrainingParams = self.params  # type: ignore[assignment]
        hz = refresh_rate_hz
        spans = [
            timing.wait("fixation acquired", p.acquire_timeout.seconds(hz)),
            timing.fixed("fixation period", p.fixation_period.seconds(hz)),
        ]
        if p.training.mode == "visual":
            spans += [timing.wait("saccade", p.response_period.seconds(hz)),
                      timing.wait("landing", p.landing_max_wait.seconds(hz))]
        return timing.TrialTiming(spans)


class _End:
    """Ends the trial with an outcome on its first frame, drawing nothing (the hold before
    it has already shown its last frame)."""

    name = "end"

    def __init__(self, outcome: Any) -> None:
        self._outcome = outcome

    def on_enter(self, ctx: Any) -> None:
        return

    def on_frame(self, ctx: Any) -> Any:
        return ctx.end_undrawn(self._outcome)
