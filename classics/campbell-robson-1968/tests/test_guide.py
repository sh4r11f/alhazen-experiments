"""The committed guide overlay is what the builder makes from the parameter files, and its
drawing is a sampled sine on the paper's square field."""

from __future__ import annotations

import json
import math

from campbell_robson1968 import guide
from campbell_robson1968.common import PROJECT


def test_overlay_is_current():
    committed = json.loads((PROJECT / "docs" / "guide-overlay.json").read_text(encoding="utf-8"))
    assert committed == json.loads(json.dumps(guide.overlay()))


def test_diagram_strips_follow_the_task_formula():
    d = guide.diagram("configs/task.yaml", fixation=True)
    strips = [e for e in d["elements"] if e["type"] == "rect" and "luminance" in e]
    assert len(strips) == 10 * guide.STRIPS_PER_CYCLE and len(d["elements"]) <= 200
    assert len({s["luminance"] for s in strips}) > 4  # graded, not two levels
    for s in strips:
        expect = d["background"] * (1 + guide.EXAMPLE_CONTRAST * math.cos(2 * math.pi * s["cx"]))
        assert abs(s["luminance"] - expect) < 1e-3
    assert not any(e["type"] == "grating" for e in d["elements"])


def test_overlay_tasks_match_the_descriptor():
    doc = json.loads((PROJECT / "docs" / "experiment.json").read_text(encoding="utf-8"))
    keys = {f"{t['id']}@{t['parameters_file']}" for t in doc["tasks"]}
    assert {t["taskKey"] for t in guide.overlay()["tasks"]} == keys
