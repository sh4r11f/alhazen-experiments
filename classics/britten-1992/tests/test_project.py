"""The folder is a standalone alhazen project and its documentation matches its code."""

from __future__ import annotations

import ast
import json
import math
import re
from pathlib import Path

import pytest
import yaml

PROJECT = Path(__file__).resolve().parents[1]


def literal(name):
    tree = ast.parse((PROJECT / "run.py").read_text(encoding="utf-8"))
    for node in tree.body:
        targets = [t.id for t in getattr(node, "targets", []) if isinstance(t, ast.Name)]
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            targets = [node.target.id]
        if name in targets:
            return node.value
    raise AssertionError(f"run.py has no {name}")


def test_run_py_tables_are_dict_literals_naming_files_that_exist():
    for name in ("TASKS", "PARAMETERS", "LADDERS"):
        assert isinstance(literal(name), ast.Dict), name
    text = (PROJECT / "run.py").read_text(encoding="utf-8")
    for rel in re.findall(r'HERE / "configs" / "([^"]+)"', text):
        assert (PROJECT / "configs" / rel).is_file(), rel


def test_experiment_json_describes_real_tasks_and_matches_the_params_files():
    doc = json.loads((PROJECT / "docs" / "experiment.json").read_text(encoding="utf-8"))
    tasks = {ast.literal_eval(k) for k in literal("TASKS").keys}
    for t in doc["tasks"]:
        assert t["id"] in tasks
        params = yaml.safe_load((PROJECT / t["parameters_file"]).read_text(encoding="utf-8"))
        for p in t["parameters"]:
            value = params
            for part in p["name"].split("."):
                assert part in value, f"{p['name']} not in {t['parameters_file']}"
                value = value[part]
            if "default" in p:
                assert p["default"] == value, p["name"]


def test_every_assumption_is_in_the_methods_table_the_descriptor_and_the_yaml():
    doc = json.loads((PROJECT / "docs" / "experiment.json").read_text(encoding="utf-8"))
    methods = (PROJECT / "docs" / "methods.md").read_text(encoding="utf-8")
    assert "## Deviations from the original" in methods
    section = methods.split("## Assumed, not in the paper", 1)[1].split("\n## ", 1)[0]
    rows = [r for r in section.splitlines() if r.startswith("|") and not set(r) <= set("|-: ")]
    assert len(rows) - 1 == len(doc["assumed"]), "one table row per assumed item"
    for item in doc["assumed"]:
        assert item["value"] and item["reason"], item
        if item.get("key"):
            file = PROJECT / item.get("file", "configs/task.yaml")
            line = next((ln for ln in file.read_text(encoding="utf-8").splitlines()
                         if re.match(rf"\s*{re.escape(item['key'].split('.')[-1])}\s*:", ln)), "")
            assert "ASSUMED" in line, f"{item['key']} is not flagged ASSUMED in {file.name}"


def test_listing_states_status_hardware_and_the_original():
    listing = json.loads((PROJECT / "docs" / "listing.json").read_text(encoding="utf-8"))
    assert listing["status"] in {"original-protocol", "adaptation", "demo"}
    assert listing["original"]["citation"] and listing["original"]["year"]
    assert listing["hardware"]["display"] is True


def test_rig_files_load_and_name_only_events_the_task_declares():
    from alhazen.config.loader import load_rig
    from alhazen.session.builder import validate_event_names

    from britten1992.task import RdkDirectionTask

    for rig_file in (PROJECT / "configs").glob("rig-*.yaml"):
        rig = load_rig(rig_file)
        if rig.devices.sync is not None:
            validate_event_names(rig.devices.sync.event_lines, RdkDirectionTask.events,
                                 f"{rig_file.name} sync.event_lines")
        if rig.display.photodiode is not None:
            validate_event_names(rig.display.photodiode.events, RdkDirectionTask.events,
                                 f"{rig_file.name} photodiode.events")


def test_the_example_rigs_have_what_the_monkey_set_needs():
    from alhazen.config.loader import load_rig

    for name in ("rig-monkey-example.yaml", "rig-recording-example.yaml"):
        rig = load_rig(PROJECT / "configs" / name)
        assert rig.devices.eyetracker is not None and rig.devices.reward is not None
        assert "STIM_ON" in rig.devices.sync.event_lines
    assert load_rig(PROJECT / "configs" / "rig-recording-example.yaml").devices.recording


def load_run_py():
    import importlib.util

    spec = importlib.util.spec_from_file_location("britten_run", PROJECT / "run.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_every_training_stage_resolves():
    from alhazen.training.ladder import load_ladder, resolve_stage

    run = load_run_py()

    for label, path in run.LADDERS.items():
        for stage in load_ladder(path).stages:
            resolved = resolve_stage(path, stage.id, run.TASKS, ladder_label=label)
            assert resolved.params.subject_kind.value == "monkey"


def test_the_training_stages_build_their_trials():
    import numpy as np
    from alhazen.config.loader import build_session_config, load_params
    from alhazen.config.models import DisplayConfig, MonitorConfig, RigConfig, SessionInfo
    from alhazen.display.screen import Screen
    from alhazen.paradigms.base import Condition
    from alhazen.task.plan import TrialSetup
    from alhazen.testing import FakeClock, FakeDisplay

    from britten1992.training import RdkTrainingParams, RdkTrainingTask

    base = load_params(PROJECT / "configs" / "task-monkey.yaml", RdkTrainingParams)
    for stage, n_targets in (("fixate", 0), ("single-target", 1), ("single-target-dots", 1)):
        task = RdkTrainingTask(base.model_copy(update={"training_stage": stage}))
        monitor = MonitorConfig(width_px=1920, height_px=1080, width_cm=60.0, distance_cm=60.0,
                                refresh_rate_hz=60.0, fullscreen=False)
        setup = TrialSetup(
            cfg=build_session_config(
                RigConfig(monitor=monitor, display=DisplayConfig(backend="simulated"),
                          data_root="."),
                SessionInfo(subject="t", session=1, run=1, task_name=task.name, seed=1),
                task.params, {}),
            screen=Screen(1920, 1080, 40.0), display=FakeDisplay(FakeClock(), 1 / 60),
            rng=np.random.default_rng(0), refresh_rate_hz=60.0, trial_index=1, attempt=1,
            condition=Condition({"direction": "pref", "coherence_pct": 51.2,
                                 "correction": False}))
        plan = task.build_trial(setup)
        targets = [r for r in plan.regions if r.startswith("target_") and r != "target_correct"]
        assert len(targets) == n_targets, stage


def test_the_simulated_subjects_follow_the_papers_weibull():
    from britten1992.simulate import p_correct

    assert p_correct(0.0, 10.0, 1.2) == 0.5
    assert p_correct(10.0, 10.0, 1.2) == pytest.approx(1 - 0.5 * math.exp(-1))
    assert p_correct(100.0, 10.0, 1.2, lapse=0.02) == pytest.approx(0.99, abs=1e-3)
