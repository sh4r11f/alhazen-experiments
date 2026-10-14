"""Trial logic on alhazen's fake clock with scripted inputs: no display, no devices."""

from __future__ import annotations

import argparse

import numpy as np
import pytest
from alhazen import InputFrame
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
from conftest import PROJECT, params_with
from pydantic import ValidationError

from stroop1935 import sheet
from stroop1935.task import (
    StroopColorNamingTask,
    StroopParams,
    StroopWordReadingTask,
    order_for_subject,
)

FRAME_S = 1 / 60
SCREEN = Screen(width_px=1920, height_px=1080, px_per_deg=40.0)
# A word item: "red" printed in blue ink. Colour naming wants blue (F), word reading red (D).
NCWD_ITEM = {"phase": "test", "test": "NCWd", "form": 1, "position": 1, "row": 1, "col": 1,
             "ink": "blue", "word": "red"}


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
                       record={**condition, **plan.record})
    return collector, engine.run_trial(ctx, plan.phases), ctx


def short(**changes):
    """The colour-naming params with a 3-frame fixation and a 30-frame deadline."""
    return params_with(block_order="A", fixation_duration={"frames": 3},
                       response_timeout={"frames": 30}, **changes)


@pytest.fixture
def task():
    return StroopColorNamingTask(short())


def script(*presses):
    """Empty frames with keys at the given frame indices: script((6, "f"), (10, "d")).
    The script ends on an empty frame, because ScriptedInputs repeats its last one."""
    last = max((i for i, _ in presses), default=0)
    frames = [InputFrame(gaze=None) for _ in range(last + 2)]
    for i, key in presses:
        frames[i] = InputFrame(gaze=None, keys=(key,))
    return frames


# Fixation is frames 0-2; the item is drawn on frame 3 and its flip stamped
# then, so frame 4 still holds pre-onset keys (ResponseWindow's rule) and the
# first key that can count is read on frame 5.

def test_the_right_first_key_is_correct_and_timed_from_the_item_flip(task):
    events, result, ctx = run_trial(task, NCWD_ITEM, script((6, "f")))
    assert result.outcome.name == "CORRECT"
    assert ctx.record["response_key"] == "f"
    assert ctx.record["first_correct"] is True
    assert ctx.record["n_errors"] == 0
    assert ctx.record["rt_ms"] == pytest.approx(2 * FRAME_S * 1000)
    assert ctx.record["rt_correct_ms"] == ctx.record["rt_ms"]
    assert ctx.record["target_color"] == "blue" and ctx.record["competing_color"] == "red"
    assert events.names()[:3] == ["FIX_ON", "RESPONSE_CUE", "RESPONSE"]


def test_a_corrected_error_keeps_the_item_until_the_right_key(task):
    events, result, ctx = run_trial(task, NCWD_ITEM, script((6, "d"), (10, "f")))
    assert result.outcome.name == "CORRECTED"
    assert ctx.record["response_key"] == "d" and ctx.record["first_correct"] is False
    assert ctx.record["n_errors"] == 1
    assert ctx.record["keys_pressed"] == "d,f"
    assert ctx.record["rt_correct_ms"] == pytest.approx(6 * FRAME_S * 1000)
    assert "CORRECTION" in events.names()


def test_an_error_never_corrected_ends_uncorrected_at_the_deadline(task):
    _, result, ctx = run_trial(task, NCWD_ITEM, script((6, "d"), (8, "k")))
    assert result.outcome.name == "UNCORRECTED"
    assert result.outcome.completed
    assert ctx.record["n_errors"] == 2 and ctx.record["rt_correct_ms"] is None


def test_no_key_at_all_is_not_completed_and_is_served_again(task):
    _, result, ctx = run_trial(task, NCWD_ITEM, script((1, "f")))  # pressed during fixation
    assert result.outcome.name == "NO_RESPONSE"
    assert not result.outcome.completed
    assert "response_key" not in ctx.record


def test_a_key_before_the_item_is_seen_does_not_count(task):
    _, result, _ = run_trial(task, NCWD_ITEM, script((4, "f")))
    assert result.outcome.name == "NO_RESPONSE"


def test_an_unbound_key_is_ignored(task):
    _, result, ctx = run_trial(task, NCWD_ITEM, script((6, "q"), (8, "f")))
    assert result.outcome.name == "CORRECT"
    assert ctx.record["keys_pressed"] == "f"


def test_without_correction_a_wrong_key_ends_the_trial():
    task = StroopColorNamingTask(short(require_correction=False))
    _, result, ctx = run_trial(task, NCWD_ITEM, script((6, "d"), (8, "f")))
    assert result.outcome.name == "WRONG"
    assert ctx.record["keys_pressed"] == "d"


def test_word_reading_answers_the_word_not_the_ink():
    task = StroopWordReadingTask(short())
    item = {**NCWD_ITEM, "test": "RCNd"}
    _, result, ctx = run_trial(task, item, script((6, "d")))
    assert result.outcome.name == "CORRECT"
    assert ctx.record["target_color"] == "red" and ctx.record["competing_color"] == "blue"
    black = {**item, "test": "RCNb", "ink": "black"}
    _, result, ctx = run_trial(task, black, script((6, "d")))
    assert result.outcome.name == "CORRECT" and ctx.record["competing_color"] == ""


def test_a_square_has_no_competing_colour(task):
    item = {**NCWD_ITEM, "test": "NC", "word": ""}
    _, result, ctx = run_trial(task, item, script((6, "f")))
    assert result.outcome.name == "CORRECT" and ctx.record["competing_key"] == ""


def test_every_params_file_loads_and_both_share_the_paradigm():
    color = load_params(PROJECT / "configs" / "task.yaml", StroopParams)
    word = load_params(PROJECT / "configs" / "task-word-reading.yaml", StroopParams)
    assert color == word  # one paradigm; the task decides what is answered


def test_the_params_model_refuses_inconsistent_files():
    with pytest.raises(ValidationError):
        params_with(keys={"red": "d", "blue": "d", "green": "j", "brown": "k", "purple": "l"})
    with pytest.raises(ValidationError):
        params_with(colors={"red": [1, -1, -1]})
    with pytest.raises(ValidationError):
        params_with(sheet_items=101)
    with pytest.raises(ValidationError):
        params_with(form_sequence=[1, 2, 3, 1])
    with pytest.raises(ValidationError):
        params_with(keys={"red": "space", "blue": "f", "green": "j", "brown": "k", "purple": "l"})


def test_the_session_is_four_sheets_in_stroops_balanced_order():
    task = StroopColorNamingTask(params_with(block_order="A"))
    blocks = task.plan(task.params)
    tests = [[c.params["test"] for c in b if c.params["phase"] == "test"] for b in blocks]
    assert [t[0] for t in tests] == ["NC", "NCWd", "NCWd", "NC"]
    assert all(len(t) == 100 for t in tests)
    forms = [{c.params["form"] for c in b if c.params["phase"] == "test"} for b in blocks]
    assert forms == [{1}, {2}, {1}, {2}]
    phases = [[c.params["phase"] for c in b] for b in blocks]
    assert phases[0][:25] == ["key_practice"] * 25 and phases[0][25:35] == ["practice"] * 10
    assert phases[1][:10] == ["practice"] * 10 and "practice" not in phases[2] + phases[3]
    assert sum(len(b) for b in blocks) == 445
    b_task = StroopColorNamingTask(params_with(block_order="B"))
    b_tests = [b[-1].params["test"] for b in b_task.plan(b_task.params)]
    assert b_tests == ["NCWd", "NC", "NC", "NCWd"]
    word = StroopWordReadingTask(params_with("configs/task-word-reading.yaml", block_order="A"))
    assert [b[-1].params["test"] for b in word.plan(word.params)] == ["RCNb", "RCNd", "RCNd", "RCNb"]


def test_the_schedule_serves_the_plan_with_rests_between_sheets():
    task = StroopColorNamingTask(params_with())
    schedule = task.duration_schedule(task.params, np.random.default_rng(0))
    assert schedule.n_trials == 445 and schedule.breaks == 3
    timing = task.trial_timing(Condition(NCWD_ITEM), 60.0)
    assert timing.min_s == pytest.approx(0.5) and timing.max_s == pytest.approx(5.5)


def test_an_unsettled_block_order_is_refused_when_scheduling():
    task = StroopColorNamingTask(params_with())
    with pytest.raises(ConfigError):
        task.make_source(task.params, np.random.default_rng(0))


def test_the_block_order_is_split_by_subject_number():
    assert order_for_subject("01")[0] == "A"
    assert order_for_subject("s02")[0] == "B"
    assert order_for_subject("sim")[0] in ("A", "B")
    assert order_for_subject("sim") == order_for_subject("sim")


def args(mode, sub="07"):
    return argparse.Namespace(mode=mode, sub=sub, ses=1, rig=None)


def test_params_hook_settles_the_order_and_shrinks_only_a_rehearsal():
    p = params_with()
    run = StroopColorNamingTask.params_hook(p, args("run"))
    assert run.block_order == "A" and "odd" in run.block_order_basis
    assert (run.sheet_items, run.practice_trials, run.key_practice_trials) == (100, 10, 25)
    sim = StroopColorNamingTask.params_hook(p, args("simulate", sub="08"))
    assert sim.block_order == "B"
    assert (sim.sheet_items, sim.practice_trials, sim.key_practice_trials) == (5, 2, 3)
    assert StroopColorNamingTask.params_hook(p, args("demo")) is p
    with pytest.raises(ConfigError):
        StroopColorNamingTask.params_hook(p, args("run", sub=None))


def test_the_subject_is_told_which_key_is_which_colour():
    text = StroopColorNamingTask(params_with()).instructions()
    assert "COLOUR OF THE INK" in text and "SPACE" in text
    for color, key in params_with().keys.items():
        assert f"{key.upper()}   {color}" in text
    assert "{KEYS}" not in text
    assert "WORD" in StroopWordReadingTask(params_with()).instructions()
    assert StroopColorNamingTask.default_params().is_file()
    assert StroopWordReadingTask.default_params().is_file()


def test_simulated_display_builds_stand_ins():
    task = StroopColorNamingTask(short())
    _, _, ctx = run_trial(task, NCWD_ITEM, script((6, "f")))
    assert ctx.stimuli["stimulus"].draw_count > 0
    assert sheet.NC in (task.CONTROL,)
