"""Depth-cued change blindness: a flicker task whose cue names a depth plane.

Rensink, O'Regan & Clark's (1997) flicker paradigm, with Experiment 3's verbal cue made
into a cue to depth. Each scene is a far surface seen behind a layer of near objects,
drawn on an ordinary 2-D screen with monocular depth cues only (scenes.py). Before the
flicker a word says where in depth to attend, NEAR or FAR; the cue is valid on most
trials, so the measure is what a depth cue buys: alternations to find a change on the
cued plane against the uncued plane.

One trial:

1. CUE_ON    a white rectangle on gray with the cue word (NEAR, FAR, or the neutral word),
             typeset in the bundled Atkinson Hyperlegible Bold
2. GRAY_ON   a plain gray field with a central fixation target (Thaler et al.'s 2013 "ABC"),
             so every search starts from the centre of the picture
3. FLICKER   A, A, A', A', ... each image ``flicker.image``, a gray blank after each, until
             the subject presses SPACE or ``max_flicker`` has passed (NO_DETECTION)
4. WHERE     image A with four numbered boxes (two on near objects, two on far ones);
             the subject presses the box the change was in
5. WHAT      the kind of change: appeared/disappeared, colour, moved

docs/methods.md lists which values come from Rensink et al., which are this design's
choices and which are assumed.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

import numpy as np
from alhazen import Condition, Duration, SubjectParams, Task, TrialPlan, TrialSetup, outcomes
from alhazen.config.models import Model
from alhazen.core.commands import DEFAULT_KEYMAP
from alhazen.core.events import EventSchema
from alhazen.core.trial import TrialContext
from alhazen.paradigms.config import SchedulerConfig
from alhazen.task import phases
from alhazen.task.duration import TrialTiming, fixed, wait
from pydantic import model_validator

from depthcb import photos, scenes
from depthcb.phases import FlickerPhase, KeyChoice
from depthcb.stimuli import make_fixation_abc, make_image, make_rect, make_text_image, render_text

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
TYPE_LABELS = {"presence": "appeared / disappeared", "color": "changed colour",
               "location": "moved"}
KEY_NAMES = {"left": "LEFT arrow", "down": "DOWN arrow", "right": "RIGHT arrow", "up": "UP arrow"}
# alhazen's experimenter keys are read before the subject's; a response key among them
# would never reach the task.
COMMAND_KEYS = frozenset(name.split("+")[-1] for name in DEFAULT_KEYMAP)
CUES = ("valid", "invalid", "neutral", "none")


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


class DepthCues(Model):
    """Which monocular depth cues the scenes carry (each can be switched off)."""

    relative_size: bool = True
    occlusion: bool = True
    cast_shadows: bool = True
    blur: bool = True
    aerial: bool = True
    texture: bool = True


class SceneParams(Model):
    """Where the scenes come from: drawn two-plane scenes (scenes.py) or photographs
    (photos.py). The drawing parameters below apply to the drawn scenes only."""

    source: Literal["procedural", "photo"] = "procedural"
    photo_set: Literal["main", "practice"] = "main"
    seed: int = 2026
    n_near: int = 8
    n_far: int = 8
    n_occluded: int = 3
    near_size_dva: float = 2.4
    far_size_dva: float = 1.5
    target_eccentricity_dva: tuple[float, float] = (3.0, 11.0)
    location_shift_dva: float = 2.0
    far_blur_dva: float = 0.06
    aerial_mix: float = 0.45
    shadow_offset_dva: float = 0.35
    shadow_opacity: float = 0.40
    render_px_per_dva: float = 40.0
    cues: DepthCues = DepthCues()

    @model_validator(mode="after")
    def _counts(self) -> SceneParams:
        if (self.n_near, self.n_far) != (8, 8):
            raise ValueError("the layout puts 2 near and 2 far objects in each quadrant: "
                             "n_near and n_far are 8")
        if not 0 < self.far_size_dva <= self.near_size_dva:
            raise ValueError("0 < far_size_dva <= near_size_dva")
        lo, hi = self.target_eccentricity_dva
        if not 0 <= lo < hi:
            raise ValueError("target_eccentricity_dva is (low, high), low < high")
        return self


class CueCounts(Model):
    """Trials per depth plane x change type cell, by cue."""

    valid: int = 12
    invalid: int = 4
    neutral: int = 0
    none: int = 0

    @model_validator(mode="after")
    def _some(self) -> CueCounts:
        if min(self.valid, self.invalid, self.neutral, self.none) < 0 or self.total == 0:
            raise ValueError("cue counts are >= 0 and not all zero")
        return self

    @property
    def total(self) -> int:
        return self.valid + self.invalid + self.neutral + self.none


class Fixation(Model):
    """The fixation target: shown on the gray field before the flicker (and optionally
    over the flicker). Sizes are Thaler et al.'s (2013) ABC target."""

    show_on_gray: bool = True
    show_during_flicker: bool = False
    outer_dva: float = 0.6
    inner_dva: float = 0.2
    color: tuple[float, float, float] = (-1.0, -1.0, -1.0)

    @model_validator(mode="after")
    def _sizes(self) -> Fixation:
        if not 0 < self.inner_dva < self.outer_dva:
            raise ValueError("0 < inner_dva < outer_dva")
        return self


class CueStyle(Model):
    """How the cue word is typeset (bundled Atkinson Hyperlegible)."""

    weight: Literal["bold", "regular"] = "bold"
    tracking_em: float = 0.12
    ink: tuple[float, float, float] = (-0.86, -0.86, -0.86)
    card: tuple[float, float, float] = (1.0, 1.0, 1.0)


class CueWords(Model):
    near: str = "NEAR"
    far: str = "FAR"
    neutral: str = "NEAR OR FAR"


class LocationProbe(Model):
    n_choices: int = 4
    box_side_dva: float = 3.6
    keys: list[str] = ["1", "2", "3", "4"]
    timeout: Duration = Duration(ms=20000)

    @model_validator(mode="after")
    def _enough_keys(self) -> LocationProbe:
        if not 2 <= self.n_choices <= len(self.keys) or self.n_choices % 2:
            raise ValueError("n_choices is even (half the boxes per plane) and <= len(keys)")
        return self


class TypeProbe(Model):
    keys: dict[str, Literal["presence", "color", "location"]] = {
        "left": "presence", "down": "color", "right": "location"}
    timeout: Duration = Duration(ms=20000)

    @model_validator(mode="after")
    def _all_types(self) -> TypeProbe:
        if sorted(self.keys.values()) != ["color", "location", "presence"]:
            raise ValueError("type keys must map one key to each of presence, color, location")
        return self


class DepthCuedFlickerTaskParams(SubjectParams):
    """A session's parameters. Durations resolve to whole frames at the measured rate."""

    image_width_dva: float = 27.0
    image_height_dva: float = 18.0
    background_gray: float = 0.0
    cue_field: Duration = Duration(ms=3000)
    cue_box_width_dva: float = 8.0
    cue_box_height_dva: float = 2.5
    cue_cap_height_dva: float = 0.9
    cue_style: CueStyle = CueStyle()
    cue_words: CueWords = CueWords()
    cue_counts: CueCounts = CueCounts()
    gray_field: Duration = Duration(ms=1000)
    fixation: Fixation = Fixation()
    flicker: FlickerTiming = FlickerTiming()
    max_flicker: Duration = Duration(ms=60000)
    detect_key: str = "space"
    location_probe: LocationProbe = LocationProbe()
    type_probe: TypeProbe = TypeProbe()
    probe_cap_height_dva: float = 0.45
    scene: SceneParams = SceneParams()
    iti: Duration = Duration(ms=500)
    paradigm: SchedulerConfig = SchedulerConfig(n_per_condition=1)

    @model_validator(mode="after")
    def _keys_do_not_clash(self) -> DepthCuedFlickerTaskParams:
        probe = set(self.location_probe.keys[: self.location_probe.n_choices])
        types = set(self.type_probe.keys)
        if probe & types or self.detect_key in probe | types:
            raise ValueError("the detection, location and type keys must all differ")
        taken = (probe | types | {self.detect_key}) & COMMAND_KEYS
        if taken:
            raise ValueError(f"{sorted(taken)} are alhazen experimenter keys (pause, calibrate, "
                             "skip, reward, ...); choose other response keys")
        if self.scene.source == "photo":
            per_cell = photos.cell_counts(self.scene.photo_set)
            if per_cell and set(per_cell.values()) != {self.cue_counts.total}:
                raise ValueError(
                    f"the {self.scene.photo_set} photograph set has "
                    f"{sorted(set(per_cell.values()))} "
                    f"pairs per plane x change-type cell; cue_counts must add up to that "
                    f"(they add up to {self.cue_counts.total})")
        return self


def scene_spec(p: DepthCuedFlickerTaskParams) -> scenes.SceneSpec:
    s = p.scene
    return scenes.SceneSpec(
        width_dva=p.image_width_dva, height_dva=p.image_height_dva, px_per_dva=s.render_px_per_dva,
        n_near=s.n_near, n_far=s.n_far, n_occluded=s.n_occluded, near_size_dva=s.near_size_dva,
        far_size_dva=s.far_size_dva, target_eccentricity_dva=tuple(s.target_eccentricity_dva),
        location_shift_dva=s.location_shift_dva, far_blur_dva=s.far_blur_dva,
        aerial_mix=s.aerial_mix, shadow_offset_dva=s.shadow_offset_dva,
        shadow_opacity=s.shadow_opacity, cues=scenes.DepthCueSet(**s.cues.model_dump()))


def design(p: DepthCuedFlickerTaskParams, rng: np.random.Generator | None = None) -> list[dict]:
    """Every trial of a session: plane x change type x cue counts, one scene each.

    Drawn scenes: cues are assigned in a fixed balanced order inside each plane x type
    cell (the scheduler shuffles the trials), and every scene is new. Photographs: each
    pair of the set is shown once, and which pairs of a cell get the valid, invalid or
    neutral cue is drawn per session from ``rng``, so no photograph is tied to one cue
    across subjects."""
    c = p.cue_counts
    if p.scene.source == "photo":
        rng = rng if rng is not None else np.random.default_rng(p.scene.seed)
        out = []
        for plane in scenes.PLANES:
            for change_type in scenes.CHANGE_TYPES:
                ids = photos.pair_ids(p.scene.photo_set, plane, change_type)
                cues = (["valid"] * c.valid + ["invalid"] * c.invalid
                        + ["neutral"] * c.neutral + ["none"] * c.none)
                order = rng.permutation(len(ids))
                out += [{"scene": photos.scene_id(ids[i]), "cue": cue}
                        for i, cue in zip(order, cues, strict=True)]
        return out
    out, k = [], 0
    for plane in scenes.PLANES:
        for change_type in scenes.CHANGE_TYPES:
            cues = (["valid"] * c.valid + ["invalid"] * c.invalid + ["neutral"] * c.neutral
                    + ["none"] * c.none)
            for cue in cues:
                out.append({"scene": scenes.scene_id(p.scene.seed + k, plane, change_type),
                            "cue": cue})
                k += 1
    return out


def cue_word(p: DepthCuedFlickerTaskParams, plane: str, cue: str) -> tuple[str, str]:
    """(word shown, plane it names: near | far | neutral | none)."""
    other = "far" if plane == "near" else "near"
    named = {"valid": plane, "invalid": other, "neutral": "neutral", "none": "none"}[cue]
    word = {"near": p.cue_words.near, "far": p.cue_words.far,
            "neutral": p.cue_words.neutral, "none": ""}[named]
    return word, named


class DepthCuedFlickerTask(Task):
    name = "depth-cued-flicker"
    events = EventSchema(("CUE_ON", "GRAY_ON", "FLICKER_ON", "IMAGE_ON", "DETECTED",
                          "LOCATION_PROBE", "LOCATION_REPORT", "TYPE_PROBE", "TYPE_REPORT"))
    outcomes = outcomes(
        CORRECT=dict(completed=True, success=True),
        MISIDENTIFIED=dict(completed=True, success=False),
        NO_DETECTION=dict(completed=True, success=False),
        NO_REPORT=dict(completed=True, success=False),
    )
    params_model = DepthCuedFlickerTaskParams

    @classmethod
    def default_params(cls) -> Path:
        return PROJECT / "configs" / "task-photos.yaml"

    def instructions(self) -> str | None:
        return (PROJECT / "instructions.md").read_text(encoding="utf-8")

    def conditions(self, rng: np.random.Generator) -> list[Condition]:
        p: DepthCuedFlickerTaskParams = self.params  # type: ignore[assignment]
        return [Condition(d) for d in design(p, rng)]

    def _cycle(self, hz: float) -> tuple[list[tuple[str | None, int]], int, int]:
        p: DepthCuedFlickerTaskParams = self.params  # type: ignore[assignment]
        img, blank = p.flicker.image.n_frames(hz), p.flicker.blank.n_frames(hz)
        cycle: list[tuple[str | None, int]] = []
        for name in p.flicker.pattern:
            cycle += [("image_a" if name == "A" else "image_b", img), (None, blank)]
        return cycle, img, blank

    def build_trial(self, setup: TrialSetup) -> TrialPlan:
        p: DepthCuedFlickerTaskParams = self.params  # type: ignore[assignment]
        hz = setup.refresh_rate_hz
        scene_id, cue = setup.condition.params["scene"], setup.condition.params["cue"]
        spec = scene_spec(p)
        if photos.is_photo(scene_id):
            pair = photos.load_pair(scene_id, spec)
            seed, plane, change_type = -1, pair.plane, pair.change_type
        else:
            seed, plane, change_type = scenes.parse_id(scene_id)
            pair = scenes.generate(seed, plane, change_type, spec)
        word, named = cue_word(p, plane, cue)
        screen, display = setup.screen, setup.display
        iw, ih = screen.deg2px(p.image_width_dva), screen.deg2px(p.image_height_dva)
        gray = (p.background_gray,) * 3
        cycle, img_frames, blank_frames = self._cycle(hz)
        pattern = p.flicker.pattern
        switches = sum(1 for a, b in zip(pattern, pattern[1:] + pattern[:1], strict=True) if a != b)
        alternation_s = len(pattern) * (img_frames + blank_frames) / hz / switches

        boxes, correct_box, box_planes = scenes.probe_boxes(
            pair, p.location_probe.n_choices, p.location_probe.box_side_dva, spec, setup.rng)
        box_keys = p.location_probe.keys[: len(boxes)]
        type_key = {v: k for k, v in p.type_probe.keys.items()}[change_type]

        def to_px(fx: float, fy: float) -> tuple[float, float]:
            return ((fx - 0.5) * iw, (0.5 - fy) * ih)

        stimuli = {
            "background": make_rect(display, (screen.width_px * 1.2, screen.height_px * 1.2),
                                    fill=gray, name="background"),
            "cue_box": make_rect(display, (screen.deg2px(p.cue_box_width_dva),
                                           screen.deg2px(p.cue_box_height_dva)),
                                 fill=tuple(p.cue_style.card), name="cue_box"),
            "fixation": make_fixation_abc(display, screen.deg2px(p.fixation.outer_dva),
                                          screen.deg2px(p.fixation.inner_dva),
                                          tuple(p.fixation.color), gray, name="fixation"),
            "image_a": make_image(display, pair.image_a, (iw, ih), name="image_a"),
            "image_b": make_image(display, pair.image_b, (iw, ih), name="image_b"),
            "type_prompt": make_text_image(display, render_text(
                "What kind of change was it?\n\n" + "\n".join(
                    f"{KEY_NAMES.get(k, k.upper())}   {TYPE_LABELS[v]}"
                    for k, v in p.type_probe.keys.items()),
                screen.deg2px(p.probe_cap_height_dva) * 1.3, (0.92, 0.92, 0.92),
                weight="regular", line_spacing=2.2), name="type_prompt"),
            "where_prompt": make_text_image(display, render_text(
                "Where was the change? Press the number of its box.",
                screen.deg2px(p.probe_cap_height_dva), (0.92, 0.92, 0.92), weight="regular"),
                pos=(0.0, -ih / 2 - screen.deg2px(1.2)), name="where_prompt"),
        }
        cue_keys = ["background", "cue_box"]
        if word:
            stimuli["cue_text"] = make_text_image(display, render_text(
                word, screen.deg2px(p.cue_cap_height_dva), tuple(p.cue_style.ink),
                weight=p.cue_style.weight, tracking_em=p.cue_style.tracking_em,
                line_spacing=1.6), name="cue_text")
            cue_keys.append("cue_text")
        gray_keys = ["background"] + (["fixation"] if p.fixation.show_on_gray else [])
        where_keys = ["background", "image_a", "where_prompt"]
        line_px = max(2.0, screen.deg2px(0.08))
        ink = (-0.9, -0.9, -0.85)
        for i, (b, key) in enumerate(zip(boxes, box_keys, strict=False)):
            cx, cy = to_px((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
            w, h = (b[2] - b[0]) * iw, (b[3] - b[1]) * ih
            stimuli[f"box_{i}"] = make_rect(display, (w, h), (cx, cy), line=ink,
                                            line_px=line_px, name=f"box_{i}")
            tag = screen.deg2px(0.9)
            stimuli[f"box_tag_{i}"] = make_rect(
                display, (tag, tag), (cx - w / 2 + tag / 2, cy + h / 2 - tag / 2), fill=ink,
                name=f"box_tag_{i}")
            stimuli[f"box_label_{i}"] = make_text_image(display, render_text(
                key, tag * 0.55, (1.0, 1.0, 1.0)), pos=(cx - w / 2 + tag / 2, cy + h / 2 - tag / 2),
                name=f"box_label_{i}")
            where_keys += [f"box_{i}", f"box_tag_{i}", f"box_label_{i}"]

        out = self.outcomes

        def score(ctx: TrialContext) -> object:
            loc_ok = ctx.record.get("location_report") == str(correct_box)
            type_ok = ctx.record.get("type_report") == change_type
            ctx.record["location_correct"] = bool(loc_ok)
            ctx.record["type_correct"] = bool(type_ok)
            return out["CORRECT"] if loc_ok and type_ok else out["MISIDENTIFIED"]

        trial_phases = [
            phases.Feedback(cue_keys, p.cue_field.seconds(hz), onset_event="CUE_ON"),
            phases.Feedback(gray_keys, p.gray_field.seconds(hz), onset_event="GRAY_ON"),
            FlickerPhase(cycle, {"image_a": "A", "image_b": "B"}, p.detect_key,
                         p.max_flicker.seconds(hz), on_timeout=out["NO_DETECTION"],
                         background_keys=["background"],
                         overlay_keys=["fixation"] if p.fixation.show_during_flicker else [],
                         onset_payload={"plane": plane, "cue": cue, "change_type": change_type,
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
            "scene": scene_id, "scene_seed": seed, "stimulus_source": p.scene.source,
            "changed_object": getattr(pair, "object_name", pair.shape),
            "plane": plane, "change_type": change_type,
            "cue": cue, "cue_word": word, "cued_plane": named,
            "shape": pair.shape, "color_a": pair.color_a, "color_b": pair.color_b,
            "present_in": pair.present_in, "eccentricity_dva": pair.eccentricity_dva,
            "changed_area_dva2": pair.changed_area_dva2,
            "change_cx": round(pair.centroid[0], 4), "change_cy": round(pair.centroid[1], 4),
            "depth_cues": ",".join(k for k, v in p.scene.cues.model_dump().items() if v),
            "image_frames": img_frames, "blank_frames": blank_frames,
            # What the frame counts give at this refresh rate (240 and 80 ms are Rensink's):
            # 233.3 / 83.3 ms at 60 Hz, exact at 75, 100 or 125 Hz.
            "image_ms_realised": round(img_frames / hz * 1000, 2),
            "blank_ms_realised": round(blank_frames / hz * 1000, 2),
            "fixation_on_gray": p.fixation.show_on_gray,
            "fixation_during_flicker": p.fixation.show_during_flicker,
            "alternation_s": round(alternation_s, 5),
            "probe_boxes": json.dumps([[round(v, 4) for v in b] for b in boxes]),
            "probe_planes": ",".join(box_planes),
            "probe_n_choices": len(boxes), "probe_correct": str(correct_box),
            "probe_correct_key": box_keys[correct_box], "type_correct_key": type_key,
        }
        return TrialPlan(phases=trial_phases, stimuli=stimuli, record=record)

    def trial_timing(self, condition: Condition, refresh_rate_hz: float) -> TrialTiming | None:
        p: DepthCuedFlickerTaskParams = self.params  # type: ignore[assignment]
        hz = refresh_rate_hz
        return TrialTiming([
            fixed("cue field", p.cue_field.seconds(hz), "Rensink et al. 1997, Fig. 1"),
            fixed("gray field + fixation", p.gray_field.seconds(hz), "Rensink et al. 1997, Fig. 1"),
            wait("flicker until SPACE", p.max_flicker.seconds(hz), 0.0,
                 "up to 60 s; 240/80 ms per image/blank (Rensink et al. 1997, p. 369)"),
            wait("where (box keys)", p.location_probe.timeout.seconds(hz), 0.0, "ASSUMED"),
            wait("what kind (arrows)", p.type_probe.timeout.seconds(hz), 0.0, "ASSUMED"),
            fixed("inter-trial interval", p.iti.seconds(hz), "ASSUMED"),
        ])

    def simulation(self, seed: int):
        from alhazen.modes.simulation import Simulation

        from depthcb.simulate import SimulatedObserver

        return Simulation(response=SimulatedObserver(seed=seed),
                          describe={"seed": seed, "source": "depthcb.simulate",
                                    "model": "alternations to detection ~ lognormal, mean 8 "
                                             "(near 7, far 9) x cue factor (valid 0.6, "
                                             "neutral 1, invalid 1.5); reports 97% correct. "
                                             "Invented numbers, not data."})
