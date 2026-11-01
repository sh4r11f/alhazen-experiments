"""Draw the stimulus preview, docs/preview.png: what a trial's display looks like.

    uv run python -m britten1992.preview            # writes docs/preview.png

Three panels drawn with the task's own dot engine (britten1992.rdk) at 25.6 %
correlation, from the two params files. Left: the human set (aperture on the
fixation point; the answer is a key after the dots go off). Middle and right:
the monkey set in its two phases, which never share the screen: first the dots
in an aperture over an example receptive field while fixation is held (the
dotted ring is the gaze window, not drawn on the screen); then the dots and
the fixation point go off and the two targets appear for the saccade. Six
consecutive frames (100 ms at 60 Hz) are superimposed, roughly what the eye
integrates; signal and noise dots are drawn alike, as on the screen.
Illustrative and uncalibrated: grey levels are display values, not cd/m2.
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


def _frame(ax, title: str) -> None:
    ax.set_xlim(-13, 13)
    ax.set_ylim(-9, 9)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for side in ax.spines.values():
        side.set_visible(False)
    ax.set_title(title, color="#f2f2f2", fontsize=9, pad=4)


def _dots_phase(ax, p, title: str, seed: int) -> None:
    """The dots phase: aperture, dots, fixation point (and, for the monkey, the gaze
    window as a dotted outline). No targets: they are not on the screen yet."""
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
        ax.add_patch(plt.Circle((0, 0), p.fix_window_dva, fill=False, ec="#d9d9d9", lw=0.6,
                                ls=":"))
    _frame(ax, title)


def _choice_phase(ax, p, title: str) -> None:
    """The monkey's choice phase: dots and fixation point off, the two targets on
    (filled, as displayed), their landing windows dotted (gaze criteria, not drawn)."""
    ax.set_facecolor(GREY)
    for x, y in target_positions_dva(p).values():
        ax.add_patch(plt.Circle((x, y), p.target_size_dva / 2, color=_rgb(p.target_color), lw=0))
        ax.add_patch(plt.Circle((x, y), p.target_window_dva, fill=False, ec="#d9d9d9", lw=0.6,
                                ls=":"))
    _frame(ax, title)


def render(out: Path) -> Path:
    human = load_params(PROJECT / "configs" / "task.yaml", RdkDirectionTaskParams)
    monkey = load_params(PROJECT / "configs" / "task-monkey.yaml", RdkDirectionTaskParams)
    fig, axes = plt.subplots(1, 3, figsize=(12.6, 3.5), dpi=110)
    fig.patch.set_facecolor("#3a3a3a")
    _dots_phase(axes[0], human, "Human: dots around fixation (key after)", seed=3)
    _dots_phase(axes[1], monkey, "Monkey, 1: 2-s dots over the RF, fixation held", seed=4)
    _choice_phase(axes[2], monkey, "Monkey, 2: dots off, two targets, saccade")
    fig.tight_layout(pad=0.6)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, facecolor=fig.get_facecolor())
    plt.close(fig)
    return out


if __name__ == "__main__":
    print(render(Path(sys.argv[1]) if len(sys.argv) > 1 else PROJECT / "docs" / "preview.png"))
