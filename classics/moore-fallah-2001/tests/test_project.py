"""The folder is a standalone alhazen project and its documentation matches its code."""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

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


def test_every_parameter_set_flags_the_same_assumptions():
    """The three parameter sets share their assumed values, and each says so on the line."""
    doc = json.loads((PROJECT / "docs" / "experiment.json").read_text(encoding="utf-8"))
    for path in sorted((PROJECT / "configs").glob("task*.yaml")):
        lines = path.read_text(encoding="utf-8").splitlines()
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        for item in doc["assumed"]:
            key = item.get("key")
            if not key:
                continue
            value = data
            for part in key.split("."):
                value = value.get(part) if isinstance(value, dict) else None
            if value is None:
                continue  # not in this file (the reward block is the monkey files')
            leaf = key.split(".")[-1]
            hit = [ln for ln in lines if re.match(rf"\s*{re.escape(leaf)}\s*:", ln)]
            assert hit and all("ASSUMED" in ln for ln in hit), f"{key} not flagged in {path.name}"


def test_every_unflagged_value_cites_the_paper_or_is_structure():
    """A task-YAML line with a scalar value says where it comes from."""
    allowed = {"subject_kind", "target_field", "enabled", "current_ua", "movement_threshold_ua"}
    for path in sorted((PROJECT / "configs").glob("task*.yaml")):
        for ln in path.read_text(encoding="utf-8").splitlines():
            m = re.match(r"\s*([A-Za-z_]+)\s*:\s*(\S.*)$", ln)
            if not m or ln.lstrip().startswith("#") or m.group(2).startswith("#"):
                continue
            if m.group(1) in allowed:
                continue
            assert "# paper:" in ln or "# ASSUMED" in ln or "# entered by the lab" in ln, (
                f"{path.name}: {ln.strip()!r} says neither paper nor ASSUMED")


def test_the_example_rigs_load_and_map_the_stimulation_trigger():
    from alhazen.config.loader import load_rig

    rig = load_rig(PROJECT / "configs" / "rig-lab-example.yaml")
    assert rig.devices.sync.event_lines["STIM_TRIGGER"]
    assert rig.devices.reward is not None and rig.devices.eyetracker is not None
    assert load_rig(PROJECT / "configs" / "rig-booth.yaml").devices.eyetracker is not None


def test_the_licence_block_is_the_repositorys():
    doc = json.loads((PROJECT / "docs" / "experiment.json").read_text(encoding="utf-8"))
    assert doc["license"] == {"code": "Apache-2.0", "docs": "CC-BY-4.0", "assets": "CC-BY-4.0"}
