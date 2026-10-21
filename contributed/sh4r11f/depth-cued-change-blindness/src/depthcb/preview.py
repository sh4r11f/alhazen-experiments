"""Draw the stimulus preview, docs/preview.png: one trial's displays, in order.

    uv run python -m depthcb.preview            # writes docs/preview.png

Six panels, each a whole screen of the example booth rig (configs/rig-booth.yaml) drawn
at the sizes configs/task.yaml gives: the cue field (here FAR), the gray field, A, the
blank, A' (a far bicycle turns from blue to red; the flicker repeats A A A' A'), and the
location probe with two boxes on near objects and two on far ones. No window is needed.
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

import numpy as np
import yaml
from alhazen.config.loader import load_params
from PIL import Image, ImageDraw, ImageFont

from depthcb import photos, scenes
from depthcb.stimuli import render_text
from depthcb.task import PROJECT, DepthCuedFlickerTaskParams, scene_spec

PANEL_W = 520
SEED, PLANE, CHANGE = 11, "far", "color"
PHOTO = "plaza-cafe-far"  # the preview's pair: a far bicycle turns from blue to red


def _font(size: int):
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf", size)
    except OSError:
        return ImageFont.load_default(size=size)


def render(out: Path) -> Path:
    p = load_params(PROJECT / "configs" / "task-photos.yaml", DepthCuedFlickerTaskParams)
    rig = yaml.safe_load((PROJECT / "configs" / "rig-booth.yaml").read_text(encoding="utf-8"))
    m = rig["monitor"]
    deg = float(np.degrees(2 * np.arctan(m["width_cm"] / 2 / m["distance_cm"])))
    ppd = m["width_px"] / deg * PANEL_W / m["width_px"]
    ph = int(round(m["height_px"] * PANEL_W / m["width_px"]))
    spec = scene_spec(p)
    pair = (photos.load_pair(photos.scene_id(PHOTO), spec) if PHOTO in photos.catalogue()
            else scenes.generate(SEED, PLANE, CHANGE, spec))
    iw, ih = int(p.image_width_dva * ppd), int(p.image_height_dva * ppd)
    x0, y0 = (PANEL_W - iw) // 2, (ph - ih) // 2
    gray = (128, 128, 128)

    def panel(img=None):
        im = Image.new("RGB", (PANEL_W, ph), gray)
        if img is not None:
            im.paste(img.resize((iw, ih), Image.LANCZOS), (x0, y0))
        return im, ImageDraw.Draw(im)

    cue, d = panel()
    bw, bh = p.cue_box_width_dva * ppd, p.cue_box_height_dva * ppd
    card = tuple(int(round((c + 1) / 2 * 255)) for c in p.cue_style.card)
    d.rectangle(((PANEL_W - bw) / 2, (ph - bh) / 2, (PANEL_W + bw) / 2, (ph + bh) / 2),
                fill=card)
    word = render_text(p.cue_words.far, p.cue_cap_height_dva * ppd, tuple(p.cue_style.ink),
                       weight=p.cue_style.weight, tracking_em=p.cue_style.tracking_em)
    cue.paste(word, (int(PANEL_W / 2 - word.width / 2), int(ph / 2 - word.height / 2)), word)
    blank_g, d = panel()
    if p.fixation.show_on_gray:  # the ABC target (Thaler et al. 2013)
        ro, ri, c = p.fixation.outer_dva * ppd / 2, p.fixation.inner_dva * ppd / 2, PANEL_W / 2
        ink = tuple(int(round((v + 1) / 2 * 255)) for v in p.fixation.color)
        d.ellipse((c - ro, ph / 2 - ro, c + ro, ph / 2 + ro), fill=ink)
        d.rectangle((c - ro - 1, ph / 2 - ri, c + ro + 1, ph / 2 + ri), fill=gray)
        d.rectangle((c - ri, ph / 2 - ro - 1, c + ri, ph / 2 + ro + 1), fill=gray)
        d.ellipse((c - ri, ph / 2 - ri, c + ri, ph / 2 + ri), fill=ink)
    a, _ = panel(pair.image_a)
    blank, _ = panel()
    b, _ = panel(pair.image_b)
    probe, d = panel(pair.image_a)
    boxes, _, _ = scenes.probe_boxes(pair, p.location_probe.n_choices,
                                     p.location_probe.box_side_dva, spec,
                                     np.random.default_rng(4))
    for key, bx in zip(p.location_probe.keys, boxes, strict=False):
        r = (x0 + bx[0] * iw, y0 + bx[1] * ih, x0 + bx[2] * iw, y0 + bx[3] * ih)
        d.rectangle(r, outline=(15, 15, 20), width=2)
        tag = 0.9 * ppd
        d.rectangle((r[0], r[1], r[0] + tag, r[1] + tag), fill=(15, 15, 20))
        label = render_text(key, tag * 0.55, (1.0, 1.0, 1.0))
        probe.paste(label, (int(r[0] + tag / 2 - label.width / 2),
                            int(r[1] + tag / 2 - label.height / 2)), label)

    fr = lambda d_: f"{d_.ms:g} ms" if d_.ms is not None else f"{d_.frames} frames"  # noqa: E731
    labels = [f"depth cue {fr(p.cue_field)}: NEAR or FAR", f"gray {fr(p.gray_field)} + fixation",
              f"A {fr(p.flicker.image)}", f"blank {fr(p.flicker.blank)}",
              f"A' {fr(p.flicker.image)} (A A A' A' ...)",
              "where? 1-4, then what kind (arrows)"]
    gap, label_h = 10, 24
    sheet = Image.new("RGB", (3 * PANEL_W + 2 * gap, 2 * (ph + label_h) + gap), (250, 250, 248))
    ds = ImageDraw.Draw(sheet)
    tf = _font(14)
    for i, (im, text) in enumerate(zip([cue, blank_g, a, blank, b, probe], labels, strict=True)):
        x, y = (i % 3) * (PANEL_W + gap), (i // 3) * (ph + label_h + gap)
        sheet.paste(im, (x, y))
        ds.text((x + 4, y + ph + 4), text, fill=(30, 30, 30), font=tf)
    out.parent.mkdir(parents=True, exist_ok=True)
    buf = io.BytesIO()
    sheet.quantize(colors=256, method=Image.Quantize.MEDIANCUT).save(buf, "PNG", optimize=True)
    out.write_bytes(buf.getvalue())
    return out


if __name__ == "__main__":
    print(render(Path(sys.argv[1]) if len(sys.argv) > 1 else PROJECT / "docs" / "preview.png"))
