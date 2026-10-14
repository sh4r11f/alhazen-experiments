"""The stimulus bank: ten arm-like objects and their perspective line drawings.

    uv run python -m shepard_metzler1971.bank           # writes stimuli/bank/
    uv run python -m shepard_metzler1971.bank --check   # regenerates in memory, compares

What the paper states (Shepard & Metzler 1971, p. 702) and this module follows:

- each object is ten solid cubes attached face to face into a rigid arm with exactly
  three right-angled elbows;
- the ten objects are two sets of five: within a set no shape can be turned into itself
  or another by any reflection or rotation short of 360 degrees, and each shape in one
  set is the mirror image of one shape in the other;
- for each object 18 perspective projections were made, one full turn about the vertical
  axis in 20-degree steps, and 7 of the 18 were kept: views in which no part of the object
  is wholly hidden by another, chosen so that two pairs differ by every angle from 0 to
  180 degrees in 20-degree steps (70 drawings in all).

The original ten shapes and Noll's projection program are not reproduced: the shapes are
generated here under the same constraints, from a fixed seed. Everything the paper does
not state (camera elevation and distance, the exact occlusion criterion, the minimum arm
length, line width, how the ten shapes were picked) is a parameter in configs/task.yaml
marked ASSUMED there and in docs/methods.md.

numpy only for the geometry and the rasterizer; the PNG writer is the stdlib's zlib, so
the same pixels always give the same bytes.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import struct
import sys
import zlib
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from shepard_metzler1971.params import MentalRotationParams, ObjectsConfig

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
BANK_DIR = PROJECT / "stimuli" / "bank"
MANIFEST = "manifest.json"
GENERATOR_VERSION = 1

UNIT = np.eye(3, dtype=int)
DIRECTIONS = [tuple(s * UNIT[a]) for a in range(3) for s in (1, -1)]


# ---------------------------------------------------------------------------
# Shapes: voxel sets, their symmetries, and the paper's constraints
# ---------------------------------------------------------------------------

def _rotations() -> list[np.ndarray]:
    """The 24 proper rotations of the cube, as integer matrices (det +1)."""
    out = []
    for perm in itertools.permutations(range(3)):
        for signs in itertools.product((1, -1), repeat=3):
            m = np.zeros((3, 3), dtype=int)
            for row, (col, s) in enumerate(zip(perm, signs, strict=True)):
                m[row, col] = s
            if round(np.linalg.det(m)) == 1:
                out.append(m)
    return sorted(out, key=lambda m: tuple(m.ravel()))


ROTATIONS = _rotations()
MIRROR = np.diag([-1, 1, 1])


def normalized(cubes: np.ndarray) -> tuple:
    """Translation-free, order-free identity of a voxel set."""
    c = cubes - cubes.min(axis=0)
    return tuple(sorted(map(tuple, c.tolist())))


def canonical(cubes: np.ndarray) -> tuple:
    """The same key for every rotation of a shape (not for its mirror image)."""
    return min(normalized(cubes @ r.T) for r in ROTATIONS)


def is_chiral(cubes: np.ndarray) -> bool:
    return canonical(cubes) != canonical(cubes @ MIRROR.T)


def rotational_symmetries(cubes: np.ndarray) -> int:
    """How many of the 24 rotations map the shape onto itself (1 = none but identity)."""
    key = normalized(cubes)
    return sum(normalized(cubes @ r.T) == key for r in ROTATIONS)


def arm_paths(cfg: ObjectsConfig) -> list[tuple[tuple[int, ...], np.ndarray]]:
    """Every arm: n_cubes in a self-avoiding straight-run path with n_elbows right-angle
    turns, each run at least min_run cube steps, and no two cubes touching face to face
    except neighbours along the arm (so it stays an arm). One representative per first
    direction pair: the rest are rotations of these."""
    n_runs = cfg.n_elbows + 1
    steps = cfg.n_cubes - 1
    out = []
    for runs in itertools.product(range(cfg.min_run, steps + 1), repeat=n_runs):
        if sum(runs) != steps:
            continue
        for dirs in itertools.product(range(6), repeat=n_runs):
            if dirs[0] != 0 or dirs[1] != 2:  # +x then +y: every other start is a rotation
                continue
            vecs = [np.array(DIRECTIONS[d]) for d in dirs]
            if any(int(np.dot(a, b)) != 0 for a, b in itertools.pairwise(vecs)):
                continue  # every elbow is a right angle
            pos = np.zeros(3, dtype=int)
            cubes = [pos.copy()]
            for v, n in zip(vecs, runs, strict=True):
                for _ in range(n):
                    pos = pos + v
                    cubes.append(pos.copy())
            arr = np.array(cubes)
            if len({tuple(c) for c in cubes}) != len(cubes):
                continue
            touching = [(i, j) for i in range(len(arr)) for j in range(i + 2, len(arr))
                        if int(np.abs(arr[i] - arr[j]).sum()) == 1]
            if touching:
                continue
            out.append((runs, arr))
    return out


def candidate_shapes(cfg: ObjectsConfig) -> list[dict]:
    """Distinct (up to rotation) arms that are chiral and have no rotational symmetry:
    the paper's 'cannot be transformed into itself by any reflection or rotation'."""
    seen: dict[tuple, dict] = {}
    for runs, cubes in arm_paths(cfg):
        if not is_chiral(cubes) or rotational_symmetries(cubes) != 1:
            continue
        key = canonical(cubes)
        if key not in seen:
            seen[key] = {"runs": list(runs), "cubes": np.array(key)}
    return [seen[k] for k in sorted(seen)]


# ---------------------------------------------------------------------------
# Projection and rasterization
# ---------------------------------------------------------------------------

@dataclass
class Camera:
    elevation_deg: float
    distance: float

    def basis(self) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        e = np.radians(self.elevation_deg)
        pos = self.distance * np.array([0.0, np.sin(e), np.cos(e)])
        fwd = -pos / np.linalg.norm(pos)
        right = np.cross(fwd, [0.0, 1.0, 0.0])
        right /= np.linalg.norm(right)
        up = np.cross(right, fwd)
        return pos, right, up, fwd


def rot_y(deg: float) -> np.ndarray:
    a = np.radians(deg)
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, 0.0, s], [0.0, 1.0, 0.0], [-s, 0.0, c]])


def exposed_faces(cubes: np.ndarray) -> list[tuple[int, np.ndarray, np.ndarray]]:
    """(cube index, outward normal, 4 corners) for every face not shared with a neighbour."""
    occupied = {tuple(c) for c in cubes.tolist()}
    faces = []
    for i, c in enumerate(cubes.astype(float)):
        for d in DIRECTIONS:
            if tuple(np.array(c, dtype=int) + d) in occupied:
                continue
            n = np.array(d, dtype=float)
            a, b = [UNIT[k].astype(float) for k in range(3) if d[k] == 0]
            centre = c + 0.5 * n
            corners = np.array([centre + 0.5 * (sa * a + sb * b)
                                for sa, sb in ((-1, -1), (1, -1), (1, 1), (-1, 1))])
            faces.append((i, n, corners))
    return faces


def project(points_world: np.ndarray, camera: Camera) -> tuple[np.ndarray, np.ndarray]:
    """Camera-space coordinates and normalized image coordinates (x right, y up)."""
    pos, right, up, fwd = camera.basis()
    rel = points_world - pos
    cam = np.stack([rel @ right, rel @ up, rel @ fwd], axis=-1)
    return cam, cam[..., :2] / cam[..., 2:3]


def world_points(cubes: np.ndarray, azimuth_deg: float) -> tuple[np.ndarray, np.ndarray]:
    """Object turned by azimuth about the vertical axis through its centroid."""
    centroid = cubes.astype(float).mean(axis=0)
    return centroid, rot_y(azimuth_deg)


@dataclass
class Render:
    ids: np.ndarray          # face index per pixel, -1 = background
    face_cube: np.ndarray    # cube index of each face
    visible_fraction: np.ndarray  # per cube: visible area / unoccluded front-face area


def rasterize(cubes: np.ndarray, azimuth_deg: float, camera: Camera, size: int,
              scale: float, offset: np.ndarray) -> Render:
    """Exact visible-surface map: for each pixel, the nearest face (1/z is linear in the
    image for a plane, so depth is exact, not interpolated)."""
    centroid, rot = world_points(cubes, azimuth_deg)
    faces = exposed_faces(cubes)
    pos, right, up, fwd = camera.basis()
    ids = np.full((size, size), -1, dtype=np.int32)
    invz = np.zeros((size, size))
    face_cube = np.array([f[0] for f in faces], dtype=np.int32)
    n_cubes = len(cubes)
    front_area = np.zeros(n_cubes)
    seen_px = np.zeros(n_cubes)
    centre_px = (size - 1) / 2.0
    for fi, (ci, normal, corners) in enumerate(faces):
        pts = (corners - centroid) @ rot.T
        nrm = rot @ normal
        if np.dot(nrm, pos - pts.mean(axis=0)) <= 1e-12:
            continue  # back face
        cam, img = project(pts, camera)
        px = centre_px + scale * (img[:, 0] - offset[0])
        py = centre_px - scale * (img[:, 1] - offset[1])
        area = 0.5 * abs(np.dot(px, np.roll(py, -1)) - np.dot(py, np.roll(px, -1)))
        front_area[ci] += area
        x0, x1 = int(np.floor(px.min())), int(np.ceil(px.max()))
        y0, y1 = int(np.floor(py.min())), int(np.ceil(py.max()))
        x0, y0 = max(x0, 0), max(y0, 0)
        x1, y1 = min(x1, size - 1), min(y1, size - 1)
        if x1 < x0 or y1 < y0:
            continue
        gx, gy = np.meshgrid(np.arange(x0, x1 + 1, dtype=float), np.arange(y0, y1 + 1, dtype=float))
        inside = np.ones(gx.shape, dtype=bool)
        orient = np.sign(np.dot(px, np.roll(py, -1)) - np.dot(py, np.roll(px, -1)))
        for k in range(4):
            ax, ay, bx, by = px[k], py[k], px[(k + 1) % 4], py[(k + 1) % 4]
            edge = (bx - ax) * (gy - ay) - (by - ay) * (gx - ax)
            inside &= orient * edge >= 0
        # plane in camera space: n . p = k ; ray p = z * (X, Y, 1)
        ncam = np.array([nrm @ right, nrm @ up, nrm @ fwd])
        kplane = float(ncam @ cam[0])
        X = (gx - centre_px) / scale + offset[0]
        Y = (centre_px - gy) / scale + offset[1]
        iz = (ncam[0] * X + ncam[1] * Y + ncam[2]) / kplane
        sub_ids = ids[y0:y1 + 1, x0:x1 + 1]
        sub_iz = invz[y0:y1 + 1, x0:x1 + 1]
        win = inside & (iz > sub_iz + 1e-12)
        sub_ids[win] = fi
        sub_iz[win] = iz[win]
    for fi in np.unique(ids[ids >= 0]):
        seen_px[face_cube[fi]] += np.count_nonzero(ids == fi)
    with np.errstate(divide="ignore", invalid="ignore"):
        frac = np.where(front_area > 0, seen_px / front_area, 0.0)
    return Render(ids=ids, face_cube=face_cube, visible_fraction=frac)


def projected_vertices(cubes: np.ndarray, azimuth_deg: float, camera: Camera) -> np.ndarray:
    """Normalized image coordinates of every cube corner (for extents and centring)."""
    centroid, rot = world_points(cubes, azimuth_deg)
    corners = np.array([c + 0.5 * np.array(s) for c in cubes.astype(float)
                        for s in itertools.product((-1, 1), repeat=3)])
    _, img = project((corners - centroid) @ rot.T, camera)
    return img


def max_extent(points: np.ndarray) -> float:
    """Largest distance between two points of the drawing: its maximum linear extent."""
    d = points[:, None, :] - points[None, :, :]
    return float(np.sqrt((d ** 2).sum(-1)).max())


def _dilate(mask: np.ndarray, radius: float) -> np.ndarray:
    r = int(np.ceil(radius))
    out = mask.copy()
    h, w = mask.shape
    padded = np.pad(mask, r)
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dx * dx + dy * dy <= radius * radius:
                out |= padded[r + dy:r + dy + h, r + dx:r + dx + w]
    return out


def line_drawing(ids: np.ndarray, line_px_ss: float, ss: int) -> np.ndarray:
    """Black hidden-line drawing on a white disc, black outside the disc, 8-bit.

    Lines are where the visible-surface map changes face (every cube edge, the outline),
    thickened to line_px_ss supersampled pixels and averaged down by ss."""
    edge = np.zeros(ids.shape, dtype=bool)
    edge[:, 1:] |= ids[:, 1:] != ids[:, :-1]
    edge[:, :-1] |= ids[:, 1:] != ids[:, :-1]
    edge[1:, :] |= ids[1:, :] != ids[:-1, :]
    edge[:-1, :] |= ids[1:, :] != ids[:-1, :]
    edge = _dilate(edge, max(line_px_ss / 2.0 - 1.0, 0.0))
    size = ids.shape[0]
    yy, xx = np.mgrid[0:size, 0:size]
    c = (size - 1) / 2.0
    disc = (xx - c) ** 2 + (yy - c) ** 2 <= (size / 2.0) ** 2
    white = disc & ~edge
    small = white.reshape(size // ss, ss, size // ss, ss).mean(axis=(1, 3))
    return np.round(small * 255.0).astype(np.uint8)


def png_bytes(gray: np.ndarray) -> bytes:
    """A minimal 8-bit grayscale PNG: same pixels, same bytes, on any machine."""
    h, w = gray.shape
    raw = b"".join(b"\x00" + gray[r].tobytes() for r in range(h))

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def read_png(data: bytes) -> np.ndarray:
    """Decode a PNG written by png_bytes (8-bit grayscale, filter 0 only)."""
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    pos, idat, w, h = 8, b"", 0, 0
    while pos < len(data):
        (n,) = struct.unpack(">I", data[pos:pos + 4])
        tag, body = data[pos + 4:pos + 8], data[pos + 8:pos + 8 + n]
        if tag == b"IHDR":
            w, h = struct.unpack(">II", body[:8])
        elif tag == b"IDAT":
            idat += body
        pos += 12 + n
    raw = np.frombuffer(zlib.decompress(idat), dtype=np.uint8).reshape(h, w + 1)
    if np.any(raw[:, 0] != 0):
        raise ValueError("only filter type 0 is supported")
    return raw[:, 1:].copy()


# ---------------------------------------------------------------------------
# Choosing views and objects
# ---------------------------------------------------------------------------

def circular_steps(i: int, j: int, n: int) -> int:
    d = abs(i - j) % n
    return min(d, n - d)


def covers_every_angle(views: tuple[int, ...], n_views: int, need: int = 2) -> bool:
    """Two unordered pairs at every angular difference 1..n_views/2 steps (0 is a view
    paired with itself, always available)."""
    counts = np.zeros(n_views // 2 + 1, dtype=int)
    for i, j in itertools.combinations(views, 2):
        counts[circular_steps(i, j, n_views)] += 1
    return bool(np.all(counts[1:] >= need))


def select_views(min_visible: np.ndarray, cfg: ObjectsConfig) -> tuple[int, ...] | None:
    """The 7 of 18 views: every cube visible enough, two pairs at each angle; among the
    sets that qualify, the one whose worst view hides least (ties: lowest indices)."""
    ok = [i for i in range(cfg.n_views) if min_visible[i] >= cfg.min_visible_fraction
          and not (cfg.exclude_face_on and is_face_on(cfg, i))]
    best, best_score = None, -1.0
    for views in itertools.combinations(ok, cfg.views_per_object):
        if not covers_every_angle(views, cfg.n_views):
            continue
        score = float(min(min_visible[v] for v in views))
        if score > best_score + 1e-12:
            best, best_score = views, score
    return best


def is_face_on(cfg: ObjectsConfig, index: int) -> bool:
    """A view straight onto the cube faces (azimuth a multiple of 90): every vertical
    edge behind another, the accidental view the paper's drawings do not show."""
    return abs(azimuth(cfg, index) / 90.0 - round(azimuth(cfg, index) / 90.0)) < 1e-9


def azimuth(cfg: ObjectsConfig, index: int) -> float:
    return cfg.view_offset_deg + cfg.view_step_deg * index


def image_name(obj: int, az_deg: float) -> str:
    return f"o{obj:02d}_az{int(round(az_deg)) % 360:03d}.png"


def build_objects(cfg: ObjectsConfig, camera: Camera) -> list[dict]:
    """Ten objects: five chosen shapes (set A, objects 1-5) and their mirror images
    (set B, objects 6-10; object k+5 is the mirror of object k)."""
    rng = np.random.default_rng(cfg.shape_seed)
    pool = candidate_shapes(cfg)
    order = rng.permutation(len(pool))
    chosen: list[dict] = []
    used: set[tuple] = set()
    probe = 128  # selection resolution: enough to see whether a cube is hidden
    for idx in order:
        shape = pool[int(idx)]
        key = shape_key = canonical(shape["cubes"])
        mirror_key = canonical(shape["cubes"] @ MIRROR.T)
        if key in used or mirror_key in used:
            continue
        rot = ROTATIONS[int(rng.integers(len(ROTATIONS)))]
        cubes = shape["cubes"] @ rot.T
        cubes = cubes - cubes.min(axis=0)
        vis = np.array([rasterize(cubes, azimuth(cfg, i), camera, probe, probe * 2.2,
                                  np.zeros(2)).visible_fraction.min()
                        for i in range(cfg.n_views)])
        views = select_views(vis, cfg)
        if views is None:
            continue
        chosen.append({"cubes": cubes, "runs": shape["runs"], "views": list(views),
                       "min_visible": [float(vis[v]) for v in views], "key": shape_key})
        used |= {key, mirror_key}
        if len(chosen) == cfg.shapes_per_set:
            break
    if len(chosen) < cfg.shapes_per_set:
        raise RuntimeError(f"only {len(chosen)} shapes meet the constraints")
    objects = []
    for k, ch in enumerate(chosen, start=1):
        objects.append({"id": k, "set": "A", "mirror_of": k + cfg.shapes_per_set,
                        "runs": ch["runs"], "cubes": ch["cubes"], "views": ch["views"],
                        "min_visible": ch["min_visible"]})
    for k, ch in enumerate(chosen, start=1):
        mirrored = ch["cubes"] @ MIRROR.T
        mirrored = mirrored - mirrored.min(axis=0)
        # Reflecting through the vertical plane that holds the camera maps the view at
        # azimuth a to the left-right mirror of the view at -a: index i -> n-1-i.
        objects.append({"id": k + cfg.shapes_per_set, "set": "B", "mirror_of": k,
                        "runs": ch["runs"], "cubes": mirrored,
                        "views": sorted(cfg.n_views - 1 - v for v in ch["views"]),
                        "min_visible": ch["min_visible"][::-1]})
    return objects


# ---------------------------------------------------------------------------
# The whole bank
# ---------------------------------------------------------------------------

def generate(params: MentalRotationParams) -> tuple[dict[str, bytes], dict]:
    """Every drawing's PNG bytes and the manifest, from the params alone."""
    cfg = params.objects
    camera = Camera(cfg.elevation_deg, cfg.camera_distance)
    objects = build_objects(cfg, camera)
    # One camera scale for all 70 drawings: the mean maximum linear extent is the
    # paper's drawing size, as a fraction of the aperture.
    verts = {(o["id"], v): projected_vertices(o["cubes"], azimuth(cfg, v), camera)
             for o in objects for v in o["views"]}
    extents = {k: max_extent(p) for k, p in verts.items()}
    mean_extent = float(np.mean(list(extents.values())))
    px_per_dva = cfg.image_px / params.aperture_dva
    scale = params.drawing_extent_dva * px_per_dva / mean_extent
    ss = cfg.supersample
    size = cfg.image_px * ss
    line_px_ss = params.line_width_dva * px_per_dva * ss
    files: dict[str, bytes] = {}
    images: dict[str, dict] = {}
    for o in objects:
        for v in o["views"]:
            pts = verts[(o["id"], v)]
            centre = (pts.min(axis=0) + pts.max(axis=0)) / 2.0
            reach = float(np.sqrt(((pts - centre) ** 2).sum(-1)).max()) * scale
            if reach > 0.47 * cfg.image_px:
                raise RuntimeError(
                    f"object {o['id']} view {v} reaches {reach:.0f} px from the centre of a "
                    f"{cfg.image_px}-px aperture: it would be cut off when rotated. Use a "
                    f"larger aperture_dva or a smaller drawing_extent_dva")
            r = rasterize(o["cubes"], azimuth(cfg, v), camera, size, scale * ss, centre)
            gray = line_drawing(r.ids, line_px_ss, ss)
            name = image_name(o["id"], azimuth(cfg, v))
            files[name] = png_bytes(gray)
            images[name] = {
                "object": o["id"], "view": v, "azimuth_deg": azimuth(cfg, v),
                "extent_dva": round(extents[(o["id"], v)] * scale / px_per_dva, 4),
                "reach_dva": round(reach / px_per_dva, 4),
                "sha256": hashlib.sha256(files[name]).hexdigest(),
            }
    manifest = {
        "generator": "shepard_metzler1971.bank",
        "generator_version": GENERATOR_VERSION,
        "licence": "CC0-1.0 (generated by this script; no third-party material)",
        "stimulus_params": stimulus_signature(params),
        "mean_extent_dva": round(float(np.mean([i["extent_dva"] for i in images.values()])), 4),
        "objects": [{"id": o["id"], "set": o["set"], "mirror_of": o["mirror_of"],
                     "runs": [int(x) for x in o["runs"]],
                     "cubes": o["cubes"].astype(int).tolist(),
                     "views": [int(v) for v in o["views"]],
                     "azimuths_deg": [azimuth(cfg, v) for v in o["views"]],
                     "min_visible_fraction": [round(x, 4) for x in o["min_visible"]]}
                    for o in objects],
        "images": dict(sorted(images.items())),
    }
    return files, manifest


def stimulus_signature(params: MentalRotationParams) -> dict:
    """The params the bank is a function of: the task refuses a YAML that differs."""
    return {
        "aperture_dva": params.aperture_dva,
        "drawing_extent_dva": params.drawing_extent_dva,
        "line_width_dva": params.line_width_dva,
        "objects": params.objects.model_dump(mode="json"),
    }


def load_manifest(bank_dir: Path = BANK_DIR) -> dict:
    return json.loads((bank_dir / MANIFEST).read_text(encoding="utf-8"))


def check_matches(params: MentalRotationParams, bank_dir: Path = BANK_DIR) -> dict:
    """The committed bank's manifest, after checking it was made from these params."""
    manifest = load_manifest(bank_dir)
    if manifest["stimulus_params"] != stimulus_signature(params):
        raise ValueError(
            "the stimulus bank in stimuli/bank was generated from different stimulus "
            "params than this params file (aperture_dva, drawing_extent_dva, line_width_dva "
            "or objects). Regenerate it: uv run python -m shepard_metzler1971.bank --params "
            "<this file>")
    return manifest


def write(params: MentalRotationParams, bank_dir: Path = BANK_DIR) -> dict:
    files, manifest = generate(params)
    bank_dir.mkdir(parents=True, exist_ok=True)
    for old in bank_dir.glob("*.png"):
        if old.name not in files:
            old.unlink()
    for name, data in files.items():
        (bank_dir / name).write_bytes(data)
    (bank_dir / MANIFEST).write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    from alhazen.config.loader import load_params

    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--params", default=str(PROJECT / "configs" / "task.yaml"))
    ap.add_argument("--out", default=str(BANK_DIR))
    ap.add_argument("--check", action="store_true",
                    help="regenerate in memory and compare with the committed bank")
    a = ap.parse_args(argv)
    params = load_params(a.params, MentalRotationParams)
    out = Path(a.out)
    if not a.check:
        m = write(params, out)
        print(f"wrote {len(m['images'])} drawings of {len(m['objects'])} objects to {out}")
        return 0
    files, manifest = generate(params)
    committed = load_manifest(out)
    same = [n for n, d in files.items() if (out / n).is_file() and (out / n).read_bytes() == d]
    print(f"{len(same)}/{len(files)} drawings byte-identical; "
          f"manifest {'identical' if committed == json.loads(json.dumps(manifest)) else 'DIFFERS'}")
    return 0 if len(same) == len(files) and committed == json.loads(json.dumps(manifest)) else 1


if __name__ == "__main__":
    sys.exit(main())
