"""Draw the stimulus preview, docs/preview.png: what one trial's display looks like.

    uv run python -m britten1992.preview            # writes docs/preview.png

Rendered with numpy/matplotlib from the same parameters the task reads, so it needs no
window. It is the picture on the Experiment Hub listing and the project page.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from alhazen.config.loader import load_params  # noqa: E402

from britten1992.task import PROJECT, RdkDirectionTaskParams  # noqa: E402


def render(out: Path) -> Path:
    p = load_params(PROJECT / "configs" / "task.yaml", RdkDirectionTaskParams)
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=150)
    fig.patch.set_facecolor("#808080")
    ax.set_facecolor("#808080")
    ax.add_patch(plt.Circle((0, 0), p.fix_size_dva / 2, color="white"))
    ax.add_patch(plt.Circle((p.target_ecc_dva, 0), p.target_size_dva / 2, color="white"))
    ax.set_xlim(-12, 12)
    ax.set_ylim(-6.75, 6.75)
    ax.set_aspect("equal")
    ax.axis("off")
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, facecolor=fig.get_facecolor(), bbox_inches="tight", pad_inches=0)
    plt.close(fig)
    return out


if __name__ == "__main__":
    print(render(Path(sys.argv[1]) if len(sys.argv) > 1 else PROJECT / "docs" / "preview.png"))
