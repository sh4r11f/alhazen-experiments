"""Trial logic on alhazen's fake clock with scripted inputs: every outcome
branch, the event timeline, the distractor cycle and the dimming."""

from __future__ import annotations

import math

import pytest
from alhazen.config.loader import load_params
from helpers import (
    CATCH_K,
    DIM_K,
    DIM_N,
    FRAME_S,
    MIN_RT_K,
    SCREEN,
    SOA_K,
    WINDOW_K,
    condition,
    params,
    run_trial,
    script,
)

from moore_fallah2001.luminance import dimmed_luminance, to_rgb
from moore_fallah2001.task import (
    PROJECT,
    TargetDimmingDetectionTask,
    TargetDimmingDetectionTaskParams,
)

# Watch frame k flips at t0 + (k + 1) frames, so DIM_ON is stamped at frame
# DIM_K + 1 and a key read on frame k is (k - DIM_K - 1) frames after it.
FIRST_HIT_K = DIM_K + 1 + MIN_RT_K


@pytest.fixture
def task():
    return TargetDimmingDetectionTask(params())


def names(collector):
    return [e.name for e in collector.events]


def t_of(collector, name):
    return next(e.t for e in collector.events if e.name == name)


def test_a_press_after_the_dimming_is_a_hit_with_its_reaction_time(task):
    ev, result, ctx, _ = run_trial(task, condition(), script(press_at=FIRST_HIT_K + 5))
    assert result.outcome.name == "HIT" and result.outcome.completed
    assert ctx.record["rt_ms"] == pytest.approx((MIN_RT_K + 5) * FRAME_S * 1000)
    assert names(ev).index("DIM_ON") < names(ev).index("RESPONSE")


def test_no_press_within_the_window_is_a_miss(task):
    ev, result, ctx, _ = run_trial(task, condition(), script())
    assert result.outcome.name == "MISS" and result.outcome.completed
    assert "RESPONSE" not in names(ev)
    end = max(e.t for e in ev.events if e.name in ("DIM_ON", "DIM_OFF"))
    assert end - t_of(ev, "DIM_ON") < WINDOW_K * FRAME_S


def test_a_press_before_the_dimming_is_early(task):
    _, result, ctx, _ = run_trial(task, condition(), script(press_at=DIM_K - 10))
    assert result.outcome.name == "EARLY_RESPONSE" and result.outcome.completed
    assert "rt_ms" not in ctx.record


def test_a_press_too_soon_after_the_dimming_is_early(task):
    _, result, ctx, _ = run_trial(task, condition(), script(press_at=FIRST_HIT_K - 1))
    assert result.outcome.name == "EARLY_RESPONSE"
    assert ctx.record["rt_ms"] < MIN_RT_K * FRAME_S * 1000


def test_a_press_on_a_catch_trial_is_a_false_alarm(task):
    ev, result, _, _ = run_trial(task, condition("catch"), script(press_at=40))
    assert result.outcome.name == "FALSE_ALARM" and result.outcome.completed
    assert "DIM_ON" not in names(ev)


def test_holding_off_a_catch_trial_is_a_correct_rejection_after_its_duration(task):
    ev, result, _, plan = run_trial(task, condition("catch"), script())
    assert result.outcome.name == "CORRECT_REJECTION" and result.outcome.success
    assert "DIM_ON" not in names(ev)
    # The target is on screen for exactly the catch duration, in frames.
    assert len(plan.stimuli["target"].draws) == CATCH_K


def test_the_dark_background_is_up_from_the_first_fixation_frame(task):
    _, _, _, plan = run_trial(task, condition("catch"), script())
    # One acquisition frame, then the catch trial's frames, all on the background.
    assert len(plan.stimuli["background"].draws) == CATCH_K + 1
    assert len(plan.stimuli["fixation"].draws) == CATCH_K + 1


def test_a_key_already_down_when_the_target_appears_is_ignored(task):
    _, result, _, _ = run_trial(task, condition("catch"), script(press_at=0))
    assert result.outcome.name == "CORRECT_REJECTION"


def test_looking_away_is_a_fixation_break_that_is_served_again(task):
    _, result, ctx, _ = run_trial(task, condition(), script(look_away_at=12))
    assert result.outcome.name == "FIX_BREAK" and not result.outcome.completed
    # Read on watch frame 12; the target's first flip was frame 0's, one frame after t0.
    assert ctx.record["fix_break_from_target_ms"] == pytest.approx(11 * FRAME_S * 1000)


def test_never_fixating_times_out_as_no_fixation(task):
    _, result, _, _ = run_trial(task, condition(), script(fixate=False))
    assert result.outcome.name == "NO_FIXATION" and not result.outcome.completed


def test_the_stimulation_trigger_precedes_the_dimming_by_the_soa(task):
    ev, _, ctx, _ = run_trial(task, condition(stimulation=True), script())
    assert t_of(ev, "DIM_ON") - t_of(ev, "STIM_TRIGGER") == pytest.approx(SOA_K * FRAME_S)
    assert ctx.record["realised_soa_ms"] == pytest.approx(SOA_K * FRAME_S * 1000)
    assert names(ev).count("STIM_TRIGGER") == 1


def test_catch_trials_on_the_stimulation_staircase_are_stimulated_too(task):
    ev, _, _, _ = run_trial(task, condition("catch", stimulation=True), script())
    assert t_of(ev, "STIM_TRIGGER") - t_of(ev, "TARGET_ON") == pytest.approx(
        (DIM_K - SOA_K) * FRAME_S)


def test_control_trials_carry_no_stimulation_trigger(task):
    ev, _, _, _ = run_trial(task, condition(stimulation=False), script())
    assert "STIM_TRIGGER" not in names(ev)


def test_the_target_dims_by_the_staircase_contrast_for_its_duration(task):
    p = task.params
    ev, _, ctx, plan = run_trial(task, condition(dim_pct=40.0), script())
    target = plan.stimuli["target"]
    dimmed = to_rgb(dimmed_luminance(p.target_cd_m2, 40.0), p.photometry)
    assert [c for _, c in target.draws].count(dimmed) == DIM_N
    assert t_of(ev, "DIM_OFF") - t_of(ev, "DIM_ON") == pytest.approx(DIM_N * FRAME_S)
    assert ctx.record["dimmed_cd_m2"] == pytest.approx(26.0 * 0.6 / 1.4)


def test_distractors_flash_one_frame_in_two_away_from_target_and_fixation(task):
    p = task.params
    _, _, ctx, plan = run_trial(task, condition("catch"), script())
    draws = plan.stimuli["distractor"].draws
    assert len(draws) == math.ceil(CATCH_K / 2)  # frames 0, 2, 4, ... of CATCH_K frames
    assert ctx.record["n_distractor_flashes"] == len(draws)
    tx, ty = ctx.record["target_x_dva"], ctx.record["target_y_dva"]
    half_side = math.sqrt(p.distractor_area_deg2) / 2
    for (x, y), _ in draws:
        x, y = SCREEN.px2deg(x), SCREEN.px2deg(y)
        assert math.hypot(x - tx, y - ty) > p.distractor_exclusion_dva
        assert math.hypot(x, y) > p.distractor_fixation_clearance_dva
        assert abs(x) + half_side <= SCREEN.px2deg(960) and abs(y) + half_side <= SCREEN.px2deg(540)
    assert len({pos for pos, _ in draws}) == len(draws)


def test_the_outside_target_is_the_mf_rotated_90_degrees_in_the_same_hemifield():
    task = TargetDimmingDetectionTask(params("task-monkey-outside.yaml"))
    _, _, ctx, _ = run_trial(task, condition(), script())
    mf = (ctx.record["mf_x_dva"], ctx.record["mf_y_dva"])
    t = (ctx.record["target_x_dva"], ctx.record["target_y_dva"])
    assert math.hypot(*t) == pytest.approx(math.hypot(*mf))
    assert mf[0] * t[0] + mf[1] * t[1] == pytest.approx(0.0, abs=1e-6)  # 90° apart
    assert math.copysign(1, t[0]) == math.copysign(1, mf[0])


def test_every_params_file_loads_and_builds_its_task():
    files = sorted((PROJECT / "configs").glob("task*.yaml"))
    assert len(files) == 3
    for path in files:
        TargetDimmingDetectionTask(load_params(path, TargetDimmingDetectionTaskParams))


def test_human_files_cannot_switch_stimulation_on():
    with pytest.raises(ValueError, match="monkey procedure"):
        params("task.yaml", stimulation={"enabled": True})


def test_monkey_files_pay_hits_and_correct_rejections_only():
    for name in ("task-monkey-inside.yaml", "task-monkey-outside.yaml"):
        p = load_params(PROJECT / "configs" / name, TargetDimmingDetectionTaskParams)
        assert set(p.reward.by_outcome) == {"HIT", "CORRECT_REJECTION"}
        assert p.stimulation.enabled


def test_a_target_off_the_screen_is_refused_before_the_trial():
    task = TargetDimmingDetectionTask(params(field={"movement_field_dva": [40.0, 0.0]}))
    with pytest.raises(Exception, match="does not fit"):
        run_trial(task, condition(), script())


def test_the_subject_is_told_what_to_do():
    assert TargetDimmingDetectionTask.default_params().is_file()
    text = (PROJECT / "instructions.md").read_text(encoding="utf-8")
    assert "SPACE" in text


def test_the_launch_estimate_counts_every_planned_trial_and_times_both_kinds():
    import numpy as np
    from alhazen.paradigms.base import Condition

    for name, per_block in (("task.yaml", 3), ("task-monkey-inside.yaml", 6)):
        p = load_params(PROJECT / "configs" / name, TargetDimmingDetectionTaskParams)
        task = TargetDimmingDetectionTask(p)
        schedule = task.duration_schedule(p, np.random.default_rng(0))
        assert schedule.n_trials == p.staircase.n_blocks * per_block
    catch = task.trial_timing(Condition({"trial_type": "catch"}), 60.0)
    blink = task.trial_timing(Condition({"trial_type": "blink"}), 60.0)
    assert catch.fixed_s == pytest.approx(0.2 + 2.1)
    assert blink.max_s == pytest.approx(2.0 + 0.2 + 1.3 + 0.8)
