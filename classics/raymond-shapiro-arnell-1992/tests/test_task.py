"""Trial logic on alhazen's fake clock with scripted inputs: no display, no devices.

A scripted subject presses a given key a few frames after a given event, so every
outcome branch is reached deterministically: HIT, MISS, FALSE_ALARM, CORRECT_REJECTION,
NO_RESPONSE (at either report) and NO_START.
"""

from __future__ import annotations

import numpy as np
import pytest
from alhazen import Duration, InputFrame
from alhazen.config.loader import build_session_config, load_params
from alhazen.config.models import DisplayConfig, MonitorConfig, RigConfig, SessionInfo
from alhazen.core.engine import TrialEngine
from alhazen.core.events import EventBus
from alhazen.core.trial import TrialContext
from alhazen.display.screen import Screen
from alhazen.errors import ConfigError
from alhazen.paradigms.base import Condition
from alhazen.task.plan import TrialSetup
from alhazen.testing import EventCollector, FakeClock, FakeDisplay, ScriptedCommands

from raymond1992.task import PROJECT, AttentionalBlinkTask, AttentionalBlinkTaskParams

HZ = 120.0
FRAME_S = 1 / HZ
SCREEN = Screen(width_px=1920, height_px=1080, px_per_deg=40.0)


class KeysAfter:
    """Input provider: presses ``keys[event]`` ``delay`` frames after that event."""

    def __init__(self, keys: dict[str, str | None], delay: int = 4) -> None:
        self.keys = keys
        self.delay = delay
        self._due: list[list] = []

    def on_event(self, event) -> None:
        key = self.keys.get(event.name)
        if key:
            self._due.append([self.delay, key])

    def __call__(self) -> InputFrame:
        pressed = []
        for item in self._due:
            item[0] -= 1
            if item[0] < 0:
                pressed.append(item[1])
        self._due = [i for i in self._due if i[0] >= 0]
        return InputFrame(gaze=None, keys=tuple(pressed))


def make_task(**overrides) -> AttentionalBlinkTask:
    params = load_params(PROJECT / "configs" / "task.yaml", AttentionalBlinkTaskParams)
    defaults = dict(response_timeout=Duration(frames=60), ready_timeout=Duration(frames=60))
    return AttentionalBlinkTask(params.model_copy(update={**defaults, **overrides}))


def cond(condition="experimental", probe_pos=None, practice=False):
    return {"condition": condition, "probe_present": probe_pos is not None,
            "probe_pos": probe_pos, "practice": practice,
            "condition_order": "experimental-first", "plan_trial": 1}


def setup_for(task, condition, seed=0, hz=HZ):
    clock = FakeClock()
    display = FakeDisplay(clock, 1 / hz)
    monitor = MonitorConfig(width_px=1920, height_px=1080, width_cm=53.0, distance_cm=35.0,
                            refresh_rate_hz=hz, fullscreen=False)
    setup = TrialSetup(
        cfg=build_session_config(
            RigConfig(monitor=monitor, display=DisplayConfig(backend="simulated"), data_root="."),
            SessionInfo(subject="t01", session=1, run=1, task_name=task.name, seed=1),
            task.params, {}),
        screen=SCREEN, display=display, rng=np.random.default_rng(seed),
        refresh_rate_hz=hz, trial_index=1, attempt=1, condition=Condition(condition))
    return clock, display, setup


def run_trial(task, condition, respond, seed=0):
    """Build and run one trial. ``respond(plan) -> {event: key}``."""
    clock, display, setup = setup_for(task, condition, seed)
    plan = task.build_trial(setup)
    inputs = KeysAfter(respond(plan))
    bus = EventBus()
    collector = EventCollector()
    bus.subscribe(collector)
    bus.subscribe(inputs.on_event)
    engine = TrialEngine(display=display, clock=clock, bus=bus, schema=task.events,
                         commands=ScriptedCommands(), input_provider=inputs)
    ctx = TrialContext(clock=clock, screen=SCREEN, rng=np.random.default_rng(0), trial_index=1,
                       params=dict(condition), stimuli=plan.stimuli, regions=plan.regions,
                       record={**condition, **plan.record})
    result = engine.run_trial(ctx, plan.phases)
    return collector, result, task.score(result.record), plan


def answers(target=True, probe="y"):
    def respond(plan):
        letter = plan.record["target_letter"].lower()
        wrong = "q" if letter != "q" else "z"
        return {"READY": "space", "TARGET_PROMPT": letter if target else wrong,
                "PROBE_PROMPT": probe}
    return respond


@pytest.mark.parametrize("probe_pos, key, outcome", [
    (3, "y", "HIT"), (3, "n", "MISS"), (None, "y", "FALSE_ALARM"),
    (None, "n", "CORRECT_REJECTION")])
def test_probe_reports_score_by_presence(probe_pos, key, outcome):
    _, result, rec, _ = run_trial(make_task(), cond(probe_pos=probe_pos), answers(probe=key))
    assert result.outcome.name == outcome
    assert rec["probe_reported"] == (key == "y")
    assert rec["probe_correct"] == (outcome in ("HIT", "CORRECT_REJECTION"))


def test_the_target_is_scored_from_the_typed_letter():
    _, _, right, _ = run_trial(make_task(), cond(probe_pos=2), answers(target=True))
    assert right["target_correct"] is True and right["target_report_pos"] == 0
    _, _, wrong, _ = run_trial(make_task(), cond(probe_pos=2), answers(target=False))
    assert wrong["target_correct"] is False


def test_a_plus_one_intrusion_is_located_in_the_stream():
    def respond(plan):
        stream, i = plan.record["stream"], plan.record["n_pretarget"]
        return {"READY": "space", "TARGET_PROMPT": stream[i + 1].lower(), "PROBE_PROMPT": "n"}
    _, _, rec, _ = run_trial(make_task(), cond(), respond)
    assert rec["target_report_pos"] == 1 and rec["target_correct"] is False


def test_no_target_report_is_served_again():
    _, result, _, _ = run_trial(make_task(), cond(probe_pos=1),
                                lambda plan: {"READY": "space", "PROBE_PROMPT": "y"})
    assert result.outcome.name == "NO_RESPONSE" and not result.outcome.completed


def test_no_probe_report_is_served_again():
    def respond(plan):
        return {"READY": "space", "TARGET_PROMPT": plan.record["target_letter"].lower()}
    _, result, _, _ = run_trial(make_task(), cond(probe_pos=1), respond)
    assert result.outcome.name == "NO_RESPONSE"


def test_a_trial_never_started_is_served_again():
    collector, result, _, _ = run_trial(make_task(), cond(), lambda plan: {})
    assert result.outcome.name == "NO_START"
    assert "FIX_ON" not in collector.names()


def test_the_control_condition_asks_only_about_the_x():
    collector, result, rec, _ = run_trial(
        make_task(), cond("control", probe_pos=4),
        lambda plan: {"READY": "space", "TARGET_PROMPT": "a", "PROBE_PROMPT": "y"})
    assert result.outcome.name == "HIT"
    assert "TARGET_PROMPT" not in collector.names()
    assert rec["target_correct"] is None


def test_keys_during_the_stream_are_not_answers():
    def respond(plan):
        return {"READY": "space", "STREAM_ON": "y", "TARGET_PROMPT": None}
    task = make_task()
    _, result, _, _ = run_trial(task, cond("control", probe_pos=None), respond)
    # The Y pressed during the stream is gone by the probe prompt: no answer, timeout.
    assert result.outcome.name == "NO_RESPONSE"


def test_the_stream_runs_frame_by_frame_at_the_papers_rate():
    collector, result, rec, plan = run_trial(make_task(), cond(probe_pos=3), answers())
    # 120 Hz: 15 ms -> 2 frames, 90 ms SOA -> 11 frames (91.7 ms), ISI 9 frames (75 ms).
    assert (rec["letter_frames"], rec["isi_frames"]) == (2, 9)
    assert rec["soa_ms"] == pytest.approx(91.667, abs=1e-3)
    t = {e.name: e.t for e in collector.events}
    n_pre = rec["n_pretarget"]
    assert 7 <= n_pre <= 15 and len(rec["stream"]) == n_pre + 1 + 8
    assert t["TARGET_ON"] - t["STREAM_ON"] == pytest.approx(n_pre * 11 * FRAME_S)
    assert t["PROBE_ON"] - t["TARGET_ON"] == pytest.approx(3 * 11 * FRAME_S)
    assert t["STREAM_ON"] - t["FIX_ON"] == pytest.approx(22 * FRAME_S)  # 180 ms -> 22 frames
    assert rec["stream"][n_pre + 3] == "X" and rec["stream"].count("X") == 1
    assert rec["stream_frames"] == 22 + len(rec["stream"]) * 11
    order = [n for n in collector.names() if n in (
        "READY", "FIX_ON", "STREAM_ON", "TARGET_ON", "PROBE_ON", "STREAM_OFF",
        "TARGET_PROMPT", "PROBE_PROMPT")]
    assert order == ["READY", "FIX_ON", "STREAM_ON", "TARGET_ON", "PROBE_ON", "STREAM_OFF",
                     "TARGET_PROMPT", "PROBE_PROMPT"]


def test_each_letter_is_shown_for_its_frames_only():
    task = make_task()
    _, _, setup = setup_for(task, cond(probe_pos=0))
    plan = task.build_trial(setup)
    timeline = plan.phases[1]._timeline
    shown = {}
    for frame in range(timeline.n_frames):
        for key in timeline.visible_at(frame):
            if key.startswith("item_"):
                shown.setdefault(key, []).append(frame)
    assert all(len(frames) == 2 for frames in shown.values())
    starts = sorted(frames[0] for frames in shown.values())
    assert set(np.diff(starts)) == {11}


def test_the_white_letter_is_the_target_and_the_x_at_zero_is_white():
    task = make_task()
    _, _, setup = setup_for(task, cond(probe_pos=0))
    plan = task.build_trial(setup)
    i = plan.record["n_pretarget"]
    assert plan.record["target_letter"] == "X"
    assert plan.stimuli[f"item_{i:02d}"] is task._stimuli["white_X"]
    others = [k for k in plan.stimuli if k.startswith("item_") and k != f"item_{i:02d}"]
    assert all(plan.stimuli[k] in [task._stimuli[f"black_{c}"] for c in plan.record["stream"]]
               for k in others)


def test_the_condition_introduction_comes_with_each_change_of_condition():
    task = make_task()
    shown = []
    for c in ("experimental", "experimental", "control", "control"):
        _, _, setup = setup_for(task, cond(c))
        shown.append(task.build_trial(setup).record["intro_shown"])
    assert shown == [True, False, True, False]


@pytest.mark.parametrize("hz, ok", [(60.0, False), (66.6667, True), (75.0, False),
                                    (100.0, True), (120.0, True), (144.0, True),
                                    (200.0, True), (240.0, True)])
def test_run_mode_refuses_refresh_rates_that_cannot_show_the_stream(hz, ok):
    task = make_task()
    _, _, setup = setup_for(task, cond(), hz=hz)
    if ok:
        task.build_trial(setup)
    else:
        with pytest.raises(ConfigError, match="SOA"):
            task.build_trial(setup)


def test_warn_mode_runs_an_inexact_rate_and_records_what_it_showed():
    task = make_task(on_inexact_timing="warn")
    _, _, setup = setup_for(task, cond(), hz=60.0)
    rec = task.build_trial(setup).record
    assert (rec["letter_frames"], rec["isi_frames"], rec["soa_ms"]) == (1, 4, pytest.approx(83.333))


def test_every_params_file_loads():
    for path in (PROJECT / "configs").glob("task*.yaml"):
        load_params(path, AttentionalBlinkTaskParams)


def test_the_subject_is_told_what_to_do():
    assert AttentionalBlinkTask.default_params().is_file()
    text = (PROJECT / "instructions.md").read_text(encoding="utf-8")
    assert "SPACE" in text and "white" in text.lower() and "X" in text
