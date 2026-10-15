"""The method-of-adjustment tasks: the knob, the commit, the timeout, and what is set."""

from __future__ import annotations

import pytest
from alhazen import InputFrame
from alhazen.config.loader import load_params
from conftest import PROJECT, run_trial

from cavanagh1992.calibration import (
    EquiluminanceParams,
    EquiluminanceSpeedTask,
    FlickerParams,
    FlickerPhotometryTask,
)
from cavanagh1992.nulling import MotionNullParams, MotionNullTask, ThresholdParams, ThresholdTask
from cavanagh1992.speed_match import SpeedMatchParams, SpeedMatchTask

FIXED = {"source": "fixed", "green_red_ratio": 1.1}


def load(name, model, **over):
    p = load_params(PROJECT / "configs" / name, model)
    data = p.model_dump()
    if "equiluminance" in data:
        data["equiluminance"] = FIXED
    data.update(over)
    return model.model_validate(data)


def turns(n_wait, events):
    """Wait out the fixation, then the given (wheel, keys) frames."""
    return [InputFrame()] * n_wait + [InputFrame(wheel=w, keys=tuple(k)) for w, k in events]


def test_the_wheel_and_the_arrow_keys_move_k_and_space_commits_it():
    task = EquiluminanceSpeedTask(load("equiluminance-speed.yaml", EquiluminanceParams))
    events = [(2.0, ()), (0.0, ("up",)), (0.0, ("down", "down")), (0.0, ("space",))]
    collector, result, ctx, plan = run_trial(task, {"direction": 1}, turns(40, events))
    assert result.outcome.name == "SET"
    start = ctx.record["k_setting_start"]
    assert ctx.record["k_setting"] == pytest.approx(start * 1.02 ** (2 + 1 - 2))
    assert plan.stimuli["stimulus"].scene.color.k == pytest.approx(ctx.record["k_setting"])
    assert ctx.record["adjust_turns"] == 3
    start_event = next(e for e in collector.events if e.name == "ADJUST_START")
    assert start_event.payload["value"] == pytest.approx(start)


def test_k_stays_within_its_limits():
    task = EquiluminanceSpeedTask(load("equiluminance-speed.yaml", EquiluminanceParams))
    _, _, ctx, _ = run_trial(task, {"direction": -1}, turns(40, [(500.0, ()), (0, ("space",))]))
    assert ctx.record["k_setting"] == pytest.approx(4.0)


def test_an_uncommitted_setting_times_out_and_is_served_again():
    task = EquiluminanceSpeedTask(load("equiluminance-speed.yaml", EquiluminanceParams,
                                       adjust_timeout={"frames": 20}))
    _, result, ctx, _ = run_trial(task, {"direction": 1}, turns(40, [(0.0, ())] * 40))
    assert result.outcome.name == "TIMEOUT" and not result.outcome.completed
    assert "k_setting" in ctx.record


def test_flicker_photometry_flickers_a_uniform_field_locked_to_whole_frames():
    task = FlickerPhotometryTask(load("flicker-photometry.yaml", FlickerParams))
    _, result, ctx, plan = run_trial(task, {}, turns(40, [(0.0, ("space",))]))
    comp = plan.stimuli["stimulus"].scene.rings[0].components[0]
    assert comp.cycles == 0 and ctx.record["flicker_hz"] == pytest.approx(15.0)
    assert result.outcome.name == "SET"


def test_the_motion_null_turns_the_two_gratings_opposite_and_records_the_contrast():
    task = MotionNullTask(load("motion-null.yaml", MotionNullParams))
    _, _, ctx, plan = run_trial(task, {"start": "above", "direction": -1},
                                turns(40, [(-10.0, ()), (0.0, ("space",))]))
    color, lum = plan.stimuli["stimulus"].scene.rings[0].components
    assert color.direction == -1 and lum.direction == 1
    assert ctx.record["null_contrast"] == pytest.approx(0.30 / 1.03**10)
    assert plan.stimuli["stimulus"].scene.color.k == pytest.approx(1.1)


def test_each_threshold_is_four_settings_twice_from_above_and_twice_from_below():
    for crit, cells in (("presence", 3), ("direction", 2)):
        task = ThresholdTask(load(f"thresholds-{crit}.yaml", ThresholdParams))
        conds = [c.params for c in task.conditions(None)]
        assert len(conds) == 4 * cells
        first = [c["start"] for c in conds[:4]]
        assert first == ["above", "below", "above", "below"]
        assert conds[0]["grating"] == "luminance" and conds[0]["mask"] == "none"


def test_a_masked_threshold_trial_superimposes_the_40_percent_colour_grating():
    task = ThresholdTask(load("thresholds-presence.yaml", ThresholdParams))
    cond = {"grating": "luminance", "mask": "color", "start": "below", "setting": 2}
    _, _, ctx, plan = run_trial(task, cond, turns(40, [(5.0, ()), (0.0, ("space",))]))
    test, mask = plan.stimuli["stimulus"].scene.rings[0].components
    assert mask.kind == "color" and mask.contrast == pytest.approx(0.40)
    assert test.direction == -mask.direction
    assert ctx.record["threshold"] == pytest.approx(0.001 * 1.05**5)


def test_speed_match_sets_the_inner_rate_against_a_0_5_hz_colour_ring():
    task = SpeedMatchTask(load("speed-global.yaml", SpeedMatchParams))
    _, result, ctx, plan = run_trial(task, {"luminance_contrast": -0.1},
                                     turns(40, [(4.0, ()), (0.0, ("space",))]))
    outer, inner = plan.stimuli["stimulus"].scene.rings
    color, lum = outer.components
    assert color.rate_hz == pytest.approx(0.5) and lum.contrast == pytest.approx(-0.1)
    assert inner.components[0].contrast == pytest.approx(0.15)
    assert inner.components[0].direction == -color.direction
    assert ctx.record["matched_rate_hz"] == pytest.approx(
        ctx.record["matched_rate_hz_start"] * 1.03**4)
    assert result.outcome.name == "SET" and ctx.record["k"] == 1.0
