"""What every task in this folder shares: the display, the colours, the photometry and
the calibration mode.

The paper's numbers are the defaults and are cited in each configs/*.yaml line
("# paper: p. N"); values the paper does not give are flagged ASSUMED there and listed
in docs/methods.md.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

import numpy as np
from alhazen import Duration, Model, SubjectParams, Task
from alhazen.errors import ConfigError
from alhazen.paradigms.config import SchedulerConfig
from pydantic import Field, model_validator

from anstiscavanagh1983.color import PAPER_YELLOW_RED_SHARE, ColourSpace, Photometry
from anstiscavanagh1983.stimulus import Fixation, frames_per_stroke, period_px

if TYPE_CHECKING:
    import argparse

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
CONFIGS = PROJECT / "configs"
Colour = Literal["red", "green", "blue", "yellow", "grey"]

CALIBRATED_BASIS = "cd/m2 from a measured photometry file (photometer V(lambda), this display)"
DEMO_BASIS = ("nominal cd/m2 from an UNMEASURED photometry file: device-specific "
              "demonstration values, not physical luminances")


class FixationParams(Model):
    square_arcmin: float = Field(6.0, gt=0)
    cross_arcmin: float = Field(6.0, gt=0)
    line_arcmin: float = Field(1.0, gt=0)


class DisplayParams(SubjectParams):
    """The display every task of this folder draws on."""

    patch_size_dva: float = Field(2.0, gt=0)
    test_colour: Colour = "red"
    reference_colour: Colour = "green"
    reference_cd_m2: float = Field(13.4, gt=0)
    fixation: FixationParams = FixationParams()
    photometry_file: str = "photometry-booth.yaml"
    display_calibration: Literal["calibrated", "uncalibrated-demo"] = "calibrated"
    yellow_red_share: float = Field(PAPER_YELLOW_RED_SHARE, gt=0, lt=1)
    snap_period_to_pixels: bool = True
    fixation_duration: Duration = Duration(ms=500)
    iti: Duration = Duration(ms=500)
    paradigm: SchedulerConfig = SchedulerConfig()

    @model_validator(mode="after")
    def _colours(self) -> DisplayParams:
        if self.test_colour == self.reference_colour:
            raise ValueError("test_colour and reference_colour must differ")
        return self

    def photometry(self) -> Photometry:
        path = Path(self.photometry_file)
        return Photometry.load(path if path.is_absolute() else CONFIGS / path)

    def colour_space(self) -> ColourSpace:
        return ColourSpace(self.photometry(), self.yellow_red_share)

    def fix(self) -> Fixation:
        f = self.fixation
        return Fixation(f.square_arcmin, f.cross_arcmin, f.line_arcmin)

    def luminance_basis(self) -> str:
        return CALIBRATED_BASIS if self.photometry().measured else DEMO_BASIS


def grating_geometry(px_per_deg: float, sf_cpd: float, snap: bool) -> tuple[int, float]:
    """(period in px, effective spatial frequency in c/deg). Snapped to a multiple of 4
    pixels so each quarter-cycle step is whole pixels; refused when it cannot be."""
    if snap:
        p = period_px(px_per_deg, sf_cpd, 4)
    else:
        raw = px_per_deg / sf_cpd
        if abs(raw / 4 - round(raw / 4)) > 1e-6:
            raise ConfigError(
                f"a period of {raw:.3f} px is not a whole number of quarter cycles; set "
                f"snap_period_to_pixels: true or choose a viewing geometry that gives one")
        p = int(round(raw))
    return p, px_per_deg / p


def timing(refresh_hz: float, cycle_hz: float, strokes: int) -> tuple[int, float]:
    """(frames per stroke, effective cycle rate in Hz)."""
    n = frames_per_stroke(refresh_hz, cycle_hz, strokes)
    return n, refresh_hz / (n * strokes)


class EquiluminanceTask(Task):
    """Shared hooks."""

    instructions_section: str = ""

    def instructions(self) -> str | None:
        return instructions_for(self.instructions_section)

    def simulation(self, seed: int):
        from alhazen.modes.simulation import Simulation

        from anstiscavanagh1983.simulate import SimulatedObserver

        observer = SimulatedObserver(seed=seed)
        return Simulation(response=observer, describe={
            "seed": seed, "source": "anstiscavanagh1983.simulate", **observer.describe()})

    @classmethod
    def params_hook(cls, params: Any, args: argparse.Namespace) -> Any:
        """Refuse a real-data session whose luminances would not be physical.

        ``display_calibration: calibrated`` (the default) needs ``measured: true`` in the
        photometry file for any mode that writes real data. ``uncalibrated-demo`` runs
        anyway and every trial is labelled with ``luminance_basis`` saying so.
        """
        from alhazen.modes import Mode

        mode = Mode(args.mode)
        if (mode.writes_real_data and params.display_calibration == "calibrated"
                and not params.photometry().measured):
            raise ConfigError(
                f"{params.photometry_file} is not a measurement (measured: false). Measure "
                f"each gun's maximum luminance through the rig's gamma correction and set "
                f"measured: true, or set display_calibration: uncalibrated-demo to run a "
                f"device-specific demonstration whose cd/m2 are nominal")
        return params

    def base_record(self, p: DisplayParams) -> dict[str, Any]:
        ph = p.photometry()
        return {"test_colour": p.test_colour, "reference_colour": p.reference_colour,
                "reference_cd_m2": p.reference_cd_m2,
                "photometry_measured": bool(ph.measured),
                "display_calibration": p.display_calibration,
                "luminance_basis": p.luminance_basis()}


def instructions_for(section: str) -> str:
    """The ``## <section>`` part of instructions.md, without its heading."""
    text = (PROJECT / "instructions.md").read_text(encoding="utf-8")
    for part in text.split("\n## ")[1:]:
        heading, _, body = part.partition("\n")
        if heading.strip() == section:
            return body.strip()
    raise ConfigError(f"instructions.md has no '## {section}' section")


def michelson(a: float, b: float) -> float:
    return (a - b) / (a + b)


def log_uniform(rng: np.random.Generator, lo: float, hi: float) -> float:
    return float(math.exp(rng.uniform(math.log(lo), math.log(hi))))
