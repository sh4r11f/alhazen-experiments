"""Posner spatial cueing: the central-cue simple-detection experiment.

Posner (1980), Fig. 1 and pp. 6-7 (the experiment of Posner, Nissen & Ogden, 1978):
a plus sign or an arrow at fixation, then 1000 ms later a filled square 7 degrees
left or right of fixation, detected with a single key. After an arrow the square is
on the indicated side on 80% of target trials (valid) and on the other side on 20%
(invalid); after the plus sign it is on either side equally often (neutral). Eye
position was monitored and only trials with steady fixation were kept.

One trial of ``posner-cueing``:

1. (eye-tracker set) the fixation point waits for gaze: ``AcquireFixation``.
2. The inter-trial interval, 1000-2000 ms, fixation point on; with the tracker,
   gaze must stay in the fixation window (``HoldFixation``).
3. The cue replaces the fixation point for the cue-target SOA (1000 ms). A key here
   is an anticipation; with the tracker, gaze must stay put.
4. The square appears (target trials) or nothing changes (catch trials). The first
   key ends the trial; RT runs from the square's first flip. The cue stays on.
5. Feedback, 500 ms: the fixation point green or red (``TrialFeedback``).

docs/methods.md says which of these values the paper states and which are assumed.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import numpy as np
from alhazen import Condition, Duration, SubjectParams, Task, TrialPlan, TrialSetup, outcomes
from alhazen.config.models import Model
from alhazen.core.events import EventSchema
from alhazen.core.trial import CircleRegion, PhaseAction
from alhazen.errors import ConfigError
from alhazen.paradigms.config import BlockConfig, SchedulerConfig
from alhazen.stimuli.fixation import make_fixation
from alhazen.task import phases
from alhazen.task.duration import TrialTiming, fixed, uniform, wait
from pydantic import model_validator

from posner1980.design import block_conditions, composition
from posner1980.phases import FixatedResponseWindow
from posner1980.stimuli import make_cue, make_target

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]


class DesignParams(Model):
    """The block composition (posner1980.design). Only ``validity`` is the paper's."""

    arrow_fraction: float = 0.5
    validity: float = 0.8
    catch_fraction: float = 0.25
    trials_per_block: int = 80

    @model_validator(mode="after")
    def _divides(self) -> DesignParams:
        composition(self.trials_per_block, self.arrow_fraction, self.validity,
                    self.catch_fraction)
        return self


class PosnerCueingTaskParams(SubjectParams):
    """A session's parameters. Durations resolve to whole frames at the measured rate."""

    # "tracker": fixation is held in a window and a break re-serves the trial.
    # "none": the keyboard-only set, for a booth without an eye tracker.
    fixation_control: Literal["tracker", "none"] = "tracker"
    fixation_window_dva: float = 1.5
    acquire_timeout: Duration = Duration(ms=5000)

    fix_size_dva: float = 0.3
    cue_size_dva: float = 1.0
    cue_stroke_dva: float = 0.12
    target_size_dva: float = 1.0
    target_ecc_dva: float = 7.0
    stimulus_color: tuple[float, float, float] = (1.0, 1.0, 1.0)

    intertrial_min: Duration = Duration(ms=1000)
    intertrial_max: Duration = Duration(ms=2000)
    cue_target_soa: Duration = Duration(ms=1000)
    cue_stays_on: bool = True
    response_deadline: Duration = Duration(ms=1000)
    feedback_duration: Duration = Duration(ms=500)
    response_key: str = "space"

    design: DesignParams = DesignParams()
    paradigm: SchedulerConfig = SchedulerConfig(n_per_condition=1, blocks=BlockConfig(n_blocks=4))

    @model_validator(mode="after")
    def _consistent(self) -> PosnerCueingTaskParams:
        if self.paradigm.kind != "sequence":
            raise ValueError(
                "paradigm.kind must be 'sequence': each block serves the fixed composition in "
                "`design`, shuffled; an adaptive scheduler has nothing to adapt here"
            )
        lo, hi = self.intertrial_min, self.intertrial_max
        if lo.ms is not None and hi.ms is not None and hi.ms < lo.ms:
            raise ValueError("intertrial_max must not be shorter than intertrial_min")
        if self.fixation_control == "tracker" and self.fixation_window_dva >= self.target_ecc_dva:
            raise ValueError(
                "fixation_window_dva must be smaller than target_ecc_dva, or a saccade to the "
                "target could stay inside the fixation window"
            )
        return self


class PosnerCueingTask(Task):
    name = "posner-cueing"
    events = EventSchema(("FIX_ON", "FIX_ACQUIRED", "CUE_ON", "EARLY_RESPONSE", "TARGET_ON",
                          "CATCH_ON", "RESPONSE"))
    outcomes = outcomes(
        DETECTED=dict(completed=True, success=True),
        MISS=dict(completed=True, success=False),
        CORRECT_REJECTION=dict(completed=True, success=True),
        FALSE_ALARM=dict(completed=True, success=False),
        ANTICIPATION=dict(completed=False),
        FIXATION_BREAK=dict(completed=False),
        NO_FIXATION=dict(completed=False),
    )
    params_model = PosnerCueingTaskParams

    @classmethod
    def default_params(cls) -> Path:
        return PROJECT / "configs" / "task.yaml"

    @classmethod
    def params_hook(cls, params: PosnerCueingTaskParams, args: Any) -> PosnerCueingTaskParams:
        """Refuse a real session of the eye-tracker set on a rig with no tracker.

        Without gaze every trial would end NO_FIXATION and be served again, forever.
        Test mode puts the mouse in for a missing tracker and simulate mode the
        autopilot, so only run mode is refused, before anything is written.
        """
        if params.fixation_control != "tracker" or getattr(args, "mode", None) != "run":
            return params
        rig_path = getattr(args, "rig", None)
        if rig_path is None:
            return params
        from alhazen.config.loader import load_rig

        rig = load_rig(rig_path)
        if rig.devices.eyetracker is None:
            raise ConfigError(
                f"the eye-tracker parameter set (fixation_control: tracker) needs a rig with an "
                f"eye tracker, and {rig_path} has none. On a booth without one, run the "
                f"keyboard-only set: --params configs/task-keyboard.yaml"
            )
        return params

    def instructions(self) -> str | None:
        return (PROJECT / "instructions.md").read_text(encoding="utf-8")

    def conditions(self, rng: np.random.Generator) -> list[Condition]:
        d: DesignParams = self.params.design  # type: ignore[attr-defined]
        return block_conditions(
            composition(d.trials_per_block, d.arrow_fraction, d.validity, d.catch_fraction)
        )

    def build_trial(self, setup: TrialSetup) -> TrialPlan:
        p: PosnerCueingTaskParams = self.params  # type: ignore[assignment]
        hz = setup.refresh_rate_hz
        cond = setup.condition.params
        tracked = p.fixation_control == "tracker"
        o = self.outcomes
        key = p.response_key

        intertrial_s = float(setup.rng.uniform(p.intertrial_min.seconds(hz),
                                               p.intertrial_max.seconds(hz)))
        catch = cond["target"] == "none"

        stimuli: dict[str, Any] = {
            "fixation": make_fixation(setup.display, setup.screen, p.fix_size_dva,
                                      fill_color=p.stimulus_color),
            "cue": make_cue(setup.display, setup.screen, cond["cue"], p.cue_size_dva,
                            p.cue_stroke_dva, p.stimulus_color),
        }
        if not catch:
            stimuli["target"] = make_target(setup.display, setup.screen, cond["target"],
                                            p.target_ecc_dva, p.target_size_dva,
                                            p.stimulus_color)
        regions = {}
        gaze: dict[str, Any] = {}
        if tracked:
            regions["fixation"] = CircleRegion((0.0, 0.0),
                                               setup.screen.deg2px(p.fixation_window_dva))
            gaze = dict(region="fixation", on_break=o["FIXATION_BREAK"])

        trial: list[Any] = []
        if tracked:
            trial += [
                phases.AcquireFixation(timeout_s=p.acquire_timeout.seconds(hz),
                                       on_timeout=o["NO_FIXATION"], onset_event="FIX_ON"),
                phases.HoldFixation(duration_s=intertrial_s, on_break=o["FIXATION_BREAK"],
                                    duration_record_key="intertrial_s"),
            ]
        else:
            trial.append(phases.Feedback(["fixation"], intertrial_s, onset_event="FIX_ON"))

        shown = ["cue"] if p.cue_stays_on else []
        trial.append(FixatedResponseWindow(
            keys={key: o["ANTICIPATION"]}, timeout_s=p.cue_target_soa.seconds(hz),
            on_timeout=PhaseAction.ADVANCE, stimulus_keys=["cue"], onset_event="CUE_ON",
            response_event="EARLY_RESPONSE", rt_record_key="early_rt_ms",
            key_record_key="early_key", **gaze))
        if catch:
            trial.append(FixatedResponseWindow(
                keys={key: o["FALSE_ALARM"]}, timeout_s=p.response_deadline.seconds(hz),
                on_timeout=o["CORRECT_REJECTION"], stimulus_keys=shown,
                onset_event="CATCH_ON", **gaze))
        else:
            trial.append(FixatedResponseWindow(
                keys={key: o["DETECTED"]}, timeout_s=p.response_deadline.seconds(hz),
                on_timeout=o["MISS"], stimulus_keys=[*shown, "target"],
                onset_event="TARGET_ON", **gaze))
        trial.append(phases.TrialFeedback(
            verdict=lambda ctx: bool(ctx.outcome is not None and ctx.outcome.success),
            then=lambda ctx: ctx.outcome, duration_s=p.feedback_duration.seconds(hz),
            stimulus_key="fixation"))

        record: dict[str, Any] = {
            "fixation_control": p.fixation_control,
            "trial_type": "catch" if catch else "target",
            "soa_ms": p.cue_target_soa.seconds(hz) * 1000.0,
        }
        if not tracked:
            record["intertrial_s"] = intertrial_s
        return TrialPlan(phases=trial, stimuli=stimuli, regions=regions, record=record)

    def trial_timing(self, condition: Condition, refresh_rate_hz: float) -> TrialTiming:
        p: PosnerCueingTaskParams = self.params  # type: ignore[assignment]
        hz = refresh_rate_hz
        spans = []
        if p.fixation_control == "tracker":
            spans.append(wait("fixation acquired", p.acquire_timeout.seconds(hz),
                              basis="until gaze reaches the fixation window"))
        spans += [
            uniform("inter-trial interval", p.intertrial_min.seconds(hz),
                    p.intertrial_max.seconds(hz)),
            fixed("cue to target", p.cue_target_soa.seconds(hz)),
            wait("detection", p.response_deadline.seconds(hz), basis="until the key"),
            fixed("feedback", p.feedback_duration.seconds(hz)),
        ]
        return TrialTiming(tuple(spans))

    def simulation(self, seed: int):
        from alhazen.modes.simulation import Simulation

        from posner1980.simulate import SimulatedEye, SimulatedObserver, SimulatedPosnerTask

        observer = SimulatedObserver(seed=seed, key=self.params.response_key)  # type: ignore[attr-defined]
        tracked = self.params.fixation_control == "tracker"  # type: ignore[attr-defined]
        eye = SimulatedEye(seed=seed) if tracked else None
        return Simulation(
            tracker=eye,
            response=observer,
            task=SimulatedPosnerTask(self.params, observer),
            describe={"seed": seed, "source": "posner1980.simulate",
                      "observer": observer.describe(),
                      "eye": eye.describe() if eye is not None else None},
        )
