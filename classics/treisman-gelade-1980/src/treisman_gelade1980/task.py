"""Feature vs conjunction search (Treisman & Gelade, 1980, Experiments I and II).

One trial (paper p. 103): a plain white field; on "ready" a white field with a central
fixation spot for 1 s; then the search display, until the subject presses the key for
"target present" (dominant hand) or "target absent" (other hand); then the RT and whether
it was correct. docs/methods.md is the specification; configs/task*.yaml the parameters.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from string import Template
from typing import Literal

import numpy as np
from alhazen import Condition, Duration, SubjectParams, Task, TrialPlan, TrialSetup, outcomes
from alhazen.config.models import Model
from alhazen.core.events import EventSchema
from alhazen.paradigms.config import SchedulerConfig
from alhazen.task import phases as alhazen_phases
from alhazen.task.duration import PlannedSchedule, TrialTiming, fixed, wait
from pydantic import field_validator, model_validator

from treisman_gelade1980 import design, glyphs
from treisman_gelade1980.phases import ReadyKey, SearchFeedback
from treisman_gelade1980.source import CardQueue
from treisman_gelade1980.stimuli import make_feedback_text, make_picture

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]

RGB = tuple[int, int, int]


class Matrix(Model):
    """One regular matrix of Experiment II (paper p. 108): rows x cols, and the extent the
    letters cover, in deg."""

    rows: int
    cols: int
    width_dva: float
    height_dva: float


class FeatureConjunctionSearchTaskParams(SubjectParams):
    """A block's parameters. Durations resolve to whole frames at the measured rate."""

    experiment: Literal[1, 2] = 1
    condition: Literal["conjunction", "feature", "easy", "difficult"] = "conjunction"
    display_sizes: list[int] = [1, 5, 15, 30]
    layout: Literal["scatter", "matrix"] = "scatter"
    # Experiment I: the scattered field and its sections.
    field_width_dva: float | None = 14.0
    field_height_dva: float | None = 8.0
    inner_ellipse_width_dva: float | None = 8.5
    inner_ellipse_height_dva: float | None = 5.5
    min_spacing_dva: float | None = 1.2
    # Experiment II: matrices by display size (1 item uses the 4-item matrix's cells).
    matrices: dict[int, Matrix] | None = None
    letter_height_dva: float = 0.8
    letter_width_dva: float = 0.6
    stroke_dva: float = 0.12
    targets: list[str] = ["T_green"]
    distractors: list[str] = ["T_brown", "X_green"]
    target_description: str = "a green T"
    inks: dict[str, RGB] = {"green": (0, 150, 70), "brown": (140, 85, 35)}
    background_rgb: RGB = (255, 255, 255)
    fixation_size_dva: float = 0.25
    fixation_rgb: RGB = (0, 0, 0)
    feedback_rgb: RGB = (0, 0, 0)
    feedback_height_dva: float = 0.8
    fixation_duration: Duration = Duration(ms=1000)
    response_timeout: Duration = Duration(ms=10000)
    ready_timeout: Duration = Duration(ms=60000)
    feedback_duration: Duration = Duration(ms=1500)
    cards_per_cell: int = 8
    dominant_hand: Literal["right", "left"] = "right"
    left_key: str = "f"
    right_key: str = "j"
    ready_key: str = "space"
    repeat_errors: bool = True
    dummy_after_error: bool = True
    paradigm: SchedulerConfig = SchedulerConfig(n_per_condition=2)

    @field_validator("display_sizes")
    @classmethod
    def _sizes(cls, v: list[int]) -> list[int]:
        if not v or any(n < 1 for n in v) or len(set(v)) != len(v):
            raise ValueError("display_sizes must be distinct positive integers")
        return v

    @model_validator(mode="after")
    def _consistent(self) -> FeatureConjunctionSearchTaskParams:
        if self.condition not in design.CONDITIONS_BY_EXPERIMENT[self.experiment]:
            allowed = design.CONDITIONS_BY_EXPERIMENT[self.experiment]
            raise ValueError(f"condition {self.condition!r} is not one of Experiment "
                             f"{self.experiment}'s: {allowed}")
        for g in [*self.targets, *self.distractors]:
            letter, _, ink = g.partition("_")
            if letter not in glyphs.LETTERS or ink not in self.inks:
                raise ValueError(f"glyph {g!r} must be <letter>_<ink> with a letter in "
                                 f"{sorted(glyphs.LETTERS)} and an ink in inks {sorted(self.inks)}")
        if set(self.targets) & set(self.distractors):
            raise ValueError("a target cannot also be a distractor")
        if self.layout == "scatter":
            needed = (self.field_width_dva, self.field_height_dva, self.inner_ellipse_width_dva,
                      self.inner_ellipse_height_dva, self.min_spacing_dva)
            if any(v is None for v in needed):
                raise ValueError(
                    "layout scatter needs the field, inner ellipse and min_spacing_dva")
        else:
            if not self.matrices:
                raise ValueError("layout matrix needs matrices")
            for n in self.display_sizes:
                m = self.matrices.get(4 if n == 1 else n)
                if m is None:
                    raise ValueError(f"no matrix for display size {n}")
                if n != 1 and m.rows * m.cols != n:
                    raise ValueError(f"display size {n} does not fill a {m.rows} x {m.cols} matrix")
        if self.cards_per_cell < 1:
            raise ValueError("cards_per_cell must be >= 1")
        if self.left_key == self.right_key or self.ready_key in (self.left_key, self.right_key):
            raise ValueError("the ready key and the two response keys must all differ")
        if self.paradigm.kind != "sequence" or self.paradigm.blocks is not None:
            raise ValueError("this task serves one block of cards: paradigm kind sequence, "
                             "no blocks "
                             "(n_per_condition is how often each card is shown)")
        return self

    @property
    def present_key(self) -> str:
        """The dominant hand's key (paper p. 103)."""
        return self.right_key if self.dominant_hand == "right" else self.left_key

    @property
    def absent_key(self) -> str:
        return self.left_key if self.dominant_hand == "right" else self.right_key


class FeatureConjunctionSearchTask(Task):
    name = "feature-conjunction-search"
    events = EventSchema(("READY_ON", "FIX_ON", "ARRAY_ON", "RESPONSE", "FEEDBACK_ON"))
    outcomes = outcomes(
        CORRECT=dict(completed=True, success=True),
        WRONG=dict(completed=True, success=False),
        NO_RESPONSE=dict(completed=False),
        NOT_STARTED=dict(completed=False),
    )
    params_model = FeatureConjunctionSearchTaskParams

    FEEDBACK_LABELS = {"CORRECT": "Correct", "WRONG": "Error", "NO_RESPONSE": "No response"}

    @classmethod
    def default_params(cls) -> Path:
        return PROJECT / "configs" / "task.yaml"

    def instructions(self) -> str | None:
        p: FeatureConjunctionSearchTaskParams = self.params  # type: ignore[assignment]
        text = (PROJECT / "instructions.md").read_text(encoding="utf-8")
        return Template(text).substitute(
            target=p.target_description, present_key=p.present_key.upper(),
            absent_key=p.absent_key.upper(), ready_key=p.ready_key.upper(),
            present_hand=p.dominant_hand,
            absent_hand="left" if p.dominant_hand == "right" else "right")

    # -- the design ---------------------------------------------------------

    def deck(self, rng: np.random.Generator) -> list[Condition]:
        """One block: every card ``paradigm.n_per_condition`` times (``rep`` 1..n)."""
        p: FeatureConjunctionSearchTaskParams = self.params  # type: ignore[assignment]
        cards = design.build_deck(p, rng)
        return [Condition({**c, "rep": r + 1, "dummy": 0, "dummy_n": 0})
                for c in cards for r in range(p.paradigm.n_per_condition)]

    def conditions(self, rng: np.random.Generator) -> list[Condition]:
        return self.deck(rng)

    def make_source(self, params, rng: np.random.Generator) -> CardQueue:
        p: FeatureConjunctionSearchTaskParams = params
        return CardQueue(self.deck(rng), rng, repeat_errors=p.repeat_errors,
                         dummy_after_error=p.dummy_after_error)

    def duration_schedule(self, params, rng: np.random.Generator) -> PlannedSchedule:
        deck = tuple(self.deck(rng))
        return PlannedSchedule(
            blocks=(deck,), breaks=0, n_cells=len(deck),
            note="every error adds the card again later in the block and one dummy trial "
                 "(paper p. 103), so a block runs about two trials longer per error")

    def trial_timing(self, condition: Condition, refresh_rate_hz: float) -> TrialTiming:
        p: FeatureConjunctionSearchTaskParams = self.params  # type: ignore[assignment]
        hz = refresh_rate_hz
        return TrialTiming([
            wait("ready (subject presses the ready key)", p.ready_timeout.seconds(hz)),
            fixed("fixation spot", p.fixation_duration.seconds(hz), "paper p. 103"),
            wait("search display until the response", p.response_timeout.seconds(hz)),
            fixed("feedback", p.feedback_duration.seconds(hz)),
        ])

    # -- one trial ----------------------------------------------------------

    def build_trial(self, setup: TrialSetup) -> TrialPlan:
        p: FeatureConjunctionSearchTaskParams = self.params  # type: ignore[assignment]
        hz = setup.refresh_rate_hz
        cond = setup.condition.params
        card = design.build_card(p, cond)
        screen = setup.screen
        geometry = dict(width_px=screen.width_px, height_px=screen.height_px,
                        px_per_deg=screen.px_per_deg, p=p)
        array_patch, array_centre = glyphs.render_patch(card.items, **geometry)
        fix_patch, fix_centre = glyphs.render_patch([], fixation=True, **geometry)
        bg = p.background_rgb
        stimuli = {
            "ready": make_picture(setup.display, screen, "ready", bg, None, (0.0, 0.0)),
            "fixation": make_picture(setup.display, screen, "fixation", bg, fix_patch, fix_centre),
            "array": make_picture(setup.display, screen, "array", bg, array_patch, array_centre),
            "feedback": make_feedback_text(setup.display, screen, bg, p.feedback_rgb,
                                           p.feedback_height_dva),
        }
        present = bool(cond["target_present"])
        correct, wrong = self.outcomes["CORRECT"], self.outcomes["WRONG"]
        keys = {p.present_key: correct if present else wrong,
                p.absent_key: wrong if present else correct}
        target = card.target
        record = {
            "experiment": p.experiment,
            "target_region": design.place_label(p, cond),
            "target_x_dva": round(target.x, 3) if target else None,
            "target_y_dva": round(target.y, 3) if target else None,
            "target_ecc_dva": round(math.hypot(target.x, target.y), 3) if target else None,
            "mean_ecc_dva": round(float(np.mean([math.hypot(i.x, i.y) for i in card.items])), 3),
            "n_items": len(card.items),
            "present_key": p.present_key,
            "absent_key": p.absent_key,
            "items": json.dumps([i.as_dict() for i in card.items], separators=(",", ":")),
        }
        return TrialPlan(
            phases=[
                ReadyKey(p.ready_key, p.ready_timeout.seconds(hz), self.outcomes["NOT_STARTED"],
                         ["ready"]),
                alhazen_phases.Feedback(["fixation"], p.fixation_duration.seconds(hz),
                                        onset_event="FIX_ON"),
                alhazen_phases.ResponseWindow(
                    keys=keys, timeout_s=p.response_timeout.seconds(hz),
                    on_timeout=self.outcomes["NO_RESPONSE"], stimulus_keys=["array"],
                    onset_event="ARRAY_ON"),
                SearchFeedback(p.feedback_duration.seconds(hz), self.FEEDBACK_LABELS),
            ],
            stimuli=stimuli,
            record=record,
        )

    def score(self, record: dict) -> dict:
        key = record.get("response_key")
        if key is not None:
            record["response"] = "present" if key == record.get("present_key") else "absent"
        return record

    # -- other modes --------------------------------------------------------

    def demo_views(self, setup):
        from alhazen.modes.demo import DemoView

        from treisman_gelade1980.stimuli import make_picture as picture

        p: FeatureConjunctionSearchTaskParams = self.params  # type: ignore[assignment]
        geometry = dict(width_px=setup.screen.width_px, height_px=setup.screen.height_px,
                        px_per_deg=setup.screen.px_per_deg, p=p)
        views = []
        deck = design.build_deck(p, setup.rng)
        for n in p.display_sizes:
            for present in (1, 0):
                cond = next(c for c in deck
                            if c["display_size"] == n and c["target_present"] == present)
                patch, centre = glyphs.render_patch(design.build_card(p, cond).items, **geometry)
                stim = picture(setup.display, setup.screen, "array", p.background_rgb, patch,
                               centre)
                label = "target present" if present else "target absent"
                views.append(DemoView(name=f"{n}-{label}",
                                      caption=f"{p.condition}: {n} items, {label}",
                                      draw=lambda t, s=stim: s.draw()))
        return views

    def simulation(self, seed: int):
        from alhazen.modes.simulation import Simulation

        from treisman_gelade1980.simulate import SimulatedSearcher, SimulatedSearchTask

        observer = SimulatedSearcher(seed=seed)
        return Simulation(response=observer, task=SimulatedSearchTask(self.params, observer),
                          describe={"seed": seed, "source": "treisman_gelade1980.simulate",
                                    **observer.describe()})
