"""Draw the stimulus preview, docs/preview.png: what a trial's display looks like.

    uv run python -m stroop1935.preview            # writes docs/preview.png

Rendered with matplotlib from the same parameters and the same sheet the task
uses, so it needs no window. Each panel is the central 6 x 3.4 dva of the
screen at true scale: the fixation point, then one item of each test (the
first items of the generated sheet). Letter shapes are DejaVu Sans, which
matplotlib ships; the task asks PsychoPy for the params file's font.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from alhazen.config.loader import load_params  # noqa: E402
from matplotlib.font_manager import FontProperties  # noqa: E402
from matplotlib.patches import Circle, PathPatch, Rectangle  # noqa: E402
from matplotlib.textpath import TextPath  # noqa: E402

from stroop1935 import sheet  # noqa: E402
from stroop1935.task import PROJECT, StroopParams  # noqa: E402

HALF_W, HALF_H = 3.0, 1.7  # dva shown around the centre of the screen


def _rgb(v) -> tuple[float, float, float]:
    """PsychoPy rgb (-1..1) to matplotlib (0..1)."""
    return tuple((x + 1.0) / 2.0 for x in v)  # type: ignore[return-value]


def _word(ax, text: str, color, height: float) -> None:
    path = TextPath((0, 0), text, size=height, prop=FontProperties(family="DejaVu Sans"))
    box = path.get_extents()
    shifted = path.transformed(matplotlib.transforms.Affine2D().translate(
        -(box.x0 + box.x1) / 2, -(box.y0 + box.y1) / 2))
    ax.add_patch(PathPatch(shifted, facecolor=color, edgecolor="none"))


def render(out: Path) -> Path:
    p = load_params(PROJECT / "configs" / "task.yaml", StroopParams)
    first = {t: sheet.items(t, p.sheet_seed, 1)[0] for t in sheet.TESTS}
    fix_caption = f"every trial: fixation point\n{p.fixation_duration.ms:g} ms, then ONE item"
    panels = [("fixation", fix_caption, None),
              (sheet.NC, "or NC: name the ink", first[sheet.NC]),
              (sheet.NCWD, "or NCWd: name the ink", first[sheet.NCWD]),
              (sheet.RCNB, "or RCNb: key the word", first[sheet.RCNB]),
              (sheet.RCND, "or RCNd: key the word", first[sheet.RCND])]
    fig, axes = plt.subplots(1, len(panels), figsize=(11, 2.75), dpi=130)
    fig.patch.set_facecolor("white")
    for ax, (test, caption, item) in zip(axes, panels, strict=True):
        ax.add_patch(Rectangle((-HALF_W, -HALF_H), 2 * HALF_W, 2 * HALF_H,
                               facecolor=_rgb(p.background_rgb), edgecolor="#999999", lw=0.6))
        if item is None:
            ax.add_patch(Circle((0, 0), p.fixation_size_dva / 2, color=_rgb(p.fixation_rgb)))
        else:
            ink = _rgb(p.black_rgb) if item.ink == "black" else _rgb(p.colors[item.ink])
            if item.word:
                _word(ax, item.word, ink, p.letter_height_dva)
            else:
                s = p.patch_size_dva
                ax.add_patch(Rectangle((-s / 2, -s / 2), s, s, facecolor=ink, edgecolor="none"))
            target = item.ink if test in (sheet.NC, sheet.NCWD) else item.word
            caption += f"\nanswer: {target} = key {p.keys[target].upper()}"
        ax.set_xlim(-HALF_W, HALF_W)
        ax.set_ylim(-HALF_H, HALF_H)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_title(caption, fontsize=8.5, color="#222222", pad=4, loc="center", y=-0.36)
    fig.suptitle("Stroop (1935) by key: a fixation point, then one of four item types "
                 "(alternatives, never shown together). Central 6 x 3.4 dva at true size; "
                 "illustrative, uncalibrated colours", fontsize=9, color="#222222", y=0.98)
    fig.subplots_adjust(left=0.01, right=0.99, top=0.88, bottom=0.25, wspace=0.06)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, facecolor=fig.get_facecolor())
    plt.close(fig)
    return out


if __name__ == "__main__":
    print(render(Path(sys.argv[1]) if len(sys.argv) > 1 else PROJECT / "docs" / "preview.png"))
