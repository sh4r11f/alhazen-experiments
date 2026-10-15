"""The documentation is honest about where every value comes from, and matches the code."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    import tomli as tomllib

PROJECT = Path(__file__).resolve().parents[1]
TASK_FILES = ["configs/task.yaml", "configs/task-fixed-set.yaml"]
# Lines that carry structure, not a value a paper could state.
STRUCTURAL = {"subject_kind", "practice", "paradigm", "kind"}


def key_lines(rel):
    for line in (PROJECT / rel).read_text(encoding="utf-8").splitlines():
        m = re.match(r"\s*([a-z_]+)\s*:", line)
        if m and not line.lstrip().startswith("#"):
            yield m.group(1), line


@pytest.mark.parametrize("rel", TASK_FILES)
def test_every_value_says_whether_the_paper_states_it(rel):
    for key, line in key_lines(rel):
        if key in STRUCTURAL:
            continue
        assert "# paper:" in line or "# ASSUMED (not in the paper):" in line, line


@pytest.mark.parametrize("rel", TASK_FILES)
def test_every_flagged_value_is_in_the_assumed_list(rel):
    doc = json.loads((PROJECT / "docs" / "experiment.json").read_text(encoding="utf-8"))
    leaves = {item["key"].split(".")[-1] for item in doc["assumed"] if item.get("key")}
    for key, line in key_lines(rel):
        if "ASSUMED" in line:
            assert key in leaves, f"{key} is flagged ASSUMED in {rel} but not listed"


def test_the_deviations_table_matches_the_descriptor():
    doc = json.loads((PROJECT / "docs" / "experiment.json").read_text(encoding="utf-8"))
    methods = (PROJECT / "docs" / "methods.md").read_text(encoding="utf-8")
    section = methods.split("## Deviations from the original", 1)[1].split("\n## ", 1)[0]
    rows = [r for r in section.splitlines() if r.startswith("|") and not set(r) <= set("|-: ")]
    assert len(rows) - 1 == len(doc["deviations"]) > 0
    for d in doc["deviations"]:
        assert d["item"] in section


def test_unkeyed_assumptions_name_a_file_that_exists():
    doc = json.loads((PROJECT / "docs" / "experiment.json").read_text(encoding="utf-8"))
    for item in doc["assumed"]:
        assert (PROJECT / item.get("file", "configs/task.yaml")).is_file(), item


def test_the_listing_is_honest():
    listing = json.loads((PROJECT / "docs" / "listing.json").read_text(encoding="utf-8"))
    assert listing["status"] == "original-protocol" and listing["collection"] == "classics"
    hw = listing["hardware"]
    assert hw["display"] and hw["keyboard"]
    assert not any(hw[k] for k in ("audio", "eye_tracker", "reward", "microstimulation",
                                   "recording", "mouse"))
    assert listing["original"]["year"] == 1966
    assert "no participant data" in listing["status_reason"].lower()


def test_every_task_has_an_entry_point_and_a_parameter_set():
    py = tomllib.loads((PROJECT / "pyproject.toml").read_text(encoding="utf-8"))
    entry = py["project"]["entry-points"]["alhazen.tasks"]
    run = (PROJECT / "run.py").read_text(encoding="utf-8")
    for task in ("memory-scanning", "memory-scanning-fixed"):
        assert task in entry and f'"{task}"' in run


def test_the_preview_is_drawn_from_the_params(tmp_path):
    from sternberg1966.preview import render

    out = render(tmp_path / "p.png")
    assert out.stat().st_size < 400_000
    shipped = PROJECT / "docs" / "preview.png"
    assert shipped.is_file() and shipped.stat().st_size < 400_000
