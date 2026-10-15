"""Draw the stimulus preview, docs/preview.png: what one trial's display looks like.

    uv run python -m funahashi1989.preview            # writes docs/preview.png

Rendered with matplotlib from the same parameters the task reads (configs/task.yaml), so it
needs no window. Four panels, one per epoch of a trial: fixation, cue, delay, response. The
cue is drawn at one location (45 deg, upper right); the faint outlines in the first panel
mark all eight cue locations and are NOT shown to the subject. Sizes are to scale except
the fixation spot (0.1 deg), drawn larger so it is visible at this size.
The field is alhazen's mid-grey (docs/methods.md says why the paper's dark screen is not used).
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from alhazen.config.loader import load_params  # noqa: E402
from matplotlib.patches import Circle, Rectangle  # noqa: E402

from funahashi1989.task import PROJECT, OdrParams, cue_position_dva  # noqa: E402

GREY = "#808080"
SHOWN_ANGLE = 45.0


def _panel(ax, p: OdrParams, title: str, fix: bool, cue: bool, saccade: bool = False,
           locations: bool = False) -> None:
    ax.set_facecolor(GREY)
    lim = p.cue_ecc_dva + 3.0
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for side in ax.spines.values():
        side.set_visible(False)
    s = p.cue_size_dva
    if locations:
        for a in p.cue_angles_deg:
            x, y = cue_position_dva(p.cue_ecc_dva, a)
            ax.add_patch(Rectangle((x - s / 2, y - s / 2), s, s, fill=False, ec="#a8a8a8",
                                   lw=0.6, ls=(0, (2, 2))))
    if fix:
        ax.add_patch(Circle((0, 0), max(p.fix_size_dva, 0.45) / 2, color=tuple(p.fix_color)))
    x, y = cue_position_dva(p.cue_ecc_dva, SHOWN_ANGLE)
    if cue:
        ax.add_patch(Rectangle((x - s / 2, y - s / 2), s, s, color=tuple(p.cue_color)))
    if saccade:
        ax.add_patch(Circle((x, y), p.target_window_dva, fill=False, ec="#d9d9d9", lw=0.8,
                            ls=(0, (3, 2))))
        ax.annotate("", xy=(x * 0.93, y * 0.93), xytext=(0, 0),
                    arrowprops=dict(arrowstyle="->", color="#1f1b17", lw=1.4))
    ax.set_title(title, fontsize=10, color="#1f1b17", pad=6)


def render(out: Path) -> Path:
    p = load_params(PROJECT / "configs" / "task.yaml", OdrParams)
    ms = lambda d: f"{d.ms / 1000:g} s"  # noqa: E731
    delays = ", ".join(ms(d) for d in p.delays)
    fig, axes = plt.subplots(1, 4, figsize=(11, 3.2), dpi=110)
    fig.patch.set_facecolor("#fbf9f5")
    _panel(axes[0], p, f"Fixation  {ms(p.fixation_period)}", fix=True, cue=False,
           locations=True)
    _panel(axes[1], p, f"Cue  {ms(p.cue_duration)}", fix=True, cue=True)
    _panel(axes[2], p, f"Delay  {delays}", fix=True, cue=False)
    _panel(axes[3], p, f"Go: saccade within {ms(p.response_period)}", fix=False, cue=False,
           saccade=True)
    fig.text(0.5, 0.02, f"Cue {p.cue_size_dva:g} deg square at {p.cue_ecc_dva:g} deg, one of "
             f"{len(p.cue_angles_deg)} locations; correct = landing within "
             f"{2 * p.target_window_dva:g} deg (diameter) of the cue location. "
             "Dashed outlines are not displayed.", ha="center", fontsize=8.5, color="#4a453f")
    fig.subplots_adjust(left=0.01, right=0.99, top=0.88, bottom=0.10, wspace=0.05)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, facecolor=fig.get_facecolor())
    plt.close(fig)
    return out


if __name__ == "__main__":
    print(render(Path(sys.argv[1]) if len(sys.argv) > 1 else PROJECT / "docs" / "preview.png"))
