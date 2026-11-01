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


def test_far_set_draws_its_own_2_deg_field_at_an_example_high_frequency():
    d = guide.diagram("configs/task-far.yaml", fixation=True, sf=4.0)
    strips = [e for e in d["elements"] if e["type"] == "rect" and "luminance" in e]
    assert len(strips) == 2 * 4 * guide.STRIPS_PER_CYCLE  # 2 deg x 4 c/deg
    assert abs(sum(s["width"] for s in strips) - 2.0) < 1e-2
    assert d["width"] < 7  # the 2 deg field and its marks, not the main set's 10 deg
    for s in strips:
        wave = math.cos(2 * math.pi * 4.0 * s["cx"])
        expect = d["background"] * (1 + guide.EXAMPLE_CONTRAST * wave)
        assert abs(s["luminance"] - expect) < 1e-3


def test_sine_square_set_draws_a_two_level_square_wave_about_the_mean():
    d = guide.diagram("configs/sine-square.yaml", fixation=True, waveform="square")
    lums = {s["luminance"] for s in d["elements"] if s["type"] == "rect" and "luminance" in s}
    m = d["background"]
    assert len(lums) == 2
    lo, hi = sorted(lums)
    assert abs(hi - m * 1.6) < 1e-3 and abs(lo - m * 0.4) < 1e-3


def test_every_parameter_set_has_its_own_guide_entry():
    import ast

    tree = ast.parse((PROJECT / "run.py").read_text(encoding="utf-8"))
    sets = next(n.value for n in tree.body if isinstance(n, ast.Assign)
                and getattr(n.targets[0], "id", "") == "PARAMETERS")
    wanted = set()
    for v in sets.values:
        task = v.elts[0].value
        path = v.elts[1].right.value
        wanted.add(f"{task}@configs/{path}")
    assert {t["taskKey"] for t in guide.overlay()["tasks"]} == wanted
