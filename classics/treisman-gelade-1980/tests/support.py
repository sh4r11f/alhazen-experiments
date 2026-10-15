"""Shared helpers for the tests: a trial runner on alhazen's fake clock, and the configs."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from alhazen import InputFrame
from alhazen.config.loader import build_session_config, load_params
from alhazen.config.models import DisplayConfig, MonitorConfig, RigConfig, SessionInfo
from alhazen.core.engine import TrialEngine
from alhazen.core.events import EventBus
from alhazen.core.trial import TrialContext
from alhazen.display.screen import Screen
from alhazen.paradigms.base import Condition
from alhazen.task.plan import TrialSetup
from alhazen.testing import EventCollector, FakeClock, FakeDisplay, ScriptedCommands, ScriptedInputs

from treisman_gelade1980.task import (
    PROJECT,
    FeatureConjunctionSearchTask,
    FeatureConjunctionSearchTaskParams,
)

FRAME_S = 1 / 60
SCREEN = Screen(width_px=1920, height_px=1080, px_per_deg=40.0)
CONFIGS = sorted((PROJECT / "configs").glob("task*.yaml"))
SIM_RIG = (
    "monitor: {{name: sim, width_px: 1920, height_px: 1080, width_cm: 53.0, distance_cm: 57.0,"
    " refresh_rate_hz: 60.0, fullscreen: false}}\n"
    "display: {{backend: simulated}}\n"
    "devices: {{}}\ndata_root: {data}\nreal_data: false\n"
)


def params(name: str = "task.yaml", **overrides) -> FeatureConjunctionSearchTaskParams:
    p = load_params(PROJECT / "configs" / name, FeatureConjunctionSearchTaskParams)
    return p.model_copy(update=overrides) if overrides else p


def short_params_file(tmp: Path, name: str = "task.yaml") -> Path:
    """A quick version of a params file for end-to-end runs: one card per cell, each
    shown once, short fixation and feedback. Everything else as shipped."""
    import yaml

    data = yaml.safe_load((PROJECT / "configs" / name).read_text(encoding="utf-8"))
    data.update(cards_per_cell=1, fixation_duration={"ms": 200}, feedback_duration={"ms": 200})
    data["paradigm"]["n_per_condition"] = 1
    out = tmp / f"short-{name}"
    out.write_text(yaml.safe_dump(data), encoding="utf-8")
    return out


def sim_rig(tmp: Path) -> Path:
    rig = tmp / "rig-sim.yaml"
    rig.write_text(SIM_RIG.format(data=tmp / "data"), encoding="utf-8")
    return rig


def a_condition(task: FeatureConjunctionSearchTask, *, size: int, present: bool,
                seed: int = 0) -> dict:
    deck = task.deck(np.random.default_rng(seed))
    return next(c.params for c in deck
                if c.params["display_size"] == size and c.params["target_present"] == int(present))


def run_trial(task, condition: dict, inputs: list[InputFrame]):
    clock = FakeClock()
    display = FakeDisplay(clock, FRAME_S)
    bus = EventBus()
    collector = EventCollector()
    bus.subscribe(collector)
    engine = TrialEngine(display=display, clock=clock, bus=bus, schema=task.events,
                         commands=ScriptedCommands(), input_provider=ScriptedInputs(inputs))
    monitor = MonitorConfig(width_px=1920, height_px=1080, width_cm=60.0, distance_cm=60.0,
                            refresh_rate_hz=60.0, fullscreen=False)
    setup = TrialSetup(
        cfg=build_session_config(
            RigConfig(monitor=monitor, display=DisplayConfig(backend="simulated"), data_root="."),
            SessionInfo(subject="t01", session=1, run=1, task_name=task.name, seed=1),
            task.params, {}),
        screen=SCREEN, display=display, rng=np.random.default_rng(0),
        refresh_rate_hz=1 / FRAME_S, trial_index=1, attempt=1, condition=Condition(condition))
    plan = task.build_trial(setup)
    ctx = TrialContext(clock=clock, screen=SCREEN, rng=np.random.default_rng(0), trial_index=1,
                       params=dict(condition), stimuli=plan.stimuli, regions=plan.regions,
                       record=dict(plan.record))
    return collector, engine.run_trial(ctx, plan.phases), ctx


def blank(n: int) -> list[InputFrame]:
    return [InputFrame(gaze=None)] * n


def press(*keys: str) -> list[InputFrame]:
    return [InputFrame(gaze=None, keys=tuple(keys))]
