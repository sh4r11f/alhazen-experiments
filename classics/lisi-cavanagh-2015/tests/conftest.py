"""Shared helpers: one trial on alhazen's fake clock, scripted gaze and keys."""

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
SCREEN = Screen(width_px=1920, height_px=1080, px_per_deg=40.0)


def build(task, condition, seed=0):
    """(plan, setup pieces) for one trial of ``task`` under ``condition``."""
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
    return task.build_trial(setup), clock, display


def run_plan(task, plan, clock, display, frames, condition):
    bus = EventBus()
    collector = EventCollector()
    bus.subscribe(collector)
    engine = TrialEngine(display=display, clock=clock, bus=bus, schema=task.events,
                         commands=ScriptedCommands(), input_provider=ScriptedInputs(frames))
    ctx = TrialContext(clock=clock, screen=SCREEN, rng=np.random.default_rng(0), trial_index=1,
                       params=dict(condition), stimuli=plan.stimuli, regions=plan.regions,
                       record=dict(plan.record))
    result = engine.run_trial(ctx, plan.phases)
    return collector, result, ctx


def at(x_dva, y_dva, i):
    """A new gaze sample at (x, y) dva on frame i."""
    return InputFrame(gaze=(SCREEN.deg2px(x_dva), SCREEN.deg2px(y_dva)), gaze_t=i * FRAME_S)


def gaze_track(points, keys_at=None):
    """Frames from a list of (x, y) or None (a blink), each a new sample; ``keys_at`` maps a
    frame index to the keys pressed on it."""
    keys_at = keys_at or {}
    out = []
    for i, pt in enumerate(points):
        keys = tuple(keys_at.get(i, ()))
        if pt is None:
            out.append(InputFrame(gaze=None, keys=keys))
        else:
            f = at(pt[0], pt[1], i)
            out.append(InputFrame(gaze=f.gaze, gaze_t=f.gaze_t, keys=keys))
    return out
