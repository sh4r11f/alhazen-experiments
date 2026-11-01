"""One trial on alhazen's fake clock with scripted inputs: no display, no devices."""

from __future__ import annotations

import numpy as np
from alhazen import InputFrame
from alhazen.config.loader import build_session_config
from alhazen.config.models import DisplayConfig, MonitorConfig, RigConfig, SessionInfo
from alhazen.core.engine import TrialEngine
from alhazen.core.events import EventBus
from alhazen.core.trial import TrialContext
from alhazen.display.screen import Screen
from alhazen.paradigms.base import Condition
from alhazen.task.plan import TrialSetup
from alhazen.testing import EventCollector, FakeClock, FakeDisplay, ScriptedCommands, ScriptedInputs

FRAME_S = 1 / 60
SCREEN = Screen(width_px=1920, height_px=1080, px_per_deg=36.0)


def run_trial(task, condition, inputs, seed=0, screen=SCREEN):
    clock = FakeClock()
    display = FakeDisplay(clock, FRAME_S)
    bus = EventBus()
    collector = EventCollector()
    bus.subscribe(collector)
    engine = TrialEngine(
        display=display,
        clock=clock,
        bus=bus,
        schema=task.events,
        commands=ScriptedCommands(),
        input_provider=ScriptedInputs(inputs),
    )
    monitor = MonitorConfig(
        width_px=1920,
        height_px=1080,
        width_cm=53.0,
        distance_cm=57.0,
        refresh_rate_hz=60.0,
        fullscreen=False,
    )
    setup = TrialSetup(
        cfg=build_session_config(
            RigConfig(monitor=monitor, display=DisplayConfig(backend="simulated"), data_root="."),
            SessionInfo(subject="t01", session=1, run=1, task_name=task.name, seed=1),
            task.params,
            {},
        ),
        screen=screen,
        display=display,
        rng=np.random.default_rng(seed),
        refresh_rate_hz=1 / FRAME_S,
        trial_index=1,
        attempt=1,
        condition=Condition(condition),
    )
    plan = task.build_trial(setup)
    ctx = TrialContext(
        clock=clock,
        screen=screen,
        rng=np.random.default_rng(0),
        trial_index=1,
        params=dict(condition),
        stimuli=plan.stimuli,
        regions=plan.regions,
        record=dict(plan.record),
    )
    return collector, engine.run_trial(ctx, plan.phases), ctx, plan


def frames(n, keys=()):
    return [InputFrame(gaze=None)] * n + [InputFrame(gaze=None, keys=tuple(keys))]
