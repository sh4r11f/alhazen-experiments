"""Trial logic on alhazen's fake clock with scripted inputs: no display, no devices."""

from __future__ import annotations

import argparse

import numpy as np
import pytest
from alhazen import Duration, InputFrame
from alhazen.config.loader import build_session_config, load_params
from alhazen.config.models import DisplayConfig, MonitorConfig, RigConfig, SessionInfo
from alhazen.core.engine import TrialEngine
from alhazen.core.events import EventBus
from alhazen.core.trial import TrialContext
from alhazen.display.screen import Screen
from alhazen.errors import ConfigError
from alhazen.paradigms.base import Condition
from alhazen.task.plan import TrialSetup
from alhazen.testing import EventCollector, FakeClock, FakeDisplay, ScriptedCommands, ScriptedInputs

from shepard_metzler1971.task import PROJECT, MentalRotationParams, MentalRotationTask

FRAME_S = 1 / 60
SCREEN = Screen(width_px=1920, height_px=1080, px_per_deg=40.0)
ITI, WARN = 3, 30  # frames: a short inter-trial interval; the paper's 0.5 s warning


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


@pytest.fixture(scope="module")
def task():
    p = load_params(PROJECT / "configs" / "task.yaml", MentalRotationParams)
    return MentalRotationTask(p.model_copy(update={
        "intertrial_interval": Duration(frames=ITI),
        "response_timeout": Duration(frames=120)}))


@pytest.fixture(scope="module")
def conditions(task):
    conds = [c.params for c in task.conditions(np.random.default_rng(0))]
    same = next(c for c in conds if c["kind"] == "same" and c["angle_deg"] == 120)
    different = next(c for c in conds if c["kind"] == "different")
    return same, different


def before_pair(n_extra=0, keys=()):
    """Frames through the ITI and the warning, then n_extra more, then a key."""
    return [InputFrame(gaze=None)] * (ITI + WARN + 2 + n_extra) + [
        InputFrame(gaze=None, keys=tuple(keys))]


def names(collector):
    return [e.name for e in collector.events]


def test_same_pair_answered_same_is_correct(task, conditions):
    _, result, ctx = run_trial(task, conditions[0], before_pair(10, ["j"]))
    assert result.outcome.name == "CORRECT"
    assert ctx.record["response_key"] == "j" and ctx.record["correct_key"] == "j"


def test_same_pair_answered_different_is_wrong(task, conditions):
    _, result, _ = run_trial(task, conditions[0], before_pair(10, ["f"]))
    assert result.outcome.name == "WRONG"


def test_different_pair_answered_different_is_correct(task, conditions):
    _, result, _ = run_trial(task, conditions[1], before_pair(10, ["f"]))
    assert result.outcome.name == "CORRECT"


def test_different_pair_answered_same_is_wrong(task, conditions):
    _, result, _ = run_trial(task, conditions[1], before_pair(10, ["j"]))
    assert result.outcome.name == "WRONG"


def test_no_answer_times_out_and_is_not_completed(task, conditions):
    _, result, _ = run_trial(task, conditions[0], [InputFrame(gaze=None)] * 400)
    assert result.outcome.name == "NO_RESPONSE"
    assert not result.outcome.completed


def test_an_unbound_key_is_not_an_answer(task, conditions):
    inputs = before_pair(5, ["k"]) + [InputFrame(gaze=None)] * 5 + [
        InputFrame(gaze=None, keys=("j",))]
    _, result, ctx = run_trial(task, conditions[0], inputs)
    assert result.outcome.name == "CORRECT" and ctx.record["response_key"] == "j"


def test_a_key_during_the_warning_is_ignored(task, conditions):
    early = [InputFrame(gaze=None)] * (ITI + 5) + [InputFrame(gaze=None, keys=("f",))]
    inputs = early + [InputFrame(gaze=None)] * (WARN + 10) + [InputFrame(gaze=None, keys=("j",))]
    _, result, ctx = run_trial(task, conditions[0], inputs)
    assert result.outcome.name == "CORRECT" and ctx.record["response_key"] == "j"


def test_events_in_order_and_the_pair_follows_the_warning_by_half_a_second(task, conditions):
    collector, _, ctx = run_trial(task, conditions[0], before_pair(20, ["j"]))
    seq = [n for n in names(collector) if n in {"ITI_ON", "WARNING_ON", "PAIR_ON", "RESPONSE"}]
    assert seq == ["ITI_ON", "WARNING_ON", "PAIR_ON", "RESPONSE"]
    gap = ctx.record["t_pair_on"] - ctx.record["t_warning_on"]
    assert gap == pytest.approx(0.5, abs=FRAME_S / 2)  # paper: p. 703


def test_reaction_time_runs_from_the_pair_onset(task, conditions):
    _, _, ctx = run_trial(task, conditions[0], before_pair(30, ["j"]))
    rt = ctx.record["rt_ms"] / 1000
    assert rt == pytest.approx(ctx.record["t_response"] - ctx.record["t_pair_on"], abs=FRAME_S)
    assert 0.4 < rt < 0.6


def test_the_condition_carries_everything_the_analysis_needs(conditions):
    for c in conditions:
        for key in ("kind", "rotation", "angle_deg", "left_image", "right_image",
                    "left_ori_deg", "right_ori_deg", "reflected_side", "session",
                    "block_type", "pair_id", "presentation"):
            assert key in c


def test_every_params_file_loads_and_matches_the_bank():
    for path in sorted((PROJECT / "configs").glob("task*.yaml")):
        MentalRotationTask(load_params(path, MentalRotationParams))


def test_a_params_file_that_disagrees_with_the_bank_is_refused():
    p = load_params(PROJECT / "configs" / "task.yaml", MentalRotationParams)
    with pytest.raises(ConfigError, match="Regenerate"):
        MentalRotationTask(p.model_copy(update={"aperture_dva": 7.0}))


def test_params_hook_takes_subject_and_session_from_the_command_line(main_params):
    p = MentalRotationTask.params_hook(main_params, argparse.Namespace(sub="s07", ses=5))
    assert (p.design.subject, p.design.session) == ("s07", 5)
    task = MentalRotationTask(p)
    sessions = {c.params["session"] for c in task.conditions(np.random.default_rng(0))}
    assert sessions == {5}
    with pytest.raises(ConfigError, match="8 sessions"):
        MentalRotationTask.params_hook(main_params, argparse.Namespace(sub="s07", ses=9))


def test_the_trial_timing_is_declared(task, conditions):
    timing = task.trial_timing(Condition(conditions[0]), 60.0)
    assert timing.min_s == pytest.approx(ITI / 60 + 0.5)


def test_the_subject_is_told_the_keys_and_the_instruction():
    text = (PROJECT / "instructions.md").read_text(encoding="utf-8").lower()
    assert "j" in text and "f" in text and "space" in text
    assert "as quickly as" in text and "error" in text


def test_the_demo_pages_through_the_three_kinds_of_pair(task):
    from alhazen.display.simulated import SimulatedDisplay
    from alhazen.modes.demo import DemoSetup

    setup = DemoSetup(display=SimulatedDisplay(60.0, frame_period_s=0), screen=SCREEN,
                      params=task.params, rng=np.random.default_rng(0))
    views = task.demo_views(setup)
    assert len(views) == 6
    assert {v.caption.split(",")[0] for v in views} >= {"same", "different (mirror image)"}
    for v in views:
        v.draw(0.0)
