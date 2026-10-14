"""Trial logic on alhazen's fake clock with scripted inputs: no display, no devices."""

from __future__ import annotations

import numpy as np
import pytest
from alhazen import Duration, InputFrame
from alhazen.config.loader import build_session_config, load_params
from alhazen.config.models import DisplayConfig, MonitorConfig, RigConfig, SessionInfo
from alhazen.core.engine import TrialEngine
from alhazen.core.events import EventBus
from alhazen.core.trial import TrialContext
from alhazen.display.screen import Screen
from alhazen.paradigms.base import Condition
from alhazen.task.plan import TrialSetup
from alhazen.testing import EventCollector, FakeClock, FakeDisplay, ScriptedCommands, ScriptedInputs

from raymond1992.task import PROJECT, AttentionalBlinkTask, AttentionalBlinkTaskParams

FRAME_S = 1 / 60
SCREEN = Screen(width_px=1920, height_px=1080, px_per_deg=40.0)


def run_trial(task, condition, inputs):
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


@pytest.fixture
def task():
    return AttentionalBlinkTask(AttentionalBlinkTaskParams(subject_kind="human",
                                           fixation_duration=Duration(frames=3),
                                           response_timeout=Duration(frames=10)))


def frames(n, keys=()):
    return [InputFrame(gaze=None)] * n + [InputFrame(gaze=None, keys=tuple(keys))]


def test_the_correct_key_scores_correct(task):
    _, result, _ = run_trial(task, {"side": "left"}, frames(6, ["f"]))
    assert result.outcome.name == "CORRECT"


def test_the_other_key_scores_wrong(task):
    _, result, _ = run_trial(task, {"side": "left"}, frames(6, ["j"]))
    assert result.outcome.name == "WRONG"


def test_no_key_times_out(task):
    _, result, _ = run_trial(task, {"side": "right"}, frames(40))
    assert result.outcome.name == "NO_RESPONSE"


def test_every_params_file_loads():
    for path in (PROJECT / "configs").glob("task*.yaml"):
        load_params(path, AttentionalBlinkTaskParams)


def test_the_subject_is_told_what_to_do():
    assert AttentionalBlinkTask.default_params().is_file()
    assert "SPACE" in (PROJECT / "instructions.md").read_text(encoding="utf-8")
