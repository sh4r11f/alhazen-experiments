"""Draw docs/preview.png: the field at four of the main set's frequencies, side by side.

    uv run python -m campbell_robson1968.preview            # writes docs/preview.png

Each panel is the task's own image (``grating.render``), pixel for pixel, at the geometry of
configs/rig-booth.yaml (about 36 px/deg) and at an ILLUSTRATIVE contrast of 0.6: threshold
contrasts would be invisible. Greys are display values, uncalibrated; the image is written
without resampling, so it shows what the code draws, not how bright a monitor makes it.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import yaml
from alhazen.config.loader import load_params
from alhazen.config.models import MonitorConfig
from alhazen.display.screen import Screen
from PIL import Image

from campbell_robson1968.common import PROJECT
from campbell_robson1968.grating import GratingSpec, render
from campbell_robson1968.task import Csf2ifcParams

PREVIEW_CONTRAST = 0.6
PREVIEW_SF = (0.5, 1.0, 2.0, 4.0)


def render_preview(out: Path) -> Path:
    p = load_params(PROJECT / "configs" / "task.yaml", Csf2ifcParams)
    rig = yaml.safe_load((PROJECT / "configs" / "rig-booth.yaml").read_text(encoding="utf-8"))
    ppd = Screen.from_monitor(MonitorConfig(**rig["monitor"])).px_per_deg
    mean = p.quantised_mean()
    panels = []
    for sf in PREVIEW_SF:
        spec = GratingSpec(
            sf_cpd=sf,
            contrast=PREVIEW_CONTRAST,
            field_dva=p.field_dva,
            mean=mean,
            orientation_deg=p.orientation_deg,
        )
        img, _ = render(spec, ppd, bits=p.display_bits, dither="none")
        panels.append(img)
    n = panels[0].shape[0]
    gap = n // 6
    canvas = np.full((n + 2 * gap, len(panels) * (n + gap) + gap), mean)
    for i, img in enumerate(panels):
        x = gap + i * (n + gap)
        canvas[gap : gap + n, x : x + n] = img
    out.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.rint(canvas * 255).astype(np.uint8), mode="L").save(out, optimize=True)
    return out


if __name__ == "__main__":
    print(
        render_preview(Path(sys.argv[1]) if len(sys.argv) > 1 else PROJECT / "docs" / "preview.png")
    )
