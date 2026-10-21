"""The photograph pairs: assets, balance, design and a simulated photograph session."""

from __future__ import annotations

import json
from collections import Counter

import numpy as np
import pandas as pd
import pytest
import yaml
from alhazen.config.loader import load_params
from conftest import PROJECT, run_simulated
from PIL import Image

from depthcb import photos, scenes
from depthcb.task import DepthCuedFlickerTaskParams, design, scene_spec

PAIRS = photos.catalogue()


def test_every_pair_is_on_disk_and_differs_only_around_its_change():
    assert len(PAIRS) == 54
    for p in PAIRS.values():
        a = np.asarray(Image.open(photos.PHOTOS / p["image_a"]).convert("RGB")).astype(int)
        b = np.asarray(Image.open(photos.PHOTOS / p["image_b"]).convert("RGB")).astype(int)
        assert a.shape == b.shape == (800, 1200, 3), p["id"]
        diff = np.abs(a - b).max(-1) > 24
        x0, y0, x1, y1 = p["bbox"]
        inside = np.zeros_like(diff)
        inside[max(0, int(y0 * 800) - 4):int(y1 * 800) + 4,
               max(0, int(x0 * 1200) - 4):int(x1 * 1200) + 4] = True
        assert diff[~inside].mean() < 0.002, p["id"]  # JPEG noise only, outside the change
        assert 3.0 <= p["eccentricity_dva"] <= 11.0, p["id"]


def test_the_sets_are_balanced_and_every_setting_has_a_near_and_a_far_change():
    for photo_set, per_cell in (("main", 8), ("practice", 1)):
        assert set(photos.cell_counts(photo_set).values()) == {per_cell}
        assert len(photos.cell_counts(photo_set)) == 6
    by_setting = Counter((p["setting"], p["plane"]) for p in PAIRS.values())
    assert set(by_setting.values()) == {1}
    assert len({s for s, _ in by_setting}) == 27
    main = {p["setting"] for p in PAIRS.values() if p["set"] == "main"}
    practice = {p["setting"] for p in PAIRS.values() if p["set"] == "practice"}
    assert not main & practice


def test_each_pair_has_foils_on_both_planes():
    for p in PAIRS.values():
        planes = Counter(f["plane"] for f in p["foils"])
        assert planes["near"] >= 2 and planes["far"] >= 2, p["id"]


def test_the_photo_design_shows_each_pair_once_with_cues_drawn_per_session():
    p = load_params(PROJECT / "configs" / "task-photos.yaml", DepthCuedFlickerTaskParams)
    d1 = design(p, np.random.default_rng(1))
    d2 = design(p, np.random.default_rng(2))
    assert len(d1) == 48 and len({t["scene"] for t in d1}) == 48
    assert Counter(t["cue"] for t in d1) == {"valid": 36, "invalid": 12}
    assert {t["scene"]: t["cue"] for t in d1} != {t["scene"]: t["cue"] for t in d2}


def test_cue_counts_must_match_the_photo_set():
    raw = yaml.safe_load((PROJECT / "configs" / "task-photos.yaml").read_text(encoding="utf-8"))
    raw["cue_counts"] = {"valid": 12, "invalid": 4, "neutral": 0, "none": 0}
    with pytest.raises(ValueError, match="cue_counts"):
        DepthCuedFlickerTaskParams.model_validate(raw)


def test_photo_probe_boxes_put_two_on_each_plane_and_one_on_the_change():
    p = load_params(PROJECT / "configs" / "task-photos.yaml", DepthCuedFlickerTaskParams)
    spec = scene_spec(p)
    rng = np.random.default_rng(0)
    for pid in PAIRS:
        pair = photos.load_pair(photos.scene_id(pid), spec)
        boxes, correct, planes = scenes.probe_boxes(pair, 4, 3.6, spec, rng)
        assert len(boxes) == 4 and sorted(planes) == ["far", "far", "near", "near"], pid
        cx, cy = pair.centroid
        b = boxes[correct]
        assert b[0] <= cx <= b[2] and b[1] <= cy <= b[3], pid


def test_a_simulated_photograph_session_runs(tmp_path):
    raw = yaml.safe_load((PROJECT / "configs" / "task-photos-practice.yaml").read_text())
    raw.update({"cue_field": {"ms": 200}, "gray_field": {"ms": 100}, "max_flicker": {"ms": 2500},
                "iti": {"ms": 50}})
    raw["flicker"].update({"image": {"frames": 3}, "blank": {"frames": 1}})
    fast = tmp_path / "task-fast-photos.yaml"
    fast.write_text(yaml.safe_dump(raw), encoding="utf-8")
    done = run_simulated(tmp_path, params=fast)
    assert done.returncode == 0, done.stdout[-3000:] + done.stderr[-3000:]
    df = pd.read_csv(next(tmp_path.rglob("*_trials.csv")))
    assert len(df) == 6 and set(df["stimulus_source"]) == {"photo"}
    assert df["scene"].str.startswith("photo/").all()
    assert set(df["fixation_on_gray"]) == {True}
    json.loads(df["probe_boxes"].iloc[0])
