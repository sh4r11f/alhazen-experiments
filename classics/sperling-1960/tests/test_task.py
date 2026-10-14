"""Trial logic on alhazen's fake clock with scripted inputs: no display, no devices."""

from __future__ import annotations

import pytest
from alhazen import Duration
from alhazen.config.loader import load_params
from alhazen.display.screen import Screen
from alhazen.errors import ConfigError
from support import by_name, condition, idle, keys, run_trial, start_and_wait, type_text

from sperling1960.task import (
    PROJECT,
    PartialReportTask,
    PartialReportTaskParams,
    score_report,
    tone_class,
)

PRESENTATION_FRAMES = 120  # long enough for the 1.0 s delay at 60 Hz


def params(**changes):
    base = load_params(PROJECT / "configs" / "task.yaml", PartialReportTaskParams)
    return PartialReportTaskParams(**{**base.model_dump(), **changes})


@pytest.fixture
def task():
    return PartialReportTask(params(report_timeout=Duration(ms=3000),
                                    start_timeout=Duration(ms=1000)))


def typed(text):
    return lambda plan: start_and_wait(PRESENTATION_FRAMES) + type_text(text)


# -- outcomes ------------------------------------------------------------------------------


def test_typing_the_cued_row_scores_every_position(task):
    events, result, plan = run_trial(task, condition(cued_row=1),
                                     lambda plan: start_and_wait(PRESENTATION_FRAMES)
                                     + type_text(plan.record["target"]))
    assert result.outcome.name == "REPORTED"
    scored = task.score(result.record)
    assert scored["response"] == plan.record["target"]
    assert scored["n_correct"] == 4 and scored["correct_mask"] == "1111"
    assert scored["letters_available"] == 12  # 4 correct x 3 rows (paper p. 7)


def test_a_letter_counts_only_in_its_own_position(task):
    def script(plan):
        target = plan.record["target"]
        swapped = target[1] + target[0] + target[2:]  # the first two exchanged
        return start_and_wait(PRESENTATION_FRAMES) + type_text(swapped)

    _, result, plan = run_trial(task, condition(cued_row=0), script)
    scored = task.score(result.record)
    target = plan.record["target"]
    expected = sum(score_report(target[1] + target[0] + target[2:], target))
    assert scored["n_correct"] == expected
    assert scored["correct_mask"][2:] == "11"


def test_enter_before_every_box_is_filled_does_not_commit_and_backspace_corrects(task):
    def script(plan):
        t = plan.record["target"]
        wrong = "Z" if t[0] != "Z" else "B"
        return (start_and_wait(PRESENTATION_FRAMES) + type_text(t[:2]) + keys("return")
                + type_text(wrong, then_enter=False) + keys("backspace") + type_text(t[2:]))

    _, result, plan = run_trial(task, condition(), script)
    assert result.outcome.name == "REPORTED"
    assert result.record["response"] == plan.record["target"]
    assert result.record["n_erasures"] == 1


def test_no_report_before_the_deadline_is_re_served(task):
    _, result, _ = run_trial(task, condition(), lambda plan: start_and_wait(30))
    assert result.outcome.name == "NO_RESPONSE" and not result.outcome.completed


def test_no_start_press_is_re_served(task):
    _, result, _ = run_trial(task, condition(), lambda plan: idle(200))
    assert result.outcome.name == "NO_START" and not result.outcome.completed


def test_keys_during_the_presentation_are_not_typed(task):
    # Letters pressed while the card is up (before the cue) never reach the report.
    def script(plan):
        return (idle(2) + keys("space") + idle(31) + type_text("BDFG", then_enter=False)
                + idle(PRESENTATION_FRAMES))

    _, result, _ = run_trial(task, condition(delay_s=1.0), script)
    assert result.outcome.name == "NO_RESPONSE"
    assert result.record["response_partial"] == ""


def test_unbound_and_blocked_keys_are_not_typed(task):
    def script(plan):
        t = plan.record["target"]
        return (start_and_wait(PRESENTATION_FRAMES) + type_text("A", then_enter=False)
                + keys("space") + type_text(t))

    _, result, plan = run_trial(task, condition(), script)
    assert result.record["response"] == plan.record["target"]


def test_keypad_digits_count_as_digits(task):
    def script(plan):
        t = plan.record["target"]
        frames = [keys(f"num_{ch}")[0] if ch.isdigit() else type_text(ch, False)[0] for ch in t]
        return start_and_wait(PRESENTATION_FRAMES) + frames + keys("num_enter")

    _, result, plan = run_trial(task, condition(), script)
    assert result.record["response"] == plan.record["target"]


def test_digits_are_not_typed_for_a_letters_only_card():
    t = PartialReportTask(params(materials=["3/3/3"], report_timeout=Duration(ms=2000)))

    def script(plan):
        return start_and_wait(PRESENTATION_FRAMES) + type_text("12", then_enter=False)

    _, result, _ = run_trial(t, condition(material="3/3/3"), script)
    assert result.record["response_partial"] == ""


# -- timing --------------------------------------------------------------------------------


@pytest.mark.parametrize("hz, frames", [(60.0, 3), (75.0, 4), (100.0, 5), (120.0, 6),
                                        (144.0, 7), (240.0, 12)])
def test_the_exposure_is_whole_frames_at_the_measured_rate(task, hz, frames):
    events, result, plan = run_trial(task, condition(), typed("BBBB"), hz=hz)
    assert plan.record["exposure_frames"] == frames
    scored = task.score(result.record)
    assert scored["exposure_ms_measured"] == pytest.approx(frames * 1000 / hz)
    assert scored["exposure_ms_planned"] == pytest.approx(frames * 1000 / hz)


@pytest.mark.parametrize("delay, frames_after_offset", [(-0.10, -6), (0.0, 0), (0.15, 9),
                                                        (0.30, 18), (0.50, 30), (1.0, 60)])
def test_the_cue_starts_at_its_delay_from_the_arrays_offset(task, delay, frames_after_offset):
    events, result, plan = run_trial(task, condition(delay_s=delay, cued_row=2), typed("BBBB"))
    ev = by_name(events)
    assert "CUE_LOW" in ev and ev["CUE_LOW"].payload == {"row": 2, "delay_s": delay}
    measured = ev["CUE_LOW"].t - ev["ARRAY_OFF"].t
    assert measured == pytest.approx(frames_after_offset / 60.0)
    assert task.score(result.record)["cue_delay_ms_measured"] == pytest.approx(
        frames_after_offset * 1000 / 60.0)


def test_a_cue_at_minus_010_comes_50_ms_before_the_array(task):
    events, _, _ = run_trial(task, condition(delay_s=-0.10), typed("BBBB"))
    ev = by_name(events)
    assert ev["ARRAY_ON"].t - ev["CUE_HIGH"].t == pytest.approx(0.05)


def test_the_presentation_starts_half_a_second_after_the_press(task):
    events, _, _ = run_trial(task, condition(), typed("BBBB"))
    ev = by_name(events)
    # The press frame is shown, then 30 frames of the fixation field, then the card.
    assert ev["ARRAY_ON"].t - ev["FIX_ON"].t == pytest.approx((2 + 1 + 30) / 60.0)


def test_the_response_boxes_appear_when_the_cue_ends(task):
    events, _, _ = run_trial(task, condition(delay_s=0.15), typed("BBBB"))
    ev = by_name(events)
    assert ev["RESPONSE_BOXES_ON"].t - ev["CUE_HIGH"].t == pytest.approx(0.5)


# -- what is drawn -------------------------------------------------------------------------


def test_the_visual_cue_bar_is_drawn_beside_the_cued_row_for_half_a_second(task):
    _, _, plan = run_trial(task, condition(delay_s=0.3, cued_row=1), typed("BBBB"))
    bar = plan.stimuli["cue_light"]
    assert bar.draw_count == 30  # 0.5 s at 60 Hz, all on the dark field
    assert plan.stimuli["cue_dark"].draw_count == 0
    assert bar.spec["xy"][1] == pytest.approx(0.0)  # the middle row of three
    assert plan.stimuli["card"].draw_count == 3


def test_a_cue_before_onset_turns_dark_while_the_card_is_lit(task):
    _, _, plan = run_trial(task, condition(delay_s=-0.10), typed("BBBB"))
    assert plan.stimuli["cue_dark"].draw_count == 3  # the three card frames
    assert plan.stimuli["cue_light"].draw_count == 27  # 3 before onset + 24 after


def test_the_fixation_cross_is_off_while_the_card_is_lit(task):
    _, _, plan = run_trial(task, condition(), typed("BBBB"))
    fix, card, field = (plan.stimuli[k].draw_count for k in ("fixation", "card", "field"))
    assert card == 3 and field == fix + card


def test_tone_mode_draws_no_bar_but_emits_the_cue_event():
    if tone_class() is None:
        pytest.skip("alhazen here has no Tone (event-bound tones); tone mode refuses to load")
    t = PartialReportTask(params(cue_mode="tone"))
    events, _, plan = run_trial(t, condition(cued_row=0), typed("BBBB"))
    assert "CUE_HIGH" in by_name(events)
    assert plan.stimuli["cue_light"].draw_count == 0


def test_a_whole_report_types_every_symbol_with_no_cue():
    t = PartialReportTask(params(report="whole", cue_delays_s=[], materials=["3/3"],
                                 report_timeout=Duration(ms=5000)))
    events, result, plan = run_trial(
        t, condition(material="3/3", report="whole"),
        lambda plan: start_and_wait(40) + type_text(plan.record["target"]))
    assert result.outcome.name == "REPORTED"
    assert not any(e.name.startswith("CUE_") for e in events)
    scored = t.score(result.record)
    assert scored["n_correct"] == 6 and scored["letters_available"] == 6


def test_a_card_that_does_not_fit_the_screen_is_refused(task):
    small = Screen(width_px=800, height_px=600, px_per_deg=40.0)  # 20 x 15 dva
    with pytest.raises(ConfigError, match="dva"):
        run_trial(task, condition(), typed("BBBB"), screen=small)


# -- params --------------------------------------------------------------------------------


def test_every_params_file_loads():
    files = sorted((PROJECT / "configs").glob("task*.yaml"))
    assert len(files) == 4
    for path in files:
        load_params(path, PartialReportTaskParams)


def test_tone_mode_refuses_to_load_without_alhazen_tone(tmp_path):
    if tone_class() is not None:
        pytest.skip("this alhazen has Tone; the refusal does not apply")
    text = (PROJECT / "configs" / "task.yaml").read_text(encoding="utf-8")
    path = tmp_path / "task-tone.yaml"
    path.write_text(text.replace("cue_mode: visual", "cue_mode: tone", 1), encoding="utf-8")
    with pytest.raises(ConfigError, match="alhazen.Tone"):
        load_params(path, PartialReportTaskParams)


def test_tone_mode_binds_the_papers_three_tones_to_the_cue_events():
    tone = tone_class()
    if tone is None:
        pytest.skip("alhazen here has no Tone (event-bound tones); see the refusal test")
    t = PartialReportTask(params(cue_mode="tone"))
    assert set(t.tones) == {"CUE_HIGH", "CUE_MID", "CUE_LOW"}
    assert set(t.tones) <= set(t.events.declared)
    assert [t.tones[k].hz for k in ("CUE_HIGH", "CUE_MID", "CUE_LOW")] == [2500, 650, 250]
    assert all(t.tones[k].seconds == pytest.approx(0.5) for k in t.tones)
    assert PartialReportTask(params()).tones == {}


@pytest.mark.parametrize("changes, message", [
    ({"consonants": "BDFGP"}, "experimenter"),
    ({"consonants": "BDAFG"}, "vowels"),
    ({"report": "whole"}, "no cue"),
    ({"cue_delays_s": []}, "cue_delays_s"),
    ({"materials": ["5/5"]}, "unknown material"),
    ({"paradigm": {"kind": "staircase", "staircase": {"parameter": "x", "start": 1, "step": 1,
                                                      "n_trials": 3}}}, "series"),
])
def test_bad_params_are_refused_with_a_reason(changes, message):
    with pytest.raises(ValueError, match=message):
        params(**changes)


def test_the_subject_is_told_what_to_do():
    assert PartialReportTask.default_params().is_file()
    for name in ("instructions.md", "instructions-tone.md", "instructions-whole.md"):
        text = (PROJECT / name).read_text(encoding="utf-8")
        assert "SPACE" in text and "ENTER" in text and "C, H, P and R" in text
