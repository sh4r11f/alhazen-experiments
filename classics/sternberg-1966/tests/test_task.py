"""Trial logic on alhazen's fake clock with scripted inputs: no display, no devices.

Every outcome branch of both procedures, the phase order, what is drawn and for how many
frames, and what lands in the record.
"""

from __future__ import annotations

import pytest
from alhazen import Duration
from alhazen.config.loader import load_params
from alhazen.core.commands import Command
from alhazen.testing import ScriptedCommands
from harness import FRAME_S, build, frames, run, typed

from sternberg1966.stimuli import RecordingLamp, RecordingText
from sternberg1966.task import (
    PROJECT,
    FixedSetMemoryScanningTask,
    FixedSetParams,
    MemoryScanningTask,
    VariedSetParams,
)

F = Duration(frames=2)  # every timed phase two frames long in these tests


@pytest.fixture
def varied():
    return MemoryScanningTask(VariedSetParams(
        subject_kind="human", item_duration=F, delay=F, warning_duration=F,
        feedback_duration=F, response_timeout=Duration(frames=20),
        recall_timeout=Duration(frames=40)))


def probe_start(s: int) -> int:
    """Frames before the test digit's phase: s items, the delay, the warning."""
    return 2 * s + 2 + 2


def answer(plan, correct: bool, task) -> str:
    positive = plan.record["probe_type"] == "positive"
    p = task.params
    return (p.positive_key if positive else p.negative_key) if correct else (
        p.negative_key if positive else p.positive_key)


def varied_trial(task, s, probe_type, script, seed=0):
    condition = {"set_size": s, "probe_type": probe_type, "stage": "test"}
    plan, env = build(task, condition, seed)
    return plan, env, condition


@pytest.mark.parametrize("probe_type", ["positive", "negative"])
@pytest.mark.parametrize("s", [1, 4, 6])
def test_a_correct_answer_and_recall(varied, s, probe_type):
    plan, env, condition = varied_trial(varied, s, probe_type, None)
    key = answer(plan, True, varied)
    ran = run(varied, plan, env, condition,
              frames(probe_start(s) + 4, key, 8, *typed(plan.record["series"]), "return"))
    assert ran.result.outcome.name == "CORRECT"
    r = ran.ctx.record
    assert r["response"] == probe_type and r["correct"] is True
    assert r["recall"] == plan.record["series"] and r["recall_correct"] is True
    assert r["recall_committed"] is True
    # 4 frames after the digit's first flip minus the two frames ResponseWindow ignores.
    assert r["rt_ms"] == pytest.approx(3 * FRAME_S * 1000, abs=0.5)
    assert ran.names == (["ITEM_ON"] * s + ["WARNING_ON", "PROBE_ON", "PROBE_DIGIT",
                         "RESPONSE", "FEEDBACK_ON", "RECALL_ON", "RECALL_DONE"])
    assert [e.payload["digit"] for e in ran.events if e.name == "ITEM_ON"] == [
        int(c) for c in plan.record["series"]]
    assert ran.event("PROBE_DIGIT").payload == {"digit": plan.record["probe_digit"]}


def test_the_series_and_probe_are_drawn_for_their_frames(varied):
    plan, env, condition = varied_trial(varied, 3, "positive", None)
    run(varied, plan, env, condition,
        frames(probe_start(3) + 4, "j", 8, *typed(plan.record["series"]), "return"))
    for k, digit in enumerate(plan.record["series"], start=1):
        item = plan.stimuli[f"item{k}"]
        assert isinstance(item, RecordingText) and item.drawn == [digit, digit]
    assert plan.stimuli["warning"].drawn == ["+", "+"]
    assert set(plan.stimuli["probe"].drawn) == {str(plan.record["probe_digit"])}
    lamp = plan.stimuli["lamp"]
    assert isinstance(lamp, RecordingLamp) and lamp.draw_count == 2


def test_a_positive_probe_is_in_the_series_and_a_negative_one_is_not(varied):
    for seed in range(40):
        for probe_type in ("positive", "negative"):
            plan, _ = build(varied, {"set_size": 4, "probe_type": probe_type, "stage": "test"},
                            seed)
            series, probe = plan.record["series"], str(plan.record["probe_digit"])
            assert len(set(series)) == 4
            assert (probe in series) == (probe_type == "positive")
            if probe_type == "positive":
                assert series[plan.record["probe_position"] - 1] == probe


def test_the_wrong_lever_scores_wrong_and_lights_red(varied):
    plan, env, condition = varied_trial(varied, 2, "negative", None)
    key = answer(plan, False, varied)
    ran = run(varied, plan, env, condition,
              frames(probe_start(2) + 4, key, 8, *typed(plan.record["series"]), "return"))
    assert ran.result.outcome.name == "WRONG"
    assert ran.ctx.record["correct"] is False
    assert ran.event("FEEDBACK_ON").payload == {"correct": False}
    assert plan.stimuli["lamp"].colors == [varied.params.wrong_color]


def test_a_correct_answer_lights_green(varied):
    plan, env, condition = varied_trial(varied, 2, "positive", None)
    run(varied, plan, env, condition,
        frames(probe_start(2) + 4, "j", 8, *typed(plan.record["series"]), "return"))
    assert plan.stimuli["lamp"].colors == [varied.params.correct_color]


def test_no_answer_times_out_with_no_light_and_no_recall(varied):
    plan, env, condition = varied_trial(varied, 3, "positive", None)
    ran = run(varied, plan, env, condition, frames(80))
    assert ran.result.outcome.name == "NO_RESPONSE"
    assert ran.result.outcome.completed is False
    assert "FEEDBACK_ON" not in ran.names and "RECALL_ON" not in ran.names
    assert "response" not in ran.ctx.record


def test_keys_before_the_test_digit_are_not_answers(varied):
    plan, env, condition = varied_trial(varied, 2, "positive", None)
    # A "no" pressed during the warning signal, then the real "yes".
    ran = run(varied, plan, env, condition,
              frames(probe_start(2) - 1, "f", 4, "j", 8, *typed(plan.record["series"]), "return"))
    assert ran.result.outcome.name == "CORRECT"
    assert ran.ctx.record["response_key"] == "j"


def test_unbound_keys_during_the_test_digit_are_ignored(varied):
    plan, env, condition = varied_trial(varied, 1, "negative", None)
    ran = run(varied, plan, env, condition,
              frames(probe_start(1) + 4, ("x", "5"), 2, "f", 8,
                     *typed(plan.record["series"]), "return"))
    assert ran.result.outcome.name == "CORRECT"


def test_a_wrong_recall_is_recorded_but_does_not_change_the_outcome(varied):
    plan, env, condition = varied_trial(varied, 3, "positive", None)
    wrong = plan.record["series"][::-1]
    ran = run(varied, plan, env, condition,
              frames(probe_start(3) + 4, "j", 8, *typed(wrong), "return"))
    assert ran.result.outcome.name == "CORRECT"
    assert ran.ctx.record["recall"] == wrong and ran.ctx.record["recall_correct"] is False


def test_backspace_edits_and_the_number_pad_types(varied):
    plan, env, condition = varied_trial(varied, 2, "positive", None)
    a, b = plan.record["series"]
    ran = run(varied, plan, env, condition,
              frames(probe_start(2) + 4, "j", 8, f"num_{a}", 1, "9", 1, "backspace", 1, b, 1,
                     "num_enter"))
    assert ran.ctx.record["recall"] == a + b and ran.ctx.record["recall_correct"] is True


def test_enter_with_nothing_typed_does_not_end_the_recall(varied):
    plan, env, condition = varied_trial(varied, 1, "negative", None)
    ran = run(varied, plan, env, condition,
              frames(probe_start(1) + 4, "f", 8, "return", 2, plan.record["series"], 1, "return"))
    assert ran.ctx.record["recall"] == plan.record["series"]
    assert ran.ctx.record["recall_committed"] is True


def test_a_recall_that_runs_out_of_time_keeps_what_was_typed(varied):
    plan, env, condition = varied_trial(varied, 2, "positive", None)
    first = plan.record["series"][0]
    ran = run(varied, plan, env, condition, frames(probe_start(2) + 4, "j", 8, first, 80))
    assert ran.result.outcome.name == "CORRECT"
    r = ran.ctx.record
    assert r["recall"] == first and r["recall_committed"] is False and r["recall_correct"] is False
    assert "recall_s" not in r


def test_the_record_says_what_the_trial_was(varied):
    plan, _ = build(varied, {"set_size": 5, "probe_type": "negative", "stage": "practice"})
    r = plan.record
    assert r["procedure"] == "varied-set" and r["stage"] == "practice"
    assert r["set_size"] == 5 and len(r["series"]) == 5 and r["probe_position"] is None


def test_a_gap_between_items_is_a_blank(varied):
    task = MemoryScanningTask(varied.params.model_copy(update={"item_gap": Duration(frames=3)}))
    plan, env, condition = varied_trial(task, 2, "positive", None)
    names = [type(ph).__name__ for ph in plan.phases]
    assert names[:3] == ["Feedback", "Blank", "Feedback"]


# ---------------------------------------------------------------- experiment 2


@pytest.fixture
def fixed():
    return FixedSetMemoryScanningTask(FixedSetParams(
        subject_kind="human", warning_duration=Duration(ms=50), feedback_duration=Duration(ms=50),
        iti=Duration(ms=100), response_to_next_probe=Duration(ms=200),
        response_timeout=Duration(frames=20)))


def fixed_condition(probe_digit=3, probe_type="positive", part=1):
    return {"part": part, "set_size": 2, "stage": "test", "positive_set": "37",
            "probe_digit": probe_digit, "probe_role": "y1", "probe_copy": 1,
            "probe_type": probe_type}


def test_the_first_trial_of_a_part_announces_the_positive_set(fixed):
    c = fixed_condition()
    plan, env = build(fixed, c)
    assert type(plan.phases[0]).__name__ == "AwaitKey"
    # SPACE on the second frame reads the set; then the ITI blank (6 frames), the warning
    # (3 frames) and the test digit.
    ran = run(fixed, plan, env, c, frames(1, "space", 6 + 3 + 4, "j", 10))
    assert ran.result.outcome.name == "CORRECT"
    assert ran.names[:2] == ["SET_ANNOUNCED", "WARNING_ON"]
    assert ran.event("SET_ANNOUNCED").payload == {"part": 1, "digits": [3, 7]}
    assert plan.stimuli["announce_set"].drawn[0] == "3 7"
    # The part is announced once: its next trial starts with the warning signal.
    plan2, _ = build(fixed, fixed_condition(probe_digit=5, probe_type="negative"))
    assert type(plan2.phases[0]).__name__ == "Feedback"
    plan3, _ = build(fixed, fixed_condition(part=2))
    assert type(plan3.phases[0]).__name__ == "AwaitKey"


def test_an_announcement_not_yet_read_is_shown_again(fixed):
    c = fixed_condition()
    plan, env = build(fixed, c)
    # The experimenter skips the trial while the set is still on screen, unread.
    skip = ScriptedCommands(batches=[[], [], [Command.SKIP_TRIAL]])
    ran = run(fixed, plan, env, c, frames(10), commands=skip)
    assert ran.result.outcome.name == "ABORTED"
    plan2, _ = build(fixed, c)
    assert type(plan2.phases[0]).__name__ == "AwaitKey"


def read(task, part=1):
    task._announced.add(part)


@pytest.mark.parametrize("probe,probe_type,key,outcome", [
    (3, "positive", "j", "CORRECT"), (5, "negative", "f", "CORRECT"),
    (3, "positive", "f", "WRONG"), (5, "negative", "j", "WRONG")])
def test_fixed_set_answers(fixed, probe, probe_type, key, outcome):
    read(fixed)
    c = fixed_condition(probe, probe_type)
    plan, env = build(fixed, c)
    ran = run(fixed, plan, env, c, frames(3 + 4, key, 10))
    assert ran.result.outcome.name == outcome
    assert ran.names == ["WARNING_ON", "PROBE_ON", "PROBE_DIGIT", "RESPONSE", "FEEDBACK_ON"]
    assert ran.ctx.record["procedure"] == "fixed-set" and ran.ctx.record["set_size"] == 2


def test_fixed_set_no_answer_times_out(fixed):
    read(fixed)
    c = fixed_condition()
    plan, env = build(fixed, c)
    ran = run(fixed, plan, env, c, frames(60))
    assert ran.result.outcome.name == "NO_RESPONSE" and "FEEDBACK_ON" not in ran.names


# ---------------------------------------------------------------- params files


def test_every_params_file_loads():
    assert load_params(PROJECT / "configs" / "task.yaml", VariedSetParams)
    assert load_params(PROJECT / "configs" / "task-fixed-set.yaml", FixedSetParams)


def test_the_subject_is_told_what_to_do_with_the_real_keys():
    for task_class, params in ((MemoryScanningTask, VariedSetParams),
                               (FixedSetMemoryScanningTask, FixedSetParams)):
        assert task_class.default_params().is_file()
        text = task_class(load_params(task_class.default_params(), params)).instructions()
        assert "SPACE" in text and "{" not in text
        assert "J  =  yes" in text and "F  =  no" in text
    assert "SPACE" in (PROJECT / "instructions.md").read_text(encoding="utf-8")
