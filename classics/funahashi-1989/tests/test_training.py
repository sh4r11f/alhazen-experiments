"""The monkey's training ladder (configs/training-odr.yaml) and its training task, through
alhazen's training mode: every stage resolves, each stage's trial is what it says, and a
whole stage session pays juice on exactly its success outcome."""

from __future__ import annotations

import importlib.util

import pytest
from alhazen import Duration
from alhazen.training.ladder import load_ladder, resolve_stage
from conftest import PROJECT, run_session
from test_task import CENTRE, FIX, Eye, run_trial

from funahashi1989.task import OculomotorDelayedResponseTask, cue_position_dva
from funahashi1989.training import OdrTrainingParams, OdrTrainingTask

LADDER = PROJECT / "configs" / "training-odr.yaml"
_spec = importlib.util.spec_from_file_location("funahashi_run_py", PROJECT / "run.py")
RUN = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(RUN)
STAGES = [s.id for s in load_ladder(LADDER).stages]


def test_the_ladder_is_registered_and_climbs_fixate_visual_short_delay_full():
    assert list(RUN.LADDERS.values()) == [LADDER]
    assert STAGES == ["fixate", "visual", "short-delay", "full"]


@pytest.mark.parametrize("stage", STAGES)
def test_every_stage_resolves_to_a_monkey_session_paying_its_success_alone(stage):
    found = resolve_stage(LADDER, stage, RUN.TASKS)
    assert found.params.subject_kind.value == "monkey"
    assert set(found.params.reward.by_outcome) == {found.stage.success}


def test_the_last_stage_is_the_experiments_own_trial():
    found = resolve_stage(LADDER, "full", RUN.TASKS)
    assert found.task_class is OculomotorDelayedResponseTask
    assert [d.seconds(60) for d in found.params.delays] == pytest.approx([1.5, 3.0, 6.0])


def test_the_short_delay_stage_uses_short_delays():
    found = resolve_stage(LADDER, "short-delay", RUN.TASKS)
    assert found.task_class is OculomotorDelayedResponseTask
    assert max(d.seconds(60) for d in found.params.delays) <= 1.0


def training(mode):
    return OdrTrainingTask(OdrTrainingParams(
        subject_kind="human", training={"mode": mode}, acquire_timeout=Duration(frames=10),
        fixation_period=Duration(frames=FIX), response_period=Duration(frames=10),
        landing_max_wait=Duration(frames=6)))


def test_the_fixate_stage_holds_the_spot_and_shows_nothing_else():
    _, result, ctx = run_trial(training("fixate"), {"cue_angle_deg": 0.0, "delay_index": -1},
                               Eye().at(CENTRE, 30).frames)
    assert result.outcome.name == "FIXATION_HELD"
    assert ctx.stimuli["cue"].draw_count == 0


def test_the_visual_stage_shows_the_square_at_go_and_pays_a_landing_on_it():
    cue = cue_position_dva(13.0, 135.0)
    eye = Eye().at(CENTRE, 1 + FIX + 3).at_dva(cue, 20)
    events, result, ctx = run_trial(training("visual"), {"cue_angle_deg": 135.0,
                                                         "delay_index": -1}, eye.frames)
    assert result.outcome.name == "CORRECT"
    assert "CUE_ON" not in events.names() and "FIX_OFF" in events.names()
    assert ctx.stimuli["cue"].draw_count > 0
    assert ctx.stimuli["fixation"].draw_count == 1 + FIX


@pytest.mark.parametrize("stage", ["fixate", "visual"])
def test_a_stage_session_pays_juice_on_exactly_its_success(tmp_path, stage):
    found = resolve_stage(LADDER, stage, RUN.TASKS)
    values = found.params.model_dump(mode="json")
    values["paradigm"] = {**values["paradigm"], "n_per_condition": 2}
    params = type(found.params).model_validate(values)
    rows, card = run_session(found.task_class(params), tmp_path / "data-training" / stage,
                             reward=True, mode="training", training_stage=found.record())
    success = found.stage.success
    paid = [r["trial_index"] for r in rows if r["outcome"] == success]
    assert paid
    assert [r["trial_index"] for r in rows if r["rewarded"] == "True"] == paid
    assert card["mode"] == "training" and card["training"]["stage"] == stage
