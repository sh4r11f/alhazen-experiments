"""Trial logic on alhazen's fake clock with scripted inputs: no display, no devices."""

from __future__ import annotations

import types

import pytest
from alhazen import InputFrame
from alhazen.config.loader import load_params
from alhazen.errors import ConfigError
from conftest import CONFIGS, PROJECT, run_trial

from anstiscavanagh1983.adjust import (
    FlickerAdjustParams,
    MinFlickerAdjustTask,
    MinMotionAdjustTask,
    MotionAdjustParams,
)
from anstiscavanagh1983.constant import ConstantParams, MinMotionConstantTask


def constant_task(**kw):
    p = load_params(CONFIGS / "task.yaml", ConstantParams)
    data = {**p.model_dump(), "fixation_duration": {"frames": 3},
            "response_timeout": {"frames": 30}, **kw}
    data["photometry_file"] = str(CONFIGS / "photometry-booth.yaml")
    return MinMotionConstantTask(ConstantParams.model_validate(data))


def frames(n, keys=()):
    return [InputFrame(gaze=None)] * n + [InputFrame(gaze=None, keys=tuple(keys))]


@pytest.mark.parametrize("key,outcome,report", [
    ("left", "MOTION_LEFT", "reference_lighter"), ("right", "MOTION_RIGHT", "test_lighter"),
    ("down", "NO_MOTION", "neither")])
def test_each_key_is_its_report(key, outcome, report):
    task = constant_task()
    _, result, ctx, _ = run_trial(task, {"test_cd_m2": 10.0, "step": 1}, frames(10, [key]))
    assert result.outcome.name == outcome
    scored = task.score(dict(ctx.record))
    assert scored["report"] == report


def test_a_leftward_step_flips_what_left_means():
    task = constant_task()
    _, _, ctx, _ = run_trial(task, {"test_cd_m2": 10.0, "step": -1}, frames(10, ["left"]))
    assert task.score(dict(ctx.record))["report"] == "test_lighter"


def test_no_key_times_out_and_is_served_again():
    _, result, _, _ = run_trial(constant_task(), {"test_cd_m2": 10.0, "step": 1}, frames(60))
    assert result.outcome.name == "NO_RESPONSE" and not result.outcome.completed


def test_the_cycle_is_frame_locked_t1_t2_t3_t4_three_frames_each():
    cond = {"test_cd_m2": 10.0, "step": 1}
    _, _, ctx, plan = run_trial(constant_task(), cond, frames(16, ["down"]))
    shown = plan.stimuli["stimulus"].shown
    assert shown[:13] == [0, 0, 0, 1, 1, 1, 2, 2, 2, 3, 3, 3, 0]
    assert ctx.record["frames_per_stroke"] == 3 and ctx.record["cycle_hz_effective"] == 5.0


def test_the_record_says_what_the_luminances_are():
    _, _, ctx, _ = run_trial(constant_task(), {"test_cd_m2": 10.0, "step": 1}, frames(5, ["down"]))
    r = ctx.record
    assert r["photometry_measured"] is False and "UNMEASURED" in r["luminance_basis"]
    assert r["reference_cd_m2"] == 13.4 and r["spatial_freq_effective_cpd"] == 2.5


def test_a_real_session_with_unmeasured_photometry_is_refused_unless_labelled_a_demo():
    task_cls = MinMotionConstantTask
    p = load_params(CONFIGS / "task.yaml", ConstantParams)
    p = ConstantParams.model_validate(
        {**p.model_dump(), "photometry_file": str(CONFIGS / "photometry-booth.yaml")})
    with pytest.raises(ConfigError):
        task_cls.params_hook(p, types.SimpleNamespace(mode="run"))
    assert task_cls.params_hook(p, types.SimpleNamespace(mode="simulate")) is p
    demo = ConstantParams.model_validate({**p.model_dump(),
                                          "display_calibration": "uncalibrated-demo"})
    assert task_cls.params_hook(demo, types.SimpleNamespace(mode="run")) is demo


def test_levels_the_display_cannot_show_are_refused_at_load():
    with pytest.raises(ValueError):
        constant_task(test_levels_cd_m2=[10.0, 80.0])


def adjust_task(cls, model, name, **kw):
    p = load_params(CONFIGS / name, model)
    data = {**p.model_dump(), "fixation_duration": {"frames": 3},
            "adjust_timeout": {"frames": 100}, **kw}
    data["photometry_file"] = str(CONFIGS / "photometry-booth.yaml")
    return cls(model.model_validate(data))


def test_the_knob_changes_the_drawn_test_luminance_and_space_commits_it():
    task = adjust_task(MinMotionAdjustTask, MotionAdjustParams, "adjust-spatial.yaml")
    cond = {"test_colour": "red", "spatial_freq_cpd": 2.5, "rate_hz": 15.0, "step": 1}
    inputs = frames(5, ["up"]) + frames(1, ["up"]) + frames(2, ["space"])
    _, result, ctx, plan = run_trial(task, cond, inputs)
    assert result.outcome.name == "SET"
    start, end = ctx.record["test_cd_m2_start"], ctx.record["test_cd_m2"]
    assert end == pytest.approx(start * 1.01**2)
    assert plan.stimuli["stimulus"].spec.test_cd_m2 == pytest.approx(end)
    assert ctx.record["frames_per_stroke"] == 1  # 15 Hz four-stroke at 60 Hz


def test_flicker_tasks_build_uniform_and_counterphase_trials():
    uni = adjust_task(MinFlickerAdjustTask, FlickerAdjustParams, "flicker-uniform.yaml")
    assert uni.layout == "uniform"
    _, res, ctx, _ = run_trial(uni, {"test_colour": "blue", "spatial_freq_cpd": 0.0,
                                     "rate_hz": 15.0, "step": 1}, frames(5, ["space"]))
    assert res.outcome.name == "SET" and ctx.record["frames_per_stroke"] == 2
    cp = adjust_task(MinFlickerAdjustTask, FlickerAdjustParams, "flicker-grating.yaml")
    assert cp.layout == "counterphase"


def test_every_params_file_loads_and_builds_its_task():
    import importlib.util

    spec = importlib.util.spec_from_file_location("run_py", PROJECT / "run.py")
    run = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(run)
    for label, (task_name, path) in run.PARAMETERS.items():
        cls = run.TASKS[task_name][0]
        p = load_params(path, cls.params_model)
        cls(p)
        assert p.subject_kind == "human", label


def test_the_subject_is_told_what_to_do():
    text = (PROJECT / "instructions.md").read_text(encoding="utf-8")
    for section in ("min-motion-constant", "min-motion-adjust", "min-flicker-adjust"):
        assert f"## {section}" in text
    assert "SPACE" in text and "DOWN" in text
