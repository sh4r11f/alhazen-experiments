"""Draw the stimulus preview, docs/preview.png: what one trial's display looks like.

    uv run python -m raymond1992.preview            # writes docs/preview.png

Left: the whole display at scale (the 16.3° x 12.5° grey field, the letter in its
centre). Right: a strip of 3° crops around the letter, one per item of an example
stream with the probe X at serial position +2, labelled with each item's onset relative
to the white target (k x 90 ms; each letter is on for 15 ms of its 90). Drawn with the
same glyphs and the same params file as the task, so it needs no window. Luminances are
shown as fractions of the configured display white, encoded for an sRGB screen.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from alhazen.config.loader import load_params  # noqa: E402

from raymond1992 import design  # noqa: E402
from raymond1992.glyphs import glyph  # noqa: E402
from raymond1992.task import PROJECT, AttentionalBlinkTaskParams  # noqa: E402

PX_PER_DEG = 60.0  # rendering resolution of the crops


def _shade(cd_m2: float, white: float) -> float:
    return float(np.clip(cd_m2 / white, 0.0, 1.0) ** (1 / 2.2))


def _crop(p: AttentionalBlinkTaskParams, letter: str | None, colour: float, dot: bool,
          size_deg: float = 3.0) -> np.ndarray:
    n = int(round(size_deg * PX_PER_DEG))
    img = np.full((n, n), _shade(p.field_cd_m2, p.display_white_cd_m2))
    if dot:
        yy, xx = np.mgrid[:n, :n]
        r = p.fixation_dot_dva * PX_PER_DEG / 2
        img[(yy - n / 2 + 0.5) ** 2 + (xx - n / 2 + 0.5) ** 2 <= r * r] = colour
    if letter:
        g = glyph(letter, p.letter_height_dva * PX_PER_DEG)
        top = int(round(n / 2 - g.cap_center_y))
        left = int(round(n / 2 - g.width_px / 2))
        region = img[top : top + g.height_px, left : left + g.width_px]
        img[top : top + g.height_px, left : left + g.width_px] = (
            region * (1 - g.alpha) + colour * g.alpha
        )
    return img


def render(out: Path, params_file: Path | None = None) -> Path:
    p = load_params(params_file or PROJECT / "configs" / "task.yaml", AttentionalBlinkTaskParams)
    white = p.display_white_cd_m2
    stream = design.make_stream(np.random.default_rng(7), 2, p.pretarget_min, p.pretarget_max,
                                p.posttarget_items)
    soa = p.letter_duration.ms + p.isi.ms if p.letter_duration.ms is not None else 90.0
    black = _shade(p.letters_cd_m2, white)
    target = _shade(p.target_cd_m2, white)

    fig = plt.figure(figsize=(11, 4.2), dpi=110)
    fig.patch.set_facecolor("#ffffff")
    ax = fig.add_axes((0.01, 0.12, 0.30, 0.76))
    ax.set_facecolor(str(_shade(p.surround_cd_m2, white)))
    w, h = p.field_width_dva, p.field_height_dva
    ax.add_patch(plt.Rectangle((-w / 2, -h / 2), w, h, color=str(_shade(p.field_cd_m2, white))))
    g = glyph(stream.target, p.letter_height_dva * 40)
    gw, gh = g.width_px / 40, g.height_px / 40
    cy = g.cap_center_y / 40
    ax.imshow(np.dstack([np.full(g.alpha.shape, target)] * 3 + [g.alpha]),
              extent=(-gw / 2, gw / 2, cy - gh, cy), zorder=3, interpolation="lanczos")
    ax.set_xlim(-w / 2 - 1.2, w / 2 + 1.2)
    ax.set_ylim(-h / 2 - 1.2, h / 2 + 1.2)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(f"the display at scale: {w}° x {h}° field, letters {p.letter_height_dva}°",
                 fontsize=9)

    items: list[tuple[str, np.ndarray]] = [("fixation\n180 ms", _crop(p, None, target, True))]
    for k in range(-2, 5):
        i = stream.target_index + k
        letter = stream.letters[i]
        is_target = k == 0
        img = _crop(p, letter, target if is_target else black, False)
        name = "target" if is_target else ("probe X" if i == stream.probe_index else f"{k:+d}")
        items.append((f"{name}\n{k * soa:+.0f} ms", img))
    n = len(items)
    x0, width = 0.33, 0.66
    cell = width / n
    for j, (label, img) in enumerate(items):
        a = fig.add_axes((x0 + j * cell + 0.004, 0.30, cell - 0.008, 0.48))
        a.imshow(img, cmap="gray", vmin=0, vmax=1, interpolation="lanczos")
        a.set_xticks([])
        a.set_yticks([])
        for s in a.spines.values():
            s.set_color("#bbbbbb")
        a.set_xlabel(label, fontsize=8.5)
    fig.text(x0 + width / 2, 0.86,
             f"RSVP at one location: each letter {p.letter_duration.ms:.0f} ms on, "
             f"{p.isi.ms:.0f} ms grey (SOA {soa:.0f} ms); 3° crops", ha="center", fontsize=9)
    fig.text(x0 + width / 2, 0.06,
             "experimental: name the white letter, then X yes/no   ·   control: ignore the "
             "white letter, X yes/no", ha="center", fontsize=8.5, color="#444444")
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, facecolor=fig.get_facecolor())
    plt.close(fig)
    return out


if __name__ == "__main__":
    print(render(Path(sys.argv[1]) if len(sys.argv) > 1 else PROJECT / "docs" / "preview.png"))
