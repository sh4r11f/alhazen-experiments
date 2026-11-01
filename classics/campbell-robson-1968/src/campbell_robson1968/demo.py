"""``--mode demo``: each spatial frequency of the parameter set at a clearly visible
contrast (0.5), on the rig's own pixels, so its geometry can be checked by eye. The
contrast is for viewing only; the tasks start near threshold."""

from __future__ import annotations

from typing import Any

from alhazen.modes.demo import DemoView

from campbell_robson1968.common import CampbellRobsonParams, cells
from campbell_robson1968.grating import GratingSpec
from campbell_robson1968.stimuli import make_grating, make_mean_field

DEMO_CONTRAST = 0.5


def grating_views(p: CampbellRobsonParams, setup: Any) -> list[Any]:
    mean = p.quantised_mean()
    field = make_mean_field(setup.display, setup.screen, mean)
    views = []
    for name, (waveform, sf) in cells(p).items():
        spec = GratingSpec(
            sf_cpd=sf,
            contrast=DEMO_CONTRAST,
            field_dva=p.field_dva,
            mean=mean,
            orientation_deg=p.orientation_deg,
            waveform=waveform,
        )
        stim = make_grating(
            setup.display, setup.screen, spec, bits=p.display_bits, dither=p.dither, seed=0
        )
        r = stim.realised

        def draw(t: float, stim: Any = stim) -> None:
            field.draw()
            stim.draw()

        views.append(
            DemoView(
                name=name,
                draw=draw,
                caption=(
                    f"{waveform} {sf:g} c/deg, contrast {DEMO_CONTRAST} (viewing only), "
                    f"{r.px_per_cycle:.1f} px/cycle, field {p.field_dva:g} deg"
                ),
            )
        )
    return views
