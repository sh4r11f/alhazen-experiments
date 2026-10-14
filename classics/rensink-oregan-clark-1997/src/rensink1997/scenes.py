"""The scene pairs a session shows, and the location probe drawn over them.

Two sources, one shape (``ScenePair``):

- ``photo/<id>``: the 12 photograph pairs shipped in ``photos/`` (made by
  scripts/build_photo_pairs.py from generated photographs; interest labels from
  scripts/rate_interest.py, the paper's five-describer rule applied to model describers).
- ``proc/<seed>/<change_type>/<interest>``: a procedural pair (``procedural.generate``),
  made from its id whenever it is needed, so a session can run on any number of them.

A scene id is a plain string so it can be a scheduler condition and a trials-table column.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image

from rensink1997 import procedural

PHOTOS = Path(__file__).resolve().parent / "photos"
CHANGE_TYPES = ("presence", "color", "location")
INTERESTS = ("central", "marginal")


@dataclass(frozen=True)
class ScenePair:
    scene: str
    source: str  # "photo" | "procedural"
    change_type: str
    interest: str  # "central" | "marginal" | "intermediate"
    interest_source: str
    object: str
    cue_valid: str
    cue_invalid: str
    bbox: tuple[float, float, float, float]  # of the change, in image fractions (x0, y0, x1, y1)
    centroid: tuple[float, float]
    area_fraction: float
    image_a: Image.Image
    image_b: Image.Image

    def area_dva2(self, width_dva: float, height_dva: float) -> float:
        return self.area_fraction * width_dva * height_dva


@lru_cache(maxsize=1)
def photo_table() -> dict[str, dict]:
    pairs = json.loads((PHOTOS / "pairs.json").read_text(encoding="utf-8"))["pairs"]
    ratings = json.loads((PHOTOS / "interest_ratings.json").read_text(encoding="utf-8"))
    out = {}
    for p in pairs:
        r = ratings["scenes"][p["id"]]
        out[p["id"]] = {**p, "interest": r["label"], "n_mentioning": r["n_mentioning"],
                        "interest_source": f"{r['n_mentioning']}/{len(r['mentioned'])} model "
                                           f"describers mentioned it (paper's rule, p. 369)"}
    return out


def photo_ids() -> list[str]:
    return sorted(photo_table())


def procedural_id(seed: int, change_type: str, interest: str) -> str:
    return f"proc/{seed}/{change_type}/{interest}"


def procedural_ids(per_cell: int, seed: int) -> list[str]:
    """``per_cell`` pairs for every change type x interest cell, seeds ``seed``, ``seed+1``..."""
    out, k = [], 0
    for change_type in CHANGE_TYPES:
        for interest in INTERESTS:
            for _ in range(per_cell):
                out.append(procedural_id(seed + k, change_type, interest))
                k += 1
    return out


def load(scene: str, area_dva2: dict[str, float] | None = None,
         shift_dva: float = 3.0) -> ScenePair:
    kind, _, rest = scene.partition("/")
    if kind == "photo":
        p = photo_table()[rest]
        return ScenePair(scene, "photo", p["change_type"], p["interest"], p["interest_source"],
                         p["object"], p["cue_valid"], p["cue_invalid"], tuple(p["bbox"]),
                         tuple(p["centroid"]), float(p["area_fraction"]),
                         Image.open(PHOTOS / p["image_a"]).convert("RGB"),
                         Image.open(PHOTOS / p["image_b"]).convert("RGB"))
    if kind == "proc":
        seed, change_type, interest = rest.split("/")
        areas = area_dva2 or {"central": 18.0, "marginal": 22.0}
        a, b, m = procedural.generate(int(seed), change_type, interest, areas[interest], shift_dva)
        return ScenePair(scene, "procedural", change_type, interest,
                         "placement rule: central = the focal object, marginal = a background "
                         "object near an edge (ASSUMED stand-in for rated interest)",
                         m["object"], m["cue_valid"], m["cue_invalid"], tuple(m["bbox"]),
                         tuple(m["centroid"]), float(m["area_fraction"]), a, b)
    raise ValueError(f"unknown scene id {scene!r}")


def probe_boxes(pair: ScenePair, n: int, side_range: tuple[float, float],
                aspect: float, rng: np.random.Generator,
                tries: int = 4000) -> tuple[list[tuple[float, float, float, float]], int]:
    """``n`` same-size boxes on the image (fractions), one around the change, the others
    elsewhere and not overlapping it or each other; returns (boxes in reading order, index
    of the correct one).

    The box size is the change's bounding box clamped to ``side_range`` (in image-width
    fractions; heights scaled by ``aspect`` = width / height of the image), centred on the
    change's centroid, so a large change and a small one get boxes a subject can tell apart.
    Fewer than ``n`` boxes come back only when the image cannot hold ``n``.
    """
    lo, hi = side_range
    x0, y0, x1, y1 = pair.bbox
    bw = float(np.clip(x1 - x0, lo, hi))
    bh = float(np.clip((y1 - y0), lo * aspect, hi * aspect))
    cx, cy = pair.centroid
    true = (float(np.clip(cx - bw / 2, 0, 1 - bw)), float(np.clip(cy - bh / 2, 0, 1 - bh)))
    boxes = [(true[0], true[1], true[0] + bw, true[1] + bh)]

    def clear(b):
        return all(b[2] <= o[0] or o[2] <= b[0] or b[3] <= o[1] or o[3] <= b[1] for o in boxes)

    for _ in range(tries):
        if len(boxes) >= n:
            break
        fx, fy = rng.uniform(0, 1 - bw), rng.uniform(0, 1 - bh)
        cand = (float(fx), float(fy), float(fx + bw), float(fy + bh))
        if clear(cand):
            boxes.append(cand)
    correct = boxes[0]
    ordered = sorted(boxes, key=lambda b: (round(b[1] * 3), b[0]))  # rows of thirds, then x
    return ordered, ordered.index(correct)
