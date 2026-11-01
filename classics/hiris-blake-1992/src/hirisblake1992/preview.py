"""Draw the stimulus preview, docs/preview.png: the two phases of a trial.

    uv run python -m hirisblake1992.preview            # writes docs/preview.png

Drawn with the task's own dot engine (hirisblake1992.dvn) and geometry
(MaeCoherenceMatchTaskParams.center_dva) from configs/task.yaml, at 60 Hz. Two separate
panels, because the two phases never share the screen: adaptation (left display all
upward, right display RDVN) and a test (left display RDVN, 0 % signal; right display the
40 % downward reference). Each display shows its dots at four consecutive steps (about
150 ms), older positions fainter, so the physical motion can be seen in a still; the
aftereffect itself is perceived, not drawn. Dots are enlarged 2x for visibility.
Illustrative and uncalibrated: screen white is not the paper's 15 cd/m2.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from alhazen.config.loader import load_params  # noqa: E402

from hirisblake1992.dvn import DynamicDotField  # noqa: E402
from hirisblake1992.task import (  # noqa: E402
    PROJECT,
    MaeCoherenceMatchTask,
    MaeCoherenceMatchTaskParams,
)

REFRESH_HZ = 60.0
STEPS = 4
DOT_SCALE = 2.0
CHROME = "#3a3a3a"


def _rgb(c: tuple[float, float, float]) -> tuple[float, float, float]:
    r, g, b = ((v + 1.0) / 2.0 for v in c)
    return (r, g, b)


def _field(ax, p, spec, side: str, seed: int) -> None:
    cx, cy = p.center_dva(side)
    dots = DynamicDotField(spec, seed)
    frames = []
    while len(frames) < STEPS:
        f = dots.step()
        if f.stepped:
            frames.append(f.xy)
    # 2 arcmin dots: points from dva at this axes scale
    size_pt = DOT_SCALE * p.dot_size_dva * 72.0 * ax.figure.get_size_inches()[0] / 13.0
    for i, xy in enumerate(frames):
        alpha = 0.18 + 0.82 * (i + 1) / STEPS
        ax.scatter(xy[:, 0] + cx, xy[:, 1] + cy, s=size_pt ** 2, marker="s",
                   c=[_rgb(p.dot_color)], alpha=alpha, lw=0)


def _cross(ax, p) -> None:
    h = p.fix_size_dva / 2
    ax.plot([-h, h], [0, 0], color=_rgb(p.fix_color), lw=1.6)
    ax.plot([0, 0], [-h, h], color=_rgb(p.fix_color), lw=1.6)


def _panel(ax, p, specs: dict, prefix: str, title: str, notes: dict[str, str]) -> None:
    ax.set_facecolor(_rgb(p.background_rgb))
    for k, side in enumerate(("left", "right")):
        _field(ax, p, specs[f"{prefix}_{side}"], side, seed=11 + k)
        cx, _ = p.center_dva(side)
        ax.text(cx, -p.aperture_dva / 2 - 0.45, notes[side], ha="center", va="top",
                fontsize=8, color="#3a3a3a")
    _cross(ax, p)
    ax.set_xlim(-6.5, 6.5)
    ax.set_ylim(-3.0, 2.3)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_title(title, color="#f2f2f2", fontsize=10, loc="left", pad=5)


def render(out: Path) -> Path:
    p = load_params(PROJECT / "configs" / "task.yaml", MaeCoherenceMatchTaskParams)
    task = MaeCoherenceMatchTask(p)
    specs = task.display_specs(0.0, REFRESH_HZ)
    fig, axes = plt.subplots(2, 1, figsize=(7.2, 6.2), dpi=150)
    fig.patch.set_facecolor(CHROME)
    _panel(axes[0], p, specs, "adapt",
           "1  Adaptation: 60 s first, then 10 s before every test",
           {"left": "all 100 dots step upward", "right": "every dot in a random direction"})
    _panel(axes[1], p, specs, "test",
           "2  Test, 2 s (here the adapted display at 0 % signal)",
           {"left": "random directions (0 % signal)", "right": "40 % step downward, 60 % random"})
    fig.text(0.5, 0.012, "Four consecutive dot steps per display (~150 ms), older ones fainter; "
             "dots drawn 2x. Illustrative, uncalibrated.", ha="center", color="#cfcfcf",
             fontsize=7)
    fig.subplots_adjust(left=0.02, right=0.98, top=0.95, bottom=0.05, hspace=0.18)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, facecolor=fig.get_facecolor())
    plt.close(fig)
    return out


if __name__ == "__main__":
    print(render(Path(sys.argv[1]) if len(sys.argv) > 1 else PROJECT / "docs" / "preview.png"))
