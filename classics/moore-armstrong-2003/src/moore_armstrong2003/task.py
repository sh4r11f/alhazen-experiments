"""FEF microstimulation gating (Moore & Armstrong 2003): what one trial is made of.

The monkey fixates a central spot. Oriented bars appear in the recorded V4 neuron's
receptive field (RF), outside it (the paper's "distracter"), or at both places at once,
and stay up for 1.5-2 s while the monkey keeps fixating; no saccade is asked for. On a
stimulation trial, 200-500 ms after the bars appear, a STIM_TRIGGER event goes out on
the display flip that marks the drawn moment; the rig file maps it to the TTL line that
triggers the lab's stimulator (the 200 Hz biphasic train itself is the stimulator's,
set to the site's subthreshold current). A control trial marks the same moment with
CONTROL_MARK, which pulses nothing that stimulates, so the recording has the same time
reference on both kinds of trial. docs/methods.md is the specification, with every value
the paper states cited to its page and every value it does not marked ASSUMED.

What this task does NOT do: record or analyse V4 activity (the paper's measure). That
needs a recording system aligned through the sync lines; see docs/methods.md.

Phase by phase (all gaze-contingent, every break ends the trial and re-serves it):

    FIX_ON ──acquire──▶ FIX_ACQUIRED ──baseline hold──▶ VIS_ON (bars on)
      ──hold, trigger_delay──▶ STIM_TRIGGER | CONTROL_MARK
      ──hold, rest of the stimulus──▶ VIS_OFF  =  COMPLETED (paid, monkey)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Literal

import numpy as np
from alhazen import Condition, Duration, SubjectParams, Task, TrialPlan, TrialSetup, outcomes
from alhazen.config.models import Model, RigConfig
from alhazen.core.events import EventSchema
from alhazen.core.trial import CircleRegion
from alhazen.errors import ConfigError
from alhazen.paradigms.config import SchedulerConfig
from alhazen.stimuli.fixation import make_fixation
from alhazen.task import duration as timing
from alhazen.task import phases
from alhazen.task.subject_kind import SubjectKind
from pydantic import model_validator

from moore_armstrong2003 import geometry as geo
from moore_armstrong2003.stimuli import make_bar

log = logging.getLogger(__name__)

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]

# The event that triggers the stimulator. A rig maps it to a TTL line in
# devices.sync.event_lines; params_hook refuses a real session that would emit it on
# stimulation trials with no line to carry it.
STIM_EVENT = "STIM_TRIGGER"
CONTROL_EVENT = "CONTROL_MARK"
REAL_SYNC_BACKENDS = ("nidaq", "datapixx")


class DurationRange(Model):
    """A range a value is drawn from on every trial, in milliseconds."""

    min: Duration
    max: Duration

    @model_validator(mode="after")
    def _ordered(self) -> DurationRange:
        if self.min.ms is None or self.max.ms is None:
            raise ValueError("give both ends of a range in ms ({ms: ...}), not frames")
        if self.min.ms > self.max.ms:
            raise ValueError(f"range min {self.min.ms} ms is above its max {self.max.ms} ms")
        return self

    def seconds(self) -> tuple[float, float]:
        assert self.min.ms is not None and self.max.ms is not None
        return self.min.ms / 1000.0, self.max.ms / 1000.0


class SiteParams(Model):
    """One recording site, as the two mapping paradigms measured it (entered per site)."""

    rf_center_dva: tuple[float, float]
    rf_diameter_dva: float
    preferred_orientation_deg: float
    saccade_endpoint_dva: tuple[float, float]
    movement_threshold_ua: float

    def kind(self) -> geo.SiteKind:
        return geo.classify_site(self.rf_center_dva, self.rf_diameter_dva,
                                 self.saccade_endpoint_dva)


class StimulationParams(Model):
    """The FEF stimulation. Only the trigger time is alhazen's; the train is the
    stimulator's, and its settings are recorded here so every row says what was set."""

    conditions: list[Literal["stim", "control"]]
    train_ms: float
    pulse_rate_hz: float
    pulse_width_ms: float
    biphasic: bool
    current_ua: float
    onset_after_display: DurationRange

    @model_validator(mode="after")
    def _valid(self) -> StimulationParams:
        if not self.conditions or len(set(self.conditions)) != len(self.conditions):
            raise ValueError("stimulation.conditions: list stim and/or control, once each")
        if self.train_ms <= 0 or self.pulse_rate_hz <= 0 or self.pulse_width_ms <= 0:
            raise ValueError("train_ms, pulse_rate_hz and pulse_width_ms must be > 0")
        if self.current_ua <= 0:
            raise ValueError("current_ua must be > 0")
        return self


class DisplaySpec(Model):
    """One display condition: what is in the RF and what is at the distracter site."""

    rf: geo.Orientation
    distracter: geo.Orientation

    @property
    def label(self) -> str:
        return f"rf-{self.rf}_dist-{self.distracter}"


class AnalysisWindows(Model):
    """The paper's measurement windows, kept beside the task so the notebook reads the
    same numbers the validation below checks the timing against."""

    visual_onset_window: Duration
    post_train_window: Duration


class RfGatingFixationTaskParams(SubjectParams):
    """A session's parameters. Durations resolve to whole frames at the measured rate."""

    site: SiteParams
    stimulation: StimulationParams
    timing_draw: Literal["uniform"]
    stimulus_duration: DurationRange
    fix_size_dva: float
    fix_rgb: tuple[float, float, float]
    fix_window_dva: float
    acquire_timeout: Duration
    baseline_hold: Duration
    iti: Duration
    displays: list[DisplaySpec]
    distracter_placement: Literal["auto"]
    distracter_position_dva: tuple[float, float] | None = None
    bar_length_dva: float
    bar_width_dva: float
    bar_contrast: float
    bar_polarity: Literal["dark", "bright"]
    analysis: AnalysisWindows
    paradigm: SchedulerConfig = SchedulerConfig(n_per_condition=10)

    @model_validator(mode="after")
    def _the_design_holds_together(self) -> RfGatingFixationTaskParams:
        stim = "stim" in self.stimulation.conditions
        # Who may be stimulated: only a monkey, and only a session that says so.
        if self.subject_kind is None:
            raise ValueError("declare subject_kind: monkey (a stimulation session) or human "
                             "(the no-stimulation demo)")
        if self.subject_kind is SubjectKind.HUMAN and stim:
            raise ValueError("subject_kind is human, and a human session is never "
                             "stimulated: stimulation.conditions must be [control]")
        # Subthreshold, always: the paper's test currents were below each site's
        # movement threshold (p. 372). A current at or above it would evoke saccades.
        if stim and self.stimulation.current_ua >= self.site.movement_threshold_ua:
            raise ValueError(
                f"stimulation.current_ua {self.stimulation.current_ua} is not below the "
                f"site's movement threshold {self.site.movement_threshold_ua} uA: the paper "
                f"stimulated below threshold (p. 372)")
        # The measurement window after the train must end before the bars go off.
        lo_vis, _ = self.stimulus_duration.seconds()
        _, hi_trig = self.stimulation.onset_after_display.seconds()
        window = self.analysis.post_train_window.ms
        if window is None:
            raise ValueError("analysis.post_train_window must be given in ms")
        latest = hi_trig + (self.stimulation.train_ms + window) / 1000.0
        if latest > lo_vis:
            raise ValueError(
                f"the latest trigger ({hi_trig * 1000:.0f} ms) + the train "
                f"({self.stimulation.train_ms:g} ms) + the post-train window ({window:g} ms) "
                f"ends after the shortest stimulus ({lo_vis * 1000:.0f} ms)")
        if not self.displays:
            raise ValueError("displays: list at least one display condition")
        labels = [d.label for d in self.displays]
        if len(set(labels)) != len(labels):
            raise ValueError(f"displays lists a condition twice: {labels}")
        for name in ("fix_size_dva", "fix_window_dva", "bar_length_dva", "bar_width_dva"):
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} must be > 0")
        geo.bar_luminance(self.bar_contrast, self.bar_polarity)  # refuses the impossible
        self._check_geometry()
        return self

    def _check_geometry(self) -> None:
        kind = self.site.kind()  # raises for a partial overlap
        rf = self.site.rf_center_dva
        dist = self.distracter_xy(kind)
        reach = self.bar_length_dva / 2
        if any(d.distracter != "none" for d in self.displays):
            gap = float(np.hypot(dist[0] - rf[0], dist[1] - rf[1]))
            if gap < self.site.rf_diameter_dva / 2 + reach:
                raise ValueError(f"the distracter at {dist} would fall inside the RF "
                                 f"(centre {rf}, diameter {self.site.rf_diameter_dva})")
        for name, (x, y) in (("RF bar", rf), ("distracter", dist)):
            if float(np.hypot(x, y)) - reach <= self.fix_window_dva:
                raise ValueError(f"the {name} at {(x, y)} reaches into the fixation window")

    def distracter_xy(self, kind: geo.SiteKind | None = None) -> geo.Point:
        return geo.distracter_position(kind or self.site.kind(), self.site.rf_center_dva,
                                       self.site.saccade_endpoint_dva,
                                       self.distracter_position_dva)


def stimulation_wiring_problem(rig: RigConfig) -> str | None:
    """Why a rig cannot carry the stimulation trigger, or None when it can.

    A stimulation session on a rig whose sync does not map STIM_TRIGGER to a real line
    would record "stim" on every stimulation trial while nothing was stimulated."""
    sync = rig.devices.sync
    if sync is None:
        return "the rig has no sync device (devices.sync)"
    if sync.backend not in REAL_SYNC_BACKENDS:
        return f"the rig's sync backend is {sync.backend!r}, which drives no hardware line"
    if STIM_EVENT not in sync.event_lines:
        return f"the rig's devices.sync.event_lines maps no line to {STIM_EVENT}"
    return None


class RfGatingFixationTask(Task):
    name = "rf-gating-fixation"
    events = EventSchema(("FIX_ON", "FIX_ACQUIRED", "VIS_ON", STIM_EVENT, CONTROL_EVENT,
                          "VIS_OFF"))
    outcomes = outcomes(
        COMPLETED=dict(completed=True, success=True),
        NO_FIXATION=dict(completed=False),
        BROKE_FIX_BASELINE=dict(completed=False),
        BROKE_FIX_STIMULUS=dict(completed=False),
        BROKE_FIX_AFTER_TRIGGER=dict(completed=False),
    )
    params_model = RfGatingFixationTaskParams

    @classmethod
    def default_params(cls) -> Path:
        return PROJECT / "configs" / "task.yaml"

    @classmethod
    def params_hook(cls, params: Any, args: Any) -> Any:
        """Refuse a real session that would stimulate with nothing wired to stimulate.

        Only run and training (a subject in the chair, the rig driven as written) are
        checked: test and simulate are what a rig without the line is for."""
        from alhazen.config.loader import load_rig
        from alhazen.modes import Mode

        mode = getattr(args, "mode", None)
        if mode is None or "stim" not in params.stimulation.conditions:
            return params
        if not Mode(mode).drives_subject:
            return params
        problem = stimulation_wiring_problem(load_rig(args.rig))
        if problem is not None:
            raise ConfigError(
                f"CANNOT RUN: this params file has stimulation trials, and {problem}. "
                f"Every stimulation trial would be recorded as stimulated with no trigger "
                f"sent. Use a rig whose sync maps {STIM_EVENT} to the stimulator's trigger "
                f"line (configs/rig-recording-example.yaml shows how), or set "
                f"stimulation.conditions: [control]")
        return params

    def instructions(self) -> str | None:
        # Shown to a human (the no-stimulation demo). A monkey session shows no
        # instruction screen: alhazen skips it for subject_kind monkey.
        return (PROJECT / "instructions.md").read_text(encoding="utf-8")

    def conditions(self, rng: np.random.Generator) -> list[Condition]:
        p: RfGatingFixationTaskParams = self.params  # type: ignore[assignment]
        return [Condition({"display": d.label, "stimulation": s})
                for d in p.displays for s in p.stimulation.conditions]

    def display_spec(self, label: str) -> DisplaySpec:
        p: RfGatingFixationTaskParams = self.params  # type: ignore[assignment]
        for d in p.displays:
            if d.label == label:
                return d
        raise KeyError(f"no display condition {label!r} in this params file")

    def build_trial(self, setup: TrialSetup) -> TrialPlan:
        p: RfGatingFixationTaskParams = self.params  # type: ignore[assignment]
        hz = setup.refresh_rate_hz
        screen = setup.screen
        spec = self.display_spec(setup.condition.params["display"])
        stim = setup.condition.params["stimulation"] == "stim"
        kind = p.site.kind()
        rf_xy = p.site.rf_center_dva
        dist_xy = p.distracter_xy(kind)

        # Drawn once per trial from the session's generator, so a seeded session replays.
        lo_v, hi_v = p.stimulus_duration.seconds()
        lo_t, hi_t = p.stimulation.onset_after_display.seconds()
        stimulus_s = float(setup.rng.uniform(lo_v, hi_v))
        trigger_s = float(setup.rng.uniform(lo_t, hi_t))

        rgb = geo.signed_rgb(geo.bar_luminance(p.bar_contrast, p.bar_polarity))
        stimuli: dict[str, Any] = {
            "fixation": make_fixation(setup.display, screen, p.fix_size_dva, p.fix_rgb),
        }
        bars = []
        for key, which, xy in (("rf_bar", spec.rf, rf_xy), ("distracter_bar", spec.distracter,
                                                            dist_xy)):
            ori = geo.orientation_deg(which, p.site.preferred_orientation_deg)
            if ori is None:
                continue
            stimuli[key] = make_bar(setup.display, screen, key, p.bar_length_dva,
                                    p.bar_width_dva, ori,
                                    (screen.deg2px(xy[0]), screen.deg2px(xy[1])), rgb)
            bars.append(key)

        out = self.outcomes
        plan_phases = [
            phases.AcquireFixation("fixation", "fixation", hold_s=0.0,
                                   timeout_s=p.acquire_timeout.seconds(hz),
                                   on_timeout=out["NO_FIXATION"], onset_event="FIX_ON",
                                   acquired_event="FIX_ACQUIRED"),
            phases.HoldFixation("fixation", "fixation", duration_s=p.baseline_hold.seconds(hz),
                                on_break=out["BROKE_FIX_BASELINE"],
                                duration_record_key="baseline_hold_s"),
            # The bars come on with VIS_ON; the trigger time is counted from that flip.
            phases.HoldFixation("fixation", "fixation", duration_s=trigger_s,
                                on_break=out["BROKE_FIX_STIMULUS"], concurrent=bars,
                                onset_event="VIS_ON", duration_record_key="trigger_delay_s"),
            # STIM_TRIGGER goes out on the first flip of this phase: the drawn moment, to
            # the nearest frame. The bars stay up; the monkey must keep fixating.
            phases.HoldFixation("fixation", "fixation", duration_s=stimulus_s - trigger_s,
                                on_break=out["BROKE_FIX_AFTER_TRIGGER"], concurrent=bars,
                                onset_event=STIM_EVENT if stim else CONTROL_EVENT,
                                duration_record_key="after_trigger_s"),
            # Nothing drawn: the flip that takes the bars off carries VIS_OFF and ends the
            # trial as completed.
            phases.Feedback([], 0.0, then=out["COMPLETED"], onset_event="VIS_OFF"),
        ]
        sync = setup.cfg.rig.devices.sync
        line = sync.event_lines.get(STIM_EVENT) if sync is not None else None
        record = {
            "display": spec.label,
            "rf_stimulus": spec.rf,
            "distracter_stimulus": spec.distracter,
            "rf_ori_deg": geo.orientation_deg(spec.rf, p.site.preferred_orientation_deg),
            "distracter_ori_deg": geo.orientation_deg(spec.distracter,
                                                      p.site.preferred_orientation_deg),
            "stimulation": "stim" if stim else "control",
            "site_kind": kind,
            "rf_x_dva": rf_xy[0],
            "rf_y_dva": rf_xy[1],
            "distracter_x_dva": dist_xy[0],
            "distracter_y_dva": dist_xy[1],
            "stimulus_duration_s": stimulus_s,
            "current_ua": p.stimulation.current_ua if stim else 0.0,
            "train_ms": p.stimulation.train_ms if stim else 0.0,
            # Which line the trigger could have gone out on, as the rig says: "" on a rig
            # that maps none (a booth, a simulated rehearsal), so a row never claims a
            # stimulation the rig could not have delivered.
            "stim_ttl_line": (line or "") if stim else "",
            "stim_ttl_backend": (sync.backend if (sync is not None and line) else "") if stim
            else "",
        }
        return TrialPlan(
            phases=plan_phases,
            stimuli=stimuli,
            regions={"fixation": CircleRegion((0.0, 0.0), screen.deg2px(p.fix_window_dva))},
            record=record,
        )

    def trial_timing(self, condition: Condition, refresh_rate_hz: float):
        p: RfGatingFixationTaskParams = self.params  # type: ignore[assignment]
        hz = refresh_rate_hz
        lo, hi = p.stimulus_duration.seconds()
        return timing.TrialTiming([
            timing.wait("fixation acquired", p.acquire_timeout.seconds(hz)),
            timing.fixed("baseline fixation", p.baseline_hold.seconds(hz)),
            timing.uniform("bars on (stimulus period)", lo, hi, basis="paper p. 373: 1.5-2 s"),
        ])

    def simulation(self, seed: int):
        from alhazen.modes.simulation import Simulation

        from moore_armstrong2003.simulate import SimulatedMonkey

        monkey = SimulatedMonkey(seed=seed)
        return Simulation(tracker=monkey, describe={"seed": seed, **monkey.describe(),
                                                    "source": "moore_armstrong2003.simulate"})
