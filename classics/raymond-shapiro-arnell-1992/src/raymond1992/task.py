"""Raymond, Shapiro & Arnell (1992), Experiment 2: the attentional blink.

One trial: the subject starts it with SPACE; a small white fixation dot is shown for
180 ms; then a rapid serial visual presentation (RSVP) of black letters on a uniform
grey field, each letter 15 ms on and 75 ms off (11.1 letters/s), with one WHITE
target letter after 7-15 others and 8 more letters after it. On half the trials a
black X (the probe) is one of the letters at serial positions 0..+8 after the target
(at 0 the white target is itself an X). After the stream the subject reports:

- experimental condition: the white letter (typed), then whether an X was present;
- control condition: whether an X was present only (told to ignore the white letter).

docs/methods.md is the specification; which values are the paper's and which are
ASSUMED is said in configs/task.yaml line by line.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Literal

import numpy as np
from alhazen import Duration, SubjectParams, Task, TrialPlan, TrialSetup, outcomes
from alhazen.core.events import EventSchema
from alhazen.core.trial import PhaseAction
from alhazen.display.frames import FrameTimeline
from alhazen.errors import ConfigError
from alhazen.paradigms.base import Condition, SimpleSequence
from alhazen.paradigms.blocks import BlockPlan
from alhazen.task import phases
from alhazen.task.duration import PlannedSchedule, TrialTiming, fixed, uniform, wait
from pydantic import BaseModel, field_validator, model_validator

from raymond1992 import design
from raymond1992.glyphs import glyph
from raymond1992.stimuli import make_dot, make_letter, make_prompt, make_rect

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
log = logging.getLogger(__name__)


class Screens(BaseModel):
    """The words on screen (none are given in the paper)."""

    model_config = {"extra": "forbid", "frozen": True}

    intro_experimental: str
    intro_control: str
    ready_experimental: str
    ready_control: str
    target_prompt: str
    probe_prompt: str


class AttentionalBlinkTaskParams(SubjectParams):
    """A session's parameters. Durations resolve to whole frames at the measured rate."""

    # Geometry (dva)
    letter_height_dva: float = 0.82
    field_width_dva: float = 16.3
    field_height_dva: float = 12.5
    fixation_dot_dva: float = 0.15
    prompt_height_dva: float = 0.5
    # Luminance (cd/m², converted on a gamma-corrected display of known white)
    field_cd_m2: float = 9.1
    target_cd_m2: float = 32.9
    letters_cd_m2: float = 0.0
    fixation_cd_m2: float = 32.9
    surround_cd_m2: float = 0.0
    prompt_cd_m2: float = 0.0
    display_white_cd_m2: float = 32.9
    # Timing
    fixation_duration: Duration = Duration(ms=180)
    fixation_gap: Duration = Duration(ms=0)
    letter_duration: Duration = Duration(ms=15)
    isi: Duration = Duration(ms=75)
    max_letter_error_ms: float = 5.0
    max_soa_error_ms: float = 2.0
    on_inexact_timing: Literal["refuse", "warn"] = "refuse"
    # Stream
    pretarget_min: int = 7
    pretarget_max: int = 15
    posttarget_items: int = 8
    # Design
    probe_positions: tuple[int, ...] = tuple(range(9))
    trials_per_probe_position: int = 10
    probe_absent_trials: int = 90
    trials_between_rests: int = 60
    practice_trials: int = 10
    practice_probe_present: int = 5
    condition_order: Literal["by-subject", "experimental-first", "control-first"] = "by-subject"
    # Responses
    probe_yes_key: str = "y"
    probe_no_key: str = "n"
    response_timeout: Duration = Duration(ms=30000)
    ready_timeout: Duration = Duration(ms=600000)
    screens: Screens | None = None

    @field_validator("probe_yes_key", "probe_no_key")
    @classmethod
    def _plain_key(cls, v: str) -> str:
        if not v or v != v.strip().lower():
            raise ValueError("a key name is lower-case, as the keyboard reports it")
        return v

    @model_validator(mode="after")
    def _consistent(self) -> AttentionalBlinkTaskParams:
        if self.probe_yes_key == self.probe_no_key:
            raise ValueError("probe_yes_key and probe_no_key must differ")
        if not 1 <= self.pretarget_min <= self.pretarget_max:
            raise ValueError("need 1 <= pretarget_min <= pretarget_max")
        if self.pretarget_max + 1 + self.posttarget_items > 26:
            raise ValueError("a stream longer than 26 letters cannot avoid repeating a letter")
        if not self.probe_positions or any(
            not 0 <= p <= self.posttarget_items for p in self.probe_positions
        ):
            raise ValueError("probe_positions must lie in 0..posttarget_items")
        for name in ("trials_per_probe_position", "trials_between_rests"):
            if getattr(self, name) < 1:
                raise ValueError(f"{name} must be >= 1")
        if self.probe_absent_trials < 0 or self.practice_trials < 0:
            raise ValueError("trial counts cannot be negative")
        if not 0 <= self.practice_probe_present <= self.practice_trials:
            raise ValueError("practice_probe_present must lie in 0..practice_trials")
        if self.display_white_cd_m2 <= 0:
            raise ValueError("display_white_cd_m2 must be > 0")
        return self

    def spec(self) -> design.DesignSpec:
        return design.DesignSpec(
            probe_positions=tuple(self.probe_positions),
            trials_per_probe_position=self.trials_per_probe_position,
            probe_absent_trials=self.probe_absent_trials,
            trials_between_rests=self.trials_between_rests,
            practice_trials=self.practice_trials,
            practice_probe_present=self.practice_probe_present,
        )


DEFAULT_SCREENS = Screens(
    intro_experimental=(
        "Next: name the WHITE letter, then say whether there was a black X.\n\n"
        "After each stream, type the white letter, then press Y if you saw an X or N if "
        "you did not.\n\nPress SPACE to start a trial."
    ),
    intro_control=(
        "Next: IGNORE the white letter. Only say whether there was a black X.\n\n"
        "After each stream, press Y if you saw an X or N if you did not.\n\n"
        "Press SPACE to start a trial."
    ),
    ready_experimental="White letter, then X?   SPACE to start",
    ready_control="Ignore the white letter. X?   SPACE to start",
    target_prompt="Type the white letter",
    probe_prompt="Was there an X?   Y = yes   N = no",
)


class AttentionalBlinkTask(Task):
    name = "attentional-blink"
    events = EventSchema((
        "READY", "START_KEY", "FIX_ON", "STREAM_ON", "TARGET_ON", "PROBE_ON", "STREAM_OFF",
        "TARGET_PROMPT", "TARGET_RESPONSE", "PROBE_PROMPT", "PROBE_RESPONSE",
    ))
    outcomes = outcomes(
        HIT=dict(completed=True, success=True),
        MISS=dict(completed=True, success=False),
        FALSE_ALARM=dict(completed=True, success=False),
        CORRECT_REJECTION=dict(completed=True, success=True),
        NO_RESPONSE=dict(completed=False),
        NO_START=dict(completed=False),
    )
    params_model = AttentionalBlinkTaskParams

    def __init__(self, params: Any) -> None:
        super().__init__(params)
        self._stimuli: dict[str, Any] | None = None
        self._stimuli_for: tuple[int, float] | None = None
        self._last_condition: str | None = None
        self._timing_checked_at: float | None = None
        # What the trial being run shows, for the simulated observer to read.
        self.current: dict[str, Any] | None = None

    @classmethod
    def default_params(cls) -> Path:
        return PROJECT / "configs" / "task.yaml"

    @classmethod
    def params_hook(cls, params: Any, args: Any) -> Any:
        """Settle the condition order from the subject id, and outside run mode let a
        refresh rate that cannot show the paper's timing run with a warning."""
        from alhazen.modes import Mode

        updates: dict[str, Any] = {
            "condition_order": design.resolve_order(
                params.condition_order, getattr(args, "sub", None)
            )
        }
        mode = getattr(args, "mode", None)
        if mode is not None and Mode(mode) is not Mode.RUN and params.on_inexact_timing == "refuse":
            updates["on_inexact_timing"] = "warn"
        return params.model_copy(update=updates)

    def instructions(self) -> str | None:
        return (PROJECT / "instructions.md").read_text(encoding="utf-8")

    @property
    def p(self) -> AttentionalBlinkTaskParams:
        return self.params  # type: ignore[return-value]

    def _screens(self) -> Screens:
        return self.p.screens or DEFAULT_SCREENS

    # -- scheduling --------------------------------------------------------

    def _order(self) -> str:
        return design.resolve_order(self.p.condition_order, None)

    def _plan(self, rng: np.random.Generator) -> list[list[dict]]:
        return design.session_plan(self.p.spec(), self._order(), rng)

    def make_source(self, params: Any, rng: np.random.Generator) -> BlockPlan:
        blocks = self._plan(rng)
        sources = [SimpleSequence([Condition(c) for c in block], shuffle=False) for block in blocks]
        return BlockPlan(sources, breaks=True)

    def duration_schedule(self, params: Any, rng: np.random.Generator) -> PlannedSchedule:
        blocks = self._plan(rng)
        return PlannedSchedule(
            blocks=tuple(tuple(Condition(c) for c in block) for block in blocks),
            breaks=len(blocks) - 1,
            n_cells=2 * (len(self.p.probe_positions) + 1),
            note="practice and main blocks per condition; rests between blocks end on SPACE",
        )

    def trial_timing(self, condition: Condition, refresh_rate_hz: float) -> TrialTiming:
        fp = self._frame_plan(refresh_rate_hz, check=False)
        lead = (fp.fixation_frames + fp.gap_frames) / refresh_rate_hz
        per_item = fp.soa_frames / refresh_rate_hz
        n_min = self.p.pretarget_min + 1 + self.p.posttarget_items
        n_max = self.p.pretarget_max + 1 + self.p.posttarget_items
        cap = self.p.response_timeout.seconds(refresh_rate_hz)
        spans = [
            wait("start (SPACE)", self.p.ready_timeout.seconds(refresh_rate_hz)),
            fixed("fixation dot", lead),
            uniform("letter stream", n_min * per_item, n_max * per_item, "7-15 pre-target letters"),
        ]
        if condition.params.get("condition", design.EXPERIMENTAL) == design.EXPERIMENTAL:
            spans.append(wait("target report", cap))
        spans.append(wait("probe report", cap))
        return TrialTiming(spans)

    # -- timing ------------------------------------------------------------

    def _frame_plan(self, hz: float, check: bool = True) -> design.FramePlan:
        p = self.p
        fp = design.frame_plan(hz, p.letter_duration, p.isi, p.fixation_duration, p.fixation_gap)
        if not check or self._timing_checked_at == hz:
            return fp
        letter_ms = p.letter_duration.seconds(hz) * 1000.0
        soa_ms = letter_ms + p.isi.seconds(hz) * 1000.0
        d_letter, d_soa = design.timing_errors(fp, letter_ms, soa_ms)
        if abs(d_letter) > p.max_letter_error_ms + 1e-9 or abs(d_soa) > p.max_soa_error_ms + 1e-9:
            message = (
                f"at {hz:.2f} Hz the stream is {fp.letter_frames} frame(s) on "
                f"({fp.letter_ms:.1f} ms) and {fp.isi_frames} off ({fp.isi_ms:.1f} ms): SOA "
                f"{fp.soa_ms:.1f} ms against the paper's {soa_ms:.0f} ms (allowed "
                f"±{p.max_soa_error_ms} ms) and letters {fp.letter_ms:.1f} ms against "
                f"{letter_ms:.0f} ms (allowed ±{p.max_letter_error_ms} ms). Rates that fit: "
                f"100, 120, 144, 200 or 240 Hz (docs/methods.md, Apparatus)."
            )
            if p.on_inexact_timing == "refuse":
                raise ConfigError(message + " Set on_inexact_timing: warn to run anyway.")
            log.warning("INEXACT TIMING: %s Running anyway (on_inexact_timing: warn).", message)
        self._timing_checked_at = hz
        return fp

    # -- stimuli -----------------------------------------------------------

    def _build_stimuli(self, setup: TrialSetup) -> dict[str, Any]:
        key = (id(setup.display), setup.screen.px_per_deg)
        if self._stimuli is not None and self._stimuli_for == key:
            return self._stimuli
        p, s, d = self.p, setup.screen, setup.display
        white = p.display_white_cd_m2
        rgb = {name: design.to_rgb(getattr(p, f"{name}_cd_m2"), white)
               for name in ("field", "target", "letters", "fixation", "surround", "prompt")}
        for name in ("field", "target", "fixation"):
            if getattr(p, f"{name}_cd_m2") > white:
                log.warning("%s_cd_m2 %.1f is above display_white_cd_m2 %.1f: drawn at white",
                            name, getattr(p, f"{name}_cd_m2"), white)
        cap_px = s.deg2px(p.letter_height_dva)
        stimuli: dict[str, Any] = {
            "surround": make_rect(d, "surround", s.width_px * 1.5, s.height_px * 1.5,
                                  rgb["surround"]),
            "field": make_rect(d, "field", s.deg2px(p.field_width_dva),
                               s.deg2px(p.field_height_dva), rgb["field"]),
            "fixation": make_dot(d, s.deg2px(p.fixation_dot_dva), rgb["fixation"]),
        }
        wrap = s.deg2px(p.field_width_dva) * 0.9
        text_px = s.deg2px(p.prompt_height_dva)
        for name, text in self._screens().model_dump().items():
            stimuli[name] = make_prompt(d, name, text, text_px, rgb["prompt"], wrap)
        for letter in design.ALPHABET:
            g = glyph(letter, cap_px)
            stimuli[f"black_{letter}"] = make_letter(d, g, rgb["letters"])
            stimuli[f"white_{letter}"] = make_letter(d, g, rgb["target"])
        self._stimuli, self._stimuli_for = stimuli, key
        return stimuli

    # -- one trial ---------------------------------------------------------

    def build_trial(self, setup: TrialSetup) -> TrialPlan:
        p = self.p
        hz = setup.refresh_rate_hz
        fp = self._frame_plan(hz)
        cond = setup.condition.params
        condition = cond["condition"]
        stream = design.make_stream(setup.rng, cond["probe_pos"], p.pretarget_min,
                                    p.pretarget_max, p.posttarget_items)
        cache = self._build_stimuli(setup)

        start = fp.fixation_frames + fp.gap_frames
        n_items = len(stream.letters)
        timeline = FrameTimeline(start + n_items * fp.soa_frames)
        timeline.show("surround", 0).show("field", 0)
        if fp.fixation_frames > 0:
            timeline.show("fixation", 0, fp.fixation_frames)
        timeline.event(0, "FIX_ON")
        stimuli: dict[str, Any] = {k: cache[k] for k in ("surround", "field", "fixation")}
        for i, letter in enumerate(stream.letters):
            key = f"item_{i:02d}"
            colour = "white" if i == stream.target_index else "black"
            stimuli[key] = cache[f"{colour}_{letter}"]
            on = start + i * fp.soa_frames
            timeline.show(key, on, on + fp.letter_frames)
        timeline.event(start, "STREAM_ON")
        timeline.event(start + stream.target_index * fp.soa_frames, "TARGET_ON")
        if stream.probe_index is not None:
            timeline.event(start + stream.probe_index * fp.soa_frames, "PROBE_ON")
        timeline.event(start + (n_items - 1) * fp.soa_frames + fp.letter_frames, "STREAM_OFF")

        intro = condition != self._last_condition
        self._last_condition = condition
        ready = f"{'intro' if intro else 'ready'}_{condition}"
        for k in (ready, "target_prompt", "probe_prompt"):
            stimuli[k] = cache[k]
        base = ["surround", "field"]
        o = self.outcomes
        cap = p.response_timeout.seconds(hz)
        trial_phases: list[Any] = [
            phases.ResponseWindow(
                keys={"space": PhaseAction.ADVANCE}, timeout_s=p.ready_timeout.seconds(hz),
                on_timeout=o["NO_START"], stimulus_keys=[*base, ready], onset_event="READY",
                response_event="START_KEY", rt_record_key="start_rt_ms",
                key_record_key="start_key"),
            phases.FrameSequence(timeline, record_prefix="stream"),
        ]
        if condition == design.EXPERIMENTAL:
            trial_phases.append(phases.ResponseWindow(
                keys={c.lower(): PhaseAction.ADVANCE for c in design.ALPHABET}, timeout_s=cap,
                on_timeout=o["NO_RESPONSE"], stimulus_keys=[*base, "target_prompt"],
                onset_event="TARGET_PROMPT", response_event="TARGET_RESPONSE",
                rt_record_key="target_rt_ms", key_record_key="target_key"))
        present = stream.probe_index is not None
        trial_phases.append(phases.ResponseWindow(
            keys={p.probe_yes_key: o["HIT"] if present else o["FALSE_ALARM"],
                  p.probe_no_key: o["MISS"] if present else o["CORRECT_REJECTION"]},
            timeout_s=cap, on_timeout=o["NO_RESPONSE"], stimulus_keys=[*base, "probe_prompt"],
            onset_event="PROBE_PROMPT", response_event="PROBE_RESPONSE",
            rt_record_key="probe_rt_ms", key_record_key="probe_key"))

        self.current = {"condition": condition, "stream": stream}
        record = {
            "stream": "".join(stream.letters),
            "target_letter": stream.target,
            "n_pretarget": stream.n_pre,
            "probe_lag_ms": (None if cond["probe_pos"] is None
                             else round(cond["probe_pos"] * fp.soa_ms, 3)),
            "intro_shown": intro,
            **fp.as_record(),
        }
        return TrialPlan(phases=trial_phases, stimuli=stimuli, record=record)

    def score(self, record: dict[str, Any]) -> dict[str, Any]:
        """Target and probe scoring, after the trial."""
        out = dict(record)
        stream = str(record.get("stream") or "")
        target_index = int(record.get("n_pretarget") or 0)
        key = record.get("target_key")
        if record.get("condition") == design.EXPERIMENTAL and isinstance(key, str) and key:
            letter = key.upper()
            out["target_report"] = letter
            out["target_correct"] = letter == record.get("target_letter")
            out["target_report_pos"] = (stream.index(letter) - target_index
                                        if letter in stream else None)
        else:
            out["target_report"] = None
            out["target_correct"] = None
            out["target_report_pos"] = None
        probe_key = record.get("probe_key")
        if probe_key in (self.p.probe_yes_key, self.p.probe_no_key):
            said = probe_key == self.p.probe_yes_key
            out["probe_reported"] = said
            out["probe_correct"] = said == bool(record.get("probe_present"))
        else:
            out["probe_reported"] = None
            out["probe_correct"] = None
        return out

    def simulation(self, seed: int):
        from alhazen.modes.simulation import Simulation

        from raymond1992.simulate import SimulatedObserver

        observer = SimulatedObserver(self, seed=seed)
        return Simulation(response=observer, describe={"seed": seed, **observer.describe()})
