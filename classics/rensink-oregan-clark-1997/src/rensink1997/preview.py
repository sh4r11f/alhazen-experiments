"""Draw the stimulus preview, docs/preview.png: what one trial's display looks like.

    uv run python -m rensink1997.preview            # writes docs/preview.png

Six panels in trial order, each a whole screen of the example booth rig
(configs/rig-booth.yaml) drawn at the sizes the task computes from configs/task.yaml:
the cue field, the gray field, A, the blank, A' (the flicker repeats A A A' A'), and the
location probe. The scene is the shipped photo pair "car" (a colour change).
No window is needed.
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

import numpy as np
import yaml
from alhazen.config.loader import load_params
from alhazen.display.screen import Screen
from PIL import Image, ImageDraw, ImageFont

from rensink1997 import scenes
from rensink1997.task import PROJECT, FlickerChangeDetectionTaskParams

PANEL_W = 400  # px per panel in the preview
SCENE = "photo/car"


def _screen() -> tuple[Screen, int, int]:
    rig = yaml.safe_load((PROJECT / "configs" / "rig-booth.yaml").read_text(encoding="utf-8"))
    m = rig["monitor"]
    deg = float(np.degrees(2 * np.arctan(m["width_cm"] / 2 / m["distance_cm"])))
    return Screen(width_px=m["width_px"], height_px=m["height_px"],
                  px_per_deg=m["width_px"] / deg), m["width_px"], m["height_px"]


def _gray(p: FlickerChangeDetectionTaskParams) -> tuple[int, int, int]:
    v = int(round((p.background_gray + 1) / 2 * 255))
    return (v, v, v)


def render(out: Path) -> Path:
    p = load_params(PROJECT / "configs" / "task.yaml", FlickerChangeDetectionTaskParams)
    screen, sw, sh = _screen()
    scale = PANEL_W / sw
    ph = int(round(sh * scale))
    pair = scenes.load(SCENE)
    iw, ih = screen.deg2px(p.image_width_dva) * scale, screen.deg2px(p.image_height_dva) * scale
    x0, y0 = (PANEL_W - iw) / 2, (ph - ih) / 2
    img_a = pair.image_a.resize((int(iw), int(ih)), Image.LANCZOS)
    img_b = pair.image_b.resize((int(iw), int(ih)), Image.LANCZOS)

    def panel():
        im = Image.new("RGB", (PANEL_W, ph), _gray(p))
        return im, ImageDraw.Draw(im)

    cue, d = panel()
    bw, bh = screen.deg2px(p.cue_box_width_dva) * scale, screen.deg2px(p.cue_box_height_dva) * scale
    d.rectangle(((PANEL_W - bw) / 2, (ph - bh) / 2, (PANEL_W + bw) / 2, (ph + bh) / 2),
                fill="white")
    gray, _ = panel()
    a, _ = panel()
    a.paste(img_a, (int(x0), int(y0)))
    blank, _ = panel()
    b, _ = panel()
    b.paste(img_b, (int(x0), int(y0)))
    probe, d = panel()
    probe.paste(img_a, (int(x0), int(y0)))
    boxes, _ = scenes.probe_boxes(pair, p.location_probe.n_choices,
                                  (p.location_probe.min_side_dva / p.image_width_dva,
                                   p.location_probe.max_side_dva / p.image_width_dva),
                                  p.image_width_dva / p.image_height_dva,
                                  np.random.default_rng(4))
    font = ImageFont.load_default(size=11)
    for key, bx in zip(p.location_probe.keys, boxes, strict=False):
        r = (x0 + bx[0] * iw, y0 + bx[1] * ih, x0 + bx[2] * iw, y0 + bx[3] * ih)
        d.rectangle(r, outline=(255, 255, 0), width=2)
        d.text((r[0] + 3, r[1] + 1), key, fill=(255, 255, 0), font=font)

    fr = lambda d_: f"{d_.ms:g} ms" if d_.ms is not None else f"{d_.frames} frames"  # noqa: E731
    labels = [f"cue field {fr(p.cue_field)}", f"gray field {fr(p.gray_field)}",
              f"A {fr(p.flicker.image)}", f"blank {fr(p.flicker.blank)}",
              f"A' {fr(p.flicker.image)} (A A A' A' ...)",
              "where? keys 1-4, then the kind (arrows)"]
    gap, label_h = 8, 22
    sheet = Image.new("RGB", (3 * PANEL_W + 2 * gap, 2 * (ph + label_h) + gap), (250, 250, 248))
    ds = ImageDraw.Draw(sheet)
    lf = ImageFont.load_default(size=14)
    for i, (im, text) in enumerate(zip([cue, gray, a, blank, b, probe], labels, strict=False)):
        x, y = (i % 3) * (PANEL_W + gap), (i // 3) * (ph + label_h + gap)
        sheet.paste(im, (x, y))
        ds.text((x + 4, y + ph + 3), text, fill=(30, 30, 30), font=lf)
    out.parent.mkdir(parents=True, exist_ok=True)
    buf = io.BytesIO()
    sheet.quantize(colors=256, method=Image.Quantize.MEDIANCUT).save(buf, "PNG", optimize=True)
    out.write_bytes(buf.getvalue())
    return out


if __name__ == "__main__":
    print(render(Path(sys.argv[1]) if len(sys.argv) > 1 else PROJECT / "docs" / "preview.png"))
