"""The two parameter sets, the rig files and the run-mode guard."""

from __future__ import annotations

import re
from argparse import Namespace

import pytest
import yaml
from alhazen.config.loader import load_params, load_rig
from alhazen.errors import ConfigError

from posner1980.task import PROJECT, PosnerCueingTask, PosnerCueingTaskParams

CONFIGS = PROJECT / "configs"


def load(name):
    return yaml.safe_load((CONFIGS / name).read_text(encoding="utf-8"))


def test_the_keyboard_set_differs_from_the_main_set_only_in_fixation_control():
    main, keyboard = load("task.yaml"), load("task-keyboard.yaml")
    assert main.pop("fixation_control") == "tracker"
    assert keyboard.pop("fixation_control") == "none"
    assert main == keyboard


def test_every_value_line_cites_the_paper_or_is_marked_assumed():
    """Each line that sets a value says where it comes from, except the structural
    ones (the parameter set's identity and the scheduler's kind and repeat count)."""
    structural = {"subject_kind", "fixation_control", "design", "paradigm", "kind",
                  "n_per_condition", "blocks"}
    for name in ("task.yaml", "task-keyboard.yaml"):
        for line in (CONFIGS / name).read_text(encoding="utf-8").splitlines():
            m = re.match(r"\s*([a-z_]+)\s*:", line)
            if not m or m.group(1) in structural:
                continue
            assert "# paper:" in line or "# ASSUMED (not in the paper):" in line, line


def test_the_paper_values_are_the_papers():
    p = load_params(CONFIGS / "task.yaml", PosnerCueingTaskParams)
    assert p.target_ecc_dva == 7.0
    assert (p.intertrial_min.ms, p.intertrial_max.ms) == (1000, 2000)
    assert p.cue_target_soa.ms == 1000
    assert p.feedback_duration.ms == 500
    assert p.design.validity == 0.8
    assert p.cue_stays_on is True


@pytest.mark.parametrize("rig", ["rig-booth.yaml", "rig-eyetracker.yaml"])
def test_the_rig_files_load_and_feedback_is_silent(rig):
    cfg = load_rig(CONFIGS / rig)
    assert cfg.display.feedback_beeps is False


def test_only_the_eyetracker_rig_has_a_tracker():
    assert load_rig(CONFIGS / "rig-booth.yaml").devices.eyetracker is None
    assert load_rig(CONFIGS / "rig-eyetracker.yaml").devices.eyetracker is not None


def _hook(params_file, mode, rig):
    p = load_params(CONFIGS / params_file, PosnerCueingTaskParams)
    return PosnerCueingTask.params_hook(p, Namespace(mode=mode, rig=str(CONFIGS / rig)))


def test_a_real_session_of_the_tracker_set_is_refused_on_a_rig_with_no_tracker():
    with pytest.raises(ConfigError, match="task-keyboard.yaml"):
        _hook("task.yaml", "run", "rig-booth.yaml")


@pytest.mark.parametrize("params_file,mode,rig", [
    ("task.yaml", "run", "rig-eyetracker.yaml"),
    ("task.yaml", "test", "rig-booth.yaml"),        # test mode: the mouse stands in
    ("task.yaml", "simulate", "rig-booth.yaml"),    # simulate: the autopilot stands in
    ("task-keyboard.yaml", "run", "rig-booth.yaml"),
])
def test_the_guard_lets_everything_else_through(params_file, mode, rig):
    assert _hook(params_file, mode, rig) is not None


def test_a_fixation_window_reaching_the_target_is_refused():
    with pytest.raises(ValueError, match="fixation_window_dva"):
        PosnerCueingTaskParams(subject_kind="human", fixation_window_dva=7.0)


def test_an_adaptive_scheduler_is_refused():
    with pytest.raises(ValueError, match="sequence"):
        PosnerCueingTaskParams(subject_kind="human",
                               paradigm={"kind": "staircase", "staircase": {
                                   "parameter": "x", "start": 1, "step": 1, "n_trials": 5}})


def test_the_duration_estimate_names_every_stretch():
    p = load_params(CONFIGS / "task.yaml", PosnerCueingTaskParams)
    timing = PosnerCueingTask(p).trial_timing(None, 60.0)
    labels = [s.label for s in timing.spans]
    assert labels[0] == "fixation acquired" and "cue to target" in labels
    kb = load_params(CONFIGS / "task-keyboard.yaml", PosnerCueingTaskParams)
    kb_spans = PosnerCueingTask(kb).trial_timing(None, 60.0).spans
    assert "fixation acquired" not in [s.label for s in kb_spans]
