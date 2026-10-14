"""Draw the stimulus preview, docs/preview.png: what one trial's display looks like.

    uv run python -m sperling1960.preview            # writes docs/preview.png

Four moments of one trial of the main parameter set (configs/task.yaml), drawn with
matplotlib from the same parameters and layout the task uses, so it needs no window:
the dark field with the dim cross, the lit card (the 50 ms exposure), the bar beside the
cued row in the dark post-exposure field, and the response boxes. Sizes are true to the
parameters in degrees of visual angle; luminances are the display values the task asks
for. The letters are a seeded random card.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from alhazen.config.loader import load_params  # noqa: E402
from matplotlib.font_manager import FontProperties  # noqa: E402
from matplotlib.patches import PathPatch, Rectangle  # noqa: E402
from matplotlib.textpath import TextPath  # noqa: E402
from matplotlib.transforms import Affine2D  # noqa: E402

from sperling1960.materials import MATERIALS, draw_array  # noqa: E402
from sperling1960.task import PROJECT, PartialReportTask, PartialReportTaskParams  # noqa: E402

FONT = FontProperties(family="DejaVu Sans", weight="bold")
_CAP = TextPath((0, 0), "H", size=1, prop=FONT).get_extents().height


def rgb(signed):
    """PsychoPy's signed RGB (-1..1) as matplotlib's 0..1."""
    return tuple((c + 1) / 2 for c in signed)


def letter(ax, ch, x, y, height, color):
    path = TextPath((0, 0), ch, size=1, prop=FONT)
    box = path.get_extents()
    scale = height / _CAP
    t = (Affine2D().translate(-(box.x0 + box.width / 2), 0).scale(scale)
         .translate(x, y - height / 2))
    ax.add_patch(PathPatch(t.transform_path(path), color=color, lw=0))


def cross(ax, p, color):
    s, w = p.fix_size_dva, p.fix_line_dva
    ax.add_patch(Rectangle((-s / 2, -w / 2), s, w, color=color, lw=0))
    ax.add_patch(Rectangle((-w / 2, -s / 2), w, s, color=color, lw=0))


def render(out: Path, seed: int = 7) -> Path:
    p = load_params(PROJECT / "configs" / "task.yaml", PartialReportTaskParams)
    task = PartialReportTask(p)
    m = MATERIALS[p.materials[0]]
    layout = task.layout(m.n_rows, m.n_cols)
    rows = draw_array(m, p.consonants, p.digits, np.random.default_rng(seed))
    cued = 1
    hz = 60.0
    n_exp = p.exposure.n_frames(hz)
    field, dim = rgb(p.field_color), rgb(p.fixation_color)
    titles = [
        "1  dark field, dim cross: SPACE starts",
        f"2  0.5 s later: the card, {n_exp} frames ({1000 * n_exp / hz:.0f} ms at {hz:.0f} Hz)",
        "3  cue (here +0.15 s): bar beside the row",
        "4  cue over: type the row, ENTER",
    ]
    fig, axes = plt.subplots(1, 4, figsize=(14, 3.6), dpi=100)
    fig.patch.set_facecolor("white")
    half_w, half_h = 11.5, 10.5
    for i, ax in enumerate(axes):
        ax.set_facecolor(field)
        ax.set_xlim(-half_w, half_w)
        ax.set_ylim(-half_h, half_h)
        ax.set_aspect("equal")
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_title(titles[i], fontsize=9.5, loc="left")
        if i != 1:
            cross(ax, p, dim)
    # 2: the lit card with its letters.
    ax = axes[1]
    ax.add_patch(Rectangle((-p.card_width_dva / 2, -p.card_height_dva / 2), p.card_width_dva,
                           p.card_height_dva, color=rgb(p.card_color), lw=0))
    for r, row in enumerate(rows):
        for c, ch in enumerate(row):
            x, y = layout.letter_xy(r, c)
            letter(ax, ch, x, y, p.letter_height_dva, rgb(p.letter_color))
    # 3: the bar beside the cued row.
    bx, by = layout.cue_bar_xy(cued)
    axes[2].add_patch(Rectangle((bx - p.cue_bar_length_dva / 2, by - p.cue_bar_width_dva / 2),
                                p.cue_bar_length_dva, p.cue_bar_width_dva,
                                color=rgb(p.cue_color), lw=0))
    # 4: the boxes, two letters typed.
    ax = axes[3]
    for i in range(m.n_cols):
        x, y = layout.response_box_xy(i, m.n_cols)
        s = p.response_box_dva
        ax.add_patch(Rectangle((x - s / 2, y - s / 2), s, s, fill=False,
                               edgecolor=rgb(p.response_color), lw=1.2))
        if i < 2:
            letter(ax, rows[cued][i], x, y, p.letter_height_dva, rgb(p.response_color))
    # A scale bar: 5 dva.
    axes[0].plot([-half_w + 1, -half_w + 6], [-half_h + 1, -half_h + 1], color="0.6", lw=1.5)
    axes[0].text(-half_w + 3.5, -half_h + 1.6, "5 dva", color="0.6", ha="center", fontsize=8)
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, facecolor=fig.get_facecolor(), bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)
    return out


if __name__ == "__main__":
    print(render(Path(sys.argv[1]) if len(sys.argv) > 1 else PROJECT / "docs" / "preview.png"))
