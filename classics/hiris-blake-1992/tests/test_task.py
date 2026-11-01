"""Trial logic on alhazen's fake clock with scripted inputs: no display, no devices."""

from __future__ import annotations

import numpy as np
import pytest
from alhazen import Duration, InputFrame
from alhazen.config.loader import build_session_config, load_params
from alhazen.config.models import DisplayConfig, MonitorConfig, RigConfig, SessionInfo
from alhazen.core.commands import Command
from alhazen.core.engine import TrialEngine
from alhazen.core.events import EventBus
from alhazen.core.trial import TrialContext
from alhazen.display.screen import Screen
from alhazen.paradigms.base import Condition
from alhazen.task.plan import TrialSetup
from alhazen.testing import EventCollector, FakeClock, FakeDisplay, ScriptedCommands, ScriptedInputs

from hirisblake1992.task import (
    PROJECT,
    MaeCoherenceMatchTask,
    MaeCoherenceMatchTaskParams,
    signal_for,
)

FRAME_S = 1 / 60
SCREEN = Screen(width_px=1920, height_px=1080, px_per_deg=72.0)


def run_trial(task, condition, inputs, commands=None):
    clock = FakeClock()
    display = FakeDisplay(clock, FRAME_S)
    bus = EventBus()
    collector = EventCollector()
    bus.subscribe(collector)
    engine = TrialEngine(display=display, clock=clock, bus=bus, schema=task.events,
                         commands=commands or ScriptedCommands(),
                         input_provider=ScriptedInputs(inputs))
    monitor = MonitorConfig(width_px=1920, height_px=1080, width_cm=53.0, distance_cm=114.0,
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
    return collector, engine.run_trial(ctx, plan.phases), ctx, plan


def make_task(**kw):
    base = dict(subject_kind="human", initial_adaptation=Duration(frames=30),
                topup_adaptation=Duration(frames=12), test_duration=Duration(frames=6),
                response_timeout=Duration(frames=40))
    base.update(kw)
    return MaeCoherenceMatchTask(MaeCoherenceMatchTaskParams(**base))


@pytest.fixture
def task():
    return make_task()


def cond(level=10.0, mode="unidirectional"):
    return {"test_signal_pct": level, "adapt_mode": mode}


def frames(n, keys=()):
    return [InputFrame(gaze=None)] * n + [InputFrame(gaze=None, keys=tuple(keys))]


def onset(collector, name):
    return next(e.t for e in collector.events if e.name == name)


def test_the_left_key_after_the_test_chooses_the_adapted_display(task):
    _, result, ctx, _ = run_trial(task, cond(), frames(45, ["left"]))
    assert result.outcome.name == "CHOSE_TEST"
    assert task.score(dict(ctx.record, outcome="CHOSE_TEST"))["chose_test"] == 1


def test_the_right_key_chooses_the_reference(task):
    _, result, ctx, _ = run_trial(task, cond(), frames(45, ["right"]))
    assert result.outcome.name == "CHOSE_REFERENCE"
    assert task.score(dict(ctx.record))["chose_test"] == 0


def test_no_key_times_out_and_is_not_a_measurement(task):
    _, result, _, _ = run_trial(task, cond(), frames(120))
    assert result.outcome.name == "NO_RESPONSE"
    assert not result.outcome.completed


def test_phases_run_in_the_papers_order_with_their_durations(task):
    collector, _, ctx, _ = run_trial(task, cond(), frames(45, ["left"]))
    adapt, test, cue = (onset(collector, n) for n in ("ADAPT_ON", "TEST_ON", "RESPONSE_CUE"))
    assert adapt < test < cue
    assert test - adapt == pytest.approx(30 * FRAME_S)  # the initial adaptation
    assert cue - test == pytest.approx(6 * FRAME_S)  # the test displays
    assert ctx.record["adaptation_kind"] == "initial"


def test_a_key_during_the_test_or_adaptation_is_not_an_answer(task):
    # pressed on frame 20 (adaptation) and frame 33 (test): ignored; no key afterwards
    inputs = [InputFrame(gaze=None)] * 20 + [InputFrame(gaze=None, keys=("left",))]
    inputs += [InputFrame(gaze=None)] * 12 + [InputFrame(gaze=None, keys=("left",))]
    inputs += [InputFrame(gaze=None)] * 90
    _, result, _, _ = run_trial(task, cond(), inputs)
    assert result.outcome.name == "NO_RESPONSE"


def test_after_the_first_test_trials_start_with_a_top_up(task):
    run_trial(task, cond(), frames(45, ["left"]))
    collector, _, ctx, _ = run_trial(task, cond(), frames(25, ["left"]))
    assert ctx.record["adaptation_kind"] == "top-up"
    assert onset(collector, "TEST_ON") - onset(collector, "ADAPT_ON") == pytest.approx(
        12 * FRAME_S)


def test_a_long_pause_repeats_the_initial_adaptation(task):
    t = [1000.0]
    task.now = lambda: t[0]
    run_trial(task, cond(), frames(45, ["left"]))
    t[0] += 29.0
    _, _, ctx, _ = run_trial(task, cond(), frames(25, ["left"]))
    assert ctx.record["adaptation_kind"] == "top-up"
    t[0] += 31.0
    _, _, ctx, _ = run_trial(task, cond(), frames(60, ["left"]))
    assert ctx.record["adaptation_kind"] == "initial"


def test_an_aborted_initial_adaptation_is_not_counted():
    task = make_task()
    skip = ScriptedCommands([[]] * 5 + [[Command.SKIP_TRIAL]])  # escape during adaptation
    _, result, _, _ = run_trial(task, cond(), frames(45, ["left"]), skip)
    assert result.outcome.name == "ABORTED"
    assert task.last_test_on is None
    _, _, ctx, _ = run_trial(task, cond(), frames(45, ["left"]))
    assert ctx.record["adaptation_kind"] == "initial"


def test_the_four_displays_follow_the_paper_in_the_adapted_set(task):
    s = task.display_specs(-20.0, 60.0)
    assert (s["adapt_left"].signal_fraction, s["adapt_left"].signal_direction_deg) == (1.0, 90.0)
    assert s["adapt_right"].signal_fraction == 0.0  # RDVN
    assert (s["test_left"].n_signal, s["test_left"].signal_direction_deg) == (20, 90.0)  # up
    assert (s["test_right"].n_signal, s["test_right"].signal_direction_deg) == (40, 270.0)
    assert task.display_specs(30.0, 60.0)["test_left"].signal_direction_deg == 270.0  # down
    assert signal_for(0.0, 90.0) == (0.0, 270.0)


def test_the_control_set_adapts_both_displays_to_random_motion():
    p = load_params(PROJECT / "configs" / "task-control.yaml", MaeCoherenceMatchTaskParams)
    s = MaeCoherenceMatchTask(p).display_specs(0.0, 60.0)
    assert s["adapt_left"].signal_fraction == s["adapt_right"].signal_fraction == 0.0
    assert s["test_right"].n_signal == 40


def test_the_displays_sit_where_the_paper_put_them():
    p = load_params(PROJECT / "configs" / "task.yaml", MaeCoherenceMatchTaskParams)
    left, right = p.center_dva("left"), p.center_dva("right")
    assert right[0] - left[0] - p.aperture_dva == pytest.approx(4.8)  # nearest edges 4.8 deg
    assert left[0] == pytest.approx(-right[0])  # the cross midway


def test_the_record_carries_the_realised_motion_and_the_seeds(task):
    _, _, ctx, _ = run_trial(task, cond(), frames(45, ["left"]))
    r = ctx.record
    assert r["update_frames"] == 3 and r["speed_dva_s"] == pytest.approx(1.914)
    assert r["dot_size_px"] == pytest.approx(2.4, abs=0.01)
    assert {k for k in r if k.startswith("seed_")} == {
        "seed_adapt_left", "seed_adapt_right", "seed_test_left", "seed_test_right"}


def test_the_dots_are_stepped_during_the_phases_that_show_them(task):
    _, _, _, plan = run_trial(task, cond(), frames(45, ["left"]))
    # 30 adaptation frames -> 9 steps of 3 frames; the test field only during the test
    assert plan.stimuli["adapt_left"].steps >= 9
    assert plan.stimuli["test_left"].steps in (1, 2)
    assert set(plan.stimuli["adapt_left"].signal_counts) == {100}
    assert set(plan.stimuli["adapt_right"].signal_counts) == {0}


def test_every_params_file_loads():
    for path in (PROJECT / "configs").glob("task*.yaml"):
        load_params(path, MaeCoherenceMatchTaskParams)


def test_bad_params_are_refused():
    with pytest.raises(ValueError):
        MaeCoherenceMatchTaskParams(subject_kind="human", test_levels_pct=[0.0, 0.0])
    with pytest.raises(ValueError):
        MaeCoherenceMatchTaskParams(subject_kind="human", key_left="x", key_right="x")


def test_the_subject_is_told_what_to_do():
    text = (PROJECT / "instructions.md").read_text(encoding="utf-8")
    assert "SPACE" in text and "Left arrow" in text and "Right arrow" in text
