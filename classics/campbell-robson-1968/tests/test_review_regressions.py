"""Regression test from the independent review of 1 Nov 2026 (evidence/independent-review).

``orientation_deg`` was accepted at load for any angle, but ``grating.measure`` (run for
every drawn grating, to log the realised contrast) only reads back stripes along the pixel
grid, so an oblique set loaded and then failed on its first trial. It is now refused at
load.
"""

from __future__ import annotations

import numpy as np
import pytest
from pydantic import ValidationError

from campbell_robson1968.common import CampbellRobsonParams
from campbell_robson1968.grating import GratingSpec, render


@pytest.mark.parametrize("ori", [45.0, 30.0, 89.0, float("nan")])
def test_oblique_orientation_refused_at_load(ori):
    with pytest.raises(ValidationError, match="orientation_deg"):
        CampbellRobsonParams(orientation_deg=ori)


@pytest.mark.parametrize("ori", [0.0, 90.0, 180.0, 270.0, -90.0, 360.0])
def test_axis_orientations_load_and_render(ori):
    p = CampbellRobsonParams(orientation_deg=ori)
    spec = GratingSpec(sf_cpd=2.0, contrast=0.2, field_dva=2.0, mean=0.5,
                       orientation_deg=p.orientation_deg)
    _, realised = render(spec, 36.0, rng=np.random.default_rng(0))
    assert realised.contrast == pytest.approx(0.2, abs=0.01)
