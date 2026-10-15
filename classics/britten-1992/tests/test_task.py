"""Trial logic on alhazen's fake clock with scripted inputs: no display, no devices.

Every outcome of both trials (keyboard and saccade) is driven here, frame by frame.
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

from britten1992.task import PROJECT, RdkDirectionTask, RdkDirectionTaskParams

FRAME_S = 1 / 60
PPD = 40.0
SCREEN = Screen(width_px=1920, height_px=1080, px_per_deg=PPD)


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


def cond(direction="pref", coherence=12.8):
    return {"direction": direction, "coherence_pct": coherence, "correction": False}


# --- keyboard (human) -----------------------------------------------------------------

STIM_FRAMES = 6


@pytest.fixture
def human():
    return RdkDirectionTask(RdkDirectionTaskParams(
        subject_kind="human", fixation_duration=Duration(frames=3),
        stimulus_duration=Duration(frames=STIM_FRAMES), response_timeout=Duration(frames=10),
        feedback_duration=Duration(frames=2)))


def keys_after(n, keys=()):
    return [InputFrame(gaze=None)] * n + [InputFrame(gaze=None, keys=tuple(keys))]


def test_the_key_for_the_motion_direction_scores_correct(human):
    events, result, ctx = run_trial(human, cond("pref"), keys_after(14, ["right"]))
    assert result.outcome.name == "CORRECT"
    assert ctx.record["feedback"] == "success"
    assert ctx.record["response_key"] == "right"
    names = events.names()
    assert names.index("FIX_ON") < names.index("STIM_ON") < names.index("RESPONSE_CUE")


def test_the_other_key_scores_wrong_and_feedback_says_so(human):
    _, result, ctx = run_trial(human, cond("anti"), keys_after(14, ["right"]))
    assert result.outcome.name == "WRONG"
    assert ctx.record["feedback"] == "failure"


def test_the_anti_key_is_correct_for_anti_motion(human):
    _, result, _ = run_trial(human, cond("anti"), keys_after(14, ["left"]))
    assert result.outcome.name == "CORRECT"


def test_a_key_during_the_dots_is_not_an_answer(human):
    # Pressed while the dots are still on: ignored, so the trial times out.
    _, result, _ = run_trial(human, cond("pref"), keys_after(5, ["right"]) + keys_after(40))
    assert result.outcome.name == "NO_RESPONSE"


def test_no_key_times_out_and_is_not_completed(human):
    _, result, ctx = run_trial(human, cond("pref"), keys_after(40))
    assert result.outcome.name == "NO_RESPONSE"
    assert not result.outcome.completed
    assert ctx.record["feedback"] == "failure"


def test_the_dots_run_for_exactly_the_stimulus_duration(human):
    _, _, ctx = run_trial(human, cond("pref", 51.2), keys_after(14, ["right"]))
    dots = ctx.stimuli["dots"].over
    assert len(dots.visible_counts) == STIM_FRAMES
    assert ctx.record["signal_dt_ms"] == pytest.approx(50.0)  # 45 ms -> 3 frames at 60 Hz


def test_score_adds_the_choice_and_signed_coherence(human):
    _, _, ctx = run_trial(human, cond("anti", 6.4), keys_after(14, ["right"]))
    scored = human.score({**ctx.record, **cond("anti", 6.4)})
    assert scored["choice"] == "pref" and scored["chose_pref"] == 1
    assert scored["signed_coherence_pct"] == pytest.approx(-6.4)


# --- saccade (monkey) -------------------------------------------------------------------

@pytest.fixture
def monkey():
    p = load_params(PROJECT / "configs" / "task-monkey.yaml", RdkDirectionTaskParams)
    return RdkDirectionTask(p.model_copy(update=dict(
        acquire_timeout=Duration(frames=10), acquire_hold=Duration(frames=0),
        prestim_hold=Duration(frames=3), stimulus_duration=Duration(frames=STIM_FRAMES),
        response_timeout=Duration(frames=20), landing_dwell=Duration(frames=3),
        error_timeout=Duration(frames=5))))


FIX = (0.0, 0.0)
PREF_TARGET = (10.0 * PPD, 0.0)  # axis 0 deg, targets 10 deg either side
ANTI_TARGET = (-10.0 * PPD, 0.0)


def gaze(points):
    return [InputFrame(gaze=g) for g in points]


def saccade_to(point, inside=13):
    """Fixate through acquisition, hold, dots and the first response frame, then land."""
    return gaze([FIX] * inside + [point] * 40)


def test_a_saccade_to_the_target_of_the_motion_direction_is_correct(monkey):
    events, result, ctx = run_trial(monkey, cond("pref"), saccade_to(PREF_TARGET))
    assert result.outcome.name == "CORRECT"
    assert ctx.record["choice"] == "pref"
    assert ctx.record["saccade_rt_ms"] > 0
    names = events.names()
    for e in ("FIX_ON", "FIX_ACQUIRED", "STIM_ON", "TARGETS_ON", "SACCADE_ONSET"):
        assert e in names
    assert "TIMEOUT_ON" not in names


def test_a_saccade_to_the_other_target_is_wrong_and_earns_the_time_out(monkey):
    events, result, ctx = run_trial(monkey, cond("pref"), saccade_to(ANTI_TARGET))
    assert result.outcome.name == "WRONG"
    assert ctx.record["choice"] == "anti"
    assert "TIMEOUT_ON" in events.names()


def test_a_saccade_to_neither_target_is_missed_and_served_again(monkey):
    _, result, ctx = run_trial(monkey, cond("pref"), saccade_to((0.0, 8.0 * PPD)))
    assert result.outcome.name == "MISSED"
    assert not result.outcome.completed
    assert ctx.record["choice"] == "none"


def test_never_looking_at_the_fixation_point_is_no_fixation(monkey):
    _, result, _ = run_trial(monkey, cond("pref"), gaze([None] * 30))
    assert result.outcome.name == "NO_FIXATION"


def test_leaving_fixation_before_the_dots_is_a_break(monkey):
    _, result, ctx = run_trial(monkey, cond("pref"), gaze([FIX] * 2 + [(3 * PPD, 0.0)] * 20))
    assert result.outcome.name == "FIX_BREAK"
    assert ctx.stimuli["dots"].over.visible_counts == []


def test_leaving_fixation_during_the_dots_is_a_break(monkey):
    _, result, ctx = run_trial(monkey, cond("pref"), gaze([FIX] * 6 + [(3 * PPD, 0.0)] * 20))
    assert result.outcome.name == "FIX_BREAK"
    assert 0 < len(ctx.stimuli["dots"].over.visible_counts) < STIM_FRAMES


def test_a_blink_during_the_dots_is_a_break(monkey):
    # The blink rule: an unverifiable sample is outside every window.
    _, result, _ = run_trial(monkey, cond("pref"), gaze([FIX] * 6 + [None] + [FIX] * 40))
    assert result.outcome.name == "FIX_BREAK"


def test_staying_on_the_fixation_point_is_no_choice(monkey):
    _, result, ctx = run_trial(monkey, cond("pref"), gaze([FIX] * 60))
    assert result.outcome.name == "NO_CHOICE"
    assert len(ctx.stimuli["dots"].over.visible_counts) == STIM_FRAMES


def test_the_fixation_window_is_the_papers_1_25_deg(monkey):
    inside = (1.2 * PPD, 0.0)
    _, result, _ = run_trial(monkey, cond("pref"), gaze([inside] * 13 + [PREF_TARGET] * 40))
    assert result.outcome.name == "CORRECT"


def test_at_zero_correlation_the_nominal_direction_is_paid(monkey):
    _, result, _ = run_trial(monkey, cond("anti", 0.0), saccade_to(ANTI_TARGET))
    assert result.outcome.name == "CORRECT"
    _, result, _ = run_trial(monkey, cond("pref", 0.0), saccade_to(ANTI_TARGET))
    assert result.outcome.name == "WRONG"


def test_the_monkey_set_pays_only_a_correct_choice(monkey):
    assert set(monkey.reward.by_outcome) == {"CORRECT"}


# --- files ------------------------------------------------------------------------------

def test_every_params_file_loads_and_builds_a_task():
    for path in (PROJECT / "configs").glob("task*.yaml"):
        RdkDirectionTask(load_params(path, RdkDirectionTaskParams))


def test_a_monkey_file_must_report_with_a_saccade():
    with pytest.raises(ValueError, match="saccade"):
        RdkDirectionTaskParams(subject_kind="monkey", response_mode="keyboard",
                               reward={"by_outcome": {"CORRECT": {"n_pulses": 1}}})


def test_the_subject_is_told_what_to_do():
    text = (PROJECT / "instructions.md").read_text(encoding="utf-8")
    assert RdkDirectionTask.default_params().is_file()
    assert "SPACE" in text and "RIGHT" in text and "LEFT" in text
