"""Stroop (1935) color-word interference, one item per trial, answered by key.

Two tasks share everything but what the subject responds to:

- ``stroop-color-naming`` is Experiment 2: name the ink. The control test is
  NC (solid colour squares), the interference test NCWd (colour words printed
  in another colour's ink).
- ``stroop-word-reading`` is Experiment 1's comparison: respond to the word.
  The control test is RCNb (the words printed in black), the interference test
  RCNd (the same words printed in another colour's ink).

A session is four blocks, one test sheet each, in Stroop's balanced order
(control, interference, interference, control, or the reverse for the other
half of the subjects; reprint p. 17), forms 1 and 2 alternating. Each item is
one trial: a fixation point, then the item until the right key is pressed.
docs/methods.md is the specification; every value the paper does not state is
in its "Assumed, not in the paper" table.
"""

from __future__ import annotations

import argparse
import logging
import re
import zlib
from pathlib import Path
from typing import Any, ClassVar, Literal

import numpy as np
from alhazen import Duration, Model, SubjectParams, Task, TrialPlan, TrialSetup, outcomes
from alhazen.core.events import EventSchema
from alhazen.errors import ConfigError
from alhazen.modes import Mode
from alhazen.paradigms.base import Condition, SimpleSequence
from alhazen.paradigms.blocks import BlockPlan
from alhazen.stimuli.fixation import make_fixation
from alhazen.task import phases
from alhazen.task.duration import PlannedSchedule, TrialTiming, drain, fixed, wait
from pydantic import field_validator, model_validator

from stroop1935 import sheet
from stroop1935.phases import CorrectedResponse
from stroop1935.stimuli import apply_background, make_patch, make_word

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
log = logging.getLogger(__name__)

RGB = tuple[float, float, float]


class RehearsalSizes(Model):
    """How much of each list a rehearsal (test and simulate modes) serves.

    Not part of the paradigm: a rehearsal checks that the session runs, and
    the full 445-trial session would take a quarter of an hour. ``params_hook``
    applies these only in test and simulate modes and says so in the log; the
    reduced numbers are what the run's config snapshot records."""

    sheet_items: int = 5
    practice_trials: int = 2
    key_practice_trials: int = 3


class StroopParams(SubjectParams):
    """A session's parameters. Every field is set in the params file, which is
    the single place the values live (configs/task*.yaml); none has a default
    here except the ones the session fills in itself."""

    background_rgb: RGB
    colors: dict[str, RGB]
    black_rgb: RGB
    font: str
    letter_height_dva: float
    patch_size_dva: float
    fixation_size_dva: float
    fixation_rgb: RGB
    fixation_duration: Duration
    response_timeout: Duration
    iti: Duration
    keys: dict[str, str]
    require_correction: bool
    practice_trials: int
    key_practice_trials: int
    sheet_items: int
    block_order: Literal["by_subject", "A", "B"]
    # Filled in by params_hook when block_order is by_subject: how the order
    # was chosen, so the run's config snapshot says it.
    block_order_basis: str | None = None
    form_sequence: tuple[int, int, int, int]
    sheet_seed: int
    rehearsal: RehearsalSizes = RehearsalSizes()

    @field_validator("background_rgb", "black_rgb", "fixation_rgb")
    @classmethod
    def _rgb(cls, v: RGB) -> RGB:
        if not all(-1.0 <= x <= 1.0 for x in v):
            raise ValueError(f"colours are PsychoPy rgb triples in -1..1, got {v}")
        return v

    @model_validator(mode="after")
    def _consistent(self) -> StroopParams:
        names = set(sheet.COLORS)
        if set(self.colors) != names:
            raise ValueError(f"colors must name exactly {sorted(names)}, got {sorted(self.colors)}")
        for name, v in self.colors.items():
            self._rgb(v)
            if tuple(v) == tuple(self.background_rgb):
                raise ValueError(f"ink {name} is the background colour")
        if set(self.keys) != names:
            raise ValueError(f"keys must map exactly {sorted(names)}, got {sorted(self.keys)}")
        bound = list(self.keys.values())
        if len(set(bound)) != len(bound):
            raise ValueError(f"each colour needs its own key, got {self.keys}")
        if "space" in bound or "escape" in bound:
            raise ValueError("space and escape belong to the session (start, pause, quit)")
        if not 1 <= self.sheet_items <= sheet.N_ITEMS:
            raise ValueError(f"sheet_items must be 1..{sheet.N_ITEMS}, got {self.sheet_items}")
        if not 0 <= self.practice_trials <= sheet.SIDE:
            raise ValueError(f"practice_trials must be 0..{sheet.SIDE}")
        if self.key_practice_trials < 0:
            raise ValueError("key_practice_trials must be >= 0")
        if any(f not in (1, 2) for f in self.form_sequence):
            raise ValueError(f"form_sequence holds forms 1 and 2, got {self.form_sequence}")
        for d in ("letter_height_dva", "patch_size_dva", "fixation_size_dva"):
            if getattr(self, d) <= 0:
                raise ValueError(f"{d} must be > 0")
        if self.response_timeout.ms is not None and self.response_timeout.ms <= 0:
            raise ValueError("response_timeout must be > 0")
        return self


def order_for_subject(subject: str) -> tuple[Literal["A", "B"], str]:
    """Which half of the subjects ``subject`` is in, and why.

    Stroop assigned half the subjects of each sex, "selected at random", to
    each order (p. 17). The rule here (ASSUMED) makes the halves exact for
    numbered subjects: the last number in the id, odd for order A and even for
    order B. An id with no number falls back to the parity of its CRC-32.
    """
    numbers = re.findall(r"\d+", subject)
    if numbers:
        n = int(numbers[-1])
        order: Literal["A", "B"] = "A" if n % 2 == 1 else "B"
        return order, f"subject {subject!r}: number {n} is {'odd' if n % 2 else 'even'}"
    c = zlib.crc32(subject.encode("utf-8"))
    order = "A" if c % 2 == 0 else "B"
    parity = "even" if c % 2 == 0 else "odd"
    return order, f"subject {subject!r} has no number: CRC-32 {c} is {parity}"


class StroopTask(Task):
    """The shared paradigm. Subclasses say which tests and what to respond to."""

    events = EventSchema(("FIX_ON", "RESPONSE_CUE", "RESPONSE", "CORRECTION"))
    outcomes = outcomes(
        CORRECT=dict(completed=True, success=True),
        CORRECTED=dict(completed=True, success=False),
        UNCORRECTED=dict(completed=True, success=False),
        WRONG=dict(completed=True, success=False),
        NO_RESPONSE=dict(completed=False),
    )
    params_model = StroopParams

    CONTROL: ClassVar[str]
    INTERFERENCE: ClassVar[str]
    RESPOND_TO: ClassVar[Literal["ink", "word"]]
    PARAMS_FILE: ClassVar[str]
    INSTRUCTIONS_SECTION: ClassVar[str]

    @classmethod
    def default_params(cls) -> Path:
        return PROJECT / "configs" / cls.PARAMS_FILE

    @classmethod
    def params_hook(cls, params: StroopParams, args: argparse.Namespace) -> StroopParams:
        """Settle the block order by subject, and shrink a rehearsal.

        In every mode that runs trials, a ``by_subject`` block order becomes A
        or B (``order_for_subject``), with the reason kept in
        ``block_order_basis``. In test and simulate modes the lists are cut to
        ``rehearsal`` sizes; the log says by how much. Run mode always serves
        the params file's own numbers.
        """
        mode = Mode(args.mode)
        if not mode.runs_trials:
            return params
        data = params.model_dump()
        if params.block_order == "by_subject":
            subject = getattr(args, "sub", None)
            if subject is None:
                raise ConfigError("block_order is by_subject and this session has no --sub; "
                                  "set block_order to A or B in the params file")
            order, basis = order_for_subject(str(subject))
            data["block_order"] = order
            data["block_order_basis"] = basis
            log.info("block order %s (%s)", order, basis)
        if not mode.drives_subject:
            for field in ("sheet_items", "practice_trials", "key_practice_trials"):
                small = getattr(params.rehearsal, field)
                if getattr(params, field) > small:
                    log.warning("%s rehearsal: %s %d -> %d", mode.value, field,
                                getattr(params, field), small)
                    data[field] = small
        return type(params).model_validate(data)

    def instructions(self) -> str | None:
        text = (PROJECT / "instructions.md").read_text(encoding="utf-8")
        sections = {}
        for chunk in re.split(r"^## ", text, flags=re.M)[1:]:
            title, _, body = chunk.partition("\n")
            sections[title.strip()] = body.strip()
        body = sections[self.INSTRUCTIONS_SECTION]
        p: StroopParams = self.params  # type: ignore[assignment]
        mapping = "\n".join(f"    {p.keys[c].upper()}   {c}" for c in sheet.COLORS)
        return body.replace("{KEYS}", mapping)

    # ------------------------------------------------------------------
    # The plan: four sheets in Stroop's balanced order
    # ------------------------------------------------------------------

    def block_tests(self, order: str) -> list[str]:
        c, i = self.CONTROL, self.INTERFERENCE
        return [c, i, i, c] if order == "A" else [i, c, c, i]

    def plan(self, params: StroopParams) -> list[list[Condition]]:
        """Each block's conditions in the order they are served."""
        if params.block_order == "by_subject":
            raise ConfigError(
                "the block order is not settled: params_hook sets it by subject when a "
                "session starts through run.py; a session built another way must set "
                "block_order to A or B")
        tests = self.block_tests(params.block_order)
        blocks: list[list[Condition]] = []
        sampled: set[str] = set()
        for index, (test, form) in enumerate(zip(tests, params.form_sequence, strict=True)):
            served: list[Condition] = []
            if index == 0 and params.key_practice_trials:
                for item in sheet.key_practice(self.CONTROL, params.sheet_seed,
                                               params.key_practice_trials):
                    served.append(self._condition("key_practice", self.CONTROL, 0, item))
            if test not in sampled and params.practice_trials:
                for item in sheet.sample(test, params.sheet_seed, params.practice_trials):
                    served.append(self._condition("practice", test, 0, item))
            sampled.add(test)
            for item in sheet.items(test, params.sheet_seed, form)[: params.sheet_items]:
                served.append(self._condition("test", test, form, item))
            blocks.append(served)
        return blocks

    @staticmethod
    def _condition(phase: str, test: str, form: int, item: sheet.Item) -> Condition:
        return Condition({"phase": phase, "test": test, "form": form, "position": item.position,
                          "row": item.row, "col": item.col, "ink": item.ink, "word": item.word})

    def conditions(self, rng: np.random.Generator) -> list[Condition]:
        p: StroopParams = self.params  # type: ignore[assignment]
        settled = p if p.block_order != "by_subject" else p.model_copy(update={"block_order": "A"})
        return [c for block in self.plan(settled) for c in block]

    def make_source(self, params: Any, rng: np.random.Generator) -> BlockPlan:
        # One block per sheet, served in sheet order (no shuffle: the sheet's
        # arrangement is the design). An item with no response goes back to
        # the end of its own block (alhazen's re-serve rule).
        return BlockPlan([SimpleSequence(block, shuffle=False) for block in self.plan(params)],
                         breaks=True)

    def duration_schedule(self, params: Any, rng: np.random.Generator) -> PlannedSchedule:
        settled = (params if params.block_order != "by_subject"
                   else params.model_copy(update={"block_order": "A"}))
        return drain(self.make_source(settled, rng))

    def trial_timing(self, condition: Condition, refresh_rate_hz: float) -> TrialTiming:
        p: StroopParams = self.params  # type: ignore[assignment]
        return TrialTiming([
            fixed("fixation", p.fixation_duration.seconds(refresh_rate_hz), "fixation_duration"),
            wait("item until the right key", p.response_timeout.seconds(refresh_rate_hz),
                 basis="response_timeout"),
        ])

    # ------------------------------------------------------------------
    # One trial
    # ------------------------------------------------------------------

    def answer(self, ink: str, word: str) -> tuple[str, str]:
        """(the colour the subject must give, the competing colour or "")."""
        if self.RESPOND_TO == "ink":
            return ink, (word if word and word != ink else "")
        return word, (ink if ink in sheet.COLORS and ink != word else "")

    def build_trial(self, setup: TrialSetup) -> TrialPlan:
        p: StroopParams = self.params  # type: ignore[assignment]
        hz = setup.refresh_rate_hz
        cond = setup.condition.params
        apply_background(setup.display, p.background_rgb)
        target, competitor = self.answer(cond["ink"], cond["word"])
        ink_rgb = p.black_rgb if cond["ink"] == "black" else p.colors[cond["ink"]]
        if cond["word"]:
            stimulus = make_word(setup.display, setup.screen, cond["word"], ink_rgb,
                                 p.letter_height_dva, p.font)
        else:
            stimulus = make_patch(setup.display, setup.screen, ink_rgb, p.patch_size_dva)
        o = self.outcomes
        return TrialPlan(
            phases=[
                phases.Feedback(["fixation"], p.fixation_duration.seconds(hz),
                                onset_event="FIX_ON"),
                CorrectedResponse(
                    tuple(p.keys[c] for c in sheet.COLORS), p.keys[target],
                    p.response_timeout.seconds(hz),
                    on_correct=o["CORRECT"], on_corrected=o["CORRECTED"],
                    on_uncorrected=o["UNCORRECTED"], on_wrong=o["WRONG"],
                    on_timeout=o["NO_RESPONSE"], require_correction=p.require_correction,
                    stimulus_keys=["stimulus"]),
            ],
            stimuli={
                "fixation": make_fixation(setup.display, setup.screen, p.fixation_size_dva,
                                          fill_color=p.fixation_rgb),
                "stimulus": stimulus,
            },
            record={
                "respond_to": self.RESPOND_TO,
                "target_color": target,
                "correct_key": p.keys[target],
                "competing_color": competitor,
                "competing_key": p.keys[competitor] if competitor else "",
                "block_order": p.block_order,
            },
        )

    # ------------------------------------------------------------------
    # The other modes
    # ------------------------------------------------------------------

    def demo_views(self, setup: Any) -> list[Any]:
        from alhazen.modes.demo import DemoView

        p: StroopParams = setup.params
        apply_background(setup.display, p.background_rgb)
        views = []
        for key, test in (("1", self.CONTROL), ("2", self.INTERFERENCE)):
            for item in sheet.items(test, p.sheet_seed, 1)[:3]:
                rgb = p.black_rgb if item.ink == "black" else p.colors[item.ink]
                stim = (make_word(setup.display, setup.screen, item.word, rgb,
                                  p.letter_height_dva, p.font) if item.word
                        else make_patch(setup.display, setup.screen, rgb, p.patch_size_dva))
                target, _ = self.answer(item.ink, item.word)
                views.append(DemoView(
                    name=f"{test} item {item.position}",
                    caption=f"{test}: ink {item.ink}, word {item.word or '(square)'}; "
                            f"answer {target} = key {p.keys[target].upper()}",
                    draw=lambda _t, s=stim: s.draw(), key=key if item.position == 1 else None))
        return views

    def simulation(self, seed: int) -> Any:
        from alhazen.modes.simulation import Simulation

        from stroop1935.simulate import SimulatedObserver, autopilot

        observer = SimulatedObserver(seed=seed)
        return Simulation(response=observer, task=autopilot(self, observer),
                          describe=observer.describe())


class StroopColorNamingTask(StroopTask):
    """Experiment 2: give the ink colour; squares (NC) vs incongruent words (NCWd)."""

    name = "stroop-color-naming"
    CONTROL = sheet.NC
    INTERFERENCE = sheet.NCWD
    RESPOND_TO = "ink"
    PARAMS_FILE = "task.yaml"
    INSTRUCTIONS_SECTION = "Colour naming"


class StroopWordReadingTask(StroopTask):
    """Experiment 1's comparison, by key: give the word; black (RCNb) vs ink (RCNd)."""

    name = "stroop-word-reading"
    CONTROL = sheet.RCNB
    INTERFERENCE = sheet.RCND
    RESPOND_TO = "word"
    PARAMS_FILE = "task-word-reading.yaml"
    INSTRUCTIONS_SECTION = "Word reading"
