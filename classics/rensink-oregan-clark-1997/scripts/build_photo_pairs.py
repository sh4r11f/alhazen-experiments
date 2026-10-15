"""Build the photographic scene pairs (A, A') from generated photographs.

    uv run --extra assets python scripts/build_photo_pairs.py --raw <folder>

<folder> holds, for every scene in src/rensink1997/photos/spec.json, the two images an
image model produced for this project: `<id>_base.png` (the scene) and
`<id>_removed.png` (an edit of that scene with ONE object removed). They are not shipped:
the composited pairs are the canonical assets. The prompts and models that made them are
in spec.json, so they can be regenerated.

Image-model edits never keep the rest of the picture pixel-identical, so the edit is not
used as A' directly. The builder takes the object's mask from the base/edit difference
(restricted to the scene's `region` when given), then composites so that A and A' differ
ONLY inside that mask:

- presence: A = base; A' = base with the masked area taken from the edit (object gone).
- color:    A = base (object blue); A' = base with the object's saturated blue pixels
            rotated in hue by `hue_shift` (blue -> red), so shading and texture are kept.
- location: a clean plate = base with the masked area taken from the edit; A = plate with
            the object pasted back (moved by `place_dy` when given); A' = plate with the
            object pasted `shift_dx` px further along x (3 deg at 1024 px = 27 deg).

Then both images are cropped to 3:2 at `crop_top` and saved as JPEG (<= 300 KB). The
geometry of the change (bounding box, area) is measured from |A - A'| and written to
photos/pairs.json, which the task reads.
"""

from __future__ import annotations

import argparse
import colorsys  # noqa: F401  (documents the HSV convention used below)
import io
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

PHOTOS = Path(__file__).resolve().parents[1] / "src" / "rensink1997" / "photos"
MAX_BYTES = 300_000


def object_mask(base: np.ndarray, removed: np.ndarray, region, thr: float = 30.0) -> np.ndarray:
    d = np.abs(base.astype(float) - removed.astype(float)).max(-1)
    d = ndi.gaussian_filter(d, 1.5)
    m = d > thr
    if region:
        x0, y0, x1, y1 = region
        box = np.zeros_like(m)
        box[y0:y1, x0:x1] = True
        m &= box
    m = ndi.binary_opening(m)
    lab, n = ndi.label(m)
    if n == 0:
        raise SystemExit("no difference found between base and removal")
    sizes = ndi.sum(m, lab, range(1, n + 1))
    keep = np.isin(lab, [i + 1 for i, s in enumerate(sizes) if s >= 0.15 * sizes.max()])
    keep = ndi.binary_fill_holes(ndi.binary_closing(keep, iterations=4))
    return keep


def feather(mask: np.ndarray, grow: int, soft: float) -> np.ndarray:
    m = ndi.binary_dilation(mask, iterations=grow) if grow > 0 else mask
    return np.clip(ndi.gaussian_filter(m.astype(float), soft), 0, 1)[..., None]


def shift(arr: np.ndarray, dx: int, dy: int) -> np.ndarray:
    out = np.zeros_like(arr)
    h, w = arr.shape[:2]
    ys, yd = (slice(0, h - dy), slice(dy, h)) if dy >= 0 else (slice(-dy, h), slice(0, h + dy))
    xs, xd = (slice(0, w - dx), slice(dx, w)) if dx >= 0 else (slice(-dx, w), slice(0, w + dx))
    out[yd, xd] = arr[ys, xs]
    return out


def recolor(img: np.ndarray, mask: np.ndarray, hue_shift: float) -> np.ndarray:
    """Rotate the hue of saturated blue pixels inside the mask (HSV, hue in [0, 1))."""
    rgb = img.astype(float) / 255.0
    mx, mn = rgb.max(-1), rgb.min(-1)
    v, c = mx, mx - mn
    s = np.where(mx > 0, c / np.maximum(mx, 1e-9), 0)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    h = np.zeros_like(mx)
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
    return np.clip(out * 255 + 0.5, 0, 255).astype(np.uint8)


def compose(scene: dict, base: np.ndarray, removed: np.ndarray, spec: dict):
    m = object_mask(base, removed, scene.get("region"))
    kind = scene["change_type"]
    if kind == "presence":
        a = base
        w = feather(m, 3, 1.5)
        b = (base * (1 - w) + removed * w).astype(np.uint8)
    elif kind == "color":
        a = base
        b = recolor(base, ndi.binary_dilation(m, iterations=2), spec["hue_shift"])
    elif kind == "location":
        w_out = feather(m, 4, 1.5)
        plate = (base * (1 - w_out) + removed * w_out)
        w_obj = feather(m, 0, 1.0)
        dy = int(scene.get("place_dy", 0))
        dx = int(scene["shift_dx"])

        def paste(dx_, dy_):
            o, ww = shift(base, dx_, dy_), shift(w_obj, dx_, dy_)
            return (plate * (1 - ww) + o * ww).astype(np.uint8)

        a, b = paste(0, dy), paste(dx, dy)
    else:
        raise SystemExit(f"unknown change type {kind}")
    top, hgt = int(scene["crop_top"]), int(spec["crop_height_px"])
    return a[top:top + hgt], b[top:top + hgt]


def save_jpeg(arr: np.ndarray, path: Path) -> int:
    for q in (90, 86, 82, 78, 74, 70):
        buf = io.BytesIO()
        Image.fromarray(arr).save(buf, "JPEG", quality=q, optimize=True, progressive=True)
        if buf.tell() <= MAX_BYTES:
            break
    path.write_bytes(buf.getvalue())
    return buf.tell()


def change_geometry(a: np.ndarray, b: np.ndarray) -> dict:
    d = np.abs(a.astype(int) - b.astype(int)).max(-1) > 24
    d = ndi.binary_opening(d)
    h, w = d.shape
    ys, xs = np.nonzero(d)
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
    args = ap.parse_args(argv)
    spec = json.loads((PHOTOS / "spec.json").read_text(encoding="utf-8"))
    pairs = []
    for scene in spec["scenes"]:
        sid = scene["id"]
        base = np.asarray(Image.open(args.raw / f"{sid}_base.png").convert("RGB"))
        removed = np.asarray(
            Image.open(args.raw / f"{sid}_removed.png").convert("RGB").resize(base.shape[1::-1])
        )
        a, b = compose(scene, base, removed, spec)
        na = save_jpeg(a, args.out / f"{sid}_a.jpg")
        nb = save_jpeg(b, args.out / f"{sid}_b.jpg")
        geo = change_geometry(a, b)
        pairs.append({"id": sid, "change_type": scene["change_type"],
                      "object": scene["object"], "cue_valid": scene["cue_valid"],
                      "cue_invalid": scene["cue_invalid"],
                      "image_a": f"{sid}_a.jpg", "image_b": f"{sid}_b.jpg",
                      "size_px": [int(a.shape[1]), int(a.shape[0])], **geo})
        print(f"{sid:11s} {geo['area_fraction']:.4f} of the image  {na // 1000} + {nb // 1000} KB")
    (args.out / "pairs.json").write_text(json.dumps({"pairs": pairs}, indent=1) + "\n",
                                         encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
