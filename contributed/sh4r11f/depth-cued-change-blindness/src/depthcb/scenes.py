"""Two-depth-plane scene pairs for the depth-cued flicker task, drawn from a seed.

A scene is a far surface seen behind a layer of near objects, on an ordinary 2-D screen.
Depth comes only from monocular (pictorial) cues, each of which can be switched off:

- relative size: near objects are larger than far ones;
- occlusion: a few far objects sit partly behind near objects;
- cast shadows: each near object throws a soft shadow onto the far surface;
- blur: the far layer is slightly defocused, as behind a near focal plane;
- aerial perspective: far colours are mixed toward the haze colour (lower contrast);
- texture: the far surface carries a fine speckle texture the near objects do not.

Near and far objects are interleaved over the whole picture (two of each in every quadrant
of a 4 x 4 grid), so a depth plane is not a region of the screen: a cue that names a plane
cannot be turned into a cue to a place. The changed object is drawn from the cued or the
uncued plane within the same eccentricity band.

The scene id ``depth/<seed>/<plane>/<change_type>`` holds everything needed to redraw it,
so a session never stores images and any number of new scenes can be made.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

PLANES = ("near", "far")
CHANGE_TYPES = ("presence", "color", "location")
SHAPES = ("disc", "square", "triangle", "diamond", "hexagon", "star")
PALETTE = {
    "red": (214, 54, 48), "orange": (236, 138, 32), "yellow": (232, 198, 36),
    "green": (46, 156, 70), "blue": (40, 104, 204), "purple": (138, 72, 180),
}
HAZE = (196, 202, 212)
WALL = (190, 194, 200)
SS = 2  # supersampling factor for anti-aliased edges


@dataclass(frozen=True)
class DepthCueSet:
    relative_size: bool = True
    occlusion: bool = True
    cast_shadows: bool = True
    blur: bool = True
    aerial: bool = True
    texture: bool = True


@dataclass(frozen=True)
class SceneSpec:
    width_dva: float = 27.0
    height_dva: float = 18.0
    px_per_dva: float = 40.0
    n_near: int = 8
    n_far: int = 8
    n_occluded: int = 3
    near_size_dva: float = 2.4
    far_size_dva: float = 1.5
    target_eccentricity_dva: tuple[float, float] = (3.0, 11.0)
    location_shift_dva: float = 2.0
    far_blur_dva: float = 0.06
    aerial_mix: float = 0.45
    shadow_offset_dva: float = 0.35
    shadow_blur_dva: float = 0.15
    shadow_opacity: float = 0.40
    cues: DepthCueSet = field(default_factory=DepthCueSet)


@dataclass
class Obj:
    shape: str
    color: str
    x: float  # dva from the picture's centre, +x right
    y: float  # dva from the picture's centre, +y down (image rows)
    plane: str
    size: float
    primary: bool = True  # False for the partly hidden far objects (never changed)
    present: bool = True


@dataclass(frozen=True)
class DepthPair:
    scene: str
    seed: int
    plane: str
    change_type: str
    shape: str
    color_a: str
    color_b: str
    present_in: str  # "both" | "A" | "B"
    eccentricity_dva: float
    centroid: tuple[float, float]  # image fractions (x, y), y down
    bbox: tuple[float, float, float, float]  # image fractions of the change
    changed_area_dva2: float
    objects: list[dict]  # every object in image A (plane, centre in fractions, primary)
    target_index: int
    image_a: Image.Image
    image_b: Image.Image


def scene_id(seed: int, plane: str, change_type: str) -> str:
    return f"depth/{seed}/{plane}/{change_type}"


def parse_id(scene: str) -> tuple[int, str, str]:
    kind, seed, plane, change_type = scene.split("/")
    if kind != "depth" or plane not in PLANES or change_type not in CHANGE_TYPES:
        raise ValueError(f"unknown scene id {scene!r}")
    return int(seed), plane, change_type


def _poly(shape: str, cx: float, cy: float, r: float) -> list[tuple[float, float]] | None:
    """Vertices of a shape of 'radius' r (None for the disc). Radii are scaled so the
    shapes have similar areas (all within 15% of the disc of radius r)."""
    def ring(n, rad, rot):
        return [(cx + rad * math.cos(rot + 2 * math.pi * k / n),
                 cy + rad * math.sin(rot + 2 * math.pi * k / n)) for k in range(n)]
    if shape == "disc":
        return None
    if shape == "square":
        return ring(4, r * 1.25, math.pi / 4)
    if shape == "diamond":
        return ring(4, r * 1.25, 0.0)
    if shape == "triangle":
        return ring(3, r * 1.5, -math.pi / 2)
    if shape == "hexagon":
        return ring(6, r * 1.1, 0.0)
    if shape == "star":
        pts = []
        for k in range(10):
            rad = r * (1.45 if k % 2 == 0 else 0.68)
            a = -math.pi / 2 + math.pi * k / 5
            pts.append((cx + rad * math.cos(a), cy + rad * math.sin(a)))
        return pts
    raise ValueError(shape)


def _draw(d: ImageDraw.ImageDraw, shape: str, cx: float, cy: float, r: float, fill,
          outline=None, width: int = 0) -> None:
    pts = _poly(shape, cx, cy, r)
    if pts is None:
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=fill, outline=outline, width=width)
    else:
        d.polygon(pts, fill=fill, outline=outline, width=width)


def _mix(c, toward, a):
    return tuple(int(round((1 - a) * ci + a * ti)) for ci, ti in zip(c, toward, strict=True))


def _layout(spec: SceneSpec, rng: np.random.Generator) -> list[Obj]:
    near_size = spec.near_size_dva
    far_size = spec.far_size_dva if spec.cues.relative_size else spec.near_size_dva
    cols, rows = 4, 4
    cw, ch = spec.width_dva / cols, spec.height_dva / rows
    planes = {}
    for qx in range(2):
        for qy in range(2):
            cells = [(qx * 2 + i, qy * 2 + j) for i in range(2) for j in range(2)]
            order = rng.permutation(4)
            for k, idx in enumerate(order):
                planes[cells[idx]] = "near" if k < 2 else "far"
    objs = []
    for (c, r_), plane in sorted(planes.items()):
        size = near_size if plane == "near" else far_size
        jx, jy = rng.uniform(-0.2, 0.2, size=2)
        x = (c + 0.5 + jx) * cw - spec.width_dva / 2
        y = (r_ + 0.5 + jy) * ch - spec.height_dva / 2
        objs.append(Obj(str(rng.choice(SHAPES)), str(rng.choice(list(PALETTE))), x, y, plane,
                        size))
    if spec.cues.occlusion and spec.n_occluded > 0:
        hosts = [o for o in objs if o.plane == "near"]
        rng.shuffle(hosts)
        placed = 0
        for host in hosts:
            if placed >= spec.n_occluded:
                break
            for _ in range(40):
                a = rng.uniform(0, 2 * math.pi)
                d = 0.62 * (host.size + far_size) / 2
                x, y = host.x + d * math.cos(a), host.y + d * math.sin(a)
                half_w, half_h = spec.width_dva / 2 - far_size, spec.height_dva / 2 - far_size
                if abs(x) > half_w or abs(y) > half_h:
                    continue
                clear = all(math.hypot(x - o.x, y - o.y) > (o.size + far_size) / 2 + 0.3
                            for o in objs if o is not host)
                if clear:
                    objs.append(Obj(str(rng.choice(SHAPES)), str(rng.choice(list(PALETTE))),
                                    x, y, "far", far_size, primary=False))
                    placed += 1
                    break
    return objs


def _texture(spec: SceneSpec, seed: int, w: int, h: int) -> Image.Image:
    rng = np.random.default_rng(seed + 7919)
    base = np.empty((h, w, 3), np.float32)
    base[:] = WALL if not spec.cues.aerial else _mix(WALL, HAZE, 0.3)
    if spec.cues.texture:
        cell = max(2, int(round(0.12 * spec.px_per_dva * SS)))
        gh, gw = -(-h // cell), -(-w // cell)
        noise = rng.normal(0, 7.0, size=(gh, gw, 1)).astype(np.float32)
        noise = np.repeat(np.repeat(noise, cell, 0), cell, 1)[:h, :w]
        base += noise
    return Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), "RGB")


def render(objs: list[Obj], spec: SceneSpec, seed: int) -> Image.Image:
    ppd = spec.px_per_dva * SS
    w, h = int(round(spec.width_dva * spec.px_per_dva)), int(round(spec.height_dva * spec.px_per_dva))
    W, H = w * SS, h * SS

    def px(o: Obj) -> tuple[float, float, float]:
        return (o.x + spec.width_dva / 2) * ppd, (o.y + spec.height_dva / 2) * ppd, o.size / 2 * ppd

    img = _texture(spec, seed, W, H).convert("RGBA")
    far = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(far)
    for o in objs:
        if o.plane != "far" or not o.present:
            continue
        cx, cy, r = px(o)
        col = PALETTE[o.color]
        if spec.cues.aerial:
            col = _mix(col, HAZE, spec.aerial_mix)
        _draw(d, o.shape, cx, cy, r, fill=col + (255,))
    if spec.cues.blur and spec.far_blur_dva > 0:
        far = far.filter(ImageFilter.GaussianBlur(spec.far_blur_dva * ppd))
    img = Image.alpha_composite(img, far)
    if spec.cues.cast_shadows:
        sh = Image.new("L", (W, H), 0)
        ds = ImageDraw.Draw(sh)
        off = spec.shadow_offset_dva * ppd
        for o in objs:
            if o.plane == "near" and o.present:
                cx, cy, r = px(o)
                _draw(ds, o.shape, cx + off, cy + off, r, fill=255)
        sh = sh.filter(ImageFilter.GaussianBlur(spec.shadow_blur_dva * ppd))
        sh = sh.point(lambda v: int(v * spec.shadow_opacity))
        black = Image.new("RGBA", (W, H), (20, 22, 28, 255))
        black.putalpha(sh)
        img = Image.alpha_composite(img, black)
    near = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dn = ImageDraw.Draw(near)
    line = max(1, int(round(0.05 * ppd)))
    for o in objs:
        if o.plane != "near" or not o.present:
            continue
        cx, cy, r = px(o)
        _draw(dn, o.shape, cx, cy, r, fill=PALETTE[o.color] + (255,), outline=(30, 30, 34, 255),
              width=line)
    img = Image.alpha_composite(img, near).convert("RGB")
    return img.resize((w, h), Image.LANCZOS)


def _pick_target(objs: list[Obj], plane: str, spec: SceneSpec, rng: np.random.Generator) -> int:
    lo, hi = spec.target_eccentricity_dva
    cands = [i for i, o in enumerate(objs) if o.primary and o.plane == plane]
    inband = [i for i in cands if lo <= math.hypot(objs[i].x, objs[i].y) <= hi]
    pool = inband or sorted(cands, key=lambda i: abs(math.hypot(objs[i].x, objs[i].y)
                                                        - (lo + hi) / 2))[:1]
    return int(rng.choice(pool))


def _shift(objs: list[Obj], i: int, spec: SceneSpec) -> tuple[float, float]:
    o, best, best_clear = objs[i], None, -1e9
    for k in range(16):
        a = 2 * math.pi * k / 16
        x = o.x + spec.location_shift_dva * math.cos(a)
        y = o.y + spec.location_shift_dva * math.sin(a)
        if abs(x) > spec.width_dva / 2 - o.size * 0.75 or abs(y) > spec.height_dva / 2 - o.size * 0.75:
            continue
        clear = min(math.hypot(x - p.x, y - p.y) - (p.size + o.size) / 2
                    for j, p in enumerate(objs) if j != i)
        if clear > best_clear:
            best, best_clear = (x, y), clear
    if best is None:
        raise ValueError("no room to move the target")
    return best


def generate(seed: int, plane: str, change_type: str, spec: SceneSpec | None = None) -> DepthPair:
    spec = spec or SceneSpec()
    if plane not in PLANES or change_type not in CHANGE_TYPES:
        raise ValueError((plane, change_type))
    rng = np.random.default_rng(seed)
    objs = _layout(spec, rng)
    i = _pick_target(objs, plane, spec, rng)
    a = [Obj(**vars(o)) for o in objs]
    b = [Obj(**vars(o)) for o in objs]
    t = objs[i]
    color_b, present_in = t.color, "both"
    if change_type == "color":
        color_b = str(rng.choice([c for c in PALETTE if c != t.color]))
        b[i].color = color_b
    elif change_type == "presence":
        present_in = "A" if rng.random() < 0.5 else "B"
        (b if present_in == "A" else a)[i].present = False
    else:
        b[i].x, b[i].y = _shift(objs, i, spec)
    img_a, img_b = render(a, spec, seed), render(b, spec, seed)
    diff = np.asarray(ImageChops.difference(img_a, img_b).convert("L")) > 12
    ys, xs = np.nonzero(diff)
    w, h = img_a.size
    if len(xs) == 0:
        raise AssertionError("scene pair without a change")
    bbox = (xs.min() / w, ys.min() / h, (xs.max() + 1) / w, (ys.max() + 1) / h)
    ecc = math.hypot(t.x, t.y)
    cx = ((t.x + b[i].x) / 2 + spec.width_dva / 2) / spec.width_dva
    cy = ((t.y + b[i].y) / 2 + spec.height_dva / 2) / spec.height_dva
    return DepthPair(
        scene=scene_id(seed, plane, change_type), seed=seed, plane=plane,
        change_type=change_type, shape=t.shape, color_a=t.color, color_b=color_b,
        present_in=present_in, eccentricity_dva=round(ecc, 3), centroid=(cx, cy), bbox=bbox,
        changed_area_dva2=round(float(diff.mean()) * spec.width_dva * spec.height_dva, 3),
        objects=[{"plane": o.plane, "primary": o.primary, "size": o.size,
                  "x": (o.x + spec.width_dva / 2) / spec.width_dva,
                  "y": (o.y + spec.height_dva / 2) / spec.height_dva} for o in objs],
        target_index=i, image_a=img_a, image_b=img_b)


def probe_boxes(pair: DepthPair, n: int, side_dva: float, spec: SceneSpec,
                rng: np.random.Generator) -> tuple[list[tuple[float, float, float, float]], int, list[str]]:
    """``n`` equal square boxes (image fractions): one on the change, the others on other
    objects, half of them on each depth plane, so neither a box's place nor its plane
    gives the answer away. Returns (boxes in reading order, index of the correct one,
    plane under each box)."""
    W, H = spec.width_dva, spec.height_dva
    tx0, ty0, tx1, ty1 = pair.bbox
    side = max(side_dva, (tx1 - tx0) * W + 0.4, (ty1 - ty0) * H + 0.4)
    bw, bh = side / W, side / H

    def box(cx, cy):
        x0 = float(np.clip(cx - bw / 2, 0, 1 - bw))
        y0 = float(np.clip(cy - bh / 2, 0, 1 - bh))
        return (x0, y0, x0 + bw, y0 + bh)

    def apart(b, others):
        return all(b[2] <= o[0] or o[2] <= b[0] or b[3] <= o[1] or o[3] <= b[1] for o in others)

    true = box((tx0 + tx1) / 2, (ty0 + ty1) / 2)
    boxes, planes = [true], [pair.plane]
    other = "far" if pair.plane == "near" else "near"
    want = [pair.plane] * (n // 2 - 1) + [other] * (n - n // 2)
    for plane in want:
        cands = [o for j, o in enumerate(pair.objects)
                 if j != pair.target_index and o["primary"] and o["plane"] == plane]
        rng.shuffle(cands)
        for o in cands:
            b = box(o["x"], o["y"])
            if apart(b, boxes):
                boxes.append(b)
                planes.append(plane)
                break
    order = sorted(range(len(boxes)), key=lambda k: (round(boxes[k][1] * 3), boxes[k][0]))
    return [boxes[k] for k in order], order.index(0), [planes[k] for k in order]
