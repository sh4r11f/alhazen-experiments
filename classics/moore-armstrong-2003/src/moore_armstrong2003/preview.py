"""Draw the stimulus preview, docs/preview.png: what one trial's display looks like.

    uv run python -m moore_armstrong2003.preview            # writes docs/preview.png

Rendered with matplotlib from the same parameters and geometry functions the task uses
(configs/task.yaml, on the example recording rig's screen), so it needs no window. Left:
the screen during the stimulus period of a "preferred bar in the RF + distracter" trial,
with the parts the subject never sees (the RF, the fixation window, the FEF site's
evoked-saccade vector) drawn as dashed annotations. Right: one trial's timeline.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import yaml  # noqa: E402
from alhazen.config.loader import load_params  # noqa: E402
from matplotlib.patches import Circle, FancyArrowPatch, Polygon, Rectangle  # noqa: E402

from moore_armstrong2003 import geometry as geo  # noqa: E402
from moore_armstrong2003.task import PROJECT, RfGatingFixationTaskParams  # noqa: E402

INK = "#1f1b17"
NOTE = "#7f1d1d"


def _grey(rgb: tuple[float, float, float]) -> str:
    v = max(0.0, min(1.0, (rgb[0] + 1) / 2))
    return matplotlib.colors.to_hex((v, v, v))


def screen_extent_dva(rig: Path) -> tuple[float, float]:
    """Half-width and half-height of the rig's screen in dva."""
    m = yaml.safe_load(rig.read_text(encoding="utf-8"))["monitor"]
    height_cm = m["width_cm"] * m["height_px"] / m["width_px"]
    half = lambda cm: math.degrees(math.atan(cm / 2 / m["distance_cm"]))  # noqa: E731
    return half(m["width_cm"]), half(height_cm)


def render(out: Path) -> Path:
    p = load_params(PROJECT / "configs" / "task.yaml", RfGatingFixationTaskParams)
    hw, hh = screen_extent_dva(PROJECT / "configs" / "rig-recording-example.yaml")
    kind = p.site.kind()
    rf, dist = p.site.rf_center_dva, p.distracter_xy(kind)
    bar = _grey(geo.signed_rgb(geo.bar_luminance(p.bar_contrast, p.bar_polarity)))
    bg = _grey((0.0, 0.0, 0.0))

    fig = plt.figure(figsize=(9.6, 4.6), dpi=130)
    fig.patch.set_facecolor("white")
    ax = fig.add_axes([0.01, 0.06, 0.55, 0.88])
    ax.add_patch(Rectangle((-hw, -hh), 2 * hw, 2 * hh, color=bg, zorder=0))
    ax.add_patch(Circle((0, 0), p.fix_size_dva / 2, color=_grey(p.fix_rgb), zorder=4))
    ax.add_patch(Circle((0, 0), p.fix_window_dva, fill=False, ls="--", lw=0.8, ec="#e8e8e8"))
    ax.add_patch(Circle(rf, p.site.rf_diameter_dva / 2, fill=False, ls="--", lw=1.0, ec=NOTE))
    for xy in (rf, dist):
        ori = geo.orientation_deg("preferred", p.site.preferred_orientation_deg)
        corners = geo.bar_corners(xy, p.bar_length_dva, p.bar_width_dva, ori)
        ax.add_patch(Polygon(corners, closed=True, color=bar, zorder=3))
    ex, ey = p.site.saccade_endpoint_dva
    ax.add_patch(FancyArrowPatch((0, 0), (ex * 0.93, ey * 0.93), arrowstyle="-|>",
                                 mutation_scale=10, lw=1.0, ls="--", color=NOTE, zorder=2))
    ax.text(rf[0], rf[1] - p.site.rf_diameter_dva / 2 - 0.9, "V4 RF + evoked\nsaccade end point",
            ha="center", va="top", fontsize=7, color=NOTE)
    ax.text(dist[0], dist[1] + 1.8, "distracter", ha="center", fontsize=7, color="#f2f2f2")
    ax.text(-hw + 0.6, hh - 0.8, "screen during the stimulus period (dashed: not shown)",
            fontsize=7, color="#f2f2f2", va="top")
    ax.set_xlim(-hw, hw)
    ax.set_ylim(-hh, hh)
    ax.set_aspect("equal")
    ax.axis("off")

    tl = fig.add_axes([0.72, 0.14, 0.27, 0.74])
    lo_t, hi_t = p.stimulation.onset_after_display.seconds()
    lo_v, hi_v = p.stimulus_duration.seconds()
    base = p.baseline_hold.ms / 1000.0
    train = p.stimulation.train_ms / 1000.0
    win = p.analysis.post_train_window.ms / 1000.0
    trig = (lo_t + hi_t) / 2
    rows = [
        ("fixation held", -base, (lo_v + hi_v) / 2, INK),
        ("bars (RF, distracter)", 0.0, (lo_v + hi_v) / 2, "#52525b"),
        ("trigger window", lo_t, hi_t, "#d4d4d8"),
        ("FEF train (stim trials)", trig, trig + train, NOTE),
        ("V4 window (analysis)", trig + train, trig + train + win, "#2f6b3f"),
    ]
    for i, (_label, a, b, colour) in enumerate(rows):
        y = len(rows) - i
        tl.add_patch(Rectangle((a, y - 0.3), b - a, 0.6, color=colour))
    events = ((-base, "FIX_ACQUIRED"), (0.0, "VIS_ON"), (trig, "STIM_TRIGGER /\nCONTROL_MARK"),
              ((lo_v + hi_v) / 2, "VIS_OFF"))
    for k, (x, name) in enumerate(events):
        tl.axvline(x, color="#a1a1aa", lw=0.6, ls=":")
        tl.text(x, len(rows) + 0.6 + 0.7 * (k % 2), name, ha="center", va="bottom", fontsize=6.5,
                color=INK)
    tl.set_xlim(-base - 0.1, hi_v + 0.1)
    tl.set_ylim(0.3, len(rows) + 2.2)
    tl.set_yticks([len(rows) - i for i in range(len(rows))], [r[0] for r in rows], fontsize=7.5)
    tl.tick_params(axis="y", length=0)
    tl.set_xlabel("time from bar onset (s)", fontsize=7.5)
    tl.tick_params(labelsize=7)
    for side in ("left", "right", "top"):
        tl.spines[side].set_visible(False)
    fig.text(0.58, 0.95, f"trigger {lo_t * 1000:.0f}-{hi_t * 1000:.0f} ms after bar onset; "
             f"{p.stimulation.train_ms:g} ms train; bars up {lo_v:.1f}-{hi_v:.1f} s",
             fontsize=7.5, color=INK)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, facecolor=fig.get_facecolor())
    plt.close(fig)
    return out


if __name__ == "__main__":
    print(render(Path(sys.argv[1]) if len(sys.argv) > 1 else PROJECT / "docs" / "preview.png"))
