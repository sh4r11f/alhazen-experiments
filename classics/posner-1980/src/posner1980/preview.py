"""Draw the stimulus preview, docs/preview.png: what the display shows on a trial.

    uv run python -m posner1980.preview            # writes docs/preview.png

Three frames, as in Posner (1980), Fig. 1: a neutral cue with its target, a valid
trial and an invalid trial, each at the moment the detection stimulus is on screen
(the cue stays on). Drawn with matplotlib from the same parameters and the same
polygons (posner1980.geometry) the task uses, on alhazen's mid-grey background, so it
needs no window.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from alhazen.config.loader import load_params  # noqa: E402
from matplotlib.patches import Polygon  # noqa: E402

from posner1980 import geometry  # noqa: E402
from posner1980.task import PROJECT, PosnerCueingTaskParams  # noqa: E402

BACKGROUND = "#808080"   # alhazen's window colour, PsychoPy rgb (0, 0, 0)
FRAMES = [("neutral", "left", "Neutral: + cue"),
          ("right", "right", "Valid: arrow, target on the cued side"),
          ("right", "left", "Invalid: arrow, target on the other side")]


def _rgb(color) -> tuple[float, float, float]:
    return tuple((c + 1.0) / 2.0 for c in color)  # PsychoPy -1..1 to matplotlib 0..1


def render(out: Path, params_file: Path | None = None) -> Path:
    p = load_params(params_file or PROJECT / "configs" / "task.yaml", PosnerCueingTaskParams)
    ink = _rgb(p.stimulus_color)
    half_w = p.target_ecc_dva + 3.0
    half_h = 3.2
    fig, axes = plt.subplots(len(FRAMES), 1, figsize=(8, 7.2), dpi=110)
    fig.patch.set_facecolor("#1f1f1f")
    for ax, (cue, target, label) in zip(axes, FRAMES, strict=True):
        ax.set_facecolor(BACKGROUND)
        for start, end in geometry.cue_strokes(cue, p.cue_size_dva):
            ax.add_patch(Polygon(geometry.stroke_polygon(start, end, p.cue_stroke_dva),
                                 closed=True, color=ink, lw=0))
        center = geometry.target_center(target, p.target_ecc_dva)
        ax.add_patch(Polygon(geometry.square_corners(center, p.target_size_dva), closed=True,
                             color=ink, lw=0))
        ax.set_xlim(-half_w, half_w)
        ax.set_ylim(-half_h, half_h)
        ax.set_aspect("equal")
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.text(-half_w + 0.4, half_h - 0.5, label, color="#f0f0f0", fontsize=10, va="top")
        ax.text(half_w - 0.4, -half_h + 0.4,
                f"target {p.target_ecc_dva:g}° from fixation, "
                f"{p.cue_target_soa.ms:g} ms after the cue",
                color="#d8d8d8", fontsize=7.5, ha="right", va="bottom")
    fig.subplots_adjust(left=0.01, right=0.99, top=0.99, bottom=0.01, hspace=0.06)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, facecolor=fig.get_facecolor())
    plt.close(fig)
    return out


if __name__ == "__main__":
    print(render(Path(sys.argv[1]) if len(sys.argv) > 1 else PROJECT / "docs" / "preview.png"))
