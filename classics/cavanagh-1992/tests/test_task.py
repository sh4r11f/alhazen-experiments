"""The tracking trial (Experiment 1) on alhazen's fake clock with scripted inputs."""

from __future__ import annotations

import importlib.util

import numpy as np
import pytest
from alhazen import InputFrame
from alhazen.config.loader import load_params
from conftest import PROJECT, run_trial

from cavanagh1992.task import AttentiveTrackingTask, AttentiveTrackingTaskParams

FIXED = {"source": "fixed", "green_red_ratio": 1.05}


def params(**over):
    p = load_params(PROJECT / "configs" / "task.yaml", AttentiveTrackingTaskParams)
    data = p.model_dump()
    data.update({"equiluminance": FIXED, **over})
    return AttentiveTrackingTaskParams.model_validate(data)


@pytest.fixture
def task():
    return AttentiveTrackingTask(params())


# Frames before the response window opens at 60 Hz: fixation 30 + pre-cue 30 + cue 60 +
# tracking 90 + test 15 (240 ms -> 14.4 -> 14 frames, rounded) ~ 225.
LEAD = 240


def frames(n_wait, keys=(), tail=0):
    return [InputFrame()] * n_wait + [InputFrame(keys=tuple(keys))] + [InputFrame()] * tail


def times(collector):
    return {e.name: e.t for e in collector.events}


def test_yes_on_the_tracked_pair_is_correct(task):
    _, result, ctx, _ = run_trial(task, {"luminance_contrast": 0.1, "test_pointer": "tracked"},
                                  frames(LEAD, ["j"]))
    assert result.outcome.name == "CORRECT"
    assert ctx.record["response_key"] == "j" and ctx.record["test_offset_bars"] == 0


def test_yes_on_an_adjacent_pair_is_wrong_and_no_is_correct(task):
    cond = {"luminance_contrast": 0.1, "test_pointer": "adjacent"}
    _, wrong, ctx, _ = run_trial(task, cond, frames(LEAD, ["j"]))
    assert wrong.outcome.name == "WRONG"
    assert abs(ctx.record["test_offset_deg"]) == pytest.approx(45.0)
    _, right, _, _ = run_trial(task, cond, frames(LEAD, ["f"]))
    assert right.outcome.name == "CORRECT"


def test_no_key_before_the_deadline_serves_the_trial_again(task):
    _, result, _, _ = run_trial(task, {"luminance_contrast": 0.4, "test_pointer": "tracked"},
                                frames(LEAD + 300))
    assert result.outcome.name == "NO_RESPONSE" and not result.outcome.completed


def test_a_key_during_the_tracking_interval_is_not_a_response(task):
    inputs = [InputFrame()] * 100 + [InputFrame(keys=("j",))] + [InputFrame()] * (LEAD - 100) \
        + [InputFrame(keys=("f",))]
    _, result, ctx, _ = run_trial(task, {"luminance_contrast": 0.1, "test_pointer": "tracked"},
                                  inputs)
    assert ctx.record["response_key"] == "f" and result.outcome.name == "WRONG"


def test_the_phases_last_what_the_paper_says(task):
    collector, _, _, _ = run_trial(task, {"luminance_contrast": 0.1, "test_pointer": "tracked"},
                                   frames(LEAD, ["j"]))
    t = times(collector)
    assert t["POINTER_OFF"] - t["POINTER_ON"] == pytest.approx(1.0, abs=1 / 60)
    assert t["TEST_ON"] - t["POINTER_OFF"] == pytest.approx(1.5, abs=1 / 60)
    assert t["RESPONSE_CUE"] - t["TEST_ON"] == pytest.approx(0.24, abs=1 / 60)


def test_the_pointer_is_on_only_while_cued_and_tested(task):
    seen = []

    class Spy:
        def __init__(self, inner, scene):
            self.inner, self.scene = inner, scene

        def update(self, dt):
            self.inner.update(dt)

        def draw(self):
            self.inner.draw()
            seen.append(self.scene.pointer)

    orig = task.build_trial

    def wrapped(setup):
        plan = orig(setup)
        stim = plan.stimuli["display"]
        plan.stimuli["display"] = Spy(stim, stim.scene)
        return plan

    task.build_trial = wrapped
    run_trial(task, {"luminance_contrast": 0.1, "test_pointer": "adjacent"}, frames(LEAD, ["f"]))
    states = ["on" if s is not None and s.offset == 0 else "test" if s is not None else "off"
              for s in seen]
    runs = [states[0]] + [b for a, b in zip(states, states[1:], strict=False) if a != b]
    assert runs == ["off", "on", "off", "test", "off"]
    assert states.count("on") == 60 and states.count("test") == 14


def test_the_luminance_grating_turns_opposite_to_the_colour_grating(task):
    _, _, _, plan = run_trial(task, {"luminance_contrast": 0.2, "test_pointer": "tracked"},
                              frames(LEAD, ["j"]))
    color, lum = plan.stimuli["display"].scene.rings[0].components
    assert color.kind == "color" and lum.kind == "luminance"
    assert color.direction == -lum.direction and lum.contrast == pytest.approx(0.2)
    assert color.contrast == pytest.approx(0.40)


def test_eight_contrasts_from_5_to_40_percent_and_half_the_tests_on_the_tracked_pair(task):
    assert task.params.luminance_contrasts() == pytest.approx(
        [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40])
    tests = [c.params["test_pointer"] for c in task.conditions(np.random.default_rng(0))]
    assert len(tests) == 16 and tests.count("tracked") == 8


def test_a_luminance_session_tracks_the_luminance_component():
    t = AttentiveTrackingTask(params(target_grating="luminance"))
    _, _, ctx, _ = run_trial(t, {"luminance_contrast": 0.3, "test_pointer": "tracked"},
                             frames(LEAD, ["j"]))
    assert ctx.record["target_component"] == 1 and ctx.record["target_grating"] == "luminance"


def run_module():
    spec = importlib.util.spec_from_file_location("run_py", PROJECT / "run.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_every_params_file_loads_with_its_model_and_builds_its_task():
    run = run_module()
    files = {path.name for _, path in run.PARAMETERS.values()}
    on_disk = {p.name for p in (PROJECT / "configs").glob("*.yaml")
               if not p.name.startswith(("rig-", "photometry-"))}
    assert files == on_disk, "every params file is on the dashboard's menu, and only those"
    for task_name, path in run.PARAMETERS.values():
        cls = run.TASKS[task_name][0]
        p = load_params(path, cls.params_model)
        if hasattr(p, "equiluminance"):
            p = cls.params_model.model_validate({**p.model_dump(), "equiluminance": FIXED})
        assert cls(p).instructions().rstrip().endswith("Press SPACE to begin.")
