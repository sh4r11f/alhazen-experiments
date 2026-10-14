"""Sperling (1960) partial report, Experiments 3 and 4: what a trial is made of.

One trial, as the paper describes it (p. 4, p. 6-8; docs/methods.md is the specification):

1. A dark field with a dim fixation cross. The observer presses SPACE when ready.
2. 0.5 s later the lit card with its letters is exposed for 50 ms (whole frames at the
   measured refresh rate), then the dark field and cross return.
3. A cue calls one row: a high, middle or low tone in the paper; here by default a bar
   beside the row (``cue_mode: visual``), because alhazen 2.16.0 cannot play a tone bound
   to an event. The cue starts at a delay measured from the array's offset (-0.10 s =
   50 ms before onset, 0, 0.15, 0.30, 0.50, 1.0 s).
4. The observer types the cued row's letters into boxes and presses Enter. Scored per
   position: a letter counts only in its correct place (p. 4).

``report: whole`` runs Experiment 1's whole report on the same materials (no cue; type
every symbol, row by row), the immediate-memory baseline the paper compares against.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any, ClassVar, Literal

import numpy as np
from alhazen import Condition, Duration, SubjectParams, Task, TrialPlan, TrialSetup, outcomes
from alhazen.core.events import EventSchema
from alhazen.display.frames import FrameTimeline
from alhazen.errors import ConfigError
from alhazen.paradigms.config import SchedulerConfig
from alhazen.task.duration import TrialTiming, drain, fixed, wait
from pydantic import model_validator

from sperling1960.materials import ALL_CUE_EVENTS, MATERIALS, cue_event, draw_array, material
from sperling1960.phases import PayloadSequence, TypedReport, WaitForKey
from sperling1960.schedule import SeriesSchedule, build_plan
from sperling1960.stimuli import Layout, make_stimuli

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]

# Letters the subject cannot type through alhazen 2.16.0: the experimenter's session keys
# (core/commands.py DEFAULT_KEYMAP: p pause, c calibrate, r manual reward, h hold stage)
# are read from the same keyboard before the subject's keys and never reach the task.
EXPERIMENTER_KEYS = frozenset("CHPR")
VOWELS = frozenset("AEIOU")

Color = tuple[float, float, float]


def tone_class() -> Any | None:
    """``alhazen.Tone`` when this alhazen has event-bound tones, else None."""
    try:
        from alhazen import Tone  # type: ignore[attr-defined]
    except ImportError:
        return None
    return Tone


def tone_missing_message() -> str:
    import alhazen

    return (
        f"cue_mode: tone needs alhazen.Tone (a tone played when a task event is emitted), "
        f"and the alhazen installed here ({alhazen.__version__}) does not have it. Run with "
        f"cue_mode: visual (the bar beside the cued row), or move this folder to an alhazen "
        f"release that has Tone: change the tag in pyproject.toml [tool.uv.sources] and "
        f"run `uv lock`."
    )


class PartialReportTaskParams(SubjectParams):
    """A session's parameters. Durations resolve to whole frames at the measured rate."""

    report: Literal["partial", "whole"] = "partial"
    materials: list[str] = ["4/4/4-LN"]
    cue_mode: Literal["visual", "tone"] = "visual"
    cue_delays_s: list[float] = [-0.10, 0.0, 0.15, 0.30, 0.50, 1.0]
    first_series: Literal["ascending", "descending"] = "ascending"
    n_series: int = 4
    samples_per_block: int = 2
    # n_per_condition: TEST trials per delay block (samples come on top). A SchedulerConfig
    # so alhazen's test and simulate modes shorten a rehearsal the way they do any design.
    paradigm: SchedulerConfig = SchedulerConfig(kind="sequence", n_per_condition=6)

    exposure: Duration = Duration(ms=50)
    start_delay: Duration = Duration(ms=500)
    start_key: str = "space"
    start_timeout: Duration = Duration(ms=60000)
    cue_duration: Duration = Duration(ms=500)
    tone_high_hz: float = 2500.0
    tone_mid_hz: float = 650.0
    tone_low_hz: float = 250.0
    tone_volume: float = 1.0
    report_timeout: Duration = Duration(ms=60000)
    iti: Duration = Duration(ms=0)

    consonants: str = "BDFGJKLMNQSTVWXYZ"
    digits: str = "0123456789"

    letter_height_dva: float = 1.17
    letter_pitch_dva: float = 1.70
    row_pitch_two_rows_dva: float = 3.16
    row_pitch_three_rows_dva: float = 1.70
    font: str = "Arial"
    card_width_dva: float = 20.6
    card_height_dva: float = 13.0
    field_color: Color = (-1.0, -1.0, -1.0)
    fixation_color: Color = (-0.7, -0.7, -0.7)
    card_color: Color = (1.0, 1.0, 1.0)
    letter_color: Color = (-1.0, -1.0, -1.0)
    cue_color: Color = (0.5, 0.5, 0.5)
    response_color: Color = (0.0, 0.0, 0.0)
    fix_size_dva: float = 0.6
    fix_line_dva: float = 0.08
    cue_bar_length_dva: float = 1.17
    cue_bar_width_dva: float = 0.2
    cue_bar_gap_dva: float = 0.6
    response_y_dva: float = -9.0
    response_box_dva: float = 1.6

    @model_validator(mode="after")
    def _check(self) -> PartialReportTaskParams:
        if not self.materials:
            raise ValueError("materials: name at least one")
        for name in self.materials:
            material(name)  # raises with the list of known materials
        if self.report == "partial":
            if not self.cue_delays_s:
                raise ValueError("a partial report needs cue_delays_s")
            if len(set(self.cue_delays_s)) != len(self.cue_delays_s):
                raise ValueError("cue_delays_s lists a delay twice")
        elif self.cue_delays_s:
            raise ValueError("report: whole has no cue; set cue_delays_s: []")
        if self.n_series < 1 or self.samples_per_block < 0:
            raise ValueError("n_series >= 1 and samples_per_block >= 0")
        cfg = self.paradigm
        if cfg.kind != "sequence" or cfg.blocks or cfg.staircase or cfg.quest:
            raise ValueError(
                "paradigm: this task serves Sperling's series of delay blocks itself; give "
                "only kind: sequence, n_per_condition (test trials per block) and shuffle"
            )
        letters = self.consonants.upper()
        if (letters != self.consonants or not letters.isalpha()
                or len(set(letters)) != len(letters)):
            raise ValueError("consonants: distinct upper-case letters")
        if VOWELS & set(letters):
            raise ValueError("consonants: no vowels (the paper used consonants only, p. 3)")
        blocked = EXPERIMENTER_KEYS & set(letters)
        if blocked:
            raise ValueError(
                f"consonants: {''.join(sorted(blocked))} cannot be typed by the subject in "
                f"alhazen 2.16.0, because those keys are the experimenter's session commands "
                f"(pause, calibrate, reward, hold); leave them out"
            )
        if not self.digits.isdigit() or len(set(self.digits)) != len(self.digits):
            raise ValueError("digits: distinct digits")
        if self.cue_mode == "tone":
            if tone_class() is None:
                raise ValueError(tone_missing_message())
            if self.cue_duration.ms is None:
                raise ValueError("cue_mode: tone needs cue_duration in ms (the tone's length)")
        return self


def tone_map(p: PartialReportTaskParams) -> dict[str, Any]:
    """Event name -> the tone it plays (paper p. 6-7: 2500, 650, 250 cps, about 0.5 s)."""
    tone = tone_class()
    if tone is None:
        raise ConfigError(tone_missing_message())
    assert p.cue_duration.ms is not None
    seconds = p.cue_duration.ms / 1000.0
    return {
        "CUE_HIGH": tone(p.tone_high_hz, seconds, p.tone_volume),
        "CUE_MID": tone(p.tone_mid_hz, seconds, p.tone_volume),
        "CUE_LOW": tone(p.tone_low_hz, seconds, p.tone_volume),
    }


def signed_frames(seconds: float, hz: float) -> int:
    """A signed delay in whole frames, rounded the way alhazen rounds durations."""
    n = Duration(ms=abs(seconds) * 1000.0).n_frames(hz)
    return -n if seconds < 0 else n


def score_report(response: str, target: str) -> list[bool]:
    """Per position: the right symbol in the right place (paper p. 4)."""
    return [i < len(response) and response[i] == ch for i, ch in enumerate(target)]


class PartialReportTask(Task):
    name = "partial-report"
    events = EventSchema(("FIX_ON", "ARRAY_ON", "ARRAY_OFF", *ALL_CUE_EVENTS, "REPORT_ON",
                          "RESPONSE_BOXES_ON", "RESPONSE"))
    outcomes = outcomes(
        REPORTED=dict(completed=True),
        NO_RESPONSE=dict(completed=False),
        NO_START=dict(completed=False),
    )
    params_model = PartialReportTaskParams
    # Event name -> Tone, for an alhazen with event-bound tones. Empty on the class: a
    # visual-cue session plays nothing. A tone-cue session binds the map on the instance
    # (see __init__), the way Task binds `reward` per instance.
    tones: ClassVar[Mapping[str, Any]] = {}

    def __init__(self, params: PartialReportTaskParams) -> None:
        super().__init__(params)
        if params.cue_mode == "tone":
            self.tones = tone_map(params)  # type: ignore[misc]

    @classmethod
    def default_params(cls) -> Path:
        return PROJECT / "configs" / "task.yaml"

    def instructions(self) -> str | None:
        p: PartialReportTaskParams = self.params  # type: ignore[assignment]
        name = ("instructions-whole.md" if p.report == "whole"
                else "instructions-tone.md" if p.cue_mode == "tone" else "instructions.md")
        return (PROJECT / name).read_text(encoding="utf-8")

    # -- scheduling ------------------------------------------------------------------

    def make_source(self, params: Any, rng: np.random.Generator) -> SeriesSchedule:
        p: PartialReportTaskParams = params
        return SeriesSchedule(build_plan(
            report=p.report, materials=p.materials, delays=p.cue_delays_s,
            n_series=p.n_series, first_series=p.first_series,
            samples_per_block=p.samples_per_block,
            test_per_block=p.paradigm.n_per_condition, rng=rng, shuffle=p.paradigm.shuffle))

    def duration_schedule(self, params: Any, rng: np.random.Generator) -> Any:
        return drain(self.make_source(params, rng))

    def trial_timing(self, condition: Condition, refresh_rate_hz: float) -> TrialTiming:
        p: PartialReportTaskParams = self.params  # type: ignore[assignment]
        hz = refresh_rate_hz
        delay = condition.params.get("delay_s")
        exposure = p.exposure.n_frames(hz) / hz
        after = max(0.0, signed_frames(delay, hz) / hz) if delay is not None else 0.0
        return TrialTiming([
            wait("observer starts the trial", p.start_timeout.seconds(hz), basis="SPACE"),
            fixed("start delay", p.start_delay.n_frames(hz) / hz, basis="start_delay"),
            fixed("exposure", exposure, basis="exposure"),
            fixed("cue delay", after + 1 / hz, basis="cue_delays_s"),
            wait("typed report", p.report_timeout.seconds(hz), basis="report_timeout"),
        ])

    # -- one trial -------------------------------------------------------------------

    def layout(self, n_rows: int, n_cols: int) -> Layout:
        p: PartialReportTaskParams = self.params  # type: ignore[assignment]
        return Layout(
            letter_height_dva=p.letter_height_dva, letter_pitch_dva=p.letter_pitch_dva,
            row_pitch_dva=p.row_pitch_two_rows_dva if n_rows == 2 else p.row_pitch_three_rows_dva,
            n_rows=n_rows, n_cols=n_cols, card_width_dva=p.card_width_dva,
            card_height_dva=p.card_height_dva, cue_bar_length_dva=p.cue_bar_length_dva,
            cue_bar_gap_dva=p.cue_bar_gap_dva, response_y_dva=p.response_y_dva,
            response_box_dva=p.response_box_dva)

    def build_trial(self, setup: TrialSetup) -> TrialPlan:
        p: PartialReportTaskParams = self.params  # type: ignore[assignment]
        hz = setup.refresh_rate_hz
        cond = setup.condition.params
        m = MATERIALS[cond["material"]]
        partial = cond["report"] == "partial"
        row = cond["cued_row"] if partial else None
        layout = self.layout(m.n_rows, m.n_cols)
        half_w, half_h = layout.extent_dva()
        screen_w = setup.screen.px2deg(setup.screen.width_px) / 2
        screen_h = setup.screen.px2deg(setup.screen.height_px) / 2
        if half_w > screen_w or half_h > screen_h:
            raise ConfigError(
                f"the card and response boxes need {2 * half_w:.1f} x {2 * half_h:.1f} dva and "
                f"this screen is {2 * screen_w:.1f} x {2 * screen_h:.1f} dva at its viewing "
                f"distance; check the rig file's geometry, or shrink card_*_dva / response_y_dva"
            )
        rows = draw_array(m, p.consonants, p.digits, setup.rng)

        n_exp = p.exposure.n_frames(hz)
        n_cue = p.cue_duration.n_frames(hz)
        on = p.start_delay.n_frames(hz)
        off = on + n_exp
        cue = off + signed_frames(cond["delay_s"], hz) if partial else None
        if n_exp < 1:
            raise ConfigError(f"exposure {p.exposure} is under one frame at {hz:.1f} Hz")
        if cue is not None and cue < 0:
            raise ConfigError(
                f"a cue {cond['delay_s']} s from the array's offset starts before the trial "
                f"does (start_delay {p.start_delay}); lengthen start_delay")
        last = max(off, cue) if cue is not None else off
        end = last + 1  # the sequence shows the offset frame and the cue's first frame
        cue_end = (cue if cue is not None else off) + n_cue

        timeline = FrameTimeline(end)
        timeline.show("field", 0)
        timeline.show("fixation", 0, on)
        timeline.show("card", on, off)
        timeline.show("fixation", off)
        timeline.event(on, "ARRAY_ON").event(off, "ARRAY_OFF")
        visual_cue = partial and p.cue_mode == "visual"
        cue_name = cue_event(m, row) if partial else None
        if cue is not None and cue_name is not None:
            timeline.event(cue, cue_name)
            if visual_cue:
                stop = min(cue_end, end)
                if cue < on:
                    timeline.show("cue_light", cue, min(on, stop))
                if cue < off and stop > on:
                    timeline.show("cue_dark", max(cue, on), min(off, stop))
                if stop > off and max(cue, off) < stop:
                    timeline.show("cue_light", max(cue, off), stop)

        n_positions = m.n_cols if partial else m.n_symbols
        allowed = p.consonants + (p.digits if m.letters_and_numbers else "")
        target = rows[row] if partial else "".join(rows)
        carry: list[tuple[str, int | None]] = [("field", None), ("fixation", None)]
        if visual_cue and cue_end > end:
            carry.append(("cue_light", cue_end - end))
        stimuli = make_stimuli(
            setup.display, setup.screen, layout, rows, row, n_positions,
            colors={"field": p.field_color, "fixation": p.fixation_color, "card": p.card_color,
                    "letters": p.letter_color, "cue": p.cue_color,
                    "response": p.response_color},
            font=p.font, fix_size_dva=p.fix_size_dva, fix_line_dva=p.fix_line_dva,
            cue_bar_width_dva=p.cue_bar_width_dva)
        outcome = self.outcomes
        phases = [
            WaitForKey(p.start_key, ["field", "fixation"], p.start_timeout.seconds(hz),
                       on_timeout=outcome["NO_START"], onset_event="FIX_ON"),
            PayloadSequence(
                timeline,
                payloads={
                    "ARRAY_ON": {"material": m.name, "rows": list(rows)},
                    **({cue_name: {"row": row, "delay_s": cond["delay_s"]}}
                       if cue_name is not None else {}),
                },
                record_prefix="presentation",
            ),
            TypedReport(
                n_positions, allowed, p.report_timeout.seconds(hz),
                on_commit=outcome["REPORTED"], on_timeout=outcome["NO_RESPONSE"],
                carry=carry, boxes_from_frame=max(0, cue_end - end),
                onset_payload={"report": cond["report"], "positions": n_positions,
                               "row": row, "delay_s": cond["delay_s"]},
            ),
        ]
        record = {
            "rows": "/".join(rows),
            "target": target,
            "n_rows": m.n_rows,
            "n_cols": m.n_cols,
            "cue_mode": p.cue_mode if partial else "none",
            "cue_event": cue_name,
            "refresh_hz": hz,
            "exposure_frames": n_exp,
            "exposure_ms_planned": n_exp * 1000.0 / hz,
            "cue_offset_frames": (cue - off) if cue is not None else None,
            "cue_delay_ms_planned": (cue - off) * 1000.0 / hz if cue is not None else None,
            "cue_frames": n_cue if partial else None,
        }
        return TrialPlan(phases=phases, stimuli=stimuli, record=record)

    def score(self, record: dict[str, Any]) -> dict[str, Any]:
        """Correct-in-position counts, and the flip-measured exposure and cue delay."""
        out = dict(record)
        t_on, t_off = record.get("t_array_on"), record.get("t_array_off")
        if t_on is not None and t_off is not None:
            measured = (t_off - t_on) * 1000.0
            out["exposure_ms_measured"] = measured
            # A dropped or late flip while the card is up lengthens the exposure. Frame QA
            # judges a trial by its fraction of dropped frames, which one late flip in 50 ms
            # never reaches, so the exposure is checked on its own: within half a frame of
            # the planned whole frames, from the flip stamps. The analysis excludes the rest.
            half_frame_ms = 500.0 / float(record.get("refresh_hz") or 60.0)
            planned = record.get("exposure_ms_planned")
            if planned is not None:
                out["exposure_ok"] = abs(measured - planned) < half_frame_ms
        cue_name = record.get("cue_event")
        t_cue = record.get(f"t_{cue_name.lower()}") if cue_name else None
        if t_cue is not None and t_off is not None:
            out["cue_delay_ms_measured"] = (t_cue - t_off) * 1000.0
        response, target = record.get("response"), record.get("target")
        if not isinstance(response, str) or not isinstance(target, str):
            return out
        mask = score_report(response, target)
        n_correct = sum(mask)
        out["correct_mask"] = "".join("1" if ok else "0" for ok in mask)
        out["n_correct"] = n_correct
        out["prop_correct"] = n_correct / len(target)
        if record.get("report") == "partial":
            n_rows = int(record["n_rows"])
            # The paper's estimate: the partial report is a random sample of what was
            # available, so letters available = correct per report x number of rows (p. 7).
            out["letters_available"] = n_correct * n_rows
            others = [r for i, r in enumerate(str(record["rows"]).split("/"))
                      if i != record.get("cued_row")]
            out["other_row_max_correct"] = max((sum(score_report(response, r)) for r in others),
                                               default=0)
        else:
            out["letters_available"] = n_correct
        return out

    def simulation(self, seed: int):
        from alhazen.modes.simulation import Simulation

        from sperling1960.simulate import SimulatedObserver

        p: PartialReportTaskParams = self.params  # type: ignore[assignment]
        observer = SimulatedObserver(seed=seed, consonants=p.consonants, digits=p.digits,
                                     start_key=p.start_key)
        return Simulation(response=observer,
                          describe={"seed": seed, "source": "sperling1960.simulate",
                                    **observer.describe()})
