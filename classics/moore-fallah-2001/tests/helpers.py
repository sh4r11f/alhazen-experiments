"""Shared test plumbing: params with short frame-exact timings, and one trial
driven through alhazen's real engine on a fake clock with scripted inputs."""

from __future__ import annotations

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

from moore_fallah2001.task import (
    PROJECT,
    TargetDimmingDetectionTask,
    TargetDimmingDetectionTaskParams,
)

FRAME_S = 1 / 60
SCREEN = Screen(width_px=1920, height_px=1080, px_per_deg=40.0)
# Frame-exact timings for the tests: the dimming at frame 30 for 2 frames, the
# stimulation trigger 10 frames before it, a 20-frame response window, presses
# within 3 frames of the dimming early, a 60-frame catch trial.
DIM_K, DIM_N, SOA_K, WINDOW_K, MIN_RT_K, CATCH_K = 30, 2, 10, 20, 3, 60


def params(config: str = "task-monkey-inside.yaml", **update) -> TargetDimmingDetectionTaskParams:
    base = load_params(PROJECT / "configs" / config, TargetDimmingDetectionTaskParams)
    data = base.model_dump(mode="json")
    data.update({
        "fix_acquire_hold": {"frames": 0}, "fix_acquire_timeout": {"frames": 10},
        "dim_onset_min": {"frames": DIM_K}, "dim_onset_max": {"frames": DIM_K},
        "dim_duration_min": {"frames": DIM_N}, "dim_duration_max": {"frames": DIM_N},
        "response_window": {"frames": WINDOW_K}, "min_rt": {"frames": MIN_RT_K},
        "catch_duration": {"frames": CATCH_K},
    })
    if data["stimulation"]["enabled"]:
        data["stimulation"]["soa"] = {"frames": SOA_K}
    data.update(update)
    return TargetDimmingDetectionTaskParams.model_validate(data)


def condition(trial_type="blink", stimulation=True, dim_pct=40.0, staircase=None, slot=0):
    return {"trial_type": trial_type, "stimulation": stimulation, "dim_pct": dim_pct,
            "staircase": staircase or ("stim" if stimulation else "control"), "slot": slot,
            "block": 1}


def script(n_watch_frames=200, press_at=None, look_away_at=None, fixate=True):
    """One acquisition frame, then watch frame k at list index k + 1."""
    frames = [InputFrame(gaze=(0.0, 0.0) if fixate else None)]
    for k in range(n_watch_frames):
        gaze = None if (not fixate or (look_away_at is not None and k >= look_away_at)) \
            else (2.0, -3.0)
        keys = ("space",) if press_at is not None and k == press_at else ()
        frames.append(InputFrame(gaze=gaze, keys=keys))
    return frames


def run_trial(task: TargetDimmingDetectionTask, cond: dict, inputs, seed: int = 0):
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
        screen=SCREEN, display=display, rng=np.random.default_rng(seed),
        refresh_rate_hz=1 / FRAME_S, trial_index=1, attempt=1, condition=Condition(cond))
    plan = task.build_trial(setup)
    ctx = TrialContext(clock=clock, screen=SCREEN, rng=np.random.default_rng(seed), trial_index=1,
                       params=dict(cond), stimuli=plan.stimuli, regions=plan.regions,
                       record={**cond, **plan.record})
    result = engine.run_trial(ctx, plan.phases)
    task.score(ctx.record)
    return collector, result, ctx, plan
