"""Flicker change blindness (Rensink, O'Regan & Clark, 1997): what a trial is made of.

One trial, as Fig. 1 of the paper (p. 369) lays it out, then the report that replaces the
paper's spoken description:

1. CUE_ON    3000 ms gray field with a white rectangle (a word in it when cues are used)
2. GRAY_ON   1000 ms gray field
3. FLICKER   A, A, A', A', ... each image 240 ms, a gray blank of 80 ms after each, until
             the subject presses SPACE or 60 s have passed (outcome NO_DETECTION)
4. WHERE     image A with numbered boxes; the subject presses the box the change was in
5. WHAT      the kind of change: P appeared/disappeared, C colour, L location

docs/methods.md says which of these numbers are the paper's and which are assumed.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

import numpy as np
from alhazen import Condition, Duration, SubjectParams, Task, TrialPlan, TrialSetup, outcomes
from alhazen.config.models import Model
from alhazen.core.events import EventSchema
from alhazen.core.trial import TrialContext
from alhazen.paradigms.config import SchedulerConfig
from alhazen.task import phases
from alhazen.task.duration import TrialTiming, fixed, wait
from pydantic import model_validator

from rensink1997 import scenes
from rensink1997.phases import FlickerPhase, KeyChoice
from rensink1997.stimuli import make_image, make_rect, make_text

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
TYPE_LABELS = {"presence": "appeared / disappeared", "color": "changed colour",
               "location": "moved"}


class FlickerTiming(Model):
    """The flicker cycle: each listed image for ``image``, a ``blank`` after each one."""

    image: Duration = Duration(ms=240)
    blank: Duration = Duration(ms=80)
    pattern: list[Literal["A", "B"]] = ["A", "A", "B", "B"]

    @model_validator(mode="after")
    def _alternates(self) -> FlickerTiming:
        if "A" not in self.pattern or "B" not in self.pattern or self.pattern[0] != "A":
            raise ValueError("the pattern starts with A and contains both A and B")
        return self


class SceneSet(Model):
    """Which scene pairs a session shows, each once."""

    photos: bool = True
    photo_ids: list[str] | None = None  # None: every shipped photo pair
    procedural_per_cell: int = 6  # per change type x interest cell
    procedural_seed: int = 1997


class LocationProbe(Model):
    n_choices: int = 4
    min_side_dva: float = 3.0
    max_side_dva: float = 7.0
    keys: list[str] = ["1", "2", "3", "4"]
    timeout: Duration = Duration(ms=20000)

    @model_validator(mode="after")
    def _enough_keys(self) -> LocationProbe:
        if not 2 <= self.n_choices <= len(self.keys):
            raise ValueError("n_choices must be between 2 and the number of keys")
        if not 0 < self.min_side_dva <= self.max_side_dva:
            raise ValueError("0 < min_side_dva <= max_side_dva")
        return self


class TypeProbe(Model):
    keys: dict[str, Literal["presence", "color", "location"]] = {
        "p": "presence", "c": "color", "l": "location"}
    timeout: Duration = Duration(ms=20000)

    @model_validator(mode="after")
    def _all_types(self) -> TypeProbe:
        if sorted(self.keys.values()) != ["color", "location", "presence"]:
            raise ValueError("type keys must map one key to each of presence, color, location")
        return self


class FlickerChangeDetectionTaskParams(SubjectParams):
    """A session's parameters. Durations resolve to whole frames at the measured rate."""

    image_width_dva: float = 27.0
    image_height_dva: float = 18.0
    background_gray: float = 0.0
    cue_field: Duration = Duration(ms=3000)
    cue_box_width_dva: float = 8.0
    cue_box_height_dva: float = 2.5
    cue_text_height_dva: float = 1.0
    cue: Literal["none", "valid", "valid50"] = "none"
    gray_field: Duration = Duration(ms=1000)
    flicker: FlickerTiming = FlickerTiming()
    max_flicker: Duration = Duration(ms=60000)
    detect_key: str = "space"
    location_probe: LocationProbe = LocationProbe()
    type_probe: TypeProbe = TypeProbe()
    probe_text_height_dva: float = 0.7
    scenes: SceneSet = SceneSet()
    change_area_dva2: dict[str, float] = {"central": 18.0, "marginal": 22.0}
    location_shift_dva: float = 3.0
    iti: Duration = Duration(ms=500)
    paradigm: SchedulerConfig = SchedulerConfig(n_per_condition=1)

    @model_validator(mode="after")
    def _keys_do_not_clash(self) -> FlickerChangeDetectionTaskParams:
        probe = set(self.location_probe.keys[: self.location_probe.n_choices])
        types = set(self.type_probe.keys)
        if probe & types or self.detect_key in probe | types:
            raise ValueError("the detection, location and type keys must all differ")
        if set(self.change_area_dva2) != {"central", "marginal"}:
            raise ValueError("change_area_dva2 needs central and marginal")
        return self


def scene_ids(p: FlickerChangeDetectionTaskParams) -> list[str]:
    ids: list[str] = []
    if p.scenes.photos:
        chosen = p.scenes.photo_ids if p.scenes.photo_ids is not None else scenes.photo_ids()
        ids += [f"photo/{i}" for i in chosen]
    ids += scenes.procedural_ids(p.scenes.procedural_per_cell, p.scenes.procedural_seed)
    return ids


def cue_plan(ids: list[str], cue: str) -> dict[str, str]:
    """Scene id -> "none" | "valid" | "invalid". With valid50, valid and invalid alternate
    within each change type x source cell, in a fixed order (balanced, not random)."""
    if cue == "none":
        return {i: "none" for i in ids}
    if cue == "valid":
        return {i: "valid" for i in ids}
    out, counts = {}, {}
    for i in ids:
        kind = i.split("/")[0]
        ct = i.split("/")[2] if kind == "proc" else scenes.photo_table()[i.split("/")[1]][
            "change_type"]
        k = counts.get((kind, ct), 0)
        out[i] = "valid" if k % 2 == 0 else "invalid"
        counts[(kind, ct)] = k + 1
    return out


class FlickerChangeDetectionTask(Task):
    name = "flicker-change-detection"
    events = EventSchema(("CUE_ON", "GRAY_ON", "FLICKER_ON", "IMAGE_ON", "DETECTED",
                          "LOCATION_PROBE", "LOCATION_REPORT", "TYPE_PROBE", "TYPE_REPORT"))
    outcomes = outcomes(
        CORRECT=dict(completed=True, success=True),
        MISIDENTIFIED=dict(completed=True, success=False),
        NO_DETECTION=dict(completed=True, success=False),
        NO_REPORT=dict(completed=True, success=False),
    )
    params_model = FlickerChangeDetectionTaskParams

    @classmethod
    def default_params(cls) -> Path:
        return PROJECT / "configs" / "task.yaml"

    def instructions(self) -> str | None:
        return (PROJECT / "instructions.md").read_text(encoding="utf-8")

    def conditions(self, rng: np.random.Generator) -> list[Condition]:
        p: FlickerChangeDetectionTaskParams = self.params  # type: ignore[assignment]
        ids = scene_ids(p)
        cues = cue_plan(ids, p.cue)
        return [Condition({"scene": i, "cue": cues[i]}) for i in ids]

    def _cycle(self, hz: float) -> tuple[list[tuple[str | None, int]], int, int]:
        p: FlickerChangeDetectionTaskParams = self.params  # type: ignore[assignment]
        img, blank = p.flicker.image.n_frames(hz), p.flicker.blank.n_frames(hz)
        cycle: list[tuple[str | None, int]] = []
        for name in p.flicker.pattern:
            cycle += [("image_a" if name == "A" else "image_b", img), (None, blank)]
        return cycle, img, blank

    def build_trial(self, setup: TrialSetup) -> TrialPlan:
        p: FlickerChangeDetectionTaskParams = self.params  # type: ignore[assignment]
        hz = setup.refresh_rate_hz
        scene_id, cue = setup.condition.params["scene"], setup.condition.params["cue"]
        pair = scenes.load(scene_id, p.change_area_dva2, p.location_shift_dva)
        screen, display = setup.screen, setup.display
        iw, ih = screen.deg2px(p.image_width_dva), screen.deg2px(p.image_height_dva)
        gray = (p.background_gray,) * 3
        cycle, img_frames, blank_frames = self._cycle(hz)
        pattern = p.flicker.pattern
        # Changes per cycle (A A B B has two), counting the wrap from the last image to the first.
        switches = sum(1 for a, b in zip(pattern, pattern[1:] + pattern[:1], strict=True) if a != b)
        alternation_s = len(p.flicker.pattern) * (img_frames + blank_frames) / hz / switches

        # The location probe: same-size boxes on image A, one around the change.
        aspect = p.image_width_dva / p.image_height_dva
        boxes, correct_box = scenes.probe_boxes(
            pair, p.location_probe.n_choices,
            (p.location_probe.min_side_dva / p.image_width_dva,
             p.location_probe.max_side_dva / p.image_width_dva),
            aspect, setup.rng)
        box_keys = p.location_probe.keys[: len(boxes)]
        type_key = {v: k for k, v in p.type_probe.keys.items()}[pair.change_type]

        def to_px(fx: float, fy: float) -> tuple[float, float]:
            return ((fx - 0.5) * iw, (0.5 - fy) * ih)

        stimuli = {
            "background": make_rect(display, (screen.width_px * 1.2, screen.height_px * 1.2),
                                    fill=gray, name="background"),
            "cue_box": make_rect(display, (screen.deg2px(p.cue_box_width_dva),
                                           screen.deg2px(p.cue_box_height_dva)),
                                 fill=(1.0, 1.0, 1.0), name="cue_box"),
            "image_a": make_image(display, pair.image_a, (iw, ih), name="image_a"),
            "image_b": make_image(display, pair.image_b, (iw, ih), name="image_b"),
            "type_prompt": make_text(
                display, "What kind of change was it?\n\n" + "\n".join(
                    f"{k.upper()}   {TYPE_LABELS[v]}" for k, v in p.type_probe.keys.items()),
                screen.deg2px(p.probe_text_height_dva) * 1.3, wrap_px=screen.deg2px(20),
                name="type_prompt"),
            "where_prompt": make_text(
                display, "Where was the change? Press the number of its box.",
                screen.deg2px(p.probe_text_height_dva), pos=(0.0, -ih / 2 - screen.deg2px(1.2)),
                name="where_prompt"),
        }
        cue_word = {"valid": pair.cue_valid, "invalid": pair.cue_invalid}.get(cue, "")
        cue_keys = ["background", "cue_box"]
        if cue_word:
            stimuli["cue_text"] = make_text(display, cue_word,
                                            screen.deg2px(p.cue_text_height_dva),
                                            color=(-1.0, -1.0, -1.0), name="cue_text")
            cue_keys.append("cue_text")
        where_keys = ["background", "image_a", "where_prompt"]
        line_px = max(2.0, screen.deg2px(0.08))
        for i, (b, key) in enumerate(zip(boxes, box_keys, strict=False)):
            cx, cy = to_px((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
            w, h = (b[2] - b[0]) * iw, (b[3] - b[1]) * ih
            stimuli[f"box_{i}"] = make_rect(display, (w, h), (cx, cy), line=(1.0, 1.0, -1.0),
                                            line_px=line_px, name=f"box_{i}")
            stimuli[f"box_label_{i}"] = make_text(
                display, key, screen.deg2px(p.probe_text_height_dva) * 1.4,
                pos=(cx - w / 2 + screen.deg2px(0.6), cy + h / 2 - screen.deg2px(0.6)),
                color=(1.0, 1.0, -1.0), name=f"box_label_{i}")
            where_keys += [f"box_{i}", f"box_label_{i}"]

        out = self.outcomes

        def score(ctx: TrialContext) -> object:
            loc_ok = ctx.record.get("location_report") == str(correct_box)
            type_ok = ctx.record.get("type_report") == pair.change_type
            ctx.record["location_correct"] = bool(loc_ok)
            ctx.record["type_correct"] = bool(type_ok)
            return out["CORRECT"] if loc_ok and type_ok else out["MISIDENTIFIED"]

        trial_phases = [
            phases.Feedback(cue_keys, p.cue_field.seconds(hz), onset_event="CUE_ON"),
            phases.Feedback(["background"], p.gray_field.seconds(hz), onset_event="GRAY_ON"),
            FlickerPhase(cycle, {"image_a": "A", "image_b": "B"}, p.detect_key,
                         p.max_flicker.seconds(hz), on_timeout=out["NO_DETECTION"],
                         background_keys=["background"],
                         onset_payload={"interest": pair.interest, "cue": cue,
                                        "blank_frames": blank_frames,
                                        "alternation_frames": round(alternation_s * hz, 3)},
                         alternation_s=alternation_s),
            KeyChoice({k: str(i) for i, k in enumerate(box_keys)}, "location_report",
                      where_keys, p.location_probe.timeout.seconds(hz), out["NO_REPORT"],
                      onset_event="LOCATION_PROBE",
                      onset_payload={"answer": box_keys[correct_box], "keys": box_keys},
                      response_event="LOCATION_REPORT"),
            KeyChoice(dict(p.type_probe.keys), "type_report", ["background", "type_prompt"],
                      p.type_probe.timeout.seconds(hz), out["NO_REPORT"], then=score,
                      onset_event="TYPE_PROBE",
                      onset_payload={"answer": type_key, "keys": list(p.type_probe.keys)},
                      response_event="TYPE_REPORT"),
        ]
        record = {
            "scene": scene_id, "source": pair.source, "change_type": pair.change_type,
            "interest": pair.interest, "changed_object": pair.object, "cue": cue,
            "cue_word": cue_word,
            "change_area_dva2": round(pair.area_dva2(p.image_width_dva, p.image_height_dva), 2),
            "change_cx": pair.centroid[0], "change_cy": pair.centroid[1],
            "image_frames": img_frames, "blank_frames": blank_frames,
            "alternation_s": round(alternation_s, 5),
            "probe_boxes": json.dumps([[round(v, 4) for v in b] for b in boxes]),
            "probe_n_choices": len(boxes), "probe_correct": str(correct_box),
            "probe_correct_key": box_keys[correct_box], "type_correct_key": type_key,
        }
        return TrialPlan(phases=trial_phases, stimuli=stimuli, record=record)

    def trial_timing(self, condition: Condition, refresh_rate_hz: float) -> TrialTiming | None:
        p: FlickerChangeDetectionTaskParams = self.params  # type: ignore[assignment]
        hz = refresh_rate_hz
        return TrialTiming([
            fixed("cue field", p.cue_field.seconds(hz), "paper p. 369, Fig. 1"),
            fixed("gray field", p.gray_field.seconds(hz), "paper p. 369, Fig. 1"),
            wait("flicker until SPACE", p.max_flicker.seconds(hz), 0.0, "paper: up to 60 s"),
            wait("where (box keys)", p.location_probe.timeout.seconds(hz), 0.0, "ASSUMED"),
            wait("what kind (P/C/L)", p.type_probe.timeout.seconds(hz), 0.0, "ASSUMED"),
        ])

    def simulation(self, seed: int):
        from alhazen.modes.simulation import Simulation

        from rensink1997.simulate import SimulatedObserver

        return Simulation(response=SimulatedObserver(seed=seed),
                          describe={"seed": seed, "source": "rensink1997.simulate",
                                    "model": "alternations to detection ~ lognormal around the "
                                             "paper's means (7.3 central, 17.1 marginal, 1.4 "
                                             "without blanks); reports 97% correct"})
