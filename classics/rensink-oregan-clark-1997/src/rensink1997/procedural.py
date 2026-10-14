"""Procedural scene pairs: unlimited A / A' images with exactly one change, from a seed.

A scene is a small outdoor view (sky, clouds, hills, ground) with background objects
(houses, trees, bushes, signs) along the horizon and one larger FOCAL object near the
centre of the foreground. One object changes between A and A':

- presence: the object is in A and absent from A';
- color:    the object's painted body is blue in A and red in A' (the paper's example of a
            colour change is "switch its color between blue and red", p. 369);
- location: the object is shifted ``shift_dva`` sideways in A' (p. 369: "shift its
            position by a few degrees"; Fig. 2 gives 3 deg).

Which object changes stands in for the paper's "interest": ``central`` changes the focal
object, ``marginal`` a background object near the left or right edge. That is a
placement rule, not the paper's rated interest (five describers, p. 369); it is listed
as ASSUMED in docs/methods.md. The changed area is set to ``area_dva2`` (the paper's
average change areas were 18 sq deg for central and 22 sq deg for marginal interests,
p. 369): the object's footprint for presence and location, its painted body for color.

The image is ``W`` x ``H`` pixels standing for 27 x 18 deg (the paper's image size), so
areas and shifts are in the image's own degrees whatever screen shows it. Both images
are rendered from one scene description with no randomness after it, then share one
noise texture, so they differ only where the changed object is.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

W, H = 1024, 683
WIDTH_DVA = 27.0
PPD = W / WIDTH_DVA  # pixels per degree of the image itself
BLUE = (45, 85, 190)
RED = (190, 45, 40)
PAINTABLE = ("house", "car", "sign")
ANY_KIND = ("house", "car", "tree", "bush", "sign")
WALLS = [(222, 205, 170), (200, 190, 180), (235, 225, 200), (190, 170, 150), (215, 200, 200)]
CARS = [(120, 120, 125), (230, 230, 225), (60, 60, 65), (150, 140, 100)]


@dataclass
class Obj:
    kind: str
    cx: float
    yb: float  # y of the base (ground contact), px
    s: float  # scale
    body: tuple[int, int, int]
    extra: dict = field(default_factory=dict)


def _parts(o: Obj):
    """(shape, coords, role, colour) in draw order. role 'body' is the painted part."""
    s, cx, yb = o.s, o.cx, o.yb
    if o.kind == "house":
        w, h = 110 * s, 78 * s
        x0, y0 = cx - w / 2, yb - h
        roof = o.extra.get("roof", (120, 50, 40))
        yield "rect", (x0, y0, x0 + w, yb), "body", o.body
        yield "poly", [(x0 - 8 * s, y0), (cx, y0 - 42 * s), (x0 + w + 8 * s, y0)], "detail", roof
        yield "rect", (cx - 11 * s, yb - 36 * s, cx + 11 * s, yb), "detail", (70, 50, 40)
        for dx in (-34, 34):
            yield "rect", (cx + dx * s - 11 * s, y0 + 14 * s, cx + dx * s + 11 * s, y0 + 34 * s),\
                "detail", (150, 170, 190)
    elif o.kind == "car":
        w, h = 130 * s, 30 * s
        x0 = cx - w / 2
        yield "rect", (x0, yb - h - 8 * s, x0 + w, yb - 8 * s), "body", o.body
        yield "poly", [(x0 + 28 * s, yb - h - 8 * s), (x0 + 44 * s, yb - h - 30 * s),
                       (x0 + 92 * s, yb - h - 30 * s), (x0 + 108 * s, yb - h - 8 * s)], "body", o.body
        yield "poly", [(x0 + 36 * s, yb - h - 10 * s), (x0 + 48 * s, yb - h - 27 * s),
                       (x0 + 88 * s, yb - h - 27 * s), (x0 + 100 * s, yb - h - 10 * s)],\
            "detail", (170, 190, 205)
        for wx in (x0 + 28 * s, x0 + 102 * s):
            yield "ellipse", (wx - 13 * s, yb - 24 * s, wx + 13 * s, yb + 2 * s), "detail", (30, 30, 30)
    elif o.kind == "tree":
        yield "rect", (cx - 7 * s, yb - 60 * s, cx + 7 * s, yb), "detail", (95, 70, 45)
        for dx, dy, r in ((0, -95, 42), (-28, -70, 32), (28, -70, 32)):
            yield "ellipse", (cx + (dx - r) * s, yb + (dy - r) * s, cx + (dx + r) * s,
                              yb + (dy + r) * s), "body", o.body
    elif o.kind == "bush":
        for dx, dy, r in ((-22, -22, 24), (20, -22, 24), (0, -34, 28)):
            yield "ellipse", (cx + (dx - r) * s, yb + (dy - r) * s, cx + (dx + r) * s,
                              yb + (dy + r) * s), "body", o.body
    elif o.kind == "sign":
        yield "rect", (cx - 4 * s, yb - 80 * s, cx + 4 * s, yb), "detail", (90, 90, 90)
        yield "rect", (cx - 40 * s, yb - 110 * s, cx + 40 * s, yb - 66 * s), "body", o.body
        yield "rect", (cx - 30 * s, yb - 96 * s, cx + 30 * s, yb - 90 * s), "detail", (240, 240, 235)
    elif o.kind == "cloud":
        for dx, dy, rx, ry in ((0, 0, 60, 26), (-45, 8, 40, 20), (48, 6, 44, 22)):
            yield "ellipse", (cx + (dx - rx) * s, yb + (dy - ry) * s, cx + (dx + rx) * s,
                              yb + (dy + ry) * s), "body", o.body
    else:
        raise ValueError(f"unknown object kind {o.kind!r}")


def _draw(draw: ImageDraw.ImageDraw, o: Obj, mode: str = "color") -> None:
    for shape, coords, role, colour in _parts(o):
        if mode == "footprint":
            fill = 255
        elif mode == "paint":
            fill = 255 if role == "body" else 0
        else:
            fill = colour
        if shape == "rect":
            draw.rectangle(coords, fill=fill)
        elif shape == "ellipse":
            draw.ellipse(coords, fill=fill)
        else:
            draw.polygon(coords, fill=fill)


def _mask(o: Obj, mode: str) -> np.ndarray:
    m = Image.new("L", (W, H), 0)
    _draw(ImageDraw.Draw(m), o, mode)
    return np.asarray(m) > 127


def _bbox(o: Obj) -> tuple[float, float, float, float]:
    ys, xs = np.nonzero(_mask(o, "footprint"))
    if len(xs) == 0:
        return (o.cx, o.yb, o.cx, o.yb)
    return (xs.min(), ys.min(), xs.max(), ys.max())


def _overlaps(a, b, pad=6.0) -> bool:
    return not (a[2] + pad < b[0] or b[2] + pad < a[0] or a[3] + pad < b[1] or b[3] + pad < a[1])


@dataclass
class ScenePlan:
    sky_top: tuple[int, int, int]
    sky_low: tuple[int, int, int]
    horizon: float
    hills: list[list[tuple[float, float]]]
    hill_colours: list[tuple[int, int, int]]
    ground: tuple[int, int, int]
    clouds: list[Obj]
    background: list[Obj]
    focal: Obj
    target: Obj  # the changed object, as it is in A (it may be the focal object)
    target_is_focal: bool
    noise_seed: int


def _scale_for(o: Obj, area_px: float, mode: str) -> float:
    probe = Obj(o.kind, W / 2, H * 0.9, 1.0, o.body, o.extra)
    a1 = _mask(probe, mode).sum()
    return float(np.sqrt(area_px / max(a1, 1)))


def plan_scene(seed: int, change_type: str, interest: str, area_dva2: float,
               shift_dva: float) -> ScenePlan:
    if change_type not in ("presence", "color", "location"):
        raise ValueError(f"change_type {change_type!r}")
    if interest not in ("central", "marginal"):
        raise ValueError(f"interest {interest!r}")
    rng = np.random.default_rng(seed)
    horizon = float(rng.uniform(0.40, 0.48) * H)
    sky_top = tuple(int(v) for v in rng.integers([70, 120, 190], [110, 160, 235]))
    sky_low = tuple(int(v) for v in rng.integers([170, 200, 225], [200, 225, 250]))
    hills, hill_colours = [], []
    for layer, (amp, base) in enumerate(((40, -10), (25, 12))):
        xs = np.linspace(0, W, 40)
        ph = rng.uniform(0, 2 * np.pi, 3)
        ys = horizon + base - amp * (0.6 * np.sin(xs / 170 + ph[0]) + 0.3 * np.sin(xs / 70 + ph[1])
                                     + 0.2 * np.sin(xs / 31 + ph[2]))
        hills.append([(0.0, float(H))] + [(float(x), float(y)) for x, y in zip(xs, ys)]
                     + [(float(W), float(H))])
        g = rng.integers(0, 25)
        hill_colours.append((110 + g - 40 * layer, 140 + g - 20 * layer, 110 - 30 * layer + g))
    ground = tuple(int(v) for v in rng.integers([95, 135, 60], [125, 165, 90]))
    clouds = [Obj("cloud", float(rng.uniform(80, W - 80)), float(rng.uniform(40, horizon - 80)),
                  float(rng.uniform(0.5, 0.9)), (245, 245, 248)) for _ in range(rng.integers(1, 4))]

    area_px = area_dva2 * PPD**2
    kinds = PAINTABLE if change_type == "color" else ANY_KIND
    focal_kind = str(rng.choice(["house", "car"] if interest == "marginal" or change_type == "color"
                                else ["house", "car", "tree"]))
    if interest == "central":
        focal_kind = str(rng.choice(kinds)) if change_type != "color" else focal_kind
    focal_body = BLUE if (interest == "central" and change_type == "color") else (
        tuple(WALLS[rng.integers(len(WALLS))]) if focal_kind == "house" else
        tuple(CARS[rng.integers(len(CARS))]) if focal_kind == "car" else (60, 120, 55))
    if focal_kind == "sign":
        focal_body = BLUE if change_type == "color" else (200, 160, 40)
    focal = Obj(focal_kind, float(rng.uniform(0.42, 0.58) * W), float(rng.uniform(0.74, 0.86) * H),
                1.0, focal_body, {"roof": (110, 45, 35)})
    if interest == "central":
        mode = "paint" if change_type == "color" else "footprint"
        focal.s = _scale_for(focal, area_px, mode)
        target = focal
    else:
        focal.s = float(rng.uniform(1.6, 2.1))
        tkind = str(rng.choice(kinds))
        tbody = BLUE if change_type == "color" else (
            (60, 115, 55) if tkind in ("tree", "bush") else
            tuple(WALLS[rng.integers(len(WALLS))]) if tkind == "house" else
            tuple(CARS[rng.integers(len(CARS))]) if tkind == "car" else (200, 160, 40))
        side = rng.choice([-1, 1])
        tx = float((rng.uniform(0.10, 0.22) if side < 0 else rng.uniform(0.78, 0.90)) * W)
        target = Obj(tkind, tx, float(horizon + rng.uniform(40, 90)), 1.0, tbody,
                     {"roof": (90, 85, 95)})
        mode = "paint" if change_type == "color" else "footprint"
        target.s = _scale_for(target, area_px, mode)
    # Keep the changed object inside the image, with room for the shift.
    shift_px = shift_dva * PPD if change_type == "location" else 0.0
    probe = Obj(target.kind, W / 2, H * 0.9, target.s, target.body, target.extra)
    bx = _bbox(probe)  # measured where nothing clips it
    half = (bx[2] - bx[0]) / 2
    lo, hi = half + 8, W - half - 8
    if change_type == "location":
        sign = -1.0 if target.cx > W / 2 else 1.0
        target.extra["shift_px"] = sign * shift_px
        lo, hi = (lo, hi - shift_px) if sign > 0 else (lo + shift_px, hi)
    target.cx = float(np.clip(target.cx, lo, hi))
    top = bx[1] - probe.yb  # how far the object reaches above its base (negative)
    target.yb = float(np.clip(target.yb, -top + 8, H - 8))

    # Background objects along the horizon, never overlapping the changed object (in
    # either of its positions) or the focal object.
    keep_clear = [_bbox(target), _bbox(focal)]
    if change_type == "location":
        moved = Obj(target.kind, target.cx + target.extra["shift_px"], target.yb, target.s,
                    target.body, target.extra)
        keep_clear.append(_bbox(moved))
    background = []
    n_wanted = int(rng.integers(14, 22))
    for _ in range(60):
        if len(background) >= n_wanted:
            break
        kind = str(rng.choice(["house", "tree", "tree", "bush", "house", "car", "sign"]))
        yb = float(horizon + rng.uniform(5, 0.32 * H))
        s = float(0.3 + (yb - horizon) / 170)
        body = (tuple(WALLS[rng.integers(len(WALLS))]) if kind == "house" else
                tuple(CARS[rng.integers(len(CARS))]) if kind == "car" else
                (200, 160, 40) if kind == "sign" else
                (55 + int(rng.integers(0, 30)), 105 + int(rng.integers(0, 30)), 50))
        o = Obj(kind, float(rng.uniform(20, W - 20)), yb, s, body,
                {"roof": tuple(int(v) for v in rng.integers([80, 40, 30], [140, 70, 60]))})
        b = _bbox(o)
        if any(_overlaps(b, k) for k in keep_clear) or any(_overlaps(b, _bbox(p), 0) for p in background):
            continue
        background.append(o)
    background.sort(key=lambda o: o.yb)
    return ScenePlan(sky_top, sky_low, horizon, hills, hill_colours, ground, clouds, background,
                     focal, target, interest == "central", int(rng.integers(0, 2**31 - 1)))


def _render(plan: ScenePlan, target_state: str) -> np.ndarray:
    """target_state: 'a' (as planned), 'absent', 'red', 'shifted'."""
    img = Image.new("RGB", (W, H))
    grad = np.linspace(0, 1, int(plan.horizon) + 40)[:, None, None]
    sky = (np.array(plan.sky_top) * (1 - grad) + np.array(plan.sky_low) * grad).astype(np.uint8)
    img.paste(Image.fromarray(np.repeat(sky, W, axis=1)), (0, 0))
    d = ImageDraw.Draw(img)
    for c in plan.clouds:
        _draw(d, c)
    for pts, col in zip(plan.hills, plan.hill_colours):
        d.polygon(pts, fill=col)
    d.rectangle((0, plan.horizon + 30, W, H), fill=plan.ground)
    target = plan.target
    if target_state == "red":
        target = Obj(target.kind, target.cx, target.yb, target.s, RED, target.extra)
    elif target_state == "shifted":
        target = Obj(target.kind, target.cx + target.extra["shift_px"], target.yb, target.s,
                     target.body, target.extra)
    for o in plan.background:
        _draw(d, o)
    if not plan.target_is_focal and target_state != "absent":
        _draw(d, target)
    if plan.target_is_focal:
        if target_state != "absent":
            _draw(d, target)
    else:
        _draw(d, plan.focal)
    arr = np.asarray(img.filter(ImageFilter.GaussianBlur(0.7)), dtype=float)
    noise = np.random.default_rng(plan.noise_seed).normal(0, 5, arr.shape)
    return np.clip(arr + noise, 0, 255).astype(np.uint8)


def change_geometry(a: np.ndarray, b: np.ndarray) -> dict:
    d = np.abs(a.astype(int) - b.astype(int)).max(-1) > 24
    h, w = d.shape
    ys, xs = np.nonzero(d)
    if len(xs) == 0:
        raise ValueError("the two images do not differ")
    return {
        "bbox": [round(float(xs.min()) / w, 4), round(float(ys.min()) / h, 4),
                 round(float(xs.max() + 1) / w, 4), round(float(ys.max() + 1) / h, 4)],
        "centroid": [round(float(xs.mean()) / w, 4), round(float(ys.mean()) / h, 4)],
        "area_fraction": round(float(d.mean()), 5),
    }


CUE_INVALID = {"house": "tree", "car": "house", "tree": "house", "bush": "house", "sign": "tree"}


def generate(seed: int, change_type: str, interest: str, area_dva2: float = 20.0,
             shift_dva: float = 3.0) -> tuple[Image.Image, Image.Image, dict]:
    """(A, A', metadata) for one procedural pair; the same arguments give the same pair."""
    plan = plan_scene(seed, change_type, interest, area_dva2, shift_dva)
    state = {"presence": "absent", "color": "red", "location": "shifted"}[change_type]
    a, b = _render(plan, "a"), _render(plan, state)
    geo = change_geometry(a, b)
    meta = {"object": plan.target.kind, "cue_valid": plan.target.kind,
            "cue_invalid": CUE_INVALID[plan.target.kind], **geo,
            "area_dva2": round(geo["area_fraction"] * W * H / PPD**2, 2)}
    return Image.fromarray(a), Image.fromarray(b), meta
