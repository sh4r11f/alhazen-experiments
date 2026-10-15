"""Trial logic on alhazen's fake clock with scripted gaze: no display, no devices.

Every outcome branch of one ODR trial, the order and timing of its events, what is on the
screen in each epoch, and the parameters the paper states.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from alhazen import ConfigError, Duration, InputFrame
from alhazen.config.loader import build_session_config, load_params
from alhazen.config.models import DisplayConfig, MonitorConfig, RigConfig, SessionInfo
from alhazen.core.engine import TrialEngine
from alhazen.core.events import EventBus
from alhazen.core.trial import TrialContext
from alhazen.display.screen import Screen
from alhazen.paradigms.base import Condition
from alhazen.task.plan import TrialSetup
from alhazen.testing import EventCollector, FakeClock, FakeDisplay, ScriptedCommands, ScriptedInputs

from funahashi1989.task import (
    PROJECT,
    OculomotorDelayedResponseTask,
    OdrParams,
    cue_position_dva,
)

FRAME_S = 1 / 60
PPD = 40.0
SCREEN = Screen(width_px=1920, height_px=1080, px_per_deg=PPD)

# Short phases so a trial is a few dozen frames: acquire <= 10, fixation 3, cue 3, delay 4,
# response <= 10, landing <= 6 frames.
FIX, CUE, DELAY = 3, 3, 4


def run_trial(task, condition, inputs, screen=SCREEN):
    clock = FakeClock()
    display = FakeDisplay(clock, FRAME_S)
    bus = EventBus()
    collector = EventCollector()
    bus.subscribe(collector)
    engine = TrialEngine(display=display, clock=clock, bus=bus, schema=task.events,
                         commands=ScriptedCommands(), input_provider=ScriptedInputs(inputs))
    monitor = MonitorConfig(width_px=screen.width_px, height_px=screen.height_px, width_cm=60.0,
                            distance_cm=60.0, refresh_rate_hz=60.0, fullscreen=False)
    setup = TrialSetup(
        cfg=build_session_config(
            RigConfig(monitor=monitor, display=DisplayConfig(backend="simulated"), data_root="."),
            SessionInfo(subject="t01", session=1, run=1, task_name=task.name, seed=1),
            task.params, {}),
        screen=screen, display=display, rng=np.random.default_rng(0),
        refresh_rate_hz=1 / FRAME_S, trial_index=1, attempt=1, condition=Condition(condition))
    plan = task.build_trial(setup)
    ctx = TrialContext(clock=clock, screen=screen, rng=np.random.default_rng(0), trial_index=1,
                       params=dict(condition), stimuli=plan.stimuli, regions=plan.regions,
                       record=dict(plan.record))
    return collector, engine.run_trial(ctx, plan.phases), ctx


def params(**changes) -> OdrParams:
    base = dict(subject_kind="human", acquire_timeout=Duration(frames=10),
                fixation_period=Duration(frames=FIX), cue_duration=Duration(frames=CUE),
                delays=[Duration(frames=DELAY), Duration(frames=2 * DELAY)],
                response_period=Duration(frames=10), landing_max_wait=Duration(frames=6))
    base.update(changes)
    return OdrParams(**base)


@pytest.fixture
def task():
    return OculomotorDelayedResponseTask(params())


class Eye:
    """Scripted gaze in centred px (y up), one new sample per frame."""

    def __init__(self):
        self.frames: list[InputFrame] = []

    def at(self, pos, n):
        for _ in range(n):
            t = len(self.frames) * FRAME_S
            self.frames.append(InputFrame(gaze=pos, gaze_t=None if pos is None else t))
        return self

    def at_dva(self, xy, n):
        return self.at((xy[0] * PPD, xy[1] * PPD), n)


CENTRE = (0.0, 0.0)
# frames at fixation through acquisition (1) + fixation + cue + delay; the go flip follows.
BEFORE_GO = 1 + FIX + CUE + DELAY


def memory_trial(landing_dva, after_go_frames=3, angle=45.0, delay_frames=DELAY):
    cue = cue_position_dva(13.0, angle)
    eye = Eye().at(CENTRE, BEFORE_GO - DELAY + delay_frames + after_go_frames)
    eye.at_dva(landing_dva(cue) if callable(landing_dva) else landing_dva, 20)
    return eye.frames


def test_a_saccade_to_the_remembered_location_is_correct(task):
    events, result, ctx = run_trial(task, {"cue_angle_deg": 45.0, "delay_index": 0},
                                    memory_trial(lambda c: (c[0] + 0.5, c[1] - 0.5)))
    assert result.outcome.name == "CORRECT"
    assert ctx.record["endpoint_measured"] is True
    assert ctx.record["endpoint_error_dva"] == pytest.approx(math.hypot(0.5, 0.5), abs=1e-6)
    assert ctx.record["saccade_latency_ms"] > 0
    assert ctx.record["delay_index"] == 0
    assert ctx.record["delay_s"] == pytest.approx(DELAY * FRAME_S)


def test_a_landing_outside_the_6_deg_window_is_inaccurate(task):
    # 45 deg off: the neighbouring location, the paper's "large saccadic error".
    _, result, ctx = run_trial(task, {"cue_angle_deg": 45.0, "delay_index": 0},
                               memory_trial(cue_position_dva(13.0, 90.0)))
    assert result.outcome.name == "INACCURATE"
    assert result.outcome.completed is True and result.outcome.success is False
    assert ctx.record["endpoint_error_dva"] > 3.0


def test_the_window_is_6_deg_across(task):
    # 2.9 deg from the cue is inside a 3-deg radius, 3.1 is outside.
    inside = run_trial(task, {"cue_angle_deg": 0.0, "delay_index": 0},
                       memory_trial((13.0 + 2.9, 0.0), angle=0.0))[1]
    outside = run_trial(task, {"cue_angle_deg": 0.0, "delay_index": 0},
                        memory_trial((13.0 + 3.1, 0.0), angle=0.0))[1]
    assert (inside.outcome.name, outside.outcome.name) == ("CORRECT", "INACCURATE")


def test_looking_away_during_the_delay_is_a_fixation_break(task):
    eye = Eye().at(CENTRE, 1 + FIX + CUE + 2).at_dva((5.0, 5.0), 30)
    _, result, _ = run_trial(task, {"cue_angle_deg": 0.0, "delay_index": 0}, eye.frames)
    assert result.outcome.name == "FIX_BREAK"
    assert result.outcome.completed is False  # served again


def test_looking_at_the_cue_while_it_is_shown_is_a_fixation_break(task):
    eye = Eye().at(CENTRE, 1 + FIX + 1).at_dva(cue_position_dva(13.0, 0.0), 30)
    _, result, _ = run_trial(task, {"cue_angle_deg": 0.0, "delay_index": 0}, eye.frames)
    assert result.outcome.name == "FIX_BREAK"


def test_a_blink_during_the_delay_is_a_fixation_break(task):
    eye = Eye().at(CENTRE, 1 + FIX + CUE + 1).at(None, 2).at(CENTRE, 30)
    _, result, _ = run_trial(task, {"cue_angle_deg": 0.0, "delay_index": 0}, eye.frames)
    assert result.outcome.name == "FIX_BREAK"


def test_never_looking_at_the_spot_is_no_fixation(task):
    _, result, _ = run_trial(task, {"cue_angle_deg": 0.0, "delay_index": 0},
                             Eye().at_dva((8.0, 0.0), 40).frames)
    assert result.outcome.name == "NO_FIXATION"


def test_staying_at_fixation_after_the_go_signal_is_no_saccade(task):
    _, result, _ = run_trial(task, {"cue_angle_deg": 0.0, "delay_index": 0},
                             Eye().at(CENTRE, 80).frames)
    assert result.outcome.name == "NO_SACCADE"
    assert result.outcome.completed is False


def test_events_come_in_the_paper_order_with_the_paper_durations(task):
    events, result, _ = run_trial(task, {"cue_angle_deg": 90.0, "delay_index": 1},
                                  memory_trial(lambda c: c, angle=90.0, delay_frames=2 * DELAY))
    names = events.names()
    order = ["FIX_ON", "FIX_ACQUIRED", "CUE_ON", "CUE_OFF", "FIX_OFF", "SACCADE_ONSET", "LANDED"]
    assert [n for n in names if n in order] == order
    t = {e.name: e.t for e in events.events}
    assert t["CUE_OFF"] - t["CUE_ON"] == pytest.approx(CUE * FRAME_S)
    assert t["FIX_OFF"] - t["CUE_OFF"] == pytest.approx(2 * DELAY * FRAME_S)
    # The hold starts on the frame after the one acquisition was read on, so the cue comes
    # one frame more than the fixation period after FIX_ACQUIRED (docs/methods.md, Procedure).
    assert t["CUE_ON"] - t["FIX_ACQUIRED"] == pytest.approx((FIX + 1) * FRAME_S)


def test_the_cue_is_drawn_only_in_the_cue_period_and_the_spot_goes_off_at_go(task):
    _, _, ctx = run_trial(task, {"cue_angle_deg": 0.0, "delay_index": 0},
                          memory_trial(lambda c: c, angle=0.0))
    assert ctx.stimuli["cue"].draw_count == CUE
    # drawn through acquisition, fixation, cue and delay; never after the go signal
    assert ctx.stimuli["fixation"].draw_count == 1 + FIX + CUE + DELAY
    assert ctx.stimuli["blank"].draw_count > 0


@pytest.mark.parametrize("angle", [0.0, 45.0, 90.0, 135.0, 180.0, 225.0, 270.0, 315.0])
def test_the_cue_sits_13_deg_out_at_its_angle(task, angle):
    _, _, ctx = run_trial(task, {"cue_angle_deg": angle, "delay_index": 0},
                          memory_trial(lambda c: c, angle=angle))
    x, y = ctx.regions["target"].center
    assert math.hypot(x, y) / PPD == pytest.approx(13.0)
    assert math.degrees(math.atan2(y, x)) % 360 == pytest.approx(angle)
    assert ctx.regions["target"].radius / PPD == pytest.approx(3.0)


def test_eight_locations_times_each_delay(task):
    conds = task.conditions(np.random.default_rng(0))
    assert len(conds) == 8 * 2
    assert {c.params["cue_angle_deg"] for c in conds} == {0, 45, 90, 135, 180, 225, 270, 315}


def test_a_screen_too_small_for_the_cues_is_refused(task):
    small = Screen(width_px=1280, height_px=720, px_per_deg=40.0)  # 9 deg up/down
    with pytest.raises(ConfigError, match="does not fit"):
        run_trial(task, {"cue_angle_deg": 90.0, "delay_index": 0}, Eye().at(CENTRE, 5).frames,
                  screen=small)


def test_overlapping_windows_are_refused():
    with pytest.raises(ValueError, match="overlaps"):
        params(fix_window_dva=11.0)


def test_every_params_file_loads():
    files = sorted((PROJECT / "configs").glob("task*.yaml"))
    assert len(files) == 2
    for path in files:
        load_params(path, OdrParams)


def test_the_main_file_has_the_papers_values():
    p = load_params(PROJECT / "configs" / "task.yaml", OdrParams)
    hz = 60.0
    assert p.fix_size_dva == 0.1 and p.cue_size_dva == 0.7 and p.cue_ecc_dva == 13.0
    assert p.cue_angles_deg == [0, 45, 90, 135, 180, 225, 270, 315]
    assert p.fixation_period.seconds(hz) == pytest.approx(0.75)
    assert p.cue_duration.seconds(hz) == pytest.approx(0.5)
    assert [d.seconds(hz) for d in p.delays] == pytest.approx([1.5, 3.0, 6.0])
    assert p.response_period.seconds(hz) == pytest.approx(0.5)
    assert p.target_window_dva * 2 == 6.0
    assert p.iti.seconds(hz) == pytest.approx(5.0)


def test_the_subject_is_told_what_to_do():
    assert OculomotorDelayedResponseTask.default_params().is_file()
    text = (PROJECT / "instructions.md").read_text(encoding="utf-8")
    assert "SPACE" in text and "square" in text
