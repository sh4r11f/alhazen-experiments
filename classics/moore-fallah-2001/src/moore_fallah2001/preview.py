"""Draw the stimulus preview, docs/preview.png: one trial's display and timeline.

    uv run python -m moore_fallah2001.preview            # writes docs/preview.png

Left, the display as a stimulation trial shows it, from the monkey
inside-the-MF parameters and the booth rig's screen: the dark background,
the fixation point and window, the target in the movement field, the
distractor exclusion circle, the distractor of this frame and the ghosts of
the ones before it, and the outside location the other parameter set uses.
Right, the trial's timeline (the paper's Fig. 1b, redrawn from the same
parameters): target luminance with its dimming, the 32-ms distractor cycle,
the stimulation trigger one SOA before the dimming, and the response window.

Rendered with numpy/matplotlib from the parameters the task reads, so it
needs no window. Grey levels show relative luminance (sRGB-encoded), not
the display's levels.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from alhazen.config.loader import load_params, load_rig  # noqa: E402
from alhazen.display.screen import Screen  # noqa: E402
from matplotlib.patches import Circle, Rectangle  # noqa: E402

from moore_fallah2001 import geometry  # noqa: E402
from moore_fallah2001.luminance import dimmed_luminance  # noqa: E402
from moore_fallah2001.task import PROJECT, TargetDimmingDetectionTaskParams  # noqa: E402

INK, MUTED, ACCENT, PAPER = "#1f1b17", "#6b655c", "#9b2226", "#fbf9f5"


def _grey(cd: float, white: float) -> tuple[float, float, float]:
    v = min(1.0, max(0.0, cd / white)) ** (1 / 2.2)
    return (v, v, v)


def render(out: Path, params_file: str = "task-monkey-inside.yaml") -> Path:
    p = load_params(PROJECT / "configs" / params_file, TargetDimmingDetectionTaskParams)
    rig = load_rig(PROJECT / "configs" / "rig-booth.yaml")
    screen = Screen.from_monitor(rig.monitor)
    half_w, half_h = screen.px2deg(screen.width_px / 2), screen.px2deg(screen.height_px / 2)
    mf = p.field.movement_field_dva
    target = geometry.target_location(mf, "inside", p.field.outside_rotation_deg)
    outside = geometry.outside_location(mf, p.field.outside_rotation_deg)
    ts, ds = math.sqrt(p.target_area_deg2), math.sqrt(p.distractor_area_deg2)
    spots = geometry.distractor_positions(
        np.random.default_rng(7), 9, half_w=half_w, half_h=half_h, half_side=ds / 2,
        target=target, exclusion_radius=p.distractor_exclusion_dva,
        fixation_clearance=p.distractor_fixation_clearance_dva)

    fig = plt.figure(figsize=(12, 4.6), dpi=110, facecolor=PAPER)
    ax = fig.add_axes((0.015, 0.06, 0.53, 0.88))
    white = p.target_cd_m2
    ax.add_patch(Rectangle((-half_w, -half_h), 2 * half_w, 2 * half_h,
                           color=_grey(p.background_cd_m2, white)))
    # This frame's distractor: the one nearest the upper-left quadrant's middle, so its
    # label stays on the display. Only one is drawn: a distractor is on for 16 ms of
    # every 32 ms and the next flash lands elsewhere, so flashes never share a frame.
    current = min(range(len(spots)), key=lambda i: math.hypot(spots[i][0] + half_w / 2,
                                                              spots[i][1] - half_h / 3))
    x, y = spots[current]
    ax.add_patch(Rectangle((x - ds / 2, y - ds / 2), ds, ds,
                           color=_grey(p.distractor_cd_m2, white), lw=0))
    ax.add_patch(Circle((0, 0), p.fix_window_radius_dva, fill=False, ls=(0, (2, 3)),
                        ec="#8d8a84", lw=0.9))
    ax.add_patch(Circle((0, 0), p.fix_size_dva / 2, color=_grey(p.fixation_cd_m2, white)))
    ax.add_patch(Circle(target, p.distractor_exclusion_dva, fill=False, ls=(0, (1, 2.5)),
                        ec="#8d8a84", lw=0.9))
    ax.add_patch(Circle(target, 2.2, fill=False, ec="#e07a5f", lw=1.4, ls=(0, (4, 3))))
    ax.add_patch(Rectangle((target[0] - ts / 2, target[1] - ts / 2), ts, ts,
                           color=_grey(p.target_cd_m2, white), lw=0))
    ax.add_patch(Rectangle((outside[0] - ts / 2, outside[1] - ts / 2), ts, ts, fill=False,
                           ec="#8d8a84", lw=1.0, ls=(0, (2, 2))))
    lab = dict(color="#d9d4ca", fontsize=8.5, family="DejaVu Sans")
    ax.text(target[0], target[1] - 3.1, "target in the movement field", ha="center", va="top",
            **lab)
    ax.text(outside[0], outside[1] - 1.1, "outside-set place\n(other set; not shown)", ha="center",
            va="top", **lab)
    ax.text(0, -p.fix_window_radius_dva - 0.6, "fixation window", ha="center", va="top", **lab)
    ax.text(x, y + ds / 2 + 0.5, "distractor, one 16-ms flash", ha="center", va="bottom", **lab)
    ax.set_xlim(-half_w, half_w)
    ax.set_ylim(-half_h, half_h)
    ax.set_aspect("equal")
    ax.axis("off")

    # The timeline, ms from target onset, for a stimulation blink trial.
    tl = fig.add_axes((0.665, 0.12, 0.32, 0.76), facecolor=PAPER)
    dim_on, dim_ms = 900.0, 48.0
    soa = p.stimulation.soa.ms or 175.0
    window = p.response_window.ms or 800.0
    rows = {"target": 4, "distractor": 3, "stimulation": 2, "response window": 1}
    tmax = p.catch_duration.ms or 2100.0
    t = np.linspace(-150, tmax, 2000)
    lum = np.where((t >= 0), 1.0, 0.0)
    dimmed = dimmed_luminance(p.target_cd_m2, 35.0) / p.target_cd_m2
    lum = np.where((t >= dim_on) & (t < dim_on + dim_ms), dimmed, lum)
    tl.plot(t, rows["target"] + 0.55 * lum, color=INK, lw=1.4)
    period, flash = (p.distractor_period.ms or 32.0), (p.distractor_flash.ms or 16.0)
    for s in np.arange(0, tmax, period):
        tl.add_patch(Rectangle((s, rows["distractor"]), flash, 0.45, color=INK, lw=0))
    tl.add_patch(Rectangle((dim_on - soa, rows["stimulation"]), p.stimulation.train.ms or 100,
                           0.45, color=ACCENT, lw=0))
    tl.add_patch(Rectangle((dim_on, rows["response window"]), window, 0.45, color="#c9c2b6", lw=0))
    tl.annotate("", xy=(dim_on, 2.62), xytext=(dim_on - soa, 2.62),
                arrowprops=dict(arrowstyle="<->", color=ACCENT, lw=1))
    tl.text(dim_on - soa / 2, 2.7, f"SOA {soa:.0f} ms", color=ACCENT, ha="center", fontsize=8.5)
    tl.text(dim_on + 25, rows["target"] + 0.62, "dimming (blink)", color=INK, fontsize=8.5)
    tl.text(dim_on - soa - 20, rows["stimulation"] + 0.22, "STIM_TRIGGER → TTL", color=ACCENT,
            fontsize=8.5, ha="right", va="center")
    tl.axvline(0, color="#c9c2b6", lw=0.8)
    tl.set_yticks([v + 0.22 for v in rows.values()], list(rows))
    tl.tick_params(axis="y", length=0, labelsize=9.5, colors=INK)
    tl.tick_params(axis="x", labelsize=8.5, colors=MUTED)
    tl.set_xlim(-150, tmax)
    tl.set_ylim(0.7, 4.85)
    tl.set_xlabel("ms from target onset (a stimulation blink trial)", color=MUTED, fontsize=9)
    for side in ("top", "right", "left"):
        tl.spines[side].set_visible(False)
    tl.spines["bottom"].set_color("#c9c2b6")
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, facecolor=fig.get_facecolor(), dpi=110)
    plt.close(fig)
    return out


if __name__ == "__main__":
    print(render(Path(sys.argv[1]) if len(sys.argv) > 1 else PROJECT / "docs" / "preview.png"))
