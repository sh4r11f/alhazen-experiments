"""Motion coherence discrimination (Britten, Shadlen, Newsome & Movshon, 1992).

One task, two ways of answering, chosen by the params file:

- ``response_mode: saccade_and_reward`` (configs/task-monkey.yaml) is the
  paper's trial (Fig. 2, pp. 4747-4748): acquire the fixation point, hold it,
  view the random-dot stimulus for 2 s with fixation held, then the fixation
  point and the dots go off, two targets appear on the motion axis, and the
  subject reports the direction with a saccade to the matching target within
  2.1 s. A correct choice is paid; a wrong one earns a brief time-out. At 0 %
  correlation the "correct" target is the trial's nominal direction, so reward
  is random on half of those trials, as in the paper.
- ``response_mode: keyboard`` (configs/task.yaml) is the human adaptation:
  the same stimulus, viewed for 2 s at a fixation point that is not enforced,
  then a key for the direction.

The dot stream is ``britten1992.rdk``. docs/methods.md is the specification;
every value the paper does not state is marked ASSUMED in the params files.
"""

from __future__ import annotations

import copy
import math
from dataclasses import replace
from pathlib import Path
from typing import Any, Literal

import numpy as np
from alhazen import (
    CircleRegion,
    Condition,
    Duration,
    SubjectParams,
    Task,
    TrialPlan,
    TrialSetup,
    outcomes,
)
from alhazen.config.models import Model
from alhazen.core.events import EventSchema
from alhazen.core.trial import Outcome, PhaseAction, TrialContext
from alhazen.paradigms.base import TrialSource
from alhazen.paradigms.config import SchedulerConfig
from alhazen.stimuli.base import NullStimulus
from alhazen.stimuli.fixation import make_fixation
from alhazen.task import duration as timing
from alhazen.task import phases
from alhazen.task.subject_kind import SubjectKind
from alhazen.task.subject_mode import SubjectMode
from pydantic import BaseModel, model_validator

from britten1992.rdk import DotFieldSpec, make_rdk

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]

# The paper's preferred and null directions. "anti" stands for null: pandas and
# most CSV readers read the word "null" as a missing value.
DIRECTIONS = ("pref", "anti")
Color = tuple[float, float, float]


class CorrectionConfig(Model):
    """Correction trials (p. 4748): after ``after_errors`` wrong choices on
    consecutive presentations of motion in one direction, motion is shown
    repeatedly in that (neglected) direction until it is chosen correctly.
    They are flagged ``correction`` and excluded from every analysis."""

    enabled: bool = False
    after_errors: int = 3
    # None: each correction trial draws one of the session's non-zero levels.
    coherence_pct: float | None = None

    @model_validator(mode="after")
    def _valid(self) -> CorrectionConfig:
        if self.after_errors < 1:
            raise ValueError("correction_trials.after_errors must be >= 1")
        return self


class RdkDirectionTaskParams(SubjectParams):
    """A session's parameters. Durations resolve to whole frames at the
    measured refresh rate; sizes are degrees of visual angle (dva)."""

    response_mode: SubjectMode = SubjectMode.KEYBOARD

    # --- the random-dot stimulus -------------------------------------------
    coherences_pct: list[float] = [0.0, 0.8, 1.6, 3.2, 6.4, 12.8, 25.6, 51.2]
    axis_deg: float = 0.0  # the "preferred" direction; "anti" is opposite
    speed_dva_s: float = 6.0
    signal_dt: Duration = Duration(ms=45)
    density_dots_deg2_s: float = 16.7
    field_dva: float = 20.0
    aperture_dva: float = 10.0
    aperture_center_dva: tuple[float, float] = (0.0, 0.0)
    aperture_fill: Color | None = (-1.0, -1.0, -1.0)
    dot_size_dva: float = 0.1
    dot_color: Color = (1.0, 1.0, 1.0)
    stimulus_seed: Literal["per_trial", "fixed"] = "per_trial"
    fixed_seed: int = 1
    stimulus_duration: Duration = Duration(ms=2000)

    # --- fixation point and targets ----------------------------------------
    fix_size_dva: float = 0.3
    fix_color: Color = (1.0, 1.0, -1.0)
    fix_window_dva: float = 1.25
    target_size_dva: float = 0.5
    target_color: Color = (1.0, 1.0, 1.0)
    target_ecc_dva: float = 10.0
    target_window_dva: float = 3.0

    # --- timing ------------------------------------------------------------
    fixation_duration: Duration = Duration(ms=500)  # keyboard: fixation point alone
    acquire_timeout: Duration = Duration(ms=5000)
    acquire_hold: Duration = Duration(ms=200)
    prestim_hold: Duration = Duration(ms=300)
    response_timeout: Duration = Duration(ms=2100)
    landing_dwell: Duration = Duration(ms=200)
    feedback_duration: Duration = Duration(ms=300)
    error_timeout: Duration = Duration(ms=1500)
    iti: Duration = Duration(ms=1000)

    key_pref: str = "right"  # keyboard: the key for motion in the pref direction
    key_anti: str = "left"  # and for the anti (the paper's null) direction
    correction_trials: CorrectionConfig = CorrectionConfig()
    paradigm: SchedulerConfig = SchedulerConfig(n_per_condition=15)

    @model_validator(mode="after")
    def _consistent(self) -> RdkDirectionTaskParams:
        if not self.coherences_pct:
            raise ValueError("coherences_pct must name at least one level")
        if any(not 0.0 <= c <= 100.0 for c in self.coherences_pct):
            raise ValueError("coherences_pct are percentages, each in [0, 100]")
        if len(set(self.coherences_pct)) != len(self.coherences_pct):
            raise ValueError("coherences_pct must not repeat a level")
        if self.aperture_dva > self.field_dva:
            raise ValueError("aperture_dva must not exceed field_dva (the plotting field)")
        if (
            self.subject_kind is SubjectKind.MONKEY
            and self.response_mode is not SubjectMode.SACCADE_AND_REWARD
        ):
            raise ValueError(
                "a monkey reports with a saccade: subject_kind monkey needs "
                "response_mode: saccade_and_reward"
            )
        if self.key_pref == self.key_anti:
            raise ValueError("key_pref and key_anti must be different keys")
        c = self.correction_trials.coherence_pct
        if c is not None and c not in self.coherences_pct:
            raise ValueError("correction_trials.coherence_pct must be one of coherences_pct")
        return self


# CORRECT / WRONG are the measured trials. The rest produced no measurement and
# their condition is served again: no key in time (keyboard); no fixation, a
# fixation break, no saccade within 2.1 s, or a saccade into neither target
# (saccade). The paper discarded those trials (pp. 4747-4748).
OUTCOME_SPECS: dict[str, dict[str, bool]] = {
    "CORRECT": dict(completed=True, success=True),
    "WRONG": dict(completed=True, success=False),
    "NO_RESPONSE": dict(completed=False),
    "NO_FIXATION": dict(completed=False),
    "FIX_BREAK": dict(completed=False),
    "NO_CHOICE": dict(completed=False),
    "MISSED": dict(completed=False),
}
OUTCOMES = outcomes(**OUTCOME_SPECS)

EVENTS = EventSchema(
    (
        "FIX_ON",
        "FIX_ACQUIRED",
        "STIM_ON",
        "RESPONSE_CUE",
        "RESPONSE",
        "TARGETS_ON",
        "SACCADE_ONSET",
        "LANDED",
        "TIMEOUT_ON",
    )
)


def direction_deg(params: RdkDirectionTaskParams, direction: str) -> float:
    """The motion direction of ``pref`` (the axis) or ``anti`` (opposite: the
    paper's null direction, labelled ``anti`` because CSV readers take the
    word "null" for a missing value)."""
    return float(params.axis_deg + (0.0 if direction == "pref" else 180.0)) % 360.0


def target_positions_dva(params: RdkDirectionTaskParams) -> dict[str, tuple[float, float]]:
    """Each direction's saccade target: on the motion axis through the fixation
    point, on the side the motion goes, ``target_ecc_dva`` from fixation."""
    out = {}
    for d in DIRECTIONS:
        theta = math.radians(direction_deg(params, d))
        out[d] = (params.target_ecc_dva * math.cos(theta), params.target_ecc_dva * math.sin(theta))
    return out


class ChoiceVerdict:
    """The saccade task's closing phase: which target the eye landed on, the
    outcome that makes, and the time-out after a wrong choice.

    Reads the landing ``LandingSample`` recorded (``endpoint_*``): inside the
    correct target is CORRECT, inside the other is WRONG, anywhere else MISSED
    (a trial the paper discarded, so it is served again). A WRONG choice is
    followed by ``error_timeout_s`` of empty screen (the paper's "brief
    time-out", p. 4747). A trial that ended earlier (a fixation break, no
    saccade) keeps its outcome and gets no time-out.
    """

    name = "choice_verdict"
    must_be_last = True

    def __init__(
        self,
        targets_px: dict[str, tuple[float, float]],
        radius_px: float,
        correct: str,
        error_timeout_s: float,
        outcome_set: Any,
    ) -> None:
        self._targets = {k: CircleRegion(v, radius_px) for k, v in targets_px.items()}
        self._correct = correct
        self._error_timeout_s = error_timeout_s
        self._o = outcome_set

    def on_enter(self, ctx: TrialContext) -> None:
        self._t0 = ctx.clock.now()
        self._wait = 0.0
        if ctx.outcome is not None:
            ctx.record["choice"] = "none"
            self._result: Outcome = ctx.outcome
            return
        chosen = None
        if ctx.record.get("endpoint_measured"):
            point = (
                ctx.screen.deg2px(ctx.record["endpoint_x_dva"]),
                ctx.screen.deg2px(ctx.record["endpoint_y_dva"]),
            )
            hits = [name for name, region in self._targets.items() if region.contains(point)]
            chosen = hits[0] if len(hits) == 1 else None
        ctx.record["choice"] = chosen or "none"
        if chosen is None:
            self._result = self._o["MISSED"]
        elif chosen == self._correct:
            self._result = self._o["CORRECT"]
        else:
            self._result = self._o["WRONG"]
            self._wait = self._error_timeout_s
            ctx.emit_on_flip("TIMEOUT_ON")

    def on_frame(self, ctx: TrialContext) -> str | Outcome:
        if ctx.time_up(self._t0, self._wait):
            return ctx.end_undrawn(self._result)
        return PhaseAction.CONTINUE


class CorrectionTrials:
    """Wraps the planned schedule with the paper's correction trials (p. 4748).

    A streak of ``after_errors`` wrong choices on consecutive presentations of
    motion in one direction (0 % trials, which carry no motion, are not
    counted) starts a series of correction trials in that direction, which
    continues until one is answered correctly. Correction trials are extra:
    they never consume a planned trial, and their condition says
    ``correction: True`` so the analysis can drop them.
    """

    def __init__(
        self,
        inner: TrialSource,
        *,
        after_errors: int,
        coherences_pct: list[float],
        coherence_pct: float | None,
        rng: np.random.Generator,
    ) -> None:
        self._inner = inner
        self._after = after_errors
        nonzero = [c for c in coherences_pct if c > 0]
        self._levels = [coherence_pct] if coherence_pct is not None else (nonzero or [0.0])
        self._rng = rng
        self._streak = {d: 0 for d in DIRECTIONS}
        self.neglected: str | None = None
        self.n_correction_trials = 0

    def _plan_left(self) -> bool:
        remaining = getattr(self._inner, "remaining", None)
        return True if remaining is None else remaining() > 0

    def next(self) -> Condition | None:
        if self.neglected is not None and self._plan_left():
            level = float(self._levels[int(self._rng.integers(len(self._levels)))])
            self.n_correction_trials += 1
            return Condition(
                {"direction": self.neglected, "coherence_pct": level, "correction": True}
            )
        self.neglected = None
        return self._inner.next()

    def record(self, condition: Condition, result: Any) -> None:
        p = condition.params
        if p.get("correction"):
            if result.outcome.completed and result.outcome.success:
                self.neglected = None
            return
        self._inner.record(condition, result)
        if not result.outcome.completed or float(p["coherence_pct"]) == 0.0:
            return
        d = p["direction"]
        if result.outcome.success:
            self._streak[d] = 0
            return
        self._streak[d] += 1
        if self._streak[d] >= self._after:
            self._streak[d] = 0
            self.neglected = d

    def remaining(self) -> int:
        remaining = getattr(self._inner, "remaining", None)
        return remaining() if remaining is not None else 0

    def summary(self) -> Any:
        return self._inner.summary()


class RdkDirectionTask(Task):
    name = "rdk-direction"
    events = EVENTS
    outcomes = OUTCOMES
    params_model = RdkDirectionTaskParams
    # A simulated subject that wants to know each trial (simulate.py); None
    # in every real session.
    trial_observer: Any = None

    @classmethod
    def default_params(cls) -> Path:
        return PROJECT / "configs" / "task.yaml"

    def instructions(self) -> str | None:
        return (PROJECT / "instructions.md").read_text(encoding="utf-8")

    # ------------------------------------------------------------------
    # scheduling
    # ------------------------------------------------------------------

    def conditions(self, rng: np.random.Generator) -> list[Condition]:
        p: RdkDirectionTaskParams = self.params  # type: ignore[assignment]
        return [
            Condition({"direction": d, "coherence_pct": float(c), "correction": False})
            for c in p.coherences_pct
            for d in DIRECTIONS
        ]

    def make_source(self, params: BaseModel, rng: np.random.Generator) -> TrialSource:
        source = super().make_source(params, rng)
        cfg: CorrectionConfig = params.correction_trials  # type: ignore[attr-defined]
        if not cfg.enabled:
            return source
        return CorrectionTrials(
            source,
            after_errors=cfg.after_errors,
            coherences_pct=list(params.coherences_pct),  # type: ignore[attr-defined]
            coherence_pct=cfg.coherence_pct,
            rng=rng,
        )

    def duration_schedule(self, params: BaseModel, rng: np.random.Generator) -> Any:
        plan = timing.drain(Task.make_source(self, params, rng))
        if params.correction_trials.enabled:  # type: ignore[attr-defined]
            note = "plus correction trials, as many as the subject's errors call for"
            return replace(plan, note=note)
        return plan

    def trial_timing(self, condition: Condition, refresh_rate_hz: float) -> timing.TrialTiming:
        p: RdkDirectionTaskParams = self.params  # type: ignore[assignment]
        hz = refresh_rate_hz
        stim = timing.fixed("random dots", p.stimulus_duration.seconds(hz), "the paper's 2 s")
        if p.response_mode is SubjectMode.KEYBOARD:
            return timing.TrialTiming(
                [
                    timing.fixed("fixation point", p.fixation_duration.seconds(hz)),
                    stim,
                    timing.wait("key", p.response_timeout.seconds(hz)),
                    timing.fixed("feedback", p.feedback_duration.seconds(hz)),
                ]
            )
        return timing.TrialTiming(
            [
                timing.wait("acquire fixation", p.acquire_timeout.seconds(hz),
                            p.acquire_hold.seconds(hz)),
                timing.fixed("hold before the dots", p.prestim_hold.seconds(hz)),
                stim,
                timing.wait("saccade", p.response_timeout.seconds(hz)),
                timing.fixed("landing", p.landing_dwell.seconds(hz)),
                timing.bounded("time-out after an error", 0.0, p.error_timeout.seconds(hz),
                               "only after a wrong choice"),
            ]
        )

    # ------------------------------------------------------------------
    # one trial
    # ------------------------------------------------------------------

    def stimulus_seed(self, setup: TrialSetup) -> int:
        p: RdkDirectionTaskParams = self.params  # type: ignore[assignment]
        if p.stimulus_seed == "fixed":
            return int(p.fixed_seed)
        return int(setup.rng.integers(0, 2**31 - 1))

    def dot_spec(self, coherence_pct: float, direction: str, hz: float) -> DotFieldSpec:
        p: RdkDirectionTaskParams = self.params  # type: ignore[assignment]
        return DotFieldSpec(
            coherence=coherence_pct / 100.0,
            direction_deg=direction_deg(p, direction),
            speed_dva_s=p.speed_dva_s,
            density=p.density_dots_deg2_s,
            field_dva=p.field_dva,
            aperture_dva=p.aperture_dva,
            refresh_hz=hz,
            signal_dt_frames=max(1, p.signal_dt.n_frames(hz)),
        )

    def _aperture(self, setup: TrialSetup) -> Any:
        """The dark disc the dots are drawn on (aperture_fill), or nothing."""
        p: RdkDirectionTaskParams = self.params  # type: ignore[assignment]
        if p.aperture_fill is None or setup.display.kind == "simulated":
            return NullStimulus("aperture")
        from psychopy import visual  # lazy

        cx, cy = (setup.screen.deg2px(v) for v in p.aperture_center_dva)
        disc = visual.Circle(
            setup.display.window,
            radius=setup.screen.deg2px(p.aperture_dva) / 2.0,
            pos=(cx, cy),
            fillColor=p.aperture_fill,
            lineColor=p.aperture_fill,
            units="pix",
        )
        return _Static(disc)

    def build_trial(self, setup: TrialSetup) -> TrialPlan:
        p: RdkDirectionTaskParams = self.params  # type: ignore[assignment]
        hz = setup.refresh_rate_hz
        cond = setup.condition.params
        direction = cond["direction"]
        coherence = float(cond["coherence_pct"])
        spec = self.dot_spec(coherence, direction, hz)
        seed = self.stimulus_seed(setup)
        dots = make_rdk(setup.display, setup.screen, spec, seed, p.aperture_center_dva,
                        p.dot_size_dva, p.dot_color)
        record: dict[str, Any] = {
            "direction_deg": direction_deg(p, direction),
            "stimulus_seed": seed,
            "signal_dt_ms": 1000.0 * spec.signal_dt_s,
            "step_dva": spec.step_dva,
            "dots_per_frame": spec.n_per_frame,
            "response_mode": p.response_mode.value,
        }
        stimuli: dict[str, Any] = {
            "fixation": make_fixation(setup.display, setup.screen, p.fix_size_dva, p.fix_color),
            "dots": _Layered(self._aperture(setup), dots),
        }
        if self.trial_observer is not None:
            self.trial_observer.note_trial(
                direction=direction,
                coherence_pct=coherence,
                targets_dva=target_positions_dva(p),
            )
        if p.response_mode is SubjectMode.KEYBOARD:
            return self._keyboard_trial(setup, direction, stimuli, record)
        return self._saccade_trial(setup, direction, stimuli, record)

    def _keyboard_trial(self, setup, direction, stimuli, record) -> TrialPlan:
        p: RdkDirectionTaskParams = self.params  # type: ignore[assignment]
        hz = setup.refresh_rate_hz
        o = self.outcomes
        other = "anti" if direction == "pref" else "pref"
        key = {"pref": p.key_pref, "anti": p.key_anti}
        keys = {key[direction]: o["CORRECT"], key[other]: o["WRONG"]}
        return TrialPlan(
            phases=[
                phases.Feedback(["fixation"], p.fixation_duration.seconds(hz),
                                onset_event="FIX_ON"),
                phases.Feedback(["dots", "fixation"], p.stimulus_duration.seconds(hz),
                                onset_event="STIM_ON"),
                phases.ResponseWindow(keys=keys, timeout_s=p.response_timeout.seconds(hz),
                                      on_timeout=o["NO_RESPONSE"], stimulus_keys=["fixation"],
                                      onset_event="RESPONSE_CUE"),
                phases.TrialFeedback(
                    verdict=lambda ctx: bool(ctx.outcome is not None and ctx.outcome.success),
                    then=lambda ctx: ctx.outcome or o["NO_RESPONSE"],
                    duration_s=p.feedback_duration.seconds(hz),
                ),
            ],
            stimuli=stimuli,
            record=record,
        )

    def _saccade_trial(
        self,
        setup: TrialSetup,
        direction: str,
        stimuli: dict[str, Any],
        record: dict[str, Any],
        *,
        show_dots: bool = True,
        shown_targets: tuple[str, ...] = DIRECTIONS,
    ) -> TrialPlan:
        """The paper's trial. The two keyword arguments exist for the training
        ladder only (britten1992.training): the stages before the two-choice
        task show one target, and the first of them no dots."""
        p: RdkDirectionTaskParams = self.params  # type: ignore[assignment]
        hz = setup.refresh_rate_hz
        s = setup.screen
        o = self.outcomes
        targets_dva = {d: xy for d, xy in target_positions_dva(p).items() if d in shown_targets}
        targets_px = {d: (s.deg2px(x), s.deg2px(y)) for d, (x, y) in targets_dva.items()}
        target_r = s.deg2px(p.target_window_dva)
        stimuli["targets"] = _Group(
            [
                make_fixation(setup.display, s, p.target_size_dva, p.target_color, pos=xy)
                for xy in targets_px.values()
            ]
        )
        regions = {"fixation": CircleRegion((0.0, 0.0), s.deg2px(p.fix_window_dva))}
        for d, xy in targets_px.items():
            regions[f"target_{d}"] = CircleRegion(xy, target_r)
        regions["target_correct"] = CircleRegion(targets_px[direction], target_r)
        return TrialPlan(
            phases=[
                phases.AcquireFixation(hold_s=p.acquire_hold.seconds(hz),
                                       timeout_s=p.acquire_timeout.seconds(hz),
                                       on_timeout=o["NO_FIXATION"]),
                phases.HoldFixation(duration_s=p.prestim_hold.seconds(hz), on_break=o["FIX_BREAK"],
                                    duration_record_key="prestim_hold_s"),
                phases.HoldFixation(duration_s=p.stimulus_duration.seconds(hz),
                                    on_break=o["FIX_BREAK"],
                                    concurrent=["dots"] if show_dots else [],
                                    onset_event="STIM_ON", duration_record_key="stimulus_hold_s"),
                phases.StimulusResponse(stimulus_key="targets", depart_region="fixation",
                                        timeout_s=p.response_timeout.seconds(hz),
                                        on_timeout=o["NO_CHOICE"], onset_event="TARGETS_ON",
                                        response_event="SACCADE_ONSET",
                                        rt_record_key="saccade_rt_ms"),
                phases.LandingSample(region="target_correct", on_hit=PhaseAction.ADVANCE,
                                     on_miss=PhaseAction.ADVANCE,
                                     dwell_s=p.landing_dwell.seconds(hz),
                                     onset_event="SACCADE_ONSET", depart_region="fixation",
                                     stimulus_keys=["targets"]),
                ChoiceVerdict(targets_px, target_r, direction, p.error_timeout.seconds(hz), o),
            ],
            stimuli=stimuli,
            regions=regions,
            record=record,
        )

    # ------------------------------------------------------------------
    # after the trial
    # ------------------------------------------------------------------

    def score(self, record: dict[str, Any]) -> dict[str, Any]:
        """Derived columns: ``choice`` (pref / anti / none), ``chose_pref``,
        and ``signed_coherence_pct`` (+ for pref, - for anti motion)."""
        p: RdkDirectionTaskParams = self.params  # type: ignore[assignment]
        out = dict(record)
        if "choice" not in out:
            key = out.get("response_key")
            choice = {p.key_pref: "pref", p.key_anti: "anti"}.get(key, "none")
            out["choice"] = choice
        out["chose_pref"] = {"pref": 1, "anti": 0}.get(out["choice"])
        direction = out.get("direction")
        if direction in DIRECTIONS and out.get("coherence_pct") is not None:
            sign = 1.0 if direction == "pref" else -1.0
            out["signed_coherence_pct"] = sign * float(out["coherence_pct"])
        return out

    def simulation(self, seed: int) -> Any:
        from alhazen.modes.simulation import Simulation

        from britten1992.simulate import SimulatedMonkey, SimulatedObserver

        p: RdkDirectionTaskParams = self.params  # type: ignore[assignment]
        if p.response_mode is SubjectMode.KEYBOARD:
            observer = SimulatedObserver(keys=(p.key_pref, p.key_anti), seed=seed)
            return Simulation(response=observer, describe=observer.describe())
        monkey = SimulatedMonkey(seed=seed)
        task = copy.copy(self)
        task.trial_observer = monkey
        return Simulation(tracker=monkey, task=task, describe=monkey.describe())


class _Static:
    """A PsychoPy shape that never changes."""

    def __init__(self, stim: Any) -> None:
        self._stim = stim

    def update(self, dt: float) -> None:
        return

    def draw(self) -> None:
        self._stim.draw()


class _Layered:
    """The aperture disc under the dots: one stimulus, drawn in that order."""

    def __init__(self, under: Any, over: Any) -> None:
        self.under, self.over = under, over

    def update(self, dt: float) -> None:
        self.under.update(dt)
        self.over.update(dt)

    def draw(self) -> None:
        self.under.draw()
        self.over.draw()


class _Group:
    """Several stimuli drawn as one (the two saccade targets)."""

    def __init__(self, members: list[Any]) -> None:
        self.members = members

    def update(self, dt: float) -> None:
        for m in self.members:
            m.update(dt)

    def draw(self) -> None:
        for m in self.members:
            m.draw()
