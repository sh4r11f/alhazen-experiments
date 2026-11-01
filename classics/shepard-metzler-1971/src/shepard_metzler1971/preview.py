"""Draw the stimulus preview, docs/preview.png: what a trial's display looks like.

    uv run python -m shepard_metzler1971.preview            # writes docs/preview.png

Three displays like the paper's Fig. 1, drawn from the real parameters and the real
stimulus bank: (A) a "same" pair 80 deg apart in the picture plane, (B) a "same" pair
80 deg apart in depth, (C) a "different" pair (one side, named from the design, shows the
mirror-image object).
Rendered with matplotlib, so it needs no window.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from alhazen.config.loader import load_params  # noqa: E402
from matplotlib.transforms import Affine2D  # noqa: E402

from shepard_metzler1971 import bank, design  # noqa: E402
from shepard_metzler1971.params import MentalRotationParams  # noqa: E402
from shepard_metzler1971.task import PROJECT  # noqa: E402

PANELS = [("A", "P-o01-a080-1-S", "same: 80° in the picture plane"),
          ("B", "D-o01-a080-1-S", "same: 80° in depth"),
          ("C", "D-o01-a080-1-D", None)]


def render(out: Path, params_file: Path | None = None) -> Path:
    p = load_params(params_file or PROJECT / "configs" / "task.yaml", MentalRotationParams)
    manifest = bank.check_matches(p)
    pairs = {q.pair_id: q for q in design.unique_pairs(p, manifest)}
    half_w, half_h = p.spacing_dva / 2 + p.aperture_dva / 2 + 1.0, p.aperture_dva / 2 + 0.8
    fig, axes = plt.subplots(len(PANELS), 1, figsize=(6.4, 3.0 * len(PANELS)), dpi=110)
    fig.patch.set_facecolor("black")
    for ax, (letter, pid, caption) in zip(axes, PANELS, strict=True):
        q = pairs[pid]
        if caption is None:  # which side holds the mirror-image object comes from the design
            caption = (f"different: {q.reflected_side} object is the mirror image, "
                       f"{q.angle_deg}° in depth")
        ax.set_facecolor("black")
        r = p.aperture_dva / 2
        for (name, ori), x in (((q.left_image, q.left_ori_deg), -p.spacing_dva / 2),
                               ((q.right_image, q.right_ori_deg), p.spacing_dva / 2)):
            img = bank.read_png((bank.BANK_DIR / name).read_bytes())
            # PsychoPy's ori is clockwise; matplotlib's rotation is counterclockwise.
            tr = Affine2D().rotate_deg_around(x, 0.0, -ori) + ax.transData
            ax.imshow(img, cmap="gray", vmin=0, vmax=255, extent=(x - r, x + r, -r, r),
                      transform=tr, interpolation="antialiased")
        ax.text(-half_w + 0.3, half_h - 0.3, f"{letter}  {caption}", color="#d4d4d8",
                fontsize=9, va="top", family="sans-serif")
        ax.set_xlim(-half_w, half_w)
        ax.set_ylim(-half_h, half_h)
        ax.set_aspect("equal")
        ax.axis("off")
    fig.text(0.5, 0.004,
             "Illustrative pairs from the stimulus bank; display values, not calibrated",
             color="#a1a1aa", fontsize=7.5, ha="center", va="bottom", family="sans-serif")
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0.025, hspace=0.02)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, facecolor="black", metadata={"Software": None})
    plt.close(fig)
    return out


if __name__ == "__main__":
    print(render(Path(sys.argv[1]) if len(sys.argv) > 1 else PROJECT / "docs" / "preview.png"))
