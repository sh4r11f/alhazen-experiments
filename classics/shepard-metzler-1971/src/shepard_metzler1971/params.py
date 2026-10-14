"""The params model: every number a session of mental-rotation runs with.

One model for the task, the stimulus bank and the design, so configs/task.yaml is the
single source of truth. The bank of drawings is generated from these values
(``python -m shepard_metzler1971.bank``) and records them in its manifest; the task
refuses to run when the YAML and the committed bank disagree.

Which values are the paper's and which are assumed is said on each line of the YAML
(``# paper: p. N`` or ``# ASSUMED (not in the paper): ...``), in docs/methods.md and in
docs/experiment.json. The defaults here are the same values; the YAML is what runs.
"""

from __future__ import annotations

from alhazen import Duration, SubjectParams
from alhazen.config.models import Model
from alhazen.paradigms.config import SchedulerConfig
from pydantic import model_validator


class ObjectsConfig(Model):
    """How the ten arm-like objects and their perspective drawings are made."""

    n_cubes: int = 10
    n_elbows: int = 3
    shapes_per_set: int = 5
    min_run: int = 2
    shape_seed: int = 1971
    n_views: int = 18
    view_step_deg: float = 20.0
    view_offset_deg: float = 10.0
    elevation_deg: float = 25.0
    camera_distance: float = 25.0
    views_per_object: int = 7
    min_visible_fraction: float = 0.2
    exclude_face_on: bool = True
    image_px: int = 512
    supersample: int = 3

    @model_validator(mode="after")
    def _valid(self) -> ObjectsConfig:
        if self.n_cubes < 2 + self.n_elbows:
            raise ValueError("n_cubes too small for that many elbows")
        if abs(self.n_views * self.view_step_deg - 360.0) > 1e-9:
            raise ValueError("n_views x view_step_deg must be one full turn (360)")
        if not 0 < self.min_visible_fraction < 1:
            raise ValueError("min_visible_fraction must lie in (0, 1)")
        if self.views_per_object > self.n_views:
            raise ValueError("views_per_object cannot exceed n_views")
        return self


class DesignConfig(Model):
    """The trial list: unique pairs, presentations, blocks and sessions."""

    seed: int = 1971
    angle_step_deg: float = 20.0
    max_angle_deg: float = 180.0
    pairs_per_object_per_angle: int = 2
    presentations: int = 2
    block_size: int = 200
    pure_blocks_per_type: int = 2
    n_sessions: int = 8
    # Filled from --sub / --ses by MentalRotationTask.params_hook; None in a file.
    subject: str | None = None
    session: int | None = None
    # A rehearsal-only stratified sample of the whole design (None: the real session).
    rehearsal_trials: int | None = None

    @model_validator(mode="after")
    def _valid(self) -> DesignConfig:
        if self.session is not None and not 1 <= self.session <= self.n_sessions:
            raise ValueError(
                f"session {self.session} is outside 1..{self.n_sessions}: the design has "
                f"{self.n_sessions} sessions of one {self.block_size}-trial block each"
            )
        if self.rehearsal_trials is not None and self.rehearsal_trials < 1:
            raise ValueError("rehearsal_trials must be >= 1 or null")
        return self


class SimulatedSubjectConfig(Model):
    """The simulated subject of --mode simulate. Not part of the paradigm."""

    intercept_s: float = 1.0
    rate_deg_per_s: float = 60.0
    different_mean_s: float = 3.8
    rt_log_sd: float = 0.25
    error_rate_at_0: float = 0.01
    error_rate_at_180: float = 0.055


class MentalRotationParams(SubjectParams):
    """A session's parameters. Durations resolve to whole frames at the measured rate."""

    drawing_extent_dva: float = 4.3
    aperture_dva: float = 6.0
    spacing_dva: float = 9.0
    line_width_dva: float = 0.04
    surface_color: tuple[float, float, float] = (-1.0, -1.0, -1.0)
    warning_dot_dva: float = 0.3
    warning_duration: Duration = Duration(ms=500)
    intertrial_interval: Duration = Duration(ms=1500)
    response_timeout: Duration = Duration(ms=30000)
    same_key: str = "j"
    different_key: str = "f"
    objects: ObjectsConfig = ObjectsConfig()
    design: DesignConfig = DesignConfig()
    simulated_subject: SimulatedSubjectConfig = SimulatedSubjectConfig()
    paradigm: SchedulerConfig = SchedulerConfig(n_per_condition=1, shuffle=False)

    @model_validator(mode="after")
    def _valid(self) -> MentalRotationParams:
        if self.same_key == self.different_key:
            raise ValueError("same_key and different_key must differ")
        if self.aperture_dva >= self.spacing_dva:
            raise ValueError("the two apertures would overlap: aperture_dva >= spacing_dva")
        if self.drawing_extent_dva >= self.aperture_dva:
            raise ValueError("drawings must fit inside the apertures")
        if self.paradigm.kind != "sequence" or self.paradigm.shuffle:
            raise ValueError(
                "paradigm must be kind: sequence with shuffle: false — the design module "
                "already fixes the order of a session's trials (docs/methods.md, Design)"
            )
        if self.paradigm.n_per_condition != 1:
            raise ValueError("paradigm.n_per_condition must be 1: each trial is its own condition")
        return self
