"""Photograph scene pairs for the depth-cued flicker task.

Each pair is a photograph of a real-looking place with two separate depths, a NEAR layer
within arm's reach of the camera and a FAR layer 10 to 30 m away, and one change (presence,
colour or location) to ONE object on ONE of the two layers. The pairs are built by
``scripts/build_photo_pairs.py`` from generated photographs (prompts in
``photos/spec.json``) and listed in ``photos/pairs.json``, which records for every pair
its plane, change type, the changed object, the geometry of the change measured from
|A - A'|, and the positions of other named objects on each layer (the foils of the
location report). The images ship with the experiment (CC BY 4.0).

A photograph's scene id is ``photo/<pair id>``.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from PIL import Image

from depthcb import scenes

PHOTOS = Path(__file__).resolve().parent / "photos"
PREFIX = "photo/"


@dataclass(frozen=True)
class PhotoPair:
    """The same fields as scenes.DepthPair, so the task and probe_boxes treat both alike."""

    scene: str
    seed: int
    plane: str
    change_type: str
    shape: str
    object_name: str
    color_a: str
    color_b: str
    present_in: str
    eccentricity_dva: float
    centroid: tuple[float, float]
    bbox: tuple[float, float, float, float]
    changed_area_dva2: float
    objects: list[dict]
    target_index: int
    image_a: Image.Image
    image_b: Image.Image


@lru_cache(maxsize=1)
def catalogue() -> dict[str, dict]:
    """pairs.json by pair id; empty when no photographs are installed."""
    path = PHOTOS / "pairs.json"
    if not path.exists():
        return {}
    return {p["id"]: p for p in json.loads(path.read_text(encoding="utf-8"))["pairs"]}


def is_photo(scene_id: str) -> bool:
    return scene_id.startswith(PREFIX)


def scene_id(pair_id: str) -> str:
    return PREFIX + pair_id


def pair_ids(photo_set: str, plane: str, change_type: str) -> list[str]:
    ids = sorted(k for k, p in catalogue().items()
                 if (p["set"], p["plane"], p["change_type"]) == (photo_set, plane, change_type))
    if not ids:
        raise FileNotFoundError(
            f"no {photo_set} photograph pairs for {plane}/{change_type} in {PHOTOS / 'pairs.json'}")
    return ids


def cell_counts(photo_set: str) -> dict[tuple[str, str], int]:
    out: dict[tuple[str, str], int] = {}
    for p in catalogue().values():
        if p["set"] == photo_set:
            key = (p["plane"], p["change_type"])
            out[key] = out.get(key, 0) + 1
    return out


def load_pair(sid: str, spec: scenes.SceneSpec) -> PhotoPair:
    """The pair for ``photo/<id>``, with geometry in image fractions and dva."""
    pid = sid[len(PREFIX):] if is_photo(sid) else sid
    rec = catalogue()[pid]
    a = Image.open(PHOTOS / rec["image_a"]).convert("RGB")
    b = Image.open(PHOTOS / rec["image_b"]).convert("RGB")
    cx, cy = rec["centroid"]
    ecc = math.hypot((cx - 0.5) * spec.width_dva, (cy - 0.5) * spec.height_dva)
    target = {"plane": rec["plane"], "primary": True, "x": cx, "y": cy, "name": rec["object"]}
    foils = [{"plane": o["plane"], "primary": True, "x": o["x"], "y": o["y"], "name": o["name"]}
             for o in rec["foils"]]
    color_a, color_b = ("blue", "red") if rec["change_type"] == "color" else ("", "")
    return PhotoPair(
        scene=scene_id(pid), seed=-1, plane=rec["plane"], change_type=rec["change_type"],
        shape=rec["object"], object_name=rec["object"], color_a=color_a, color_b=color_b,
        present_in="A" if rec["change_type"] == "presence" else "both",
        eccentricity_dva=round(ecc, 3), centroid=(cx, cy), bbox=tuple(rec["bbox"]),
        changed_area_dva2=round(rec["area_fraction"] * spec.width_dva * spec.height_dva, 3),
        objects=[target] + foils, target_index=0, image_a=a, image_b=b)
