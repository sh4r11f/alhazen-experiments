"""Trial logic on alhazen's fake clock with scripted inputs: no display, no devices.

Every outcome branch of both parameter sets. Durations are given in frames here so
the frame on which each phase starts is known exactly:

    keyboard: frames 0-5 inter-trial interval, 6-11 cue, 12-21 detection window
    tracker:  the same after fixation is acquired on frame 0
"""

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

from posner1980.task import PROJECT, PosnerCueingTask, PosnerCueingTaskParams

FRAME_S = 1 / 60
SCREEN = Screen(width_px=1920, height_px=1080, px_per_deg=40.0)
FIX = (0.0, 0.0)
AWAY = (7 * 40.0, 0.0)          # gaze on a target position, 7 dva right

VALID = {"cue": "left", "target": "left", "validity": "valid", "slot": 0}
INVALID = {"cue": "left", "target": "right", "validity": "invalid", "slot": 1}
NEUTRAL = {"cue": "neutral", "target": "right", "validity": "neutral", "slot": 2}
CATCH = {"cue": "right", "target": "none", "validity": "catch", "slot": 3}


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


def make_task(control: str) -> PosnerCueingTask:
    return PosnerCueingTask(PosnerCueingTaskParams(
        subject_kind="human", fixation_control=control,
        intertrial_min=Duration(frames=6), intertrial_max=Duration(frames=6),
        cue_target_soa=Duration(frames=6), response_deadline=Duration(frames=10),
        feedback_duration=Duration(frames=3), acquire_timeout=Duration(frames=10)))


def frames(n=60, key_at=None, gaze=FIX, away_from=None):
    """``n`` input frames; the response key on frame ``key_at``; gaze at fixation, or
    on a target position from frame ``away_from`` on (None = a blink there, see below)."""
    out = []
    for i in range(n):
        g = gaze
        if away_from is not None and i >= away_from:
            g = AWAY
        out.append(InputFrame(gaze=g, keys=("space",) if i == key_at else ()))
    return out


def names(collector):
    """The task's own events, in order (alhazen's TRIAL_START/TRIAL_END left out)."""
    return [e.name for e in collector.events if not e.name.startswith("TRIAL_")]


@pytest.fixture
def keyboard():
    return make_task("none")


@pytest.fixture
def tracker():
    return make_task("tracker")


# --- keyboard-only set ---------------------------------------------------------------


def test_a_key_after_the_target_is_a_detection_timed_from_the_target_flip(keyboard):
    collector, result, ctx = run_trial(keyboard, VALID, frames(key_at=17))
    assert result.outcome.name == "DETECTED"
    # The key is read on frame 17; the square's first flip is frame 12's.
    assert ctx.record["rt_ms"] == pytest.approx(5 * FRAME_S * 1000, abs=FRAME_S * 1000 + 1e-6)
    assert names(collector)[:3] == ["FIX_ON", "CUE_ON", "TARGET_ON"]


@pytest.mark.parametrize("cond", [VALID, INVALID, NEUTRAL])
def test_no_key_on_a_target_trial_is_a_miss(keyboard, cond):
    _, result, _ = run_trial(keyboard, cond, frames())
    assert result.outcome.name == "MISS"
    assert result.outcome.completed and not result.outcome.success


def test_no_key_on_a_catch_trial_is_a_correct_rejection(keyboard):
    collector, result, _ = run_trial(keyboard, CATCH, frames())
    assert result.outcome.name == "CORRECT_REJECTION"
    assert "TARGET_ON" not in names(collector) and "CATCH_ON" in names(collector)


def test_a_key_on_a_catch_trial_is_a_false_alarm(keyboard):
    _, result, _ = run_trial(keyboard, CATCH, frames(key_at=16))
    assert result.outcome.name == "FALSE_ALARM"


def test_a_key_during_the_cue_is_an_anticipation_and_is_served_again(keyboard):
    collector, result, ctx = run_trial(keyboard, VALID, frames(key_at=9))
    assert result.outcome.name == "ANTICIPATION"
    assert not result.outcome.completed
    assert "early_rt_ms" in ctx.record and "TARGET_ON" not in names(collector)


def test_a_key_during_the_intertrial_interval_is_ignored(keyboard):
    _, result, _ = run_trial(keyboard, VALID, frames(key_at=2))
    assert result.outcome.name == "MISS"


def test_the_keyboard_set_never_looks_at_gaze(keyboard):
    _, result, _ = run_trial(keyboard, VALID, frames(key_at=17, gaze=None))
    assert result.outcome.name == "DETECTED"


def test_the_cue_stays_on_with_the_target_and_feedback_goes_green(keyboard):
    _, _, ctx = run_trial(keyboard, VALID, frames(key_at=17))
    cue, target, fixation = (ctx.stimuli[k] for k in ("cue", "target", "fixation"))
    assert cue.draw_count > 6 and target.draw_count >= 1
    assert fixation.colors[-1] == (-1.0, 1.0, -1.0)


def test_the_cue_target_soa_is_six_frames(keyboard):
    _, _, ctx = run_trial(keyboard, NEUTRAL, frames(key_at=17))
    soa = ctx.record["t_target_on"] - ctx.record["t_cue_on"]
    assert soa == pytest.approx(6 * FRAME_S, abs=1e-9)
    assert ctx.record["intertrial_s"] == pytest.approx(6 * FRAME_S)


# --- eye-tracker set -----------------------------------------------------------------


def test_steady_fixation_and_a_key_is_a_detection(tracker):
    collector, result, _ = run_trial(tracker, INVALID, frames(key_at=18))
    assert result.outcome.name == "DETECTED"
    assert names(collector)[:4] == ["FIX_ON", "FIX_ACQUIRED", "CUE_ON", "TARGET_ON"]


def test_no_gaze_at_fixation_ends_the_attempt_as_no_fixation(tracker):
    _, result, _ = run_trial(tracker, VALID, frames(gaze=AWAY))
    assert result.outcome.name == "NO_FIXATION"
    assert not result.outcome.completed


@pytest.mark.parametrize("frame,period", [(3, "intertrial"), (10, "cue"), (15, "detection")])
def test_leaving_fixation_at_any_point_is_a_fixation_break(tracker, frame, period):
    collector, result, _ = run_trial(tracker, VALID, frames(key_at=19, away_from=frame))
    assert result.outcome.name == "FIXATION_BREAK", period
    assert not result.outcome.completed
    seen = names(collector)
    if period == "intertrial":
        assert "CUE_ON" not in seen
    elif period == "cue":
        assert "CUE_ON" in seen and "TARGET_ON" not in seen
    else:
        assert "TARGET_ON" in seen and "RESPONSE" not in seen


def test_a_blink_is_a_fixation_break(tracker):
    inputs = frames(key_at=19)
    inputs[10] = InputFrame(gaze=None)
    _, result, _ = run_trial(tracker, NEUTRAL, inputs)
    assert result.outcome.name == "FIXATION_BREAK"


def test_a_catch_trial_with_steady_fixation_is_a_correct_rejection(tracker):
    _, result, _ = run_trial(tracker, CATCH, frames())
    assert result.outcome.name == "CORRECT_REJECTION"


def test_a_fixation_break_turns_the_feedback_red(tracker):
    _, _, ctx = run_trial(tracker, VALID, frames(away_from=10))
    assert ctx.stimuli["fixation"].colors[-1] == (1.0, -1.0, -1.0)


def test_the_fixation_window_has_the_configured_radius(tracker):
    _, _, ctx = run_trial(tracker, VALID, frames(key_at=18))
    assert ctx.regions["fixation"].radius == pytest.approx(1.5 * 40.0)


# --- files ---------------------------------------------------------------------------


def test_every_params_file_loads():
    for path in (PROJECT / "configs").glob("task*.yaml"):
        load_params(path, PosnerCueingTaskParams)


def test_the_subject_is_told_what_to_do():
    assert PosnerCueingTask.default_params().is_file()
    text = (PROJECT / "instructions.md").read_text(encoding="utf-8")
    assert "SPACE" in text and "centre" in text
