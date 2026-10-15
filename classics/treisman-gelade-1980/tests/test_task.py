"""Trial logic on alhazen's fake clock with scripted inputs: no display, no devices.

Every outcome branch: a correct and a wrong "present", a correct "absent", no response
(the deadline), a trial never started (the ready field's deadline); plus the response
mapping, where reaction time starts, and what feedback says.
"""

from __future__ import annotations

import pytest
from alhazen import Duration
from alhazen.config.loader import load_params
from support import CONFIGS, a_condition, blank, params, press, run_trial

from treisman_gelade1980.task import (
    FeatureConjunctionSearchTask,
    FeatureConjunctionSearchTaskParams,
)

# Fixation 3 frames, response deadline 20 frames, ready deadline 30 frames, feedback 2.
FAST = dict(fixation_duration=Duration(frames=3), response_timeout=Duration(frames=20),
            ready_timeout=Duration(frames=30), feedback_duration=Duration(frames=2))


@pytest.fixture
def task():
    return FeatureConjunctionSearchTask(params(**FAST))


def started(*rest):
    """Ready field (first frame ignored), SPACE, then fixation, then whatever follows."""
    return blank(2) + press("space") + blank(3) + [f for part in rest for f in part]


def test_present_answered_present_is_correct(task):
    cond = a_condition(task, size=15, present=True)
    events, result, ctx = run_trial(task, cond, started(blank(4), press("j"), blank(10)))
    assert result.outcome.name == "CORRECT"
    assert ctx.record["response_key"] == "j"
    assert ctx.record["feedback"].startswith("Correct")


def test_present_answered_absent_is_wrong(task):
    cond = a_condition(task, size=15, present=True)
    _, result, ctx = run_trial(task, cond, started(blank(4), press("f"), blank(10)))
    assert result.outcome.name == "WRONG"
    assert ctx.record["feedback"].startswith("Error")


def test_absent_answered_absent_is_correct(task):
    cond = a_condition(task, size=5, present=False)
    _, result, _ = run_trial(task, cond, started(blank(4), press("f"), blank(10)))
    assert result.outcome.name == "CORRECT"


def test_absent_answered_present_is_wrong(task):
    cond = a_condition(task, size=5, present=False)
    _, result, _ = run_trial(task, cond, started(blank(4), press("j"), blank(10)))
    assert result.outcome.name == "WRONG"


def test_no_key_before_the_deadline_is_no_response(task):
    cond = a_condition(task, size=30, present=True)
    _, result, ctx = run_trial(task, cond, started(blank(60)))
    assert result.outcome.name == "NO_RESPONSE"
    assert not result.outcome.completed
    assert ctx.record["feedback"] == "No response"


def test_a_trial_nobody_starts_is_not_started_and_not_completed(task):
    cond = a_condition(task, size=1, present=True)
    events, result, _ = run_trial(task, cond, blank(80))
    assert result.outcome.name == "NOT_STARTED"
    assert not result.outcome.completed
    assert "ARRAY_ON" not in events.names()


def test_a_ready_key_on_the_first_frame_does_not_start_the_trial(task):
    cond = a_condition(task, size=1, present=True)
    events, result, _ = run_trial(task, cond, press("space") + blank(80))
    assert result.outcome.name == "NOT_STARTED"


def test_response_keys_during_fixation_are_not_answers(task):
    # "j" pressed while the fixation spot is up: ignored, so the trial times out.
    cond = a_condition(task, size=5, present=True)
    frames = blank(2) + press("space") + press("j") + blank(60)
    _, result, _ = run_trial(task, cond, frames)
    assert result.outcome.name == "NO_RESPONSE"


def test_events_run_in_the_papers_order(task):
    cond = a_condition(task, size=5, present=True)
    events, _, _ = run_trial(task, cond, started(blank(4), press("j"), blank(10)))
    ours = {"READY_ON", "FIX_ON", "ARRAY_ON", "RESPONSE", "FEEDBACK_ON"}
    names = [n for n in events.names() if n in ours]
    assert names == ["READY_ON", "FIX_ON", "ARRAY_ON", "RESPONSE", "FEEDBACK_ON"]


def test_the_fixation_spot_lasts_its_duration_and_rt_runs_from_the_array(task):
    cond = a_condition(task, size=5, present=True)
    events, _, ctx = run_trial(task, cond, started(blank(6), press("j"), blank(10)))
    t = {e.name: e.t for e in events.events}
    assert t["ARRAY_ON"] - t["FIX_ON"] == pytest.approx(3 / 60, abs=1e-9)
    # The key is read at the start of a frame; RESPONSE is stamped on that frame's flip,
    # one frame later. RT is from the array's flip to the read.
    rt = (t["RESPONSE"] - t["ARRAY_ON"]) * 1000 - 1000 / 60
    assert ctx.record["rt_ms"] == pytest.approx(rt, abs=1e-6)


def test_the_dominant_hand_answers_present():
    left = FeatureConjunctionSearchTask(params(dominant_hand="left", **FAST))
    assert (left.params.present_key, left.params.absent_key) == ("f", "j")
    cond = a_condition(left, size=5, present=True)
    _, result, _ = run_trial(left, cond, started(blank(4), press("f"), blank(10)))
    assert result.outcome.name == "CORRECT"


def test_the_record_rebuilds_the_display(task):
    import json

    from treisman_gelade1980 import design

    cond = a_condition(task, size=15, present=True)
    _, _, ctx = run_trial(task, cond, started(blank(4), press("j"), blank(10)))
    items = json.loads(ctx.record["items"])
    card = design.build_card(task.params, cond)
    assert len(items) == ctx.record["n_items"] == 15
    assert [i["glyph"] for i in items] == [i.glyph for i in card.items]
    assert ctx.record["target_region"] in design.SECTIONS


def test_every_params_file_loads():
    assert len(CONFIGS) == 4
    for path in CONFIGS:
        load_params(path, FeatureConjunctionSearchTaskParams)


def test_a_condition_from_the_wrong_experiment_is_refused():
    with pytest.raises(ValueError, match="not one of Experiment"):
        FeatureConjunctionSearchTaskParams(experiment=2, condition="feature")


def test_a_glyph_with_no_ink_is_refused():
    with pytest.raises(ValueError, match="ink"):
        FeatureConjunctionSearchTaskParams(targets=["T_purple"])


def test_the_subject_is_told_what_to_do():
    assert FeatureConjunctionSearchTask.default_params().is_file()
    text = FeatureConjunctionSearchTask(params()).instructions()
    assert "SPACE" in text and "a green T" in text
    assert "press J with your right hand" in text and "press F with your left hand" in text
    feature = FeatureConjunctionSearchTask(params("task-exp1-feature.yaml")).instructions()
    assert "a blue letter or an S" in feature



def test_the_demo_pages_through_every_display_size_and_answer():
    from types import SimpleNamespace

    import numpy as np
    from alhazen.testing import FakeClock, FakeDisplay
    from support import SCREEN

    task = FeatureConjunctionSearchTask(params("task-exp2-easy.yaml"))
    setup = SimpleNamespace(display=FakeDisplay(FakeClock()), screen=SCREEN, params=task.params,
                            rng=np.random.default_rng(0))
    views = task.demo_views(setup)
    assert len(views) == 8
    views[0].draw(0.0)


def test_the_duration_estimate_counts_one_block():
    import numpy as np

    task = FeatureConjunctionSearchTask(params())
    assert task.duration_schedule(task.params, np.random.default_rng(0)).n_trials == 128
    timing = task.trial_timing(None, 60.0)
    assert timing.fixed_s == pytest.approx(1.0 + 1.5)
