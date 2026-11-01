"""Trial logic of both tasks on alhazen's fake clock with scripted keys."""

from __future__ import annotations

import pytest
from alhazen import Duration
from alhazen.config.loader import load_params
from alhazen.display.screen import Screen
from alhazen.errors import ConfigError
from harness import frames, run_trial

from campbell_robson1968.adjust import CsfAdjustmentParams, CsfAdjustmentTask
from campbell_robson1968.common import PROJECT
from campbell_robson1968.task import Csf2ifcParams, Csf2ifcTask

SHORT = dict(
    fixation_duration=Duration(frames=3),
    interval_duration=Duration(frames=6),
    isi=Duration(frames=4),
    response_timeout=Duration(frames=10),
    feedback_duration=Duration(frames=2),
)
TRIAL_FRAMES = 3 + 6 + 4 + 6


@pytest.fixture
def task():
    p = load_params(PROJECT / "configs" / "task.yaml", Csf2ifcParams)
    return Csf2ifcTask(p.model_copy(update=SHORT))


def _signal(task, seed):
    *_, ctx, _ = run_trial(task, {"cell": "sine-4", "log_contrast": -1.5}, frames(60), seed=seed)
    return ctx.record["signal_interval"]


def test_the_key_for_the_signal_interval_scores_correct(task):
    for seed in range(6):
        cond = {"cell": "sine-4", "log_contrast": -1.5}
        _, _, ctx0, _ = run_trial(task, cond, frames(60), seed=seed)
        right = ctx0.record["correct_key"]
        wrong = "j" if right == "f" else "f"
        assert (
            run_trial(task, cond, frames(TRIAL_FRAMES + 2, [right]), seed=seed)[1].outcome.name
            == "CORRECT"
        )
        assert (
            run_trial(task, cond, frames(TRIAL_FRAMES + 2, [wrong]), seed=seed)[1].outcome.name
            == "WRONG"
        )


def test_both_intervals_are_used(task):
    assert {_signal(task, s) for s in range(20)} == {1, 2}


def test_no_key_times_out(task):
    _, result, _, _ = run_trial(task, {"cell": "sine-1", "log_contrast": -2.0}, frames(80))
    assert result.outcome.name == "NO_RESPONSE"


def test_a_key_during_the_intervals_is_not_a_response(task):
    seq = frames(8, ["f"])[:-1] + frames(0, ["f"]) + frames(40)
    _, result, _, _ = run_trial(task, {"cell": "sine-1", "log_contrast": -2.0}, seq)
    assert result.outcome.name == "NO_RESPONSE"


def test_grating_is_drawn_only_in_its_interval_for_exactly_its_frames(task):
    for seed in range(4):
        _, result, ctx, plan = run_trial(
            task,
            {"cell": "sine-2", "log_contrast": -1.0},
            frames(TRIAL_FRAMES + 2, ["f"]),
            seed=seed,
        )
        assert plan.stimuli["grating"].draw_count == 6
        assert ctx.record["interval_frames"] == 6 and ctx.record["isi_frames"] == 4
        # each phase's onset is stamped on its own flip, in order
        t = [
            ctx.record[k]
            for k in ("t_fix_on", "t_interval1_on", "t_isi_on", "t_interval2_on", "t_response_cue")
        ]
        assert t == sorted(t)
        assert t[2] - t[1] == pytest.approx(6 / 60) and t[3] - t[2] == pytest.approx(4 / 60)
        assert t[4] - t[3] == pytest.approx(6 / 60)


def test_record_logs_requested_and_realised_values(task):
    _, _, ctx, _ = run_trial(task, {"cell": "sine-8", "log_contrast": -2.0}, frames(30))
    r = ctx.record
    assert r["contrast_requested"] == pytest.approx(0.01)
    assert r["contrast_realised"] == pytest.approx(0.01, rel=0.15)
    assert (
        r["sf_cpd"] == 8.0 and r["waveform"] == "sine" and r["px_per_cycle"] == pytest.approx(4.5)
    )
    assert r["mean_luminance"] == pytest.approx(128 / 255)
    for k in ("phase_deg", "noise_seed", "dither", "display_bits", "field_px", "n_codes"):
        assert k in r


def test_rig_too_coarse_for_a_frequency_is_refused_before_drawing(task):
    coarse = Screen(width_px=1920, height_px=1080, px_per_deg=20.0)
    with pytest.raises(ConfigError, match="sine-8"):
        run_trial(task, {"cell": "sine-1", "log_contrast": -2.0}, frames(5), screen=coarse)


def test_every_params_file_loads_and_builds():
    for path, model, cls in [
        ("task.yaml", Csf2ifcParams, Csf2ifcTask),
        ("task-far.yaml", Csf2ifcParams, Csf2ifcTask),
        ("sine-square.yaml", Csf2ifcParams, Csf2ifcTask),
        ("adjustment.yaml", CsfAdjustmentParams, CsfAdjustmentTask),
    ]:
        cls(load_params(PROJECT / "configs" / path, model))


def test_sine_square_set_interleaves_both_waveforms():
    p = load_params(PROJECT / "configs" / "sine-square.yaml", Csf2ifcParams)
    names = {c.params["cell"] for c in Csf2ifcTask(p).conditions(None)}
    assert names == {f"{w}-{f}" for w in ("sine", "square") for f in ("0.5", "1", "2", "3")}


@pytest.fixture
def adjust():
    p = load_params(PROJECT / "configs" / "adjustment.yaml", CsfAdjustmentParams)
    return CsfAdjustmentTask(
        p.model_copy(
            update=dict(
                fixation_duration=Duration(frames=2),
                flicker_period=Duration(ms=200),
                flicker_on=Duration(ms=100),
                adjust_timeout=Duration(frames=200),
            )
        )
    )


def test_adjustment_knob_and_commit(adjust):
    seq = frames(5) + frames(0, ["down"]) + frames(0, ["down"]) + frames(2, ["space"])
    _, result, ctx, _ = run_trial(adjust, {"cell": "sine-2"}, seq)
    r = ctx.record
    assert result.outcome.name == "SET"
    assert r["setting"] == pytest.approx(r["setting_start"] / 10**0.1)
    assert r["contrast_set"] == pytest.approx(r["setting"])
    assert r["contrast_realised"] == pytest.approx(r["setting"], rel=0.2)
    assert r["adjust_turns"] == 2


def test_adjustment_flicker_is_on_half_of_each_cycle_in_frames(adjust):
    seq = frames(2 + 36, ["space"])
    _, result, ctx, plan = run_trial(adjust, {"cell": "sine-1"}, seq)
    flick = plan.stimuli["flicker"]
    assert ctx.record["flicker_on_frames"] == 6 and ctx.record["flicker_period_frames"] == 12
    assert flick.frame == ctx.record["frames_shown"]
    assert ctx.record["frames_grating_on"] == sum(1 for i in range(flick.frame) if i % 12 < 6)
    assert 0 < ctx.record["frames_grating_on"] < flick.frame


def test_adjustment_times_out_and_records_the_setting(adjust):
    _, result, ctx, _ = run_trial(adjust, {"cell": "sine-1"}, frames(260))
    assert result.outcome.name == "TIMEOUT" and "setting" in ctx.record


def test_the_subject_is_told_what_to_do():
    assert "SPACE" in (PROJECT / "instructions.md").read_text(encoding="utf-8")
    assert "SPACE" in (PROJECT / "instructions-adjustment.md").read_text(encoding="utf-8")
