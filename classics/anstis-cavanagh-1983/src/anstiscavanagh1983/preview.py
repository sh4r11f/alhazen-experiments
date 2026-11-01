"""Draw the stimulus preview, docs/preview.png: one cycle of Experiment 1's display.

    uv run python -m anstiscavanagh1983.preview            # writes docs/preview.png

The four gratings T1-T4 are the arrays the task draws (stimulus.frames) for
configs/task.yaml at a test level below the reference (red 10.0 vs green 13.4 cd/m2),
steps rightward, at 40 px/deg, from the example photometry, then encoded as sRGB for a
picture. They are shown side by side in time order: on the screen they occupy the same
place, one after the other, each for 3 frames (50 ms) at 60 Hz. Under each, the summed
luminance across the patch (cd/m2): the colour gratings carry a small modulation only
because red is darker than green here; the light/dark grating carries 6.25%.
The ticks mark where one red bar's (T1, T3) or light bar's (T2, T4) left edge is: each
grating is a quarter cycle to the right of the one before. Illustrative and uncalibrated:
a monitor shows these colours only as the example photometry assumes.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from alhazen.config.loader import load_params  # noqa: E402

from anstiscavanagh1983.common import PROJECT, grating_geometry  # noqa: E402
from anstiscavanagh1983.constant import ConstantParams  # noqa: E402
from anstiscavanagh1983.stimulus import Spec, frames, stroke_luminance  # noqa: E402

PX_PER_DEG = 40.0
TEST_CD_M2 = 10.0
INK, MUTED, PAPER = "#1f1b17", "#6b645c", "#fbf9f5"


def srgb(linear: np.ndarray) -> np.ndarray:
    x = np.clip(linear, 0.0, 1.0)
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * x ** (1 / 2.4) - 0.055)


def cycle(params_file: Path | None = None) -> tuple[Spec, list[np.ndarray], list[np.ndarray]]:
    p = load_params(params_file or PROJECT / "configs" / "task.yaml", ConstantParams)
    period, _ = grating_geometry(PX_PER_DEG, p.spatial_freq_cpd, True)
    size = int(round(p.patch_size_dva * PX_PER_DEG))
    spec = Spec("four_stroke", p.test_colour, p.reference_colour, TEST_CD_M2, p.reference_cd_m2,
                size, period, 1, 0, p.interleave_contrast, p.interleave_mix, p.dither_rows)
    space = p.colour_space()
    imgs = frames(spec, space, PX_PER_DEG, p.fix())
    lums = [stroke_luminance(spec, space, k)[0].sum(axis=1) for k in range(4)]
    return spec, imgs, lums


def render(out: Path) -> Path:
    spec, imgs, lums = cycle()
    labels = ["T1  red | green", "T2  light | dark", "T3  green | red", "T4  dark | light"]
    fig, axes = plt.subplots(2, 4, figsize=(8.4, 3.6), dpi=150,
                             gridspec_kw={"height_ratios": [3, 1.1], "hspace": 0.12})
    fig.patch.set_facecolor(PAPER)
    n, q = spec.size_px, spec.period_px // 4
    lo = min(v.min() for v in lums)
    hi = max(v.max() for v in lums)
    for k in range(4):
        ax = axes[0, k]
        pad = np.zeros((n + 16, n + 16, 3))  # dark surround around the 2 x 2 deg patch
        pad[8:-8, 8:-8] = imgs[k]
        ax.imshow(srgb(pad), interpolation="nearest")
        edge = 8 + (spec.offset_px + k * q) % spec.period_px
        ax.plot([edge - 0.5, edge - 0.5], [-10, 3], color="#7f1d1d", lw=1.6, clip_on=False)
        ax.set_title(labels[k], fontsize=8, color=INK, loc="left")
        ax.axis("off")
        b = axes[1, k]
        b.step(np.arange(n), lums[k], where="mid", color=INK, lw=0.9)
        b.set_ylim(lo - 0.6, hi + 0.6)
        b.set_xlim(-4, n + 4)
        b.set_facecolor(PAPER)
        for side in ("top", "right"):
            b.spines[side].set_visible(False)
        b.tick_params(labelsize=6, colors=MUTED)
        if k:
            b.set_yticklabels([])
        else:
            b.set_ylabel("cd/m²", fontsize=6, color=MUTED)
        b.set_xticks([0, n / 2, n])
        b.set_xticklabels(["0", "1", "2 deg"])
    fig.text(0.01, 0.01, "One cycle in time order, same place on screen; 50 ms each. "
             "Red 10.0 vs green 13.4 cd/m². Illustrative, uncalibrated sRGB.",
             fontsize=6.5, color=MUTED)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, facecolor=fig.get_facecolor(), bbox_inches="tight", pad_inches=0.08)
    plt.close(fig)
    return out


if __name__ == "__main__":
    print(render(Path(sys.argv[1]) if len(sys.argv) > 1 else PROJECT / "docs" / "preview.png"))
