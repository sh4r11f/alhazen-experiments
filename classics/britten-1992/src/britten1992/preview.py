"""Draw the stimulus preview, docs/preview.png: what a trial's display looks like.

    uv run python -m britten1992.preview            # writes docs/preview.png

Two panels from the two params files, drawn with the task's own dot engine
(britten1992.rdk) at 25.6 % correlation: the human set (aperture on the
fixation point) and the monkey set (aperture over an example receptive field,
with the two saccade targets that appear when the dots go off, outlined). Six
consecutive frames (100 ms at 60 Hz) are superimposed, roughly what the eye
integrates; signal and noise dots are drawn alike, as on the screen.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from alhazen.config.loader import load_params  # noqa: E402

from britten1992.rdk import CorrelatedDotField  # noqa: E402
from britten1992.task import (  # noqa: E402
    PROJECT,
    RdkDirectionTask,
    RdkDirectionTaskParams,
    target_positions_dva,
)

GREY = "#808080"
REFRESH_HZ = 60.0
FRAMES = 6
COHERENCE_PCT = 25.6


def _rgb(color: tuple[float, float, float]) -> tuple[float, float, float]:
    """PsychoPy's signed RGB (-1..1) to matplotlib's 0..1."""
    r, g, b = ((v + 1.0) / 2.0 for v in color)
    return (r, g, b)


def _panel(ax, params_file: str, title: str, seed: int) -> None:
    p = load_params(PROJECT / "configs" / params_file, RdkDirectionTaskParams)
    task = RdkDirectionTask(p)
    spec = task.dot_spec(COHERENCE_PCT, "pref", REFRESH_HZ)
    dots = CorrelatedDotField(spec, seed)
    cx, cy = p.aperture_center_dva
    ax.set_facecolor(GREY)
    if p.aperture_fill is not None:
        ax.add_patch(plt.Circle((cx, cy), p.aperture_dva / 2, color=_rgb(p.aperture_fill), lw=0))
    for _ in range(20):  # past the first frames, which have no signal dots yet
        dots.step()
    for _ in range(FRAMES):
        f = dots.step()
        xy = f.xy[f.visible]
        ax.scatter(xy[:, 0] + cx, xy[:, 1] + cy, s=2.2, c=[_rgb(p.dot_color)], lw=0)
    ax.add_patch(plt.Circle((0, 0), p.fix_size_dva / 2, color=_rgb(p.fix_color), zorder=5))
    if p.response_mode.value == "saccade_and_reward":
        for x, y in target_positions_dva(p).values():
            ax.add_patch(plt.Circle((x, y), p.target_size_dva / 2, fill=False,
                                    ec=_rgb(p.target_color), lw=1.0, ls="--"))
        ax.add_patch(plt.Circle((0, 0), p.fix_window_dva, fill=False, ec="#d9d9d9", lw=0.6,
                                ls=":"))
    ax.set_xlim(-13, 13)
    ax.set_ylim(-9, 9)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for side in ax.spines.values():
        side.set_visible(False)
    ax.set_title(title, color="#f2f2f2", fontsize=10, pad=4)


def render(out: Path) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.6), dpi=110)
    fig.patch.set_facecolor("#3a3a3a")
    _panel(axes[0], "task.yaml", "Human set: dots around fixation, then a key", seed=3)
    _panel(axes[1], "task-monkey.yaml",
           "Monkey set: dots over the RF, then a saccade to a target", seed=4)
    fig.tight_layout(pad=0.6)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, facecolor=fig.get_facecolor())
    plt.close(fig)
    return out


if __name__ == "__main__":
    print(render(Path(sys.argv[1]) if len(sys.argv) > 1 else PROJECT / "docs" / "preview.png"))
