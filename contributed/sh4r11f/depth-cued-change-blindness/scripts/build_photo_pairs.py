"""Build the photograph scene pairs (A, A') from generated photographs.

    uv run python scripts/build_photo_pairs.py --raw <folder> [--only <id> ...]

<folder> holds, for every scene in src/depthcb/photos/spec.json, the two images an image
model produced for this experiment: ``<id>_base.png`` (the scene, 1536 x 1024) and
``<id>_removed.png`` (an edit of that scene with ONE object removed). They are not
shipped: the composited pairs are the canonical assets, and spec.json records the prompts
and models, so they can be regenerated.

Image-model edits never keep the rest of the picture pixel-identical, so the edit is not
used as A' directly. The changed object's mask is the largest region where base and edit
differ (plus nearby pieces of it); then A and A' are composited so that they differ ONLY
inside that mask:

- presence: one image is the base, the other the base with the masked area taken from the
            edit (object gone). Which of A and A' holds the object alternates over the set.
- color:    A = base (object blue); A' = base with the object's blue pixels rotated in hue
            by ``hue_shift`` (blue -> red), so shading and texture are kept.
- location: a clean plate = base with the masked area taken from the edit; A = plate with
            the object pasted back; A' = plate with the object pasted ``location_shift_dva``
            further along x, toward the picture's vertical midline.

Both images are resized to ``out_px`` (27 x 18 dva) and saved as JPEG of about 95 KB. The
geometry of the change (bounding box, centroid, area) is measured from |A - A'| and written to
photos/pairs.json together with the foils of the location report (spec.json: ``foils``,
other named objects on each layer, placed by hand on the base photograph).
"""

from __future__ import annotations

import argparse
import io
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

PHOTOS = Path(__file__).resolve().parents[1] / "src" / "depthcb" / "photos"
MAX_BYTES = 95_000  # 108 images must fit the Experiment Platform bundle (12 MB of binaries)


def object_mask(base: np.ndarray, removed: np.ndarray, px_per_dva: float,
                thr: float = 28.0) -> np.ndarray:
    """The removed object: the largest connected region of |base - edit| > thr, plus
    other pieces at least 15% of its size within 1.5 dva of it (a handle, a reflection)."""
    d = ndi.gaussian_filter(np.abs(base.astype(float) - removed.astype(float)).max(-1), 1.5)
    m = ndi.binary_opening(d > thr, iterations=2)
    lab, n = ndi.label(m)
    if n == 0:
        raise SystemExit("no difference found between base and removal")
    sizes = ndi.sum(m, lab, range(1, n + 1))
    main = lab == (int(np.argmax(sizes)) + 1)
    near = ndi.binary_dilation(main, iterations=int(1.5 * px_per_dva))
    keep = main.copy()
    for i, s in enumerate(sizes):
        piece = lab == i + 1
        if s >= 0.15 * sizes.max() and (piece & near).any():
            keep |= piece
    return ndi.binary_fill_holes(ndi.binary_closing(keep, iterations=4))


def feather(mask: np.ndarray, grow: int, soft: float) -> np.ndarray:
    m = ndi.binary_dilation(mask, iterations=grow) if grow > 0 else mask
    return np.clip(ndi.gaussian_filter(m.astype(float), soft), 0, 1)[..., None]


def shift(arr: np.ndarray, dx: int) -> np.ndarray:
    out = np.zeros_like(arr)
    if dx >= 0:
        out[:, dx:] = arr[:, : arr.shape[1] - dx]
    else:
        out[:, :dx] = arr[:, -dx:]
    return out


def recolor(img: np.ndarray, mask: np.ndarray, hue_shift: float) -> tuple[np.ndarray, int]:
    """Rotate the hue of saturated blue pixels inside the mask (HSV, hue in [0, 1)).
    Returns the image and the number of pixels recoloured."""
    rgb = img.astype(float) / 255.0
    mx, mn = rgb.max(-1), rgb.min(-1)
    v, c = mx, mx - mn
    s = np.where(mx > 0, c / np.maximum(mx, 1e-9), 0)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    nz = c > 1e-9
    rc = np.where(nz, (mx - r) / np.maximum(c, 1e-9), 0)
    gc = np.where(nz, (mx - g) / np.maximum(c, 1e-9), 0)
    bc = np.where(nz, (mx - b) / np.maximum(c, 1e-9), 0)
    h = np.where(r == mx, bc - gc, np.where(g == mx, 2.0 + rc - bc, 4.0 + gc - rc))
    h = (h / 6.0) % 1.0
    blue = mask & nz & (s > 0.18) & (h > 0.48) & (h < 0.78)
    h2 = np.where(blue, (h + hue_shift) % 1.0, h)
    i = np.floor(h2 * 6).astype(int) % 6
    f = h2 * 6 - np.floor(h2 * 6)
    p, q, t = v * (1 - s), v * (1 - s * f), v * (1 - s * (1 - f))
    choices = [(v, t, p), (q, v, p), (p, v, t), (p, q, v), (t, p, v), (v, p, q)]
    out = np.zeros_like(rgb)
    for k, (cr, cg, cb) in enumerate(choices):
        sel = i == k
        out[..., 0] = np.where(sel, cr, out[..., 0])
        out[..., 1] = np.where(sel, cg, out[..., 1])
        out[..., 2] = np.where(sel, cb, out[..., 2])
    out = np.where(blue[..., None], out, rgb)
    soft = np.clip(ndi.gaussian_filter(blue.astype(float), 1.0), 0, 1)[..., None]
    out = rgb * (1 - soft) + out * soft
    return np.clip(out * 255 + 0.5, 0, 255).astype(np.uint8), int(blue.sum())


def compose(scene: dict, base: np.ndarray, removed: np.ndarray, spec: dict, swap: bool):
    px_per_dva = base.shape[1] / spec["image_dva"][0]
    m = object_mask(base, removed, px_per_dva)
    kind = scene["change_type"]
    info: dict = {"mask_px": int(m.sum())}
    if kind == "presence":
        w = feather(m, 3, 1.5)
        gone = (base * (1 - w) + removed * w).astype(np.uint8)
        a, b = (gone, base) if swap else (base, gone)
        info["present_in"] = "B" if swap else "A"
    elif kind == "color":
        a = base
        b, n = recolor(base, ndi.binary_dilation(m, iterations=2), spec["hue_shift"])
        info["recoloured_px"] = n
    elif kind == "location":
        plate = base * (1 - feather(m, 4, 1.5)) + removed * feather(m, 4, 1.5)
        w_obj = feather(m, 0, 1.0)
        cx = float(np.nonzero(m)[1].mean()) / base.shape[1]
        dx = int(round(spec["location_shift_dva"] * px_per_dva)) * (1 if cx < 0.5 else -1)

        def paste(dx_):
            return (plate * (1 - shift(w_obj, dx_)) + shift(base, dx_) * shift(w_obj, dx_)
                    ).astype(np.uint8)

        a, b = paste(0), paste(dx)
        info["shift_px_raw"] = dx
    else:
        raise SystemExit(f"unknown change type {kind}")
    size = tuple(spec["out_px"])
    a = np.asarray(Image.fromarray(a).resize(size, Image.LANCZOS))
    b = np.asarray(Image.fromarray(b).resize(size, Image.LANCZOS))
    return a, b, info


def save_jpeg(arr: np.ndarray, path: Path) -> int:
    for q in (92, 90, 88, 86, 84, 82, 80, 78, 76, 74, 72, 70, 68, 66, 64, 62, 60):
        buf = io.BytesIO()
        Image.fromarray(arr).save(buf, "JPEG", quality=q, optimize=True, progressive=True)
        if buf.tell() <= MAX_BYTES:
            break
    path.write_bytes(buf.getvalue())
    return buf.tell()


def change_geometry(a: np.ndarray, b: np.ndarray) -> dict:
    d = ndi.binary_opening(np.abs(a.astype(int) - b.astype(int)).max(-1) > 24)
    h, w = d.shape
    ys, xs = np.nonzero(d)
    if len(xs) == 0:
        raise SystemExit("A and A' do not differ")
    return {
        "bbox": [round(xs.min() / w, 4), round(ys.min() / h, 4),
                 round((xs.max() + 1) / w, 4), round((ys.max() + 1) / h, 4)],
        "centroid": [round(float(xs.mean()) / w, 4), round(float(ys.mean()) / h, 4)],
        "area_fraction": round(float(d.mean()), 5),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True, type=Path)
    ap.add_argument("--out", type=Path, default=PHOTOS)
    ap.add_argument("--only", nargs="*")
    args = ap.parse_args(argv)
    spec = json.loads((PHOTOS / "spec.json").read_text(encoding="utf-8"))
    W, H = spec["image_dva"]
    old = {}
    if (args.out / "pairs.json").exists():
        old = {p["id"]: p for p in json.loads((args.out / "pairs.json").read_text())["pairs"]}
    pairs = []
    presence = [s["id"] for s in spec["scenes"] if s["change_type"] == "presence"]
    for scene in spec["scenes"]:
        sid = scene["id"]
        if scene.get("exclude"):
            continue
        if args.only and sid not in args.only and sid in old:
            pairs.append(old[sid])
            continue
        base = np.asarray(Image.open(args.raw / f"{sid}_base.png").convert("RGB"))
        removed = np.asarray(Image.open(args.raw / f"{sid}_removed.png").convert("RGB")
                             .resize(base.shape[1::-1], Image.LANCZOS))
        swap = scene["change_type"] == "presence" and presence.index(sid) % 2 == 1
        a, b, info = compose(scene, base, removed, spec, swap)
        na = save_jpeg(a, args.out / f"{sid}_a.jpg")
        nb = save_jpeg(b, args.out / f"{sid}_b.jpg")
        geo = change_geometry(a, b)
        cx, cy = geo["centroid"]
        ecc = math.hypot((cx - 0.5) * W, (cy - 0.5) * H)
        pairs.append({"id": sid, "set": scene["set"], "setting": scene["setting_id"],
                      "plane": scene["plane"], "change_type": scene["change_type"],
                      "object": scene["target"], "image_a": f"{sid}_a.jpg",
                      "image_b": f"{sid}_b.jpg", "size_px": list(spec["out_px"]), **geo,
                      "eccentricity_dva": round(ecc, 2),
                      "area_dva2": round(geo["area_fraction"] * W * H, 2),
                      "foils": scene.get("foils", []), "build": info})
        print(f"{sid:22s} {scene['plane']:4s} {scene['change_type']:8s} ecc {ecc:5.1f} dva  "
              f"area {geo['area_fraction'] * W * H:6.2f} dva2  {(na + nb) // 1000} KB")
    (args.out / "pairs.json").write_text(json.dumps({"pairs": pairs}, indent=1) + "\n",
                                         encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
