"""Trial logic on alhazen's fake clock with scripted inputs: no display, no devices."""

from __future__ import annotations

import json

import numpy as np
import pytest
from alhazen import Duration, InputFrame
from alhazen.config.loader import build_session_config, load_params
from alhazen.config.models import DisplayConfig, MonitorConfig, RigConfig, SessionInfo
from alhazen.core.engine import TrialEngine
from alhazen.core.events import EventBus
from alhazen.core.trial import TrialContext
from alhazen.display.screen import Screen
from alhazen.paradigms.base import Condition
from alhazen.task.plan import TrialSetup
from alhazen.testing import EventCollector, FakeClock, FakeDisplay, ScriptedCommands, ScriptedInputs

from rensink1997.phases import FlickerPhase
from rensink1997.task import (
    PROJECT,
    FlickerChangeDetectionTask,
    FlickerChangeDetectionTaskParams,
    FlickerTiming,
    LocationProbe,
    SceneSet,
    TypeProbe,
    cue_plan,
    scene_ids,
)

FRAME_S = 1 / 60
SCREEN = Screen(width_px=1920, height_px=1080, px_per_deg=40.0)
SCENE = "proc/5/presence/central"
CUE, GRAY, IMG, BLANK = 3, 2, 2, 1  # frames, in the fast params below
CYCLE = 4 * (IMG + BLANK)
NO_DETECTION = FlickerChangeDetectionTask.outcomes["NO_DETECTION"]


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
                       record=dict(plan.record))
    return collector, engine.run_trial(ctx, plan.phases), ctx


def fast_params(**over):
    kw = dict(
        subject_kind="human", cue_field=Duration(frames=CUE), gray_field=Duration(frames=GRAY),
        flicker=FlickerTiming(image=Duration(frames=IMG), blank=Duration(frames=BLANK)),
        max_flicker=Duration(frames=60),
        location_probe=LocationProbe(timeout=Duration(frames=20)),
        type_probe=TypeProbe(timeout=Duration(frames=20)),
        scenes=SceneSet(photos=False, procedural_per_cell=1))
    kw.update(over)
    return FlickerChangeDetectionTaskParams(**kw)


@pytest.fixture
def task():
    return FlickerChangeDetectionTask(fast_params())


def blank(n):
    return [InputFrame(gaze=None)] * n


def press(key):
    return [InputFrame(gaze=None, keys=(key,))]


def script(detect_at=20, box=None, kind=None, gap=6):
    """Nothing until frame `detect_at`, SPACE, then the box key, then the type key."""
    frames = blank(detect_at) + press("space") + blank(gap)
    if box is not None:
        frames += press(box) + blank(gap)
    if kind is not None:
        frames += press(kind) + blank(gap)
    return frames + blank(1)


def answers(task, scene=SCENE):
    """(the correct box key, the correct type key) of a trial of `scene`."""
    _, _, ctx = run_trial(task, {"scene": scene, "cue": "none"}, blank(200))
    return ctx.record["probe_correct_key"], ctx.record["type_correct_key"]


def test_seeing_the_change_and_reporting_it_right_scores_correct(task):
    box, kind = answers(task)
    events, result, ctx = run_trial(task, {"scene": SCENE, "cue": "none"},
                                    script(box=box, kind=kind))
    assert result.outcome.name == "CORRECT"
    assert ctx.record["location_correct"] and ctx.record["type_correct"]
    assert ctx.record["type_report"] == "presence"
    assert ctx.record["rt_ms"] > 0 and ctx.record["alternations"] > 0
    names = events.names()
    for name in ("CUE_ON", "GRAY_ON", "FLICKER_ON", "IMAGE_ON", "DETECTED", "LOCATION_PROBE",
                 "LOCATION_REPORT", "TYPE_PROBE", "TYPE_REPORT"):
        assert name in names, name
    assert names.index("CUE_ON") < names.index("GRAY_ON") < names.index("FLICKER_ON")


def test_the_wrong_box_is_misidentified(task):
    box, kind = answers(task)
    wrong = next(k for k in ("1", "2", "3", "4") if k != box)
    _, result, ctx = run_trial(task, {"scene": SCENE, "cue": "none"},
                               script(box=wrong, kind=kind))
    assert result.outcome.name == "MISIDENTIFIED"
    assert not ctx.record["location_correct"] and ctx.record["type_correct"]


def test_the_wrong_type_is_misidentified(task):
    box, _ = answers(task)
    _, result, ctx = run_trial(task, {"scene": SCENE, "cue": "none"}, script(box=box, kind="right"))
    assert result.outcome.name == "MISIDENTIFIED"
    assert ctx.record["location_correct"] and not ctx.record["type_correct"]


def test_no_key_within_the_limit_is_no_detection(task):
    events, result, ctx = run_trial(task, {"scene": SCENE, "cue": "none"}, blank(300))
    assert result.outcome.name == "NO_DETECTION"
    assert "rt_ms" not in ctx.record and "LOCATION_PROBE" not in events.names()
    assert ctx.record["flicker_frames"] == 60


def test_detecting_but_not_reporting_is_no_report(task):
    _, result, _ = run_trial(task, {"scene": SCENE, "cue": "none"}, script())
    assert result.outcome.name == "NO_REPORT"


def test_a_key_pressed_before_the_flicker_does_not_count_as_detection(task):
    frames = press("space") + blank(2) + press("space") + blank(300)  # both in the cue field
    _, result, _ = run_trial(task, {"scene": SCENE, "cue": "none"}, frames)
    assert result.outcome.name == "NO_DETECTION"


def test_the_flicker_runs_a_a_b_b_with_a_blank_after_each_image(task):
    events, _, ctx = run_trial(task, {"scene": SCENE, "cue": "none"}, script(detect_at=60))
    shown = [e.payload["image"] for e in events.events if e.name == "IMAGE_ON"]
    assert shown[:8] == ["A", "A", "B", "B", "A", "A", "B", "B"]
    names = events.names()
    seen = [e.payload["image"] for e in events.events[: names.index("DETECTED")]
            if e.name == "IMAGE_ON"]
    assert ctx.record["images_shown"] == len(seen)
    pairs = zip(seen, seen[1:], strict=False)
    assert ctx.record["changes_shown"] == sum(a != b for a, b in pairs)
    t = [e.t for e in events.events if e.name == "IMAGE_ON"]
    assert np.allclose(np.diff(t), (IMG + BLANK) * FRAME_S)  # frame-exact onsets


def test_alternations_are_rt_over_the_time_between_changes(task):
    box, kind = answers(task)
    _, _, ctx = run_trial(task, {"scene": SCENE, "cue": "none"},
                          script(detect_at=40, box=box, kind=kind))
    period = CYCLE / 2 * FRAME_S  # two changes per A A B B cycle
    assert ctx.record["alternation_s"] == pytest.approx(period, abs=1e-4)
    assert ctx.record["alternations"] == pytest.approx(ctx.record["rt_ms"] / 1000 / period,
                                                       abs=1e-3)


def test_the_segment_schedule_and_a_zero_frame_blank():
    names = {"a": "A", "b": "B"}
    phase = FlickerPhase([("a", 3), (None, 1), ("b", 3), (None, 1)], names, "space", 1.0,
                         on_timeout=NO_DETECTION)
    assert [phase.segment_at(f)[1] for f in range(9)] == ["a", "a", "a", None, "b", "b", "b",
                                                          None, "a"]
    noblank = FlickerPhase([("a", 3), (None, 0), ("b", 3), (None, 0)], names, "space", 1.0,
                           on_timeout=NO_DETECTION)
    assert noblank.cycle_frames == 6
    assert [noblank.segment_at(f)[1] for f in range(7)] == ["a"] * 3 + ["b"] * 3 + ["a"]


def test_paper_timing_resolves_to_whole_frames():
    task = FlickerChangeDetectionTask(load_params(PROJECT / "configs" / "task.yaml",
                                                  FlickerChangeDetectionTaskParams))
    cycle, img, blank_frames = task._cycle(60.0)
    assert (img, blank_frames) == (14, 5)  # 233 and 83 ms: 240 and 80 to the nearest frame
    assert [k for k, _ in cycle] == ["image_a", None, "image_a", None, "image_b", None,
                                     "image_b", None]
    assert task._cycle(100.0)[1:] == (24, 8)  # exact at 100 Hz


def test_a_photo_trial_has_four_separate_probe_boxes_one_around_the_change(task):
    _, _, ctx = run_trial(task, {"scene": "photo/car", "cue": "none"}, blank(100))
    boxes = json.loads(ctx.record["probe_boxes"])
    assert len(boxes) == 4 and ctx.record["source"] == "photo"
    cx, cy = ctx.record["change_cx"], ctx.record["change_cy"]
    x0, y0, x1, y1 = boxes[int(ctx.record["probe_correct"])]
    assert x0 <= cx <= x1 and y0 <= cy <= y1
    for i, a in enumerate(boxes):
        for b in boxes[i + 1:]:
            assert a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1], "overlap"


def test_a_valid_cue_names_the_changed_part_and_an_invalid_one_another(task):
    _, _, valid = run_trial(task, {"scene": "photo/car", "cue": "valid"}, blank(10))
    _, _, invalid = run_trial(task, {"scene": "photo/car", "cue": "invalid"}, blank(10))
    _, _, none = run_trial(task, {"scene": "photo/car", "cue": "none"}, blank(10))
    assert valid.record["cue_word"] == "car" and invalid.record["cue_word"] not in ("", "car")
    assert none.record["cue_word"] == "" and "cue_text" not in none.stimuli


def test_the_main_set_is_48_scenes_each_once_and_valid50_is_balanced():
    p = load_params(PROJECT / "configs" / "task.yaml", FlickerChangeDetectionTaskParams)
    ids = scene_ids(p)
    assert len(ids) == len(set(ids)) == 48
    cues = cue_plan(ids, "valid50")
    assert sum(v == "valid" for v in cues.values()) == 24


def test_practice_is_six_scenes_two_per_type_none_shared_with_a_test_set():
    practice = scene_ids(load_params(PROJECT / "configs" / "task-practice.yaml",
                                     FlickerChangeDetectionTaskParams))
    assert sorted(i.split("/")[2] for i in practice) == (
        ["color"] * 2 + ["location"] * 2 + ["presence"] * 2)
    tests = set()
    for f in ("task.yaml", "task-noblank.yaml", "task-exp2.yaml", "task-exp3-valid.yaml",
              "task-exp3-valid50.yaml"):
        tests |= set(scene_ids(load_params(PROJECT / "configs" / f,
                                           FlickerChangeDetectionTaskParams)))
    assert not set(practice) & tests


def test_every_params_file_loads():
    for path in (PROJECT / "configs").glob("task*.yaml"):
        load_params(path, FlickerChangeDetectionTaskParams)


def test_clashing_keys_are_refused():
    with pytest.raises(ValueError):
        fast_params(detect_key="left")


def test_alhazens_experimenter_keys_are_refused_as_responses():
    with pytest.raises(ValueError, match="experimenter keys"):
        fast_params(type_probe=TypeProbe(keys={"p": "presence", "c": "color", "l": "location"}))


def test_the_subject_is_told_what_to_do():
    text = (PROJECT / "instructions.md").read_text(encoding="utf-8")
    assert FlickerChangeDetectionTask.default_params().is_file()
    for word in ("SPACE", "LEFT arrow", "DOWN", "RIGHT arrow", "1 to 4"):
        assert word in text, word
