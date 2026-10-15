"""Draw the stimulus preview, docs/preview.png: what the two experiments' displays look like.

    uv run python -m cavanagh1992.preview            # writes docs/preview.png

Rendered with the same ``Scene`` and ``SceneRaster`` the tasks draw, from the parameter
files (configs/task.yaml, configs/speed-global.yaml) at photometric equiluminance (k = 1)
and the example photometry, then encoded as sRGB for a picture. Left: an Experiment 1
tracking trial while the pointers are on (luminance grating at 10%, near the motion
null). Right: an Experiment 2 display (outer colour grating, inner 15% luminance
comparison).
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from alhazen.config.loader import load_params  # noqa: E402

from cavanagh1992.common import PROJECT  # noqa: E402
from cavanagh1992.scene import Component, Pointer, Ring, Scene, SceneRaster  # noqa: E402
from cavanagh1992.speed_match import SpeedMatchParams  # noqa: E402
from cavanagh1992.task import AttentiveTrackingTaskParams  # noqa: E402

PX_PER_DEG = 22.0


def srgb(linear: np.ndarray) -> np.ndarray:
    """Linear 0..1 to sRGB-encoded 0..1, for a picture viewed on an ordinary screen."""
    x = np.clip(linear, 0.0, 1.0)
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * x ** (1 / 2.4) - 0.055)


def tracking_scene() -> Scene:
    p = load_params(PROJECT / "configs" / "task.yaml", AttentiveTrackingTaskParams)
    color = Component("color", p.color_contrast, p.n_cycles, p.rate_hz, 1, 0.3)
    lum = Component("luminance", 0.10, p.n_cycles, p.rate_hz, -1, 1.1)
    scene = Scene([Ring(p.annulus_inner_dva, p.annulus_outer_dva, [color, lum])],
                  p.color_model(1.0), p.bullseye_radius_dva, p.bullseye_rings,
                  p.pointer_geometry(), pointer=Pointer(0, 0, 1, 1))
    return scene


def speed_scene() -> Scene:
    p = load_params(PROJECT / "configs" / "speed-global.yaml", SpeedMatchParams)
    outer = [Component("color", p.color_contrast, p.n_cycles, p.outer_rate_hz, 1, 0.0)]
    inner = [Component("luminance", p.comparison_contrast, p.comparison_cycles, 0.5, -1, 0.7)]
    return Scene([Ring(p.annulus_inner_dva, p.annulus_outer_dva, outer),
                  Ring(*p.inner_ring_dva, inner)], p.color_model(1.0),
                 p.bullseye_radius_dva, p.bullseye_rings, p.pointer_geometry())


def render(out: Path) -> Path:
    panels = [(tracking_scene(), "Exp. 1: colour vs luminance, pointers on"),
              (speed_scene(), "Exp. 2: colour ring, luminance comparison")]
    fig, axes = plt.subplots(1, 2, figsize=(8, 4.2), dpi=110)
    fig.patch.set_facecolor("#1b1b1b")
    for ax, (scene, title) in zip(axes, panels, strict=True):
        img = srgb(SceneRaster(scene, PX_PER_DEG).render())
        ax.imshow(img, interpolation="nearest")
        ax.set_title(title, color="#e8e8e8", fontsize=9)
        ax.axis("off")
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out, facecolor=fig.get_facecolor(), bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)
    return out


if __name__ == "__main__":
    print(render(Path(sys.argv[1]) if len(sys.argv) > 1 else PROJECT / "docs" / "preview.png"))
