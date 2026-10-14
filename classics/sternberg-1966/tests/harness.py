"""Run one trial on alhazen's fake clock with scripted inputs: no display, no devices."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from alhazen import InputFrame
from alhazen.config.loader import build_session_config
from alhazen.config.models import DisplayConfig, MonitorConfig, RigConfig, SessionInfo
from alhazen.core.engine import TrialEngine
from alhazen.core.events import EventBus
from alhazen.core.trial import TrialContext
from alhazen.display.screen import Screen
from alhazen.paradigms.base import Condition
from alhazen.task.plan import TrialPlan, TrialSetup
from alhazen.testing import EventCollector, FakeClock, FakeDisplay, ScriptedCommands, ScriptedInputs

FRAME_S = 1 / 60
SCREEN = Screen(width_px=1920, height_px=1080, px_per_deg=40.0)
EMPTY = InputFrame(gaze=None)


@dataclass
class Ran:
    plan: TrialPlan
    result: Any
    ctx: TrialContext
    events: list[Any]

    @property
    def names(self) -> list[str]:
        return [e.name for e in self.events if e.name not in ("TRIAL_START", "TRIAL_END")]

    def event(self, name: str) -> Any:
        return next(e for e in self.events if e.name == name)


def build(task, condition: dict, seed: int = 0) -> tuple[TrialPlan, Any]:
    clock = FakeClock()
    display = FakeDisplay(clock, FRAME_S)
    monitor = MonitorConfig(width_px=1920, height_px=1080, width_cm=60.0, distance_cm=60.0,
                            refresh_rate_hz=60.0, fullscreen=False)
    setup = TrialSetup(
        cfg=build_session_config(
            RigConfig(monitor=monitor, display=DisplayConfig(backend="simulated"), data_root="."),
            SessionInfo(subject="t01", session=1, run=1, task_name=task.name, seed=1),
            task.params, {}),
        screen=SCREEN, display=display, rng=np.random.default_rng(seed),
        refresh_rate_hz=1 / FRAME_S, trial_index=1, attempt=1, condition=Condition(condition))
    return task.build_trial(setup), (clock, display)


def run(task, plan: TrialPlan, env, condition: dict, inputs: list[InputFrame]) -> Ran:
    clock, display = env
    bus = EventBus()
    collector = EventCollector()
    bus.subscribe(collector)
    engine = TrialEngine(display=display, clock=clock, bus=bus, schema=task.events,
                         commands=ScriptedCommands(), input_provider=ScriptedInputs(inputs))
    ctx = TrialContext(clock=clock, screen=SCREEN, rng=np.random.default_rng(0), trial_index=1,
                       params=dict(condition), stimuli=plan.stimuli, regions=plan.regions,
                       record=dict(plan.record))
    result = engine.run_trial(ctx, plan.phases)
    return Ran(plan, result, ctx, collector.events)


def frames(*segments: Any) -> list[InputFrame]:
    """Build an input script: an int is that many empty frames, a str or tuple of str is one
    frame with those keys. Always ends with empty frames, because ScriptedInputs repeats
    its last frame forever."""
    out: list[InputFrame] = []
    for seg in segments:
        if isinstance(seg, int):
            out += [EMPTY] * seg
        else:
            keys = (seg,) if isinstance(seg, str) else tuple(seg)
            out.append(InputFrame(gaze=None, keys=keys))
    return out + [EMPTY] * 3


def typed(text: str, gap: int = 1) -> list[Any]:
    """Keys typed one per frame with ``gap`` empty frames between them."""
    out: list[Any] = []
    for ch in text:
        out += [ch, gap]
    return out
