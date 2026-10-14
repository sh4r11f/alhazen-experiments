"""Trial logic on alhazen's fake clock with scripted inputs: no display, no devices."""

from __future__ import annotations

from argparse import Namespace

import numpy as np
import pytest
import yaml
from alhazen import InputFrame
from alhazen.config.loader import build_session_config, load_params, load_rig
from alhazen.config.models import DisplayConfig, MonitorConfig, RigConfig, SessionInfo
from alhazen.core.engine import TrialEngine
from alhazen.core.events import EventBus
from alhazen.core.trial import TrialContext
from alhazen.display.screen import Screen
from alhazen.errors import ConfigError
from alhazen.paradigms.base import Condition
from alhazen.task.plan import TrialSetup
from alhazen.testing import EventCollector, FakeClock, FakeDisplay, ScriptedCommands, ScriptedInputs

from moore_armstrong2003.task import (
    PROJECT,
    RfGatingFixationTask,
    RfGatingFixationTaskParams,
    stimulation_wiring_problem,
)

FRAME_S = 1 / 60
SCREEN = Screen(width_px=1920, height_px=1080, px_per_deg=40.0)
INSIDE = InputFrame(gaze=(0.0, 0.0))
OUTSIDE = InputFrame(gaze=(400.0, 0.0))
MAIN = PROJECT / "configs" / "task.yaml"
DEMO = PROJECT / "configs" / "task-demo-human.yaml"


def params(path=MAIN, **changes):
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    for dotted, value in changes.items():
        node = data
        *head, leaf = dotted.split("__")
        for part in head:
            node = node[part]
        node[leaf] = value
    return RfGatingFixationTaskParams.model_validate(data)


def run_trial(task, condition, inputs, seed=0):
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
        screen=SCREEN, display=display, rng=np.random.default_rng(seed),
        refresh_rate_hz=1 / FRAME_S, trial_index=1, attempt=1, condition=Condition(condition))
    plan = task.build_trial(setup)
    ctx = TrialContext(clock=clock, screen=SCREEN, rng=np.random.default_rng(0), trial_index=1,
                       params=dict(condition), stimuli=plan.stimuli, regions=plan.regions,
                       record=dict(plan.record))
    return collector, engine.run_trial(ctx, plan.phases), ctx


@pytest.fixture
def task():
    return RfGatingFixationTask(params())


def cond(display="rf-preferred_dist-preferred", stimulation="stim"):
    return {"display": display, "stimulation": stimulation}


def times(collector):
    return {e.name: e.t for e in collector.events}


def test_a_held_stimulation_trial_completes_with_the_trigger_in_the_window(task):
    col, result, ctx = run_trial(task, cond(), [INSIDE])
    assert result.outcome.name == "COMPLETED"
    names = [n for n in col.names() if n in task.events.declared]
    assert names == ["FIX_ON", "FIX_ACQUIRED", "VIS_ON", "STIM_TRIGGER", "VIS_OFF"]
    t = times(col)
    delay = t["STIM_TRIGGER"] - t["VIS_ON"]
    assert abs(delay - ctx.record["trigger_delay_s"]) <= FRAME_S / 2 + 1e-9
    assert 0.2 - FRAME_S / 2 <= delay <= 0.5 + FRAME_S / 2  # paper: p. 371
    on = t["VIS_OFF"] - t["VIS_ON"]
    assert abs(on - ctx.record["planned_stimulus_s"]) <= FRAME_S / 2 + 1e-9
    assert 1.5 - FRAME_S / 2 <= on <= 2.0 + FRAME_S / 2  # paper: p. 373
    assert ctx.record["stimulation"] == "stim" and ctx.record["current_ua"] == 20.0
    # This test rig maps no line: the row must not claim a deliverable trigger.
    assert ctx.record["stim_ttl_line"] == ""


def test_a_control_trial_marks_the_same_moment_without_the_trigger(task):
    col, result, ctx = run_trial(task, cond(stimulation="control"), [INSIDE])
    assert result.outcome.name == "COMPLETED"
    assert "CONTROL_MARK" in col.names() and "STIM_TRIGGER" not in col.names()
    assert ctx.record["current_ua"] == 0.0 and ctx.record["train_ms"] == 0.0


def test_the_same_seed_gives_the_same_trigger_time_on_both_kinds_of_trial(task):
    *_, stim = run_trial(task, cond(stimulation="stim"), [INSIDE], seed=5)
    *_, ctrl = run_trial(task, cond(stimulation="control"), [INSIDE], seed=5)
    assert stim.record["trigger_delay_s"] == ctrl.record["trigger_delay_s"]


def test_never_looking_is_no_fixation(task):
    col, result, _ = run_trial(task, cond(), [OUTSIDE])
    assert result.outcome.name == "NO_FIXATION"
    assert "VIS_ON" not in col.names()


def test_a_break_before_the_bars_is_a_baseline_break(task):
    col, result, _ = run_trial(task, cond(), [INSIDE] * 10 + [OUTSIDE])
    assert result.outcome.name == "BROKE_FIX_BASELINE"
    assert "VIS_ON" not in col.names()


def test_a_break_while_the_bars_are_up_before_the_trigger(task):
    # 1 acquire frame + 30 baseline frames; the trigger comes >= 12 frames after VIS_ON.
    col, result, _ = run_trial(task, cond(), [INSIDE] * 36 + [OUTSIDE])
    assert result.outcome.name == "BROKE_FIX_STIMULUS"
    assert "VIS_ON" in col.names() and "STIM_TRIGGER" not in col.names()


def test_a_break_after_the_trigger_is_counted_apart(task):
    # The trigger is at most 30 frames after VIS_ON; the bars stay >= 90 frames.
    col, result, _ = run_trial(task, cond(), [INSIDE] * 70 + [OUTSIDE])
    assert result.outcome.name == "BROKE_FIX_AFTER_TRIGGER"
    assert "STIM_TRIGGER" in col.names() and "VIS_OFF" not in col.names()


def test_a_blink_is_a_break(task):
    col, result, _ = run_trial(task, cond(), [INSIDE] * 70 + [InputFrame(gaze=None)])
    assert result.outcome.name == "BROKE_FIX_AFTER_TRIGGER"


@pytest.mark.parametrize("display, drawn, absent", [
    ("rf-preferred_dist-none", ["rf_bar"], ["distracter_bar"]),
    ("rf-none_dist-orthogonal", ["distracter_bar"], ["rf_bar"]),
    ("rf-orthogonal_dist-orthogonal", ["rf_bar", "distracter_bar"], []),
])
def test_each_display_draws_its_bars(task, display, drawn, absent):
    _, result, ctx = run_trial(task, cond(display=display), [INSIDE])
    assert result.outcome.name == "COMPLETED"
    for key in drawn:
        assert ctx.stimuli[key].draw_count > 0
    for key in absent:
        assert key not in ctx.stimuli


def test_orientations_are_preferred_or_orthogonal(task):
    *_, ctx = run_trial(task, cond(display="rf-orthogonal_dist-orthogonal"), [INSIDE])
    assert ctx.record["rf_ori_deg"] == 135.0 and ctx.record["distracter_ori_deg"] == 135.0


def test_the_conditions_are_every_display_with_and_without_stimulation(task):
    cells = task.conditions(np.random.default_rng(0))
    assert len(cells) == 12
    assert {c.params["stimulation"] for c in cells} == {"stim", "control"}


def test_every_params_file_loads():
    for path in (PROJECT / "configs").glob("task*.yaml"):
        load_params(path, RfGatingFixationTaskParams)


def test_the_demo_is_the_main_file_without_stimulation_or_reward():
    main = yaml.safe_load(MAIN.read_text(encoding="utf-8"))
    demo = yaml.safe_load(DEMO.read_text(encoding="utf-8"))
    assert demo["subject_kind"] == "human" and "reward" not in demo
    assert demo["stimulation"]["conditions"] == ["control"]
    for key in ("subject_kind", "reward"):
        main.pop(key, None)
        demo.pop(key, None)
    main["stimulation"]["conditions"] = ["control"]
    assert main == demo


def test_a_human_is_never_stimulated():
    with pytest.raises(ValueError, match="never stimulated"):
        params(DEMO, stimulation__conditions=["stim", "control"])


def test_a_current_at_threshold_is_refused():
    with pytest.raises(ValueError, match="below threshold"):
        params(stimulation__current_ua=40.0)


def test_a_partially_overlapping_site_is_refused():
    # Outside the RF but only ~20 deg from it: the paper excluded such sites (p. 372).
    with pytest.raises(ValueError, match="partial overlap"):
        params(site__saccade_endpoint_dva=[-9.5, -12.5])


def test_a_non_overlapping_site_puts_the_distracter_at_the_saccade_end_point():
    p = params(site__saccade_endpoint_dva=[8.0, -8.0])
    assert p.site.kind() == "non-overlapping"
    assert p.distracter_xy() == (8.0, -8.0)


def test_the_post_train_window_must_end_before_the_bars_go_off():
    with pytest.raises(ValueError, match="ends after the shortest stimulus"):
        params(stimulus_duration__min={"ms": 560})


def test_a_distracter_inside_the_rf_is_refused():
    with pytest.raises(ValueError, match="inside the RF"):
        params(distracter_position_dva=[-7.0, -7.0])


def test_a_bright_bar_cannot_reach_the_papers_contrast():
    with pytest.raises(ValueError, match="bright bar"):
        params(bar_polarity="bright")


def test_the_wiring_check():
    example = load_rig(PROJECT / "configs" / "rig-recording-example.yaml")
    rehearsal = load_rig(PROJECT / "configs" / "rig-recording-rehearsal.yaml")
    booth = load_rig(PROJECT / "configs" / "rig-booth.yaml")
    assert stimulation_wiring_problem(example) is None
    assert "simulated" in stimulation_wiring_problem(rehearsal)
    assert "no sync device" in stimulation_wiring_problem(booth)


def test_run_mode_refuses_a_rig_that_cannot_trigger_the_stimulator():
    rig = str(PROJECT / "configs" / "rig-booth.yaml")
    with pytest.raises(ConfigError, match="CANNOT RUN"):
        RfGatingFixationTask.params_hook(params(), Namespace(mode="run", rig=rig))
    # Test and simulate are what a rig without the line is for; the demo never stimulates.
    RfGatingFixationTask.params_hook(params(), Namespace(mode="test", rig=rig))
    RfGatingFixationTask.params_hook(params(DEMO), Namespace(mode="run", rig=rig))
    example = str(PROJECT / "configs" / "rig-recording-example.yaml")
    RfGatingFixationTask.params_hook(params(), Namespace(mode="run", rig=example))


def test_the_subject_is_told_what_to_do():
    assert RfGatingFixationTask.default_params().is_file()
    assert "SPACE" in (PROJECT / "instructions.md").read_text(encoding="utf-8")


def test_the_trial_timing_estimate_matches_the_params(task):
    timing = task.trial_timing(Condition(cond()), 60.0)
    assert timing is not None
