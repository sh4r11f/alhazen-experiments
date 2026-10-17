"""The scenes, the design and the parameter sets, without running a session."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest
from alhazen.config.loader import load_params
from PIL import ImageChops

from depthcb import scenes
from depthcb.task import DepthCuedFlickerTaskParams, cue_word, design, scene_spec

PROJECT = Path(__file__).resolve().parents[1]
CONFIGS = sorted((PROJECT / "configs").glob("task*.yaml"))


@pytest.mark.parametrize("cfg", CONFIGS, ids=lambda p: p.stem)
def test_every_parameter_set_loads_and_balances_its_cells(cfg):
    p = load_params(cfg, DepthCuedFlickerTaskParams)
    d = design(p)
    assert len({t["scene"] for t in d}) == len(d)
    cells = {}
    for t in d:
        _, plane, ct = scenes.parse_id(t["scene"])
        cells.setdefault((plane, ct), []).append(t["cue"])
    assert len(cells) == 6
    assert len({tuple(sorted(v)) for v in cells.values()}) == 1


def test_main_set_is_96_trials_75_percent_valid():
    p = load_params(PROJECT / "configs" / "task.yaml", DepthCuedFlickerTaskParams)
    cues = [t["cue"] for t in design(p)]
    assert len(cues) == 96 and cues.count("valid") == 72 and cues.count("invalid") == 24


def test_practice_and_main_scenes_never_overlap():
    seeds = {}
    for name in ("task", "task-practice"):
        p = load_params(PROJECT / "configs" / f"{name}.yaml", DepthCuedFlickerTaskParams)
        seeds[name] = {scenes.parse_id(t["scene"])[0] for t in design(p)}
    assert not seeds["task"] & seeds["task-practice"]


def test_cue_words_name_the_right_plane():
    p = load_params(PROJECT / "configs" / "task.yaml", DepthCuedFlickerTaskParams)
    assert cue_word(p, "near", "valid") == ("NEAR", "near")
    assert cue_word(p, "near", "invalid") == ("FAR", "far")
    assert cue_word(p, "far", "invalid") == ("NEAR", "near")
    assert cue_word(p, "far", "neutral") == ("NEAR OR FAR", "neutral")


@pytest.mark.parametrize("plane", scenes.PLANES)
@pytest.mark.parametrize("change_type", scenes.CHANGE_TYPES)
def test_a_pair_differs_only_at_the_change_on_the_named_plane(plane, change_type):
    spec = scenes.SceneSpec()
    pair = scenes.generate(31, plane, change_type, spec)
    assert pair.plane == plane and pair.change_type == change_type
    t = pair.objects[pair.target_index]
    assert t["plane"] == plane and t["primary"]
    lo, hi = spec.target_eccentricity_dva
    assert lo <= pair.eccentricity_dva <= hi
    diff = np.asarray(ImageChops.difference(pair.image_a, pair.image_b).convert("L")) > 12
    ys, xs = np.nonzero(diff)
    w, h = pair.image_a.size
    # the difference lies within the target's reach (its size, a move, a near shadow)
    reach = (t["size"] + spec.location_shift_dva + spec.shadow_offset_dva + 1.0) / spec.width_dva
    cx, cy = pair.centroid
    assert np.all(np.abs(xs / w - cx) <= reach)
    assert np.all(np.abs(ys / h - cy) * spec.height_dva / spec.width_dva <= reach)
    if change_type == "color":
        assert pair.color_a != pair.color_b
    if change_type == "presence":
        assert pair.present_in in ("A", "B")


def test_pairs_are_reproducible_from_their_id():
    a = scenes.generate(77, "far", "location")
    b = scenes.generate(77, "far", "location")
    assert a.image_a.tobytes() == b.image_a.tobytes()
    assert a.image_b.tobytes() == b.image_b.tobytes()


def test_planes_are_interleaved_over_the_picture():
    pair = scenes.generate(5, "near", "color")
    prim = [o for o in pair.objects if o["primary"]]
    for qx in (0, 1):
        for qy in (0, 1):
            quad = [o["plane"] for o in prim
                    if (o["x"] >= 0.5) == bool(qx) and (o["y"] >= 0.5) == bool(qy)]
            assert sorted(quad) == ["far", "far", "near", "near"]


def test_near_objects_occlude_some_far_ones_and_far_ones_are_smaller():
    pair = scenes.generate(8, "far", "presence")
    hidden = [o for o in pair.objects if not o["primary"]]
    assert hidden and all(o["plane"] == "far" for o in hidden)
    sizes = {o["plane"]: o["size"] for o in pair.objects if o["primary"]}
    assert sizes["far"] < sizes["near"]


def test_switching_cues_off_removes_them():
    flat = scenes.SceneSpec(cues=scenes.DepthCueSet(relative_size=False, occlusion=False))
    pair = scenes.generate(8, "far", "presence", flat)
    assert all(o["primary"] for o in pair.objects)
    assert len({o["size"] for o in pair.objects}) == 1


def test_probe_boxes_are_half_near_half_far_and_hold_the_change():
    spec = scenes.SceneSpec()
    for seed in range(6):
        pair = scenes.generate(seed, "far" if seed % 2 else "near", "location", spec)
        boxes, k, planes = scenes.probe_boxes(pair, 4, 3.6, spec, np.random.default_rng(seed))
        assert sorted(planes) == ["far", "far", "near", "near"]
        x0, y0, x1, y1 = boxes[k]
        cx, cy = pair.centroid
        assert x0 <= cx <= x1 and y0 <= cy <= y1
        for i, a in enumerate(boxes):
            for b in boxes[i + 1:]:
                assert a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1]


def test_the_size_matched_set_draws_equal_planes():
    p = load_params(PROJECT / "configs" / "task-matched-size.yaml", DepthCuedFlickerTaskParams)
    pair = scenes.generate(3, "near", "color", scene_spec(p))
    assert len({o["size"] for o in pair.objects}) == 1
    assert math.isclose(p.scene.far_size_dva, p.scene.near_size_dva)
