"""What both tasks share: the stimulus parameters, the cells, and the geometry check."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from alhazen import Duration, SubjectParams
from alhazen.errors import ConfigError
from pydantic import field_validator

from campbell_robson1968.grating import code_step_contrast, sampling_problem

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]


class CampbellRobsonParams(SubjectParams):
    """Stimulus parameters shared by both tasks. Sizes in degrees of visual angle, from
    the rig's measured geometry; luminances in linearised display units (0..1)."""

    field_dva: float = 10.0
    sf_cpd: list[float] = [0.5, 1.0, 2.0, 4.0, 8.0]
    waveforms: list[Literal["sine", "square"]] = ["sine"]
    orientation_deg: float = 0.0
    random_phase: bool = True
    mean_luminance: float = 0.5
    display_bits: int = 8
    dither: Literal["none", "noisy-bit"] = "noisy-bit"
    min_px_per_cycle: float = 4.0
    square_min_px_per_cycle: float = 12.0
    fix_size_dva: float = 0.15
    fix_luminance: float = 0.0
    marks_gap_dva: float = 0.3
    marks_arm_dva: float = 0.6
    marks_width_dva: float = 0.06
    marks_luminance: float = 0.0
    fixation_duration: Duration = Duration(ms=500)
    iti: Duration = Duration(ms=500)

    @field_validator("sf_cpd")
    @classmethod
    def _positive(cls, v: list[float]) -> list[float]:
        if not v or any(f <= 0 for f in v) or len(set(v)) != len(v):
            raise ValueError("sf_cpd must be distinct positive spatial frequencies")
        return v

    @field_validator("waveforms")
    @classmethod
    def _distinct(cls, v: list[str]) -> list[str]:
        if not v or len(set(v)) != len(v):
            raise ValueError("waveforms must be a non-empty list without repeats")
        return v

    def quantised_mean(self) -> float:
        """The mean snapped to a code value, so the field's mean and the surround's
        are the same code (no step at the field's edge)."""
        levels = 2**self.display_bits - 1
        return round(self.mean_luminance * levels) / levels


def cell_name(waveform: str, sf: float) -> str:
    return f"{waveform}-{sf:g}"


def cells(p: CampbellRobsonParams) -> dict[str, tuple[str, float]]:
    """Cell label -> (waveform, sf_cpd): every waveform at every frequency."""
    return {cell_name(w, f): (w, float(f)) for w in p.waveforms for f in p.sf_cpd}


def check_geometry(
    p: CampbellRobsonParams, px_per_deg: float, width_px: int, height_px: int
) -> dict[str, float]:
    """Refuse, before a stimulus is drawn, any cell this rig cannot show faithfully, and
    a field that does not fit on the screen. Returns facts worth recording."""
    problems = [
        f"{name}: {msg}"
        for name, (w, f) in cells(p).items()
        if (
            msg := sampling_problem(f, px_per_deg, w, p.min_px_per_cycle, p.square_min_px_per_cycle)
        )
    ]
    side = p.field_dva * px_per_deg + 2 * (p.marks_gap_dva + p.marks_width_dva) * px_per_deg
    if side > min(width_px, height_px):
        problems.append(
            f"the {p.field_dva:g} deg field and its marks need {side:.0f} px; the "
            f"screen is {width_px} x {height_px}"
        )
    # Cycles in the field: the paper found thresholds rise when fewer than four cycles
    # are visible (p. 553); said, not refused, because the paper's own lowest
    # frequencies had the same limit.
    if problems:
        raise ConfigError(
            "This rig cannot show the parameter set as specified:\n- "
            + "\n- ".join(problems)
            + "\nUse a longer viewing distance or a denser display, or drop "
            "those frequencies (configs/rig-booth-far.yaml is an example "
            "for the high-frequency set)."
        )
    return {
        "px_per_deg": float(px_per_deg),
        "min_cycles_in_field": float(p.field_dva * min(p.sf_cpd)),
        "code_step_contrast": code_step_contrast(p.quantised_mean(), p.display_bits),
    }
