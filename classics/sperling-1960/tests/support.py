"""Run one trial of the task on alhazen's fake clock with scripted inputs."""

from __future__ import annotations

from collections.abc import Callable

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

SCREEN = Screen(width_px=1920, height_px=1080, px_per_deg=40.0)


def condition(material="4/4/4-LN", delay_s=0.0, cued_row=0, report="partial", sample=False):
    return {"report": report, "material": material, "delay_s": delay_s if report == "partial"
            else None, "series": 1, "series_direction": "ascending", "block": 0,
            "cued_row": cued_row if report == "partial" else None, "sample": sample}


def idle(n):
    return [InputFrame()] * n


def keys(*names):
    return [InputFrame(keys=tuple(names))]


def run_trial(task, cond, script: Callable[[TrialPlan], list[InputFrame]], hz=60.0,
              screen=SCREEN, seed=0):
    """Build the trial, script its inputs from the plan (so a test can type the target),
    run it. Returns (events, result, plan)."""
    clock = FakeClock()
    display = FakeDisplay(clock, 1.0 / hz)
    bus = EventBus()
    collector = EventCollector()
    bus.subscribe(collector)
    monitor = MonitorConfig(width_px=screen.width_px, height_px=screen.height_px,
                            width_cm=60.0, distance_cm=60.0, refresh_rate_hz=hz,
                            fullscreen=False)
    setup = TrialSetup(
        cfg=build_session_config(
            RigConfig(monitor=monitor, display=DisplayConfig(backend="simulated"), data_root="."),
            SessionInfo(subject="t01", session=1, run=1, task_name=task.name, seed=1),
            task.params, {}),
        screen=screen, display=display, rng=np.random.default_rng(seed), refresh_rate_hz=hz,
        trial_index=1, attempt=1, condition=Condition(cond))
    plan = task.build_trial(setup)
    frames = script(plan) + idle(1)  # the last frame repeats: end on an empty one
    engine = TrialEngine(display=display, clock=clock, bus=bus, schema=task.events,
                         commands=ScriptedCommands(), input_provider=ScriptedInputs(frames))
    ctx = TrialContext(clock=clock, screen=screen, rng=np.random.default_rng(seed),
                       trial_index=1, params=dict(cond), stimuli=plan.stimuli,
                       regions=plan.regions, record={**cond, **plan.record})
    result = engine.run_trial(ctx, plan.phases)
    return collector.events, result, plan


def start_and_wait(n_frames=60):
    """Press SPACE, then let the presentation run its course (keys there are ignored)."""
    return idle(2) + keys("space") + idle(n_frames)


def type_text(text, then_enter=True):
    out = [InputFrame(keys=(ch.lower(),)) for ch in text]
    return out + (keys("return") if then_enter else [])


def by_name(events):
    return {e.name: e for e in events}
