"""The two numbers the saccade task needs from a participant's perceptual run.

    uv run python -m lisi_cavanagh2015.pse <perception run folder>

Fits the cumulative Gaussian to each drift pairing (lisi_cavanagh2015.analysis) and prints
the two lines to put in that participant's copy of configs/task.yaml.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from lisi_cavanagh2015.analysis import perceptual_pse


def pse_lines(run: Path) -> str:
    trials = pd.concat(pd.read_csv(f) for f in sorted(Path(run).glob("*_trials.csv")))
    fits = perceptual_pse(trials).set_index("tilt_side")
    lines = []
    for side in ("right", "left"):
        if side in fits.index:
            r = fits.loc[side]
            lines.append(f"path_angle_{side}_deg: {r.pse_deg:.1f}   # PSE from {Path(run).name}"
                         f" (sigma {r.sigma_deg:.1f} deg, {int(r.n)} trials)")
    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    print(pse_lines(Path(sys.argv[1])))
