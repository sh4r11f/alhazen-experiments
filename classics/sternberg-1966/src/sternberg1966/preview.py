"""Draw the stimulus preview, docs/preview.png: one experiment-1 trial, display by display.

    uv run python -m sternberg1966.preview            # writes docs/preview.png

Drawn with matplotlib from the same parameters the task reads (configs/task.yaml): the
digit height, colours, warning symbol, lamp size and place, and every duration. It needs no
window. It is the picture on the Experiment Hub listing and the project page.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from alhazen.config.loader import load_params  # noqa: E402
from matplotlib.patches import Circle, PathPatch, Rectangle  # noqa: E402
from matplotlib.textpath import TextPath  # noqa: E402

from sternberg1966.task import PROJECT, VariedSetParams  # noqa: E402

VIEW_W, VIEW_H = 20.0, 11.25  # each panel shows this much of the screen, in dva
BACKGROUND = "#808080"  # the rig's mid-grey (PsychoPy rgb 0, 0, 0)


def _rgb(color: tuple[float, float, float]) -> tuple[float, float, float]:
    """PsychoPy's signed rgb (-1..1) to matplotlib's 0..1."""
    return tuple((c + 1.0) / 2.0 for c in color)  # type: ignore[return-value]


def _text(ax, text: str, height_dva: float, color, x0: float, y0: float) -> None:
    # PsychoPy's TextStim height is the font size (em), as here; a digit is ~0.73 of it.
    path = TextPath((0, 0), text, size=height_dva, prop={"family": "DejaVu Sans Mono"})
    box = path.get_extents()
    shifted = path.transformed(
        matplotlib.transforms.Affine2D().translate(x0 - box.x0 - box.width / 2,
                                                   y0 - box.y0 - box.height / 2))
    ax.add_patch(PathPatch(shifted, facecolor=color, edgecolor="none"))


def render(out: Path, params_file: Path | None = None) -> Path:
    p = load_params(params_file or PROJECT / "configs" / "task.yaml", VariedSetParams)
    ink = _rgb(p.digit_color)
    series, probe = "381", "8"
    lamp_y = -p.feedback_offset_dva
    panels = [(d, f"digit {i + 1}\n{p.item_duration.ms / 1000:g} s", "digit")
              for i, d in enumerate(series)]
    panels += [
        ("", f"delay\n{p.delay.ms / 1000:g} s", "blank"),
        (p.warning_symbol, f"warning signal\n{p.warning_duration.ms / 1000:g} s", "digit"),
        (probe, "test digit\nuntil J (yes) or F (no)", "digit"),
        ("", f"feedback light alone\n{p.feedback_duration.ms / 1000:g} s", "lamp"),
        ("381", "recall in order\ntyped, then Enter", "recall"),
    ]
    fig, axes = plt.subplots(2, 4, figsize=(12, 6.0), dpi=100)
    fig.patch.set_facecolor("white")
    for ax, (text, label, kind) in zip(axes.flat, panels, strict=True):
        ax.add_patch(Rectangle((-VIEW_W / 2, -VIEW_H / 2), VIEW_W, VIEW_H, facecolor=BACKGROUND,
                               edgecolor="#333333", lw=1))
        if kind in ("digit", "recall") and text:
            _text(ax, text, p.digit_height_dva, ink, 0.0, 0.0)
        if kind == "recall":
            _text(ax, p.recall_prompt, p.prompt_height_dva, ink, 0.0,
                  p.feedback_offset_dva + 0.5)
        if kind == "lamp":
            ax.add_patch(Circle((0.0, lamp_y), p.feedback_size_dva / 2,
                                facecolor=_rgb(p.correct_color), edgecolor="none"))
        ax.set_xlim(-VIEW_W / 2 - 0.2, VIEW_W / 2 + 0.2)
        ax.set_ylim(-VIEW_H / 2 - 0.2, VIEW_H / 2 + 0.2)
        ax.set_aspect("equal")
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.set_xlabel(label, fontsize=11, color="#222222", labelpad=6)
    fig.suptitle("Sternberg (1966), experiment 1: one trial with s = 3 and a positive test digit",
                 fontsize=13, color="#111111")
    fig.text(0.5, 0.015, f"Illustrative frames in order, not a recording; display values, "
             f"not calibrated "
             f"luminance. Panels show {VIEW_W:g} x {VIEW_H:g} dva; digit font size "
             f"{p.digit_height_dva:g} dva (configs/task.yaml).",
             ha="center", fontsize=9, color="#555555")
    fig.tight_layout(rect=(0, 0.03, 1, 0.95), h_pad=2.5)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, facecolor=fig.get_facecolor())
    plt.close(fig)
    return out


if __name__ == "__main__":
    print(render(Path(sys.argv[1]) if len(sys.argv) > 1 else PROJECT / "docs" / "preview.png"))
