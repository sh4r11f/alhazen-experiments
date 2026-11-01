"""Regression tests from the independent review of 1 Nov 2026 (evidence/independent-review).

With the paper's raster-line dither (interleave_mix: line_dither) the light bars of the
mixture grating carry the test colour itself at (1 + c) x its luminance. The knob's upper
limit was computed for the additive mixture only, so on a display whose test gun is the
binding limit the knob could be turned to a luminance whose light dither rows need a gun
level above 1, and the stimulus raised in the middle of a setting.
"""

from __future__ import annotations

import numpy as np
import pytest
import yaml
from alhazen.config.loader import load_params
from conftest import CONFIGS

from anstiscavanagh1983.adjust import MinMotionAdjustTask, MotionAdjustParams
from anstiscavanagh1983.stimulus import Fixation, Spec, frames

# A plausible MEASURED panel with a dim red gun (white about 180 cd/m2).
DIM = {"red_max_cd_m2": 40.0, "green_max_cd_m2": 130.0, "blue_max_cd_m2": 12.0,
       "measured": True}


def adjust_task(tmp_path, **kw):
    ph = tmp_path / "photometry-dim.yaml"
    ph.write_text(yaml.safe_dump(DIM), encoding="utf-8")
    p = load_params(CONFIGS / "adjust-red-green.yaml", MotionAdjustParams)
    data = {**p.model_dump(), "photometry_file": str(ph), **kw}
    return MinMotionAdjustTask(MotionAdjustParams.model_validate(data))


def light_level_max(task, colour, value):
    p = task.params
    spec = Spec("four_stroke", colour, p.reference_colour, value, p.reference_cd_m2, 32, 16,
                1, 0, p.interleave_contrast, p.interleave_mix, p.dither_rows)
    return max(float(np.max(img)) for img in frames(spec, p.colour_space(), 40.0, None))


@pytest.mark.parametrize("mix", ["additive", "line_dither"])
def test_knob_top_is_drawable(tmp_path, mix):
    task = adjust_task(tmp_path, interleave_mix=mix)
    lo, hi = task._range("red")
    # Every stroke at the top of the knob fits in 0..1 (it raised for line_dither).
    frames(Spec("four_stroke", "red", "green", hi, 13.4, 32, 16, 1, 0, 0.0625, mix, 2),
           task.params.colour_space(), 40.0, Fixation())
    assert light_level_max(task, "red", hi) <= 1.0 + 1e-9


def test_line_dither_cap_is_tight(tmp_path):
    task = adjust_task(tmp_path, interleave_mix="line_dither")
    _, hi = task._range("red")
    # The red rows of the light bar reach the red gun's maximum exactly at the cap.
    assert hi == pytest.approx(DIM["red_max_cd_m2"] / (1.0 + 0.0625))
    assert light_level_max(task, "red", hi) == pytest.approx(1.0)


def test_line_dither_reference_rows_checked_at_load(tmp_path):
    # A reference whose light dither rows exceed the display is refused before a trial.
    with pytest.raises(ValueError, match="gun levels"):
        adjust_task(tmp_path, interleave_mix="line_dither", reference_cd_m2=125.0,
                    limits=(0.01, 4.0), start_range=(0.02, 0.05))
