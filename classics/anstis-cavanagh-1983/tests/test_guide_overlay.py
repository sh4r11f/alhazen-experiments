"""The task guides: one per parameter set run.py names, generated from the code, accepted
by the pinned alhazen's guide builder, and drawing each set's own stimulus with the
paper's frame relationships (T3 = T1 half a cycle on, T2 a quarter cycle on, T4 = T2 half a
cycle on; counterphase states exchange the colours)."""

from __future__ import annotations

import ast
import json
import subprocess
import sys

import pytest
import yaml
from alhazen.experiment_platform.guides import build_guide
from conftest import PROJECT


def run_parameters() -> list[tuple[str, str]]:
    tree = ast.parse((PROJECT / "run.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "PARAMETERS":
            out = []
            for value in node.value.values:
                task = ast.literal_eval(value.elts[0])
                path = value.elts[1]
                out.append((task, "configs/" + ast.literal_eval(path.right)))
            return out
    raise AssertionError("run.py has no PARAMETERS")


OVERLAY = json.loads((PROJECT / "docs" / "guide-overlay.json").read_text(encoding="utf-8"))
DOC = json.loads((PROJECT / "docs" / "experiment.json").read_text(encoding="utf-8"))
BY_KEY = {t["taskKey"]: t for t in OVERLAY["tasks"]}


def test_the_overlay_is_generated_from_the_current_code():
    done = subprocess.run([sys.executable, str(PROJECT / "scripts" / "guide_overlay.py"),
                           "--check"], cwd=PROJECT, capture_output=True, text=True)
    assert done.returncode == 0, done.stdout + done.stderr


def test_every_named_parameter_set_has_a_descriptor_entry_and_a_guide():
    sets = {f"{task}@{file}" for task, file in run_parameters()}
    described = {f"{t['id']}@{t['parameters_file']}" for t in DOC["tasks"]}
    assert len(sets) == 7
    assert sets == described == set(BY_KEY)


def test_the_guide_builder_accepts_every_overlay_task():
    files = {p.relative_to(PROJECT).as_posix(): p.read_text(encoding="utf-8")
             for p in PROJECT.rglob("*")
             if p.is_file() and p.suffix in (".json", ".md", ".yaml")
             and not {".venv", "data", "__pycache__"} & set(p.parts)}
    listing = {"id": "anstis-cavanagh-1983", "version": "0.1.0", "title": "t",
               "bundle": {"id": "b1"}, "source": {}}
    guide = build_guide(listing, {"methods": files["docs/methods.md"]}, files,
                        overlay={"bundleId": "b1", "json": json.dumps(OVERLAY)})
    assert not guide.get("warnings")
    drawn = {t["taskKey"] for t in guide["tasks"] if t.get("diagram") and t.get("timeline")}
    assert drawn == set(BY_KEY)


def strokes(task: dict) -> list[list[tuple[float, float, str]]]:
    """Per stroke panel: (left, right, colour) of each bar, relative to the panel's left
    edge, read from the drawn rects (panels are the T<k> labels' left edges)."""
    els = task["diagram"]["elements"]
    lefts = sorted(e["x"] for e in els if e["type"] == "text" and e["text"].startswith("T"))
    dim = next(e for e in els if e["type"] == "dimension")
    size = dim["x2"] - dim["x1"]
    out = []
    for left in lefts:
        half = [(e, e["width"] / 2) for e in els if e["type"] == "rect"]
        bars = [(round(e["cx"] - h - left, 3), round(e["cx"] + h - left, 3), e["color"])
                for e, h in half if e["height"] == size
                and left - 1e-6 <= e["cx"] <= left + size + 1e-6]
        out.append(sorted(bars))
    return out


def colour_at(bars, u):
    return next(c for a, b, c in bars if a <= u < b)


def samples(bars):
    edges = sorted({a for a, _, _ in bars} | {b for _, b, _ in bars})
    return [(x + y) / 2 for x, y in zip(edges, edges[1:], strict=False)]


FOUR = [k for k in BY_KEY if not k.startswith("min-flicker-adjust")]


@pytest.mark.parametrize("key", FOUR)
def test_four_stroke_guides_keep_the_papers_phase_relations(key):
    t1, t2, t3, t4 = strokes(BY_KEY[key])
    for u in samples(t1) + samples(t3):
        assert colour_at(t1, u) != colour_at(t3, u)  # colours exchanged everywhere
    assert {c for *_, c in t1} == {c for *_, c in t3}
    for u in samples(t2) + samples(t4):
        assert colour_at(t2, u) != colour_at(t4, u)  # light and dark exchanged
    bar = sorted(b - a for a, b, _ in t1)[len(t1) // 2]  # an interior bar = half a cycle
    ticks = sorted(e["x1"] for e in BY_KEY[key]["diagram"]["elements"]
                   if e["type"] == "line" and e.get("color") == "#7f1d1d")
    steps = [round(b - a, 3) for a, b in zip(ticks, ticks[1:], strict=False)]
    lefts = sorted(e["x"] for e in BY_KEY[key]["diagram"]["elements"]
                   if e["type"] == "text" and e["text"].startswith("T"))
    shifts = [round((tk - lf) - (ticks[0] - lefts[0]), 3)
              for tk, lf in zip(ticks, lefts, strict=True)]
    assert shifts == [round(k * bar / 2, 3) for k in range(4)]  # a quarter cycle per stroke
    assert len(steps) == 3
    for k, (panel, tick, left) in enumerate(zip((t1, t2, t3, t4), ticks, lefts, strict=True)):
        u = round(tick - left, 3)
        before, after = colour_at(panel, (u - 0.01) % (bar * 2)), colour_at(panel, u + 0.01)
        assert before != after  # the tick sits on a bar edge
        if k % 2:  # mixture strokes: the tick opens a light bar
            assert sum(int(after[i:i + 2], 16) for i in (1, 3, 5)) > \
                sum(int(before[i:i + 2], 16) for i in (1, 3, 5))


@pytest.mark.parametrize("key", list(BY_KEY))
def test_each_guide_shows_its_own_files_values(key):
    task, file = key.split("@")
    p = yaml.safe_load((PROJECT / file).read_text(encoding="utf-8"))
    caption = BY_KEY[key]["diagram"]["caption"]
    assert f"{p['reference_cd_m2']:g}" in caption
    labels = " ".join(e["text"] for e in BY_KEY[key]["diagram"]["elements"]
                      if e["type"] == "text")
    test = p.get("test_colour") or p["test_colours"][0]
    assert test in labels and p["reference_colour"] in labels
    assert "uncalibrated" in caption
    assert "measured photometry" in BY_KEY[key]["description"]


def test_counterphase_flicker_guide_exchanges_colours():
    a, b = strokes(BY_KEY["min-flicker-adjust@configs/flicker-grating.yaml"])
    for u in samples(a) + samples(b):
        assert colour_at(a, u) != colour_at(b, u)
