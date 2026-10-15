"""What every task in this folder shares: the display geometry and colours of
Cavanagh (1992), the photometry they are built on, and where k comes from.

The paper's numbers are the defaults here and are cited in each configs/*.yaml line
("# paper: p. N"); values the paper does not give are flagged ASSUMED there and listed in
docs/methods.md.
"""

from __future__ import annotations

import logging
import math
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd
from alhazen import Duration, Model, SubjectParams, Task
from alhazen.errors import ConfigError
from alhazen.paradigms.config import SchedulerConfig
from pydantic import Field, model_validator

from cavanagh1992.color import ColorModel, EquiluminanceChoice, Photometry, red_luminance_share
from cavanagh1992.scene import PointerGeometry

if TYPE_CHECKING:
    import argparse

log = logging.getLogger(__name__)

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
CONFIGS = PROJECT / "configs"


class PointerParams(Model):
    inner_dva: float = 1.3
    outer_dva: float = 3.9
    width_inner_dva: float = 0.08
    width_outer_dva: float = 0.35


class CavanaghParams(SubjectParams):
    """The display every task of this folder draws on."""

    annulus_inner_dva: float = Field(4.0, gt=0)
    annulus_outer_dva: float = Field(8.4, gt=0)
    bullseye_radius_dva: float = Field(1.0, gt=0)
    bullseye_rings: int = Field(4, ge=1)
    n_cycles: int = Field(8, ge=2)
    rate_hz: float = Field(2.0, gt=0)
    mean_luminance_cd_m2: float = Field(45.0, gt=0)
    red_phosphor_xy: tuple[float, float] = (0.608, 0.348)
    green_phosphor_xy: tuple[float, float] = (0.249, 0.602)
    mean_xy: tuple[float, float] = (0.409, 0.488)
    color_contrast: float = Field(0.40, ge=0, le=1)
    photometry_file: str = "photometry-booth.yaml"
    fixation_duration: Duration = Duration(ms=500)
    iti: Duration = Duration(ms=500)
    paradigm: SchedulerConfig = SchedulerConfig()

    @model_validator(mode="after")
    def _geometry(self) -> CavanaghParams:
        if self.annulus_inner_dva >= self.annulus_outer_dva:
            raise ValueError("annulus_inner_dva must be below annulus_outer_dva")
        if self.bullseye_radius_dva >= self.annulus_inner_dva:
            raise ValueError("the bull's-eye must fit inside the annulus")
        if self.n_cycles % 2:
            raise ValueError("n_cycles must be even: a tracked pair is two opposite bars")
        return self

    def photometry(self) -> Photometry:
        path = Path(self.photometry_file)
        return Photometry.load(path if path.is_absolute() else CONFIGS / path)

    def color_model(self, k: float = 1.0) -> ColorModel:
        ph = self.photometry()
        return ColorModel(
            mean_cd_m2=self.mean_luminance_cd_m2,
            red_share=red_luminance_share(self.red_phosphor_xy, self.green_phosphor_xy,
                                          self.mean_xy),
            red_max_cd_m2=ph.red_max_cd_m2, green_max_cd_m2=ph.green_max_cd_m2, k=k)


class TrackedDisplayParams(CavanaghParams):
    """Tasks that show the colour grating at the observer's equiluminance."""

    equiluminance: EquiluminanceChoice = EquiluminanceChoice()
    pointer: PointerParams = PointerParams()

    def k(self) -> float:
        e = self.equiluminance
        if e.source == "photometric":
            return 1.0
        if e.green_red_ratio is None:
            raise ConfigError(
                "equiluminance.green_red_ratio is not set: it is filled in from the subject's "
                "calibration when a session starts (run.py). Building a trial outside a "
                "session needs equiluminance.source fixed or photometric")
        return float(e.green_red_ratio)

    def pointer_geometry(self) -> PointerGeometry:
        p = self.pointer
        return PointerGeometry(p.inner_dva, p.outer_dva, p.width_inner_dva, p.width_outer_dva)


def pointer_geometry_default(params: CavanaghParams) -> PointerGeometry:
    p = PointerParams()
    return PointerGeometry(p.inner_dva, p.outer_dva, p.width_inner_dva, p.width_outer_dva)


# -- the subject's equiluminance setting, from their own calibration runs -------------

SETTING_COLUMN = "k_setting"


def geometric_summary(values: np.ndarray) -> tuple[float, float]:
    logs = np.log(np.asarray(values, dtype=float))
    sd = float(logs.std(ddof=1)) if logs.size > 1 else float("nan")
    return float(math.exp(logs.mean())), sd


def latest_calibration(data_root: Path, subject: str, task: str) -> tuple[float, str] | None:
    """The subject's k from their most recent run of ``task`` under ``data_root``: the
    geometric mean of its committed settings, and a sentence saying where it came from.
    None when there is no such run, or it holds no committed setting."""
    from alhazen.data.paths import find_runs

    runs = [r for r in find_runs(data_root) if r.subject == subject and r.task == task]
    for run in sorted(runs, key=lambda r: (r.session, r.run, str(r.path)), reverse=True):
        for csv in sorted(run.path.glob("*_trials.csv")):
            df = pd.read_csv(csv)
            if SETTING_COLUMN not in df or "outcome" not in df:
                continue
            settings = df.loc[df["outcome"] == "SET", SETTING_COLUMN].dropna()
            if settings.empty:
                continue
            k, sd = geometric_summary(settings.to_numpy())
            where = csv.relative_to(data_root).as_posix()
            return k, (f"{task}: geometric mean of {len(settings)} settings in {where} "
                       f"(sd of log k {sd:.3f})")
    return None


class CavanaghTask(Task):
    """Shared hooks. Every concrete task declares name, events, outcomes, params_model."""

    instructions_section: str = ""

    def instructions(self) -> str | None:
        return instructions_for(self.instructions_section)

    def simulation(self, seed: int):
        from alhazen.modes.simulation import Simulation

        from cavanagh1992.simulate import SimulatedObserver

        observer = SimulatedObserver(seed=seed)
        return Simulation(response=observer, describe={
            "seed": seed, "source": "cavanagh1992.simulate", **observer.describe()})

    @classmethod
    def params_hook(cls, params: Any, args: argparse.Namespace) -> Any:
        """Fill in equiluminance.green_red_ratio (and its basis) for tasks that need it.

        ``calibration``: the subject's most recent run of the chosen equiluminance task,
        in the data root this session writes to (the rehearsal root for test and
        simulate). A run-mode session with no calibration is refused. A rehearsal with
        none uses photometric equiluminance (k = 1) and says so in the basis.
        """
        if not isinstance(params, TrackedDisplayParams):
            return params
        e = params.equiluminance
        if e.source != "calibration" or e.green_red_ratio is not None:
            if e.source == "photometric":
                return _with_k(params, 1.0, "photometric: equal luminance by the photometer")
            return params
        from alhazen.config.loader import load_rig
        from alhazen.modes import Mode
        from alhazen.modes.rehearsal import rehearsal_root

        mode = Mode(args.mode)
        if not mode.runs_trials:
            return _with_k(params, 1.0, f"photometric: {mode.value} mode has no subject")
        sub, rig = getattr(args, "sub", None), getattr(args, "rig", None)
        found = None
        if sub is not None and rig is not None:
            root = Path(load_rig(rig).data_root)
            if not mode.writes_real_data:
                root = rehearsal_root(root)
            found = latest_calibration(root, str(sub), e.method)
        if found is not None:
            k, basis = found
            log.warning("equiluminance: k = %.4f from %s", k, basis)
            return _with_k(params, k, basis)
        if mode.writes_real_data:
            raise ConfigError(
                f"subject {sub} has no {e.method} run to take their equiluminance from. Run "
                f"`run.py --task {e.method}` for this subject first, or set "
                f"equiluminance.source to fixed (with green_red_ratio) or photometric")
        return _with_k(params, 1.0, f"photometric: no {e.method} run for subject {sub} "
                                    f"(rehearsal only; a real session would be refused)")


def _with_k(params: TrackedDisplayParams, k: float, basis: str) -> TrackedDisplayParams:
    data = params.model_dump()
    data["equiluminance"] = {**data["equiluminance"], "green_red_ratio": k, "basis": basis}
    return type(params).model_validate(data)


def instructions_for(section: str) -> str:
    """The ``## <section>`` part of instructions.md, without its heading."""
    text = (PROJECT / "instructions.md").read_text(encoding="utf-8")
    parts = text.split("\n## ")
    for part in parts[1:]:
        heading, _, body = part.partition("\n")
        if heading.strip() == section:
            return body.strip()
    raise ConfigError(f"instructions.md has no '## {section}' section")


def random_phase(rng: np.random.Generator) -> float:
    return float(rng.uniform(0.0, 2.0 * math.pi))


def log_uniform(rng: np.random.Generator, lo: float, hi: float) -> float:
    return float(math.exp(rng.uniform(math.log(lo), math.log(hi))))
