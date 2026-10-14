"""Experiment 1, part 1: the perceptual task (Lisi & Cavanagh 2015).

A double-drift Gabor moves back and forth along a path of varying orientation, 10 dva to
the right of fixation, until the observer reports with the left or right arrow key whether
the path is tilted left or right of vertical. The physical path orientation is set by
interleaved adaptive staircases, one set for each drift pairing (the stimulus that makes a
right-tilted path look vertical, and the one for a left-tilted path), so the session
finds, for each, the physical orientation that is seen as vertical.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from alhazen import Condition, Duration, Task, TrialPlan, TrialSetup, outcomes
from alhazen.core.events import EventSchema
from alhazen.core.trial import CircleRegion
from alhazen.errors import ConfigError
from alhazen.paradigms.blocks import BlockPlan
from alhazen.paradigms.config import QuestConfig, SchedulerConfig
from alhazen.paradigms.questplus import QuestPlus
from alhazen.task import phases
from alhazen.task.duration import TrialTiming, adaptive_bounds, jittered, wait
from pydantic import model_validator

from lisi_cavanagh2015.common import (
    PROJECT,
    DoubleDriftParams,
    FixatedResponseWindow,
    make_trajectory,
    trajectory_record,
)
from lisi_cavanagh2015.geometry import SIDES
from lisi_cavanagh2015.stimuli import make_dot, make_gabor

STAIRCASE_KEY = "staircase"
ANGLE_KEY = "path_angle_deg"


class PerceptionParams(DoubleDriftParams):
    """The perceptual task's parameters (configs/task-perception.yaml)."""

    left_key: str = "left"
    right_key: str = "right"
    response_timeout: Duration = Duration(ms=30000)
    staircases_per_side: int = 2
    paradigm: SchedulerConfig = SchedulerConfig(
        kind="questplus",
        quest=QuestConfig(parameter=ANGLE_KEY, intensities=[0.0], thresholds=[0.0],
                          interleave_by=STAIRCASE_KEY),
    )

    @model_validator(mode="after")
    def _quest_over_the_path_angle(self) -> PerceptionParams:
        if self.paradigm.kind != "questplus" or self.paradigm.quest is None:
            raise ValueError("the perceptual task's paradigm is kind: questplus")
        if self.paradigm.quest.parameter != ANGLE_KEY:
            raise ValueError(f"the staircases vary {ANGLE_KEY!r}")
        if self.paradigm.quest.interleave_by != STAIRCASE_KEY:
            raise ValueError(f"the staircases are interleaved by {STAIRCASE_KEY!r}")
        if self.staircases_per_side < 1:
            raise ValueError("staircases_per_side must be >= 1")
        if self.left_key == self.right_key:
            raise ValueError("left_key and right_key must differ")
        return self


class RandomInterleavedQuest:
    """One QUEST+ staircase per condition, served in random order.

    alhazen's QuestPlus interleaves its staircases round-robin; the paper interleaved the
    left- and right-tilt trials randomly. Each trial picks one unfinished staircase at
    random. A trial that ends without a response (a fixation break, a blink, no key) is
    served again straight away with the same orientation, as the paper's "immediately
    aborted and repeated", and is never folded into a staircase.
    """

    def __init__(self, quest: QuestConfig, levels: list[dict[str, Any]],
                 rng: np.random.Generator, score: Any) -> None:
        self._rng = rng
        self._n_trials = quest.n_trials
        self._names = [str(level[STAIRCASE_KEY]) for level in levels]
        self._entries = {
            str(level[STAIRCASE_KEY]): QuestPlus(
                parameter=quest.parameter, intensities=quest.intensities,
                thresholds=quest.thresholds, slopes=quest.slopes,
                lower_asymptotes=quest.lower_asymptotes, lapse_rates=quest.lapse_rates,
                n_trials=quest.n_trials, scale=quest.scale, fixed=dict(level), score=score)
            for level in levels
        }
        self._done = {name: 0 for name in self._names}
        self._retry: str | None = None

    def next(self) -> Condition | None:
        if self._retry is not None:
            return self._entries[self._retry].next()
        open_ = [n for n in self._names if self._done[n] < self._n_trials]
        if not open_:
            return None
        name = open_[int(self._rng.integers(len(open_)))]
        return self._entries[name].next()

    def record(self, condition: Condition, result: Any) -> None:
        name = str(condition.params[STAIRCASE_KEY])
        self._entries[name].record(condition, result)
        if result.outcome.completed:
            self._done[name] += 1
            self._retry = None
        else:
            self._retry = name

    def summary(self) -> Any:
        import pandas as pd

        frames = []
        for name, entry in self._entries.items():
            df = entry.summary()
            df[STAIRCASE_KEY] = name
            frames.append(df)
        return pd.concat(frames, ignore_index=True)


class DoubleDriftPerceptionTask(Task):
    name = "double-drift-perception"
    events = EventSchema(("FIX_ON", "FIX_ACQUIRED", "GABOR_ON", "RESPONSE"))
    outcomes = outcomes(
        REPORTED_RIGHT=dict(completed=True, success=True),
        REPORTED_LEFT=dict(completed=True, success=False),
        NO_FIXATION=dict(completed=False),
        FIX_BREAK=dict(completed=False),
        NO_RESPONSE=dict(completed=False),
    )
    params_model = PerceptionParams

    @classmethod
    def default_params(cls) -> Path:
        return PROJECT / "configs" / "task-perception.yaml"

    def instructions(self) -> str | None:
        return (PROJECT / "instructions-perception.md").read_text(encoding="utf-8")

    def conditions(self, rng: np.random.Generator) -> list[Condition]:
        p: PerceptionParams = self.params  # type: ignore[assignment]
        return [
            Condition({STAIRCASE_KEY: f"{side}-{k}", "tilt_side": side})
            for side in SIDES for k in range(1, p.staircases_per_side + 1)
        ]

    def score_trial(self, result: Any) -> bool:
        # What the staircases titrate: the proportion of "right" reports.
        return result.outcome.name == "REPORTED_RIGHT"

    def make_source(self, params: Any, rng: np.random.Generator) -> Any:
        p: PerceptionParams = params
        quest = p.paradigm.quest
        assert quest is not None  # the params validator guarantees it
        levels = [dict(c.params) for c in self.conditions(rng)]
        inner = RandomInterleavedQuest(quest, levels, rng, self.score_trial)
        blocks = p.paradigm.blocks
        if blocks is None:
            return inner
        needed = quest.n_trials * len(levels)
        bound = blocks.trials_per_block
        if bound is not None and blocks.n_blocks * bound < needed:
            raise ConfigError(
                f"{blocks.n_blocks} blocks x {bound} trials = {blocks.n_blocks * bound} "
                f"completed trials, but {len(levels)} staircases x {quest.n_trials} trials need "
                f"{needed}: raise the blocks or lower quest.n_trials")
        return BlockPlan(inner, n_blocks=blocks.n_blocks, trials_per_block=bound, rng=rng,
                         breaks=blocks.breaks, validate_after_break=blocks.validate_after_break)

    def duration_schedule(self, params: Any, rng: np.random.Generator) -> Any:
        return adaptive_bounds(params.paradigm, self.conditions(rng))

    def trial_timing(self, condition: Condition, refresh_rate_hz: float) -> TrialTiming:
        p: PerceptionParams = self.params  # type: ignore[assignment]
        hz = refresh_rate_hz
        return TrialTiming([
            wait("acquire fixation", p.acquire_timeout.seconds(hz)),
            jittered("foreperiod", p.foreperiod.seconds(hz), p.foreperiod_jitter.seconds(hz)),
            wait("double-drift until the response", p.response_timeout.seconds(hz),
                 minimum_s=0.3),
        ])

    def build_trial(self, setup: TrialSetup) -> TrialPlan:
        p: PerceptionParams = self.params  # type: ignore[assignment]
        hz = setup.refresh_rate_hz
        cond = setup.condition.params
        start = str(setup.rng.choice(p.start_directions))
        traj = make_trajectory(p, angle_deg=float(cond[ANGLE_KEY]), side=str(cond["tilt_side"]),
                               internal_motion=True, start_direction=start, rng=setup.rng)
        o = self.outcomes
        window = setup.screen.deg2px(p.fix_window_dva)
        return TrialPlan(
            phases=[
                phases.AcquireFixation(hold_s=p.acquire_hold.seconds(hz),
                                       timeout_s=p.acquire_timeout.seconds(hz),
                                       on_timeout=o["NO_FIXATION"]),
                phases.HoldFixation(duration_s=p.foreperiod.seconds(hz),
                                    jitter_s=p.foreperiod_jitter.seconds(hz),
                                    on_break=o["FIX_BREAK"],
                                    duration_record_key="foreperiod_s"),
                FixatedResponseWindow(
                    keys={p.left_key: o["REPORTED_LEFT"], p.right_key: o["REPORTED_RIGHT"]},
                    timeout_s=p.response_timeout.seconds(hz), on_timeout=o["NO_RESPONSE"],
                    stimulus_keys=["fixation", "gabor"], onset_event="GABOR_ON",
                    region="fixation", on_break=o["FIX_BREAK"]),
            ],
            stimuli={
                "fixation": make_dot(setup.display, setup.screen, p.fix_size_dva, p.fix_color),
                "gabor": make_gabor(setup.display, setup.screen, traj),
            },
            regions={"fixation": CircleRegion((0.0, 0.0), window)},
            record={**trajectory_record(traj), STAIRCASE_KEY: cond[STAIRCASE_KEY]},
        )

    def score(self, record: dict[str, Any]) -> dict[str, Any]:
        out = dict(record)
        key = out.get("response_key")
        if isinstance(key, str):
            out["reported_right"] = key == self.params.right_key  # type: ignore[attr-defined]
        return out

    def simulation(self, seed: int) -> Any:
        from alhazen.modes.simulation import Simulation

        from lisi_cavanagh2015.simulate import autopilot_for

        task, tracker, response = autopilot_for(type(self), self.params, seed,
                                                model=getattr(self, "observer_model", None))
        return Simulation(task=task, tracker=tracker, response=response,
                          describe={"seed": seed, "source": "lisi_cavanagh2015.simulate",
                                    **tracker.describe()})
