"""Trial logic of both tasks on alhazen's fake clock with scripted gaze and keys: every
outcome branch, the Gabor's removal at saccade onset, and where the landing is measured
from. No display, no devices."""

from __future__ import annotations

import math

import pytest
from alhazen import Duration
from alhazen.config.loader import load_params
from conftest import FRAME_S, build, gaze_track, run_plan

from lisi_cavanagh2015.geometry import Trajectory
from lisi_cavanagh2015.task import (
    PROJECT,
    DoubleDriftPerceptionTask,
    DoubleDriftSaccadesTask,
    PerceptionParams,
    SaccadeParams,
)

FIX = (0.0, 0.0)
AWAY = (-6.0, 4.0)


def frames(seconds):
    return int(round(seconds / FRAME_S))


@pytest.fixture
def sacc_task():
    p = load_params(PROJECT / "configs" / "task.yaml", SaccadeParams)
    return DoubleDriftSaccadesTask(p.model_copy(update={"foreperiod_jitter": Duration(ms=0)}))


@pytest.fixture
def perc_task():
    p = load_params(PROJECT / "configs" / "task-perception.yaml", PerceptionParams)
    return DoubleDriftPerceptionTask(p.model_copy(update={
        "foreperiod_jitter": Duration(ms=0), "response_timeout": Duration(ms=2000)}))


SACC_COND = {"tilt_side": "right", "internal_motion": True, "start_direction": "up"}


def saccade_script(task, plan, *, latency_s=0.25, landing=(9.5, 0.4), blink_at=None,
                   break_at=None, never_leave=False, total_s=8.0):
    """Gaze for one saccade trial: on fixation, then (latency after the dot goes off) a
    jump to ``landing`` that stays there. Frame counts from the trial's own plan."""
    p = task.params
    t_go = (p.acquire_hold.seconds(60) + 2 * FRAME_S + p.foreperiod.seconds(60)
            + plan.record["fix_off_s"])
    pts = []
    for i in range(frames(total_s)):
        t = i * FRAME_S
        if blink_at is not None and blink_at <= t < blink_at + 0.1:
            pts.append(None)
        elif break_at is not None and t >= break_at:
            pts.append(AWAY)
        elif never_leave or t < t_go + latency_s:
            pts.append(FIX)
        else:
            pts.append(landing)
    return gaze_track(pts)


def test_a_saccade_after_the_dot_goes_off_is_measured(sacc_task):
    plan, clock, display = build(sacc_task, SACC_COND)
    events, result, ctx = run_plan(sacc_task, plan, clock, display,
                                   saccade_script(sacc_task, plan), SACC_COND)
    assert result.outcome.name == "SACCADE"
    names = events.names()
    for e in ("FIX_ON", "FIX_ACQUIRED", "GABOR_ON", "FIX_OFF", "RESPONSE_ONSET", "LANDED"):
        assert e in names
    rec = ctx.record
    assert 200 <= rec["saccade_latency_ms"] <= 320
    assert rec["endpoint_measured"] and rec["endpoint_settled"]
    assert rec["endpoint_x_dva"] == pytest.approx(9.5)
    # The landing is judged from where the Gabor was on the saccade-onset flip.
    t = rec["t_response_onset"] - rec["t_gabor_on"]
    traj = plan.stimuli["gabor"].trajectory
    x, y = traj.position(t)
    assert rec["endpoint_reference_x_dva"] == pytest.approx(x)
    assert rec["endpoint_reference_y_dva"] == pytest.approx(y)
    # The dot goes off at the scheduled time after Gabor onset (to the frame).
    assert rec["t_fix_off"] - rec["t_gabor_on"] == pytest.approx(rec["fix_off_s"], abs=FRAME_S)


def test_the_gabor_moves_with_the_dot_up_and_is_removed_at_saccade_onset(sacc_task):
    plan, clock, display = build(sacc_task, SACC_COND)
    gabor = plan.stimuli["gabor"]
    _, result, ctx = run_plan(sacc_task, plan, clock, display,
                              saccade_script(sacc_task, plan), SACC_COND)
    assert result.outcome.name == "SACCADE"
    # Drawn every frame from GABOR_ON up to and including the departure frame, never after.
    shown = (ctx.record["t_response_onset"] - ctx.record["t_gabor_on"]) / FRAME_S + 1
    assert gabor.draw_count == pytest.approx(shown, abs=1)
    assert gabor.time_s == pytest.approx(ctx.record["t_response_onset"] - ctx.record["t_gabor_on"],
                                         abs=1e-9)
    # The fixation dot is not drawn once it has gone off.
    fix_draws = plan.stimuli["fixation"].draw_count
    on_screen_before_off = (ctx.record["t_fix_off"] - ctx.record["t_fix_on"]) / FRAME_S
    assert fix_draws == pytest.approx(on_screen_before_off, abs=2)


def test_no_fixation_times_out(sacc_task):
    plan, clock, display = build(sacc_task, SACC_COND)
    _, result, _ = run_plan(sacc_task, plan, clock, display, gaze_track([AWAY] * 400), SACC_COND)
    assert result.outcome.name == "NO_FIXATION"
    assert not result.outcome.completed


def test_a_look_away_while_the_gabor_moves_is_a_break(sacc_task):
    plan, clock, display = build(sacc_task, SACC_COND)
    script = saccade_script(sacc_task, plan, break_at=0.1 + 0.5 + 0.3)
    _, result, ctx = run_plan(sacc_task, plan, clock, display, script, SACC_COND)
    assert result.outcome.name == "FIX_BREAK"
    assert not result.outcome.completed
    assert "t_fix_off" not in ctx.record


def test_a_blink_before_the_dot_goes_off_is_a_break(sacc_task):
    plan, clock, display = build(sacc_task, SACC_COND)
    script = saccade_script(sacc_task, plan, blink_at=0.4)
    _, result, _ = run_plan(sacc_task, plan, clock, display, script, SACC_COND)
    assert result.outcome.name == "FIX_BREAK"


def test_no_saccade_before_the_deadline(sacc_task):
    plan, clock, display = build(sacc_task, SACC_COND)
    script = saccade_script(sacc_task, plan, never_leave=True)
    _, result, ctx = run_plan(sacc_task, plan, clock, display, script, SACC_COND)
    assert result.outcome.name == "NO_SACCADE"
    assert "t_fix_off" in ctx.record and "t_response_onset" not in ctx.record


def test_score_adds_the_gabor_at_onset_and_the_saccade_vector(sacc_task):
    plan, clock, display = build(sacc_task, SACC_COND)
    _, result, ctx = run_plan(sacc_task, plan, clock, display,
                              saccade_script(sacc_task, plan), SACC_COND)
    row = sacc_task.score(dict(ctx.record))
    assert row["gabor_x_at_onset_dva"] == pytest.approx(row["endpoint_reference_x_dva"])
    assert row["saccade_dx_dva"] == pytest.approx(row["endpoint_x_dva"] - row["fixation_x_dva"])
    assert row["drift_sign_at_onset"] in (-1, 1)
    assert abs(row["gabor_along_at_onset_dva"]) <= 1.5 + 1e-9


def test_the_control_trial_has_no_internal_motion(sacc_task):
    cond = {**SACC_COND, "internal_motion": False}
    plan, *_ = build(sacc_task, cond)
    traj: Trajectory = plan.stimuli["gabor"].trajectory
    assert not traj.internal_motion
    assert traj.drift_phase_cycles(1.3) == 0.0
    assert traj.angle_deg == sacc_task.params.path_angle_right_deg


def test_the_saccade_paths_are_the_perceived_vertical_orientations(sacc_task):
    for side, angle in (("right", 49.0), ("left", -52.0)):
        plan, *_ = build(sacc_task, {**SACC_COND, "tilt_side": side})
        assert plan.record["path_angle_deg"] == angle
        assert plan.stimuli["gabor"].trajectory.side == side


# -- the perceptual task ---------------------------------------------------------------------
PERC_COND = {"staircase": "right-1", "tilt_side": "right", "path_angle_deg": 40.0}


def perception_script(task, *, key=None, key_at_s=1.5, break_at=None, n_s=4.0):
    p = task.params
    pts, keys_at = [], {}
    t_gabor = p.acquire_hold.seconds(60) + 2 * FRAME_S + p.foreperiod.seconds(60)
    for i in range(frames(n_s)):
        t = i * FRAME_S
        pts.append(AWAY if break_at is not None and t >= break_at else FIX)
    if key is not None:
        keys_at[frames(t_gabor + key_at_s)] = [key]
    keys_at[3] = ["right"]  # pressed before the Gabor: never a response
    return gaze_track(pts, keys_at)


@pytest.mark.parametrize("key, outcome", [("right", "REPORTED_RIGHT"), ("left", "REPORTED_LEFT")])
def test_an_arrow_key_is_the_report(perc_task, key, outcome):
    plan, clock, display = build(perc_task, PERC_COND)
    events, result, ctx = run_plan(perc_task, plan, clock, display,
                                   perception_script(perc_task, key=key), PERC_COND)
    assert result.outcome.name == outcome and result.outcome.completed
    assert ctx.record["response_key"] == key
    assert ctx.record["rt_ms"] == pytest.approx(1500, abs=40)
    assert {"GABOR_ON", "RESPONSE"} <= set(events.names())
    assert perc_task.score(dict(ctx.record))["reported_right"] is (key == "right")


def test_no_key_before_the_deadline(perc_task):
    plan, clock, display = build(perc_task, PERC_COND)
    _, result, _ = run_plan(perc_task, plan, clock, display, perception_script(perc_task),
                            PERC_COND)
    assert result.outcome.name == "NO_RESPONSE" and not result.outcome.completed


def test_a_look_away_before_the_report_aborts_the_trial(perc_task):
    plan, clock, display = build(perc_task, PERC_COND)
    script = perception_script(perc_task, key="right", key_at_s=2.0, break_at=1.4)
    _, result, ctx = run_plan(perc_task, plan, clock, display, script, PERC_COND)
    assert result.outcome.name == "FIX_BREAK"
    assert "response_key" not in ctx.record


def test_a_blink_before_the_report_aborts_the_trial(perc_task):
    plan, clock, display = build(perc_task, PERC_COND)
    script = perception_script(perc_task, key="right", key_at_s=2.0)
    i = frames(1.6)
    script[i] = type(script[i])(gaze=None)
    _, result, _ = run_plan(perc_task, plan, clock, display, script, PERC_COND)
    assert result.outcome.name == "FIX_BREAK"


def test_no_fixation_in_the_perceptual_task(perc_task):
    plan, clock, display = build(perc_task, PERC_COND)
    _, result, _ = run_plan(perc_task, plan, clock, display, gaze_track([AWAY] * 400), PERC_COND)
    assert result.outcome.name == "NO_FIXATION"


def test_the_perceptual_gabor_is_the_condition_s_orientation_and_pairing(perc_task):
    plan, *_ = build(perc_task, {**PERC_COND, "tilt_side": "left", "path_angle_deg": -30.0})
    traj: Trajectory = plan.stimuli["gabor"].trajectory
    assert traj.angle_deg == -30.0 and traj.side == "left" and traj.internal_motion
    assert math.isclose(traj.along(0.0), 0.0, abs_tol=1e-12)  # starts mid-path


def test_every_params_file_loads():
    load_params(PROJECT / "configs" / "task.yaml", SaccadeParams)
    load_params(PROJECT / "configs" / "task-perception.yaml", PerceptionParams)


def test_the_subject_is_told_what_to_do():
    assert DoubleDriftSaccadesTask.default_params().is_file()
    assert DoubleDriftPerceptionTask.default_params().is_file()
    for name in ("instructions.md", "instructions-perception.md"):
        assert "SPACE" in (PROJECT / name).read_text(encoding="utf-8")
