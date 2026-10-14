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


# ---------------------------------------------------------------------------
# Beyond the template: every value in every params file says where it comes from.
# ---------------------------------------------------------------------------

SOURCES = ("# paper:", "# ASSUMED (not in the paper)", "# DEVIATION", "# alhazen")
VALUE_LINE = re.compile(r"^\s*-?\s*([A-Za-z_][\w]*|\d+)\s*:\s*(?!#)(\S.*)$")


def value_lines(path):
    for ln in path.read_text(encoding="utf-8").splitlines():
        if ln.lstrip().startswith("#"):
            continue
        m = VALUE_LINE.match(ln)
        if m:
            yield m.group(1), ln


def test_every_value_in_every_params_file_cites_the_paper_or_is_flagged():
    for path in sorted((PROJECT / "configs").glob("task*.yaml")):
        for key, ln in value_lines(path):
            assert any(s in ln for s in SOURCES), f"{path.name}: {key!r} has no source"


def test_every_assumed_line_is_documented_and_every_documented_key_is_flagged():
    doc = json.loads((PROJECT / "docs" / "experiment.json").read_text(encoding="utf-8"))
    documented = {i["key"].split(".")[-1] for i in doc["assumed"] if i.get("key")}
    for path in sorted((PROJECT / "configs").glob("task*.yaml")):
        for key, ln in value_lines(path):
            if "ASSUMED" in ln:
                assert key in documented, f"{path.name}: {key} ASSUMED but undocumented"
    for item in doc["assumed"]:
        if item.get("key"):
            assert item.get("file", "configs/task.yaml").startswith("configs/task")


def test_deviations_match_between_methods_and_descriptor():
    doc = json.loads((PROJECT / "docs" / "experiment.json").read_text(encoding="utf-8"))
    methods = (PROJECT / "docs" / "methods.md").read_text(encoding="utf-8")
    section = methods.split("## Deviations from the original", 1)[1].split("\n## ", 1)[0]
    rows = [r for r in section.splitlines() if r.startswith("|") and not set(r) <= set("|-: ")]
    assert len(rows) - 1 == len(doc["deviations"])


def test_the_parameter_sets_menu_names_every_task_file():
    text = (PROJECT / "run.py").read_text(encoding="utf-8")
    for path in (PROJECT / "configs").glob("task*.yaml"):
        assert f'"{path.name}"' in text, path.name


def test_the_listing_claims_no_participant_result():
    listing = json.loads((PROJECT / "docs" / "listing.json").read_text(encoding="utf-8"))
    assert listing["status"] == "original-protocol" and listing["status_reason"]
    assert listing["collection"] == "classics"
    assert all(listing["hardware"][k] is False for k in
               ("audio", "eye_tracker", "reward", "microstimulation", "recording"))
    methods = (PROJECT / "docs" / "methods.md").read_text(encoding="utf-8")
    assert "no participant data" in methods
