"""Draw the stimulus preview, docs/preview.png, from the real parameters (configs/task.yaml).

    uv run python -m lisi_cavanagh2015.preview            # writes docs/preview.png

Left: the display during a saccade trial (grey field, black fixation dot, the double-drift
Gabor 10 dva to the right on its path). Middle: the Gabor enlarged on its way up and on its
way down, drawn by the same luminance function the tests check: the stripes run along the
path and drift across it, reversing with each pass. Right: the physical path and the
vertical path it is seen as, which the saccades do not follow (the paper's result).
Rendered with numpy/matplotlib, so it needs no window.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from alhazen.config.loader import load_params  # noqa: E402

from lisi_cavanagh2015.common import PROJECT, make_trajectory  # noqa: E402
from lisi_cavanagh2015.geometry import path_vectors  # noqa: E402
from lisi_cavanagh2015.saccade import SaccadeParams  # noqa: E402

GREY = 0.5


def _image(traj, t, cx, cy, half, n):
    xs = np.linspace(cx - half, cx + half, n)
    ys = np.linspace(cy + half, cy - half, n)  # image rows run downwards
    X, Y = np.meshgrid(xs, ys)
    return GREY + GREY * traj.luminance(X, Y, t)


def render(out: Path) -> Path:
    p = load_params(PROJECT / "configs" / "task.yaml", SaccadeParams)
    traj = make_trajectory(p, angle_deg=p.path_angle_right_deg, side="right",
                           internal_motion=True, start_direction="up",
                           rng=np.random.default_rng(3))
    u, n = path_vectors(traj.angle_deg)
    cx, cy = traj.center
    half_len = traj.length_dva / 2
    fig = plt.figure(figsize=(11, 3.9), dpi=110)
    fig.patch.set_facecolor("white")
    gs = fig.add_gridspec(1, 4, width_ratios=[1.9, 0.85, 0.85, 1.05], wspace=0.08)

    # -- the display -------------------------------------------------------------------
    ax = fig.add_subplot(gs[0])
    ax.set_facecolor((GREY,) * 3)
    t_show = 0.4
    img = _image(traj, t_show, cx, cy, 2.2, 600)
    ax.imshow(img, extent=(cx - 2.2, cx + 2.2, cy - 2.2, cy + 2.2), cmap="gray", vmin=0,
              vmax=1, interpolation="bilinear", zorder=1)
    ends = np.array([traj.center - half_len * u, traj.center + half_len * u])
    ax.plot(ends[:, 0], ends[:, 1], color="#c9a227", lw=0.9, ls=(0, (3, 3)), zorder=2)
    ax.add_patch(plt.Circle((0, 0), p.fix_size_dva / 2, color="black", zorder=3))
    ax.add_patch(plt.Circle((0, 0), p.fix_window_dva, fill=False, ec="white", lw=0.6,
                            ls=":", zorder=3))
    ax.set_xlim(-3, 14)
    ax.set_ylim(-4.6, 4.6)
    ax.set_aspect("equal")
    ax.set_xticks([0, 5, 10])
    ax.set_yticks([-4, 0, 4])
    ax.tick_params(labelsize=7, colors="0.35")
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_title(f"Saccade trial: Gabor 10 dva right, path {traj.angle_deg:.0f} deg",
                 fontsize=9, loc="left")
    ax.text(0, -0.75, "fixation\n(2 dva window)", ha="center", va="top", fontsize=7, color="w")
    ax.text(cx, cy - 2.5, f"{traj.length_dva:.0f} dva path, {traj.speed_dva_s:.0f} dva/s",
            fontsize=7, color="w", ha="center", va="top")

    # -- the Gabor, enlarged, up and down ---------------------------------------------------
    for k, (t, label) in enumerate([(0.3, "moving up: drift to the left"),
                                    (1.05, "moving down: drift to the right")]):
        axg = fig.add_subplot(gs[1 + k])
        pos = traj.position(t)
        half = 0.45
        axg.imshow(_image(traj, t, pos[0], pos[1], half, 360),
                   extent=(-half, half, -half, half), cmap="gray", vmin=0, vmax=1)
        axg.plot([-half * u[0], half * u[0]], [-half * u[1], half * u[1]], color="#c9a227",
                 lw=0.8, ls=(0, (3, 3)))
        d = int(traj.direction(t))
        s = int(traj.drift_sign(t))
        axg.annotate("", xy=(0.30 * d * u[0] - 0.3 * n[0], 0.30 * d * u[1] - 0.3 * n[1]),
                     xytext=(-0.3 * n[0], -0.3 * n[1]),
                     arrowprops=dict(arrowstyle="-|>", color="white", lw=1.2))
        axg.annotate("", xy=(0.36 * s * n[0], 0.36 * s * n[1]), xytext=(0.0, 0.0),
                     arrowprops=dict(arrowstyle="-|>", color="#e4572e", lw=1.4))
        axg.set_xlim(-half, half)
        axg.set_ylim(-half, half)
        axg.set_xticks([])
        axg.set_yticks([])
        axg.set_title(label, fontsize=8)
        if k == 0:
            axg.text(-half, -half - 0.08, "white: envelope motion   red: internal drift\n"
                     "stripes along the path, drift across it", fontsize=6.5, va="top")

    # -- the paper's reported result, kept apart from the stimulus panels -----------------
    # Not a stimulus and not a result of this software: the perceived (illusory) path is
    # never on the screen; the panel restates what Lisi & Cavanagh (2015) reported.
    axp = fig.add_subplot(gs[3])
    axp.plot(ends[:, 0] - cx, ends[:, 1] - cy, color="0.2", lw=2.2,
             label=(f"physical path ({traj.angle_deg:.0f} deg, on screen):\n"
                    "saccades landed along it (paper)"))
    axp.plot([0, 0], [-half_len, half_len], color="#e4572e", lw=2, ls="--",
             label="reported perceived path (vertical;\nnever displayed)")
    axp.set_xlim(-2.2, 2.2)
    axp.set_ylim(-2.2, 2.2)
    axp.set_aspect("equal")
    axp.set_xticks([])
    axp.set_yticks([])
    axp.legend(fontsize=6.8, loc="lower center", frameon=False, bbox_to_anchor=(0.5, -0.32))
    axp.set_title("Paper's result (Fig. 1), not a stimulus", fontsize=8.5)
    for s in axp.spines.values():
        s.set_color("0.8")
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, bbox_inches="tight", pad_inches=0.08)
    plt.close(fig)
    return out


if __name__ == "__main__":
    print(render(Path(sys.argv[1]) if len(sys.argv) > 1 else PROJECT / "docs" / "preview.png"))
