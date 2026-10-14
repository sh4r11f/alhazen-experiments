"""Sternberg (1966): the two memory-scanning procedures as alhazen tasks.

- ``memory-scanning`` (experiment 1, the varied-set procedure): a series of 1-6 different
  digits shown one at a time, a delay, a warning signal, a test digit answered with one of
  two keys, a feedback light, and an ordered recall of the series.
- ``memory-scanning-fixed`` (experiment 2, the fixed-set procedure): a positive set of 1, 2
  or 4 digits announced once per part, then trials of warning signal, test digit, response
  and feedback light, with test digits drawn from the paper's fixed population.

docs/methods.md is the specification. Every value the paper states is cited in the params
files ("# paper: p. N"); every value it does not is marked "# ASSUMED".
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np
from alhazen import Condition, Duration, SubjectParams, Task, TrialPlan, TrialSetup, outcomes
from alhazen.core.events import EventSchema
from alhazen.paradigms.base import SimpleSequence
from alhazen.paradigms.blocks import BlockPlan
from alhazen.paradigms.config import SchedulerConfig
from alhazen.task import phases
from alhazen.task.duration import PlannedSchedule, TrialTiming, drain, fixed, wait
from alhazen.task.subject_kind import SubjectKind
from pydantic import model_validator

from sternberg1966 import design
from sternberg1966.phases import AwaitKey, FeedbackLight, ProbeResponse, RecallEntry
from sternberg1966.stimuli import make_lamp, make_text

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]

# Keys alhazen's experimenter controls read (core/commands.py DEFAULT_KEYMAP); a response
# key must not be one of them, or a press would pause or skip the trial instead.
COMMAND_KEYS = frozenset({"escape", "p", "c", "r", "h", "bracketleft", "bracketright", "[", "]"})
RECALL_KEYS = frozenset({"return", "num_enter", "enter", "backspace"})

Color = tuple[float, float, float]


class ScanningParams(SubjectParams):
    """What both procedures share: the display, the warning, the keys, the light."""

    digit_height_dva: float = 1.5
    digit_color: Color = (1.0, 1.0, 1.0)
    warning_symbol: str = "+"
    warning_duration: Duration = Duration(ms=500)
    positive_key: str = "j"
    negative_key: str = "f"
    response_timeout: Duration = Duration(ms=5000)
    feedback_duration: Duration = Duration(ms=500)
    feedback_size_dva: float = 1.0
    feedback_offset_dva: float = 2.5
    correct_color: Color = (-1.0, 1.0, -1.0)
    wrong_color: Color = (1.0, -1.0, -1.0)
    iti: Duration = Duration(ms=1000)
    practice: SchedulerConfig | None = SchedulerConfig(n_per_condition=2)
    paradigm: SchedulerConfig = SchedulerConfig(n_per_condition=12)

    @model_validator(mode="after")
    def _valid(self) -> ScanningParams:
        if self.subject_kind is SubjectKind.MONKEY:
            raise ValueError(
                "Sternberg's task needs a subject who reads digits and answers yes/no with "
                "keys; declare subject_kind: human"
            )
        keys = (self.positive_key, self.negative_key)
        if keys[0] == keys[1]:
            raise ValueError("positive_key and negative_key must differ")
        for key in keys:
            if key in COMMAND_KEYS or key in RECALL_KEYS or design_digit(key):
                raise ValueError(
                    f"response key {key!r} is taken: digits, Enter and Backspace type the "
                    f"recall, and {sorted(COMMAND_KEYS)} are the experimenter's controls"
                )
        if self.warning_symbol.strip().isdigit() or not self.warning_symbol.strip():
            raise ValueError("the warning signal must be a visible non-digit symbol")
        for name in ("practice", "paradigm"):
            cfg = getattr(self, name)
            if cfg is not None and (cfg.kind != "sequence" or cfg.blocks is not None):
                raise ValueError(
                    f"{name}: this task plans its own blocks; use kind: sequence with "
                    f"n_per_condition (and shuffle), no blocks"
                )
        if self.digit_height_dva <= 0 or self.feedback_size_dva <= 0:
            raise ValueError("sizes must be > 0")
        return self


def design_digit(key: str) -> bool:
    name = key[4:] if key.startswith("num_") else key
    return len(name) == 1 and name.isdigit()


class VariedSetParams(ScanningParams):
    """Experiment 1 (paper: p. 652)."""

    set_sizes: list[int] = [1, 2, 3, 4, 5, 6]
    item_duration: Duration = Duration(ms=1200)
    item_gap: Duration = Duration(ms=0)
    delay: Duration = Duration(ms=2000)
    recall_timeout: Duration = Duration(ms=30000)
    recall_prompt: str = "Type the digits in order, then press Enter"
    prompt_height_dva: float = 0.8

    @model_validator(mode="after")
    def _set_sizes(self) -> VariedSetParams:
        if not self.set_sizes or len(set(self.set_sizes)) != len(self.set_sizes):
            raise ValueError("set_sizes must be a non-empty list without repeats")
        if any(not 1 <= s <= 9 for s in self.set_sizes):
            raise ValueError("every set size must be 1..9 (a negative probe needs a spare digit)")
        return self


class FixedSetParams(ScanningParams):
    """Experiment 2 (paper: p. 652-653)."""

    part_order: list[int] | None = None
    response_to_next_probe: Duration = Duration(ms=3700)
    announcement_text: str = "Your digits for this part:"
    announcement_hint: str = "Press SPACE to start"
    prompt_height_dva: float = 0.8
    practice: SchedulerConfig | None = SchedulerConfig(n_per_condition=4)
    paradigm: SchedulerConfig = SchedulerConfig(n_per_condition=8)

    @model_validator(mode="after")
    def _fixed(self) -> FixedSetParams:
        if self.part_order is not None:
            order = self.part_order
            if not order or len(set(order)) != len(order) or not set(order) <= {1, 2, 4}:
                raise ValueError(
                    "part_order lists positive-set sizes from {1, 2, 4}, each at most once "
                    "(the paper ran all three; a subset is for rehearsals)"
                )
        # The paper fixes one interval: 3.7 s from a response to the next test digit
        # (p. 653). Here it is the feedback light, the inter-trial interval and the warning
        # signal, back to back, so the three must add up to it.
        parts = (self.feedback_duration, self.iti, self.warning_duration)
        if any(d.ms is None for d in (*parts, self.response_to_next_probe)):
            raise ValueError(
                "give feedback_duration, iti, warning_duration and response_to_next_probe in "
                "ms: the first three must add up to the fourth"
            )
        total = sum(d.ms for d in parts)  # type: ignore[misc]
        if not math.isclose(total, self.response_to_next_probe.ms, abs_tol=0.5):  # type: ignore[arg-type]
            raise ValueError(
                f"feedback_duration + iti + warning_duration = {total:g} ms, but "
                f"response_to_next_probe is {self.response_to_next_probe.ms:g} ms: the paper's "
                f"3.7 s from a response to the next test digit is made of exactly these three"
            )
        return self


class _MemoryScanning(Task):
    """What both procedures share. Not a task itself (no name)."""

    outcomes = outcomes(
        CORRECT=dict(completed=True, success=True),
        WRONG=dict(completed=True, success=False),
        NO_RESPONSE=dict(completed=False),
    )
    instructions_file = "instructions.md"

    def instructions(self) -> str | None:
        p: ScanningParams = self.params  # type: ignore[assignment]
        text = (PROJECT / self.instructions_file).read_text(encoding="utf-8")
        return text.replace("{POSITIVE_KEY}", p.positive_key.upper()).replace(
            "{NEGATIVE_KEY}", p.negative_key.upper()
        )

    def _scored(self, ctx: Any) -> Any:
        return self.outcomes["CORRECT"] if ctx.record["correct"] else self.outcomes["WRONG"]

    def _common_stimuli(self, setup: TrialSetup, probe: int) -> dict[str, Any]:
        p: ScanningParams = self.params  # type: ignore[assignment]
        lamp_y = -setup.screen.deg2px(p.feedback_offset_dva)
        return {
            "warning": make_text(setup.display, setup.screen, "warning", p.warning_symbol,
                                 p.digit_height_dva, p.digit_color),
            "probe": make_text(setup.display, setup.screen, "probe", str(probe),
                               p.digit_height_dva, p.digit_color),
            "lamp": make_lamp(setup.display, setup.screen, p.feedback_size_dva, (0.0, lamp_y)),
        }

    def _probe_phases(self, setup: TrialSetup, probe: int, positive: bool) -> list[Any]:
        p: ScanningParams = self.params  # type: ignore[assignment]
        hz = setup.refresh_rate_hz
        return [
            phases.Feedback(["warning"], p.warning_duration.seconds(hz), onset_event="WARNING_ON"),
            ProbeResponse(probe, positive, p.positive_key, p.negative_key,
                          p.response_timeout.seconds(hz), self.outcomes["NO_RESPONSE"],
                          stimulus_keys=["probe"]),
        ]

    def duration_schedule(self, params: Any, rng: np.random.Generator) -> PlannedSchedule:
        # make_source draws only from rng and touches nothing else, so it can be drained.
        return drain(self.make_source(params, rng))

    def simulation(self, seed: int) -> Any:
        from alhazen.modes.simulation import Simulation

        from sternberg1966.simulate import SimulatedObserver

        p: ScanningParams = self.params  # type: ignore[assignment]
        observer = SimulatedObserver(seed=seed, positive_key=p.positive_key,
                                     negative_key=p.negative_key, **self.observer_model)
        return Simulation(response=observer, describe={
            "seed": seed, "source": "sternberg1966.simulate", **observer.describe()})

    observer_model: dict[str, float] = {}

    def demo_views(self, setup: Any) -> list[Any]:
        from sternberg1966.demo import trial_views

        return trial_views(self, setup)


class MemoryScanningTask(_MemoryScanning):
    """Experiment 1, the varied-set procedure (paper: p. 652)."""

    name = "memory-scanning"
    events = EventSchema(("ITEM_ON", "WARNING_ON", "PROBE_ON", "PROBE_DIGIT", "RESPONSE",
                          "FEEDBACK_ON", "RECALL_ON", "RECALL_DONE"))
    params_model = VariedSetParams
    # The simulated subject answers with the paper's own experiment-1 fit (p. 652).
    observer_model = {"intercept_ms": 397.2, "slope_ms": 37.9}

    @classmethod
    def default_params(cls) -> Path:
        return PROJECT / "configs" / "task.yaml"

    def conditions(self, rng: np.random.Generator) -> list[Condition]:
        p: VariedSetParams = self.params  # type: ignore[assignment]
        return [Condition({"set_size": s, "probe": probe})
                for s in p.set_sizes for probe in ("positive", "negative")]

    def make_source(self, params: Any, rng: np.random.Generator) -> BlockPlan:
        """Practice then test, each a shuffled list with every (set size, probe type) cell
        equally often: 24 practice and 144 test trials with the default params."""
        cells = self.conditions(rng)
        sources = []
        for stage, cfg in (("practice", params.practice), ("test", params.paradigm)):
            if cfg is None:
                continue
            staged = [Condition({**c.params, "stage": stage}) for c in cells]
            sources.append(SimpleSequence(staged, n_repeats=cfg.n_per_condition, rng=rng,
                                          shuffle=cfg.shuffle))
        return BlockPlan(sources, rng=rng, breaks=True)

    def build_trial(self, setup: TrialSetup) -> TrialPlan:
        p: VariedSetParams = self.params  # type: ignore[assignment]
        hz = setup.refresh_rate_hz
        c = setup.condition.params
        trial = design.varied_set_trial(int(c["set_size"]), c["probe"] == "positive", setup.rng)
        stimuli = self._common_stimuli(setup, trial.probe)
        prompt_y = setup.screen.deg2px(p.feedback_offset_dva + 0.5)
        stimuli["prompt"] = make_text(setup.display, setup.screen, "prompt", p.recall_prompt,
                                      p.prompt_height_dva, p.digit_color, (0.0, prompt_y))
        stimuli["typed"] = make_text(setup.display, setup.screen, "typed", "",
                                     p.digit_height_dva, p.digit_color)
        plan: list[Any] = []
        for position, digit in enumerate(trial.series, start=1):
            key = f"item{position}"
            stimuli[key] = make_text(setup.display, setup.screen, key, str(digit),
                                     p.digit_height_dva, p.digit_color)
            if position > 1 and p.item_gap.n_frames(hz) > 0:
                plan.append(phases.Blank(p.item_gap.seconds(hz)))
            plan.append(phases.Feedback(
                [key], p.item_duration.seconds(hz),
                on_show=_emitter("ITEM_ON", {"position": position, "digit": digit})))
        plan.append(phases.Blank(p.delay.seconds(hz)))
        plan += self._probe_phases(setup, trial.probe, trial.positive)
        plan.append(FeedbackLight("lamp", p.correct_color, p.wrong_color,
                                  p.feedback_duration.seconds(hz)))
        plan.append(RecallEntry(trial.series, "prompt", "typed", p.recall_timeout.seconds(hz),
                                then=self._scored))
        return TrialPlan(phases=plan, stimuli=stimuli, record={
            "procedure": "varied-set",
            "stage": c["stage"],
            "set_size": len(trial.series),
            "probe_type": c["probe"],
            "series": "".join(str(d) for d in trial.series),
            "probe_digit": trial.probe,
            "probe_position": trial.probe_position,
        })

    def trial_timing(self, condition: Condition, refresh_rate_hz: float) -> TrialTiming:
        p: VariedSetParams = self.params  # type: ignore[assignment]
        hz = refresh_rate_hz
        s = int(condition.params["set_size"])
        return TrialTiming([
            fixed("series", s * p.item_duration.seconds(hz) + (s - 1) * p.item_gap.seconds(hz),
                  "paper: 1.2 s per digit"),
            fixed("delay", p.delay.seconds(hz), "paper: 2.0 s"),
            fixed("warning", p.warning_duration.seconds(hz), "ASSUMED"),
            wait("response", p.response_timeout.seconds(hz), 0.3, "the subject's RT"),
            fixed("feedback light", p.feedback_duration.seconds(hz), "ASSUMED"),
            wait("recall", p.recall_timeout.seconds(hz), 0.5 + 0.4 * s, "typing the series"),
        ])


class FixedSetMemoryScanningTask(_MemoryScanning):
    """Experiment 2, the fixed-set procedure (paper: p. 652-653)."""

    name = "memory-scanning-fixed"
    events = EventSchema(("SET_ANNOUNCED", "WARNING_ON", "PROBE_ON", "PROBE_DIGIT",
                          "RESPONSE", "FEEDBACK_ON"))
    params_model = FixedSetParams
    instructions_file = "instructions-fixed-set.md"
    observer_model = {"intercept_ms": 369.4, "slope_ms": 38.3}

    def __init__(self, params: FixedSetParams) -> None:
        super().__init__(params)
        # Parts whose positive set the subject has read (AwaitKey accepted). Not part of
        # any condition: an announcement aborted or re-served is shown again until read.
        self._announced: set[int] = set()

    @classmethod
    def default_params(cls) -> Path:
        return PROJECT / "configs" / "task-fixed-set.yaml"

    def make_source(self, params: Any, rng: np.random.Generator) -> BlockPlan:
        """Per part: practice, then test, each a random permutation of whole copies of the
        15-stimulus population (paper: p. 653): 4 copies (60 trials) and 8 copies (120)."""
        roles = design.assign_roles(rng)
        cells = design.population(roles)
        sources = []
        for part, size in enumerate(design.part_order(params.part_order, rng), start=1):
            positive = design.positive_set(roles, size)
            for stage, cfg in (("practice", params.practice), ("test", params.paradigm)):
                if cfg is None:
                    continue
                conditions = [Condition({
                    "part": part, "set_size": size, "stage": stage,
                    "positive_set": "".join(str(d) for d in positive),
                    "probe_digit": cell.digit, "probe_role": cell.role,
                    "probe_copy": cell.copy, "probe_type":
                        "positive" if cell.digit in positive else "negative",
                }) for cell in cells]
                sources.append(SimpleSequence(conditions, n_repeats=cfg.n_per_condition,
                                              rng=rng, shuffle=cfg.shuffle))
        return BlockPlan(sources, rng=rng, breaks=True)

    def build_trial(self, setup: TrialSetup) -> TrialPlan:
        p: FixedSetParams = self.params  # type: ignore[assignment]
        hz = setup.refresh_rate_hz
        c = setup.condition.params
        part, probe = int(c["part"]), int(c["probe_digit"])
        stimuli = self._common_stimuli(setup, probe)
        plan: list[Any] = []
        if part not in self._announced:
            digits = " ".join(c["positive_set"])
            gap = setup.screen.deg2px(1.5 * p.digit_height_dva)
            stimuli["announce_text"] = make_text(setup.display, setup.screen, "announce_text",
                                                 p.announcement_text, p.prompt_height_dva,
                                                 p.digit_color, (0.0, gap))
            stimuli["announce_set"] = make_text(setup.display, setup.screen, "announce_set",
                                                digits, p.digit_height_dva, p.digit_color)
            stimuli["announce_hint"] = make_text(setup.display, setup.screen, "announce_hint",
                                                 p.announcement_hint, p.prompt_height_dva,
                                                 p.digit_color, (0.0, -gap))
            plan.append(AwaitKey(["announce_text", "announce_set", "announce_hint"], "space",
                                 "SET_ANNOUNCED",
                                 {"part": part, "digits": [int(d) for d in c["positive_set"]]},
                                 on_accept=lambda: self._announced.add(part)))
            plan.append(phases.Blank(p.iti.seconds(hz)))
        plan += self._probe_phases(setup, probe, c["probe_type"] == "positive")
        plan.append(FeedbackLight("lamp", p.correct_color, p.wrong_color,
                                  p.feedback_duration.seconds(hz), then=self._scored))
        return TrialPlan(phases=plan, stimuli=stimuli, record={
            "procedure": "fixed-set",
            "stage": c["stage"],
            "part": part,
            "set_size": int(c["set_size"]),
            "positive_set": c["positive_set"],
            "probe_type": c["probe_type"],
            "probe_digit": probe,
            "probe_role": c["probe_role"],
        })

    def trial_timing(self, condition: Condition, refresh_rate_hz: float) -> TrialTiming:
        p: FixedSetParams = self.params  # type: ignore[assignment]
        hz = refresh_rate_hz
        return TrialTiming([
            fixed("warning", p.warning_duration.seconds(hz), "ASSUMED"),
            wait("response", p.response_timeout.seconds(hz), 0.3, "the subject's RT"),
            fixed("feedback light", p.feedback_duration.seconds(hz), "ASSUMED"),
        ])


def _emitter(name: str, payload: dict[str, Any]) -> Any:
    def emit(ctx: Any) -> None:
        ctx.emit_on_flip(name, payload)

    return emit
