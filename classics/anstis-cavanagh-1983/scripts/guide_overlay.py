"""Write docs/guide-overlay.json: the Experiment Platform's compact task guides (timeline,
stimulus schematic, description) for EVERY parameter set run.py names, generated from the
task's own code and each set's own parameters file.

    uv run python scripts/guide_overlay.py            # rewrites docs/guide-overlay.json
    uv run python scripts/guide_overlay.py --check    # exit 1 if the file is out of date

One overlay task per parameter file, keyed ``<task id>@<parameters file>`` to match the
entries in docs/experiment.json. Every bar in the schematics is a run of identical columns
of the arrays the task draws (stimulus.stroke_luminance) at 40 px/deg, for that file's
colours, reference luminance, mixture contrast and an example spatial frequency from that
file, coloured with the sRGB encoding of the linear gun levels the example photometry gives:
illustrative and uncalibrated. Strokes are drawn side by side in time order; on the screen
they occupy the same place, one after another. Only element fields the released guide schema
accepts are used (rect, circle, line, text, dimension, with the color/stroke_width extensions).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from alhazen.config.loader import load_params  # noqa: E402

from anstiscavanagh1983.adjust import FlickerAdjustParams, MotionAdjustParams  # noqa: E402
from anstiscavanagh1983.constant import ConstantParams  # noqa: E402
from anstiscavanagh1983.stimulus import Spec, stroke_luminance  # noqa: E402

PPD = 40.0
OUT = ROOT / "docs" / "guide-overlay.json"
GAP = 0.7  # dva between panels
REFRESH = 60.0  # the paper's TV and the example rig


def hexrgb(linear: np.ndarray) -> str:
    x = np.clip(np.asarray(linear, float), 0.0, 1.0)
    s = np.where(x <= 0.0031308, 12.92 * x, 1.055 * x ** (1 / 2.4) - 0.055)
    return "#" + "".join(f"{int(round(v * 255)):02x}" for v in s)


def r3(v: float) -> float:
    return round(float(v), 3)


def ms_text(ms: float) -> str:
    return f"{ms:.3g} ms"


def example_sf(sfs: list[float]) -> float:
    """The example spatial frequency drawn: 2.5 c/deg (Experiment 1's) when the file has
    it, otherwise the file's first."""
    return 2.5 if 2.5 in sfs else float(sfs[0])


def period_px(sf: float) -> int:
    return max(4, 4 * int(round(PPD / sf / 4)))


def bars(spec: Spec, space, k: int, cx: float, size_dva: float) -> list[dict]:
    """Rect elements for stroke k: one per run of identical columns, centred at cx."""
    row = space.levels(stroke_luminance(spec, space, k)[0])  # (width, 3) linear levels
    out, start = [], 0
    n = row.shape[0]
    for i in range(1, n + 1):
        if i == n or not np.allclose(row[i], row[start]):
            x0 = cx - size_dva / 2 + start / PPD
            w = (i - start) / PPD
            out.append({"type": "rect", "cx": r3(x0 + w / 2), "cy": 0, "width": r3(w),
                        "height": r3(size_dva), "role": "stimulus", "color": hexrgb(row[start])})
            start = i
    return out


def fixation(cx: float) -> list[dict]:
    return [{"type": "rect", "cx": r3(cx), "cy": 0, "width": 0.1, "height": 0.1,
             "role": "stimulus", "color": "#0000ff"},
            {"type": "line", "x1": r3(cx - 0.05), "y1": 0, "x2": r3(cx + 0.05), "y2": 0,
             "role": "stimulus", "color": "#ffffff", "stroke_width": 0.02},
            {"type": "line", "x1": r3(cx), "y1": -0.05, "x2": r3(cx), "y2": 0.05,
             "role": "stimulus", "color": "#ffffff", "stroke_width": 0.02}]


def panels(spec: Spec, space, size: float, names: list[str], timing: str) -> list[dict]:
    """The strokes of one cycle side by side, labelled T1.., with a tick at the left edge
    of the first test bar (colour strokes) or light bar (mixture strokes)."""
    els = []
    nk = spec.strokes
    xs = [(i - (nk - 1) / 2) * (size + GAP) for i in range(nk)]
    q = spec.period_px // 4
    for k, cx in enumerate(xs):
        els += bars(spec, space, k, cx, size)
        els += fixation(cx)
        els.append({"type": "text", "x": r3(cx), "y": r3(size / 2 + 0.55),
                    "text": f"T{k + 1}  {names[k]}", "role": "annotation",
                    "font_size": 0.22})
        shift = spec.step * k * q if spec.layout == "four_stroke" else k * 2 * q
        edge = cx - size / 2 + ((spec.offset_px + shift) % spec.period_px) / PPD
        els.append({"type": "line", "x1": r3(edge), "y1": r3(size / 2 + 0.05),
                    "x2": r3(edge), "y2": r3(size / 2 + 0.3), "role": "annotation",
                    "color": "#7f1d1d", "stroke_width": 0.06})
    els.append({"type": "dimension", "x1": r3(xs[0] - size / 2), "y1": r3(-size / 2 - 0.35),
                "x2": r3(xs[0] + size / 2), "y2": r3(-size / 2 - 0.35),
                "value": {"param": "patch_size_dva"}, "text": "patch"})
    order = "in this order" if nk == 4 else "alternating"
    tx = 0.0
    els.append({"type": "text", "x": r3(tx),
                "y": r3(-size / 2 - 0.8), "text": f"{timing}, {order}",
                "role": "annotation"})
    return els


def names4(test: str, ref: str, mixture: str) -> list[str]:
    return [f"{test} | {ref}", f"light | dark {mixture}", f"{ref} | {test}",
            f"dark | light {mixture}"]


MIXTURE = {("red", "green"): "yellow", ("blue", "yellow"): "grey", ("red", "grey"): "pink",
           ("green", "grey"): "pale green", ("blue", "grey"): "pale blue"}


def diagram(width: float, caption: str, elements: list[dict]) -> dict:
    return {"width": r3(width), "height": 4.4, "unit": "dva", "background": 0,
            "caption": caption, "elements": elements}


def fix_track(last: str) -> dict:
    return {"label": "Fixation cross on blue square", "role": "stimulus",
            "from": "fixate", "to": last}


ITI = {"label": "Dark interval", "timing": {"kind": "parameter", "param": "iti"}}
FIXATE = {"id": "fixate", "label": "Fixation cross",
          "timing": {"kind": "parameter", "param": "fixation_duration"},
          "start_events": ["FIX_ON"]}
CALIBRATION = ("Physical cd/m2 need a measured photometry file on a gamma-linearised "
               "display; with the example file the values are nominal and device-specific "
               "(every trial records its luminance basis). Not a colour-vision test.")


# --- Experiment 1: constant stimuli ------------------------------------------------
CONSTANT = {
    "configs/task.yaml": {
        "title": "red/green",
        "paper": ("Paper (pp. 155-157): square-wave 2.5 c/deg, 2 x 2 deg in a dark "
                  "surround, four-stroke cycle at 5 Hz, green 13.4 cd/m2, red 8-12 cd/m2 ten "
                  "times each, yellow grating 6.25%, white cross on a blue 6-min square."),
        "assumed": ("ASSUMED: 0.25 cd/m2 level spacing, keys, 500-ms fixation and interval, "
                    "10-s deadline, cross size, random start phase; the step direction is "
                    "counterbalanced (a deviation)."),
        "question": "At what luminance is red as bright as green for the visual system's "
                    "motion pathway, for this observer?",
    },
    "configs/task-blue-yellow.yaml": {
        "title": "blue/yellow",
        "paper": ("Paper (p. 157, Fig. 2b): the same procedure with blue bars varied against "
                  "yellow bars held at 7.9 cd/m2 (yellow x 0.51, y 0.44), interleaved with "
                  "light and dark grey, the mixture of blue and yellow."),
        "assumed": ("ASSUMED: blue levels 8-12 cd/m2 in 0.25 steps (range not stated; Fig. 2b "
                    "axes), grey-grating contrast 6.25% (not restated), yellow = red + green "
                    "guns with 41.9% of its luminance from red (from the paper's chromaticities), "
                    "keys and timing as for red/green."),
        "question": "At what luminance is blue as bright as yellow for the motion pathway, "
                    "for this observer?",
    },
}


def constant_task(file: str) -> dict:
    meta = CONSTANT[file]
    p = load_params(ROOT / file, ConstantParams)
    space = p.colour_space()
    size = p.patch_size_dva
    levels = sorted(p.test_levels_cd_m2)
    level = levels[len(levels) // 2]
    spec = Spec("four_stroke", p.test_colour, p.reference_colour, level, p.reference_cd_m2,
                int(round(size * PPD)), period_px(p.spatial_freq_cpd), 1, 0,
                p.interleave_contrast)
    frames = max(1, round(REFRESH / (4 * p.cycle_hz)))
    ms = 1000.0 * frames / REFRESH
    mix = MIXTURE.get((p.test_colour, p.reference_colour), "mixture")
    t, r = p.test_colour, p.reference_colour
    relation = "lighter" if level > p.reference_cd_m2 else "darker"
    return {
        "taskKey": f"min-motion-constant@{file}",
        "description": (
            f"**Question.** {meta['question']}\n\n"
            f"**What the observer sees and does.** A [[param:patch_size_dva]] patch of "
            f"square-wave stripes at [[param:spatial_freq_cpd]] around a white cross on a "
            f"blue square. A {t}/{r} grating (T1), a light/dark grating of their {mix} "
            f"mixture a quarter cycle on (T2), the {t}/{r} grating half a cycle on (T3) and "
            f"the mixture three quarters on (T4) repeat at [[param:cycle_hz]] "
            f"({ms_text(ms)} per grating at 60 Hz). If {t} is lighter than {r} the stripes "
            f"seem to drift with the steps, if darker against them. The observer presses "
            f"LEFT, RIGHT or DOWN (no consistent motion).\n\n"
            f"**Varied.** {t.capitalize()} luminance ([[param:test_levels_cd_m2]]) against "
            f"{r} at [[param:reference_cd_m2]], and the step direction (left or right), "
            f"[[param:paradigm.n_per_condition]] times each.\n\n"
            f"**Measured.** Percent left, right and neither per {t} luminance; the PSE where "
            f"neither direction prevails; the width of the neither band.\n\n"
            f"**Meaning and limits.** The PSE is this observer's luminance match for this "
            f"stimulus on this display. {CALIBRATION}"),
        "timeline": {
            "caption": "One trial. The cycle T1-T4 repeats until a key; only the key wait "
                       "is event-dependent.",
            "phases": [FIXATE,
                       {"id": "respond", "label": "Cycle runs; report", "timing": {
                           "kind": "event", "until": "LEFT, RIGHT or DOWN",
                           "max": {"param": "response_timeout"}},
                        "start_events": ["RESPONSE_CUE"], "end_events": ["RESPONSE"]}],
            "tracks": [fix_track("respond"),
                       {"label": f"T1 T2 T3 T4 repeating, {ms_text(ms)} each",
                        "role": "stimulus", "from": "respond", "to": "respond"},
                       {"label": "Key: left / right / neither", "role": "response",
                        "from": "respond", "to": "respond"}],
            "branches": [{"from": "respond", "kind": "failure", "when": "no key in time",
                          "outcome": "NO_RESPONSE", "effect": "served again"}],
            "end": {"outcome": "NO_MOTION",
                    "label": "MOTION_LEFT, MOTION_RIGHT or NO_MOTION"},
            "between_trials": ITI},
        "diagram": diagram(
            4 * size + 3 * GAP + 0.4,
            (f"One four-stroke cycle drawn side by side in time order; on the screen all "
             f"four occupy the same place, one after another. {t.capitalize()} {level:g} vs "
             f"{r} {p.reference_cd_m2:g} cd/m2 (the middle test level; {t} photometrically "
             f"{relation}), steps rightward, {p.spatial_freq_cpd:g} c/deg. Bars are the "
             f"task's own arrays at 40 px/deg; inks are sRGB renderings of the example "
             f"photometry's gun levels, illustrative and uncalibrated. Oxblood ticks mark "
             f"where the first {t} (T1, T3) or light (T2, T4) bar starts: a quarter cycle "
             f"further right each stroke."
             + (" The mixture is called grey after the paper (p. 157); on the example "
                "display's primaries its additive mean renders bluish." if mix == "grey" else "")),
            panels(spec, space, size, names4(t, r, mix), f"{ms_text(ms)} each")),
        "sourceFiles": ["src/anstiscavanagh1983/stimulus.py",
                        "src/anstiscavanagh1983/constant.py",
                        "src/anstiscavanagh1983/color.py", file, "scripts/guide_overlay.py"],
        "notes": [meta["paper"], meta["assumed"],
                  f"Mixture bars are drawn as the additive mean of {t} and {r} (the paper "
                  f"dithered raster lines); line_dither reproduces the dither."],
    }


# --- Experiments 2-3 and the red/green setting: minimum motion by adjustment --------
MOTION = {
    "configs/adjust-spatial.yaml": {
        "question": "How bright must red, green and blue be to match grey for the motion "
                    "pathway, and does that change with spatial frequency (Experiment 2)?",
        "varied": "Colour ([[param:test_colours]]) x spatial frequency "
                  "([[param:spatial_freqs_cpd]]) at [[param:rates_hz]].",
        "paper": ("Paper (pp. 157-159): red, green, blue vs grey 13.6 cd/m2, pink 12.5%, "
                  "15 Hz (one TV frame per grating), 0.625-5 c/deg, joystick, six readings "
                  "per point, counterbalanced randomized order."),
        "assumed": "ASSUMED: 2 x 2 deg size, start 0.7-1.3 x reference, 1% steps, 60-s "
                   "deadline, additive pink.",
        "limit": "Settings at different spatial frequencies differ (the paper's Fig. 3).",
    },
    "configs/adjust-temporal.yaml": {
        "question": "Does the minimum-motion match of red, green and blue against grey "
                    "change with temporal frequency (Experiment 3)?",
        "varied": "Colour ([[param:test_colours]]) x cycle rate ([[param:rates_hz]]) at "
                  "[[param:spatial_freqs_cpd]].",
        "paper": ("Paper (p. 161, Fig. 4): gratings as in Experiment 2 at 2.5 c/deg, four-"
                  "stroke rates 0.9375, 1.875, 3.75, 7.5 and 15 Hz (submultiples of 60 Hz); "
                  "settings were largely independent of rate."),
        "assumed": "ASSUMED: six readings (not restated), 2 x 2 deg size, start 0.7-1.3 x "
                   "reference, 1% steps, 60-s deadline, additive pink.",
        "limit": "The paper found little effect of rate; that is a claim to test, not a "
                 "property of this software.",
    },
    "configs/adjust-red-green.yaml": {
        "question": "A practical red/green equiluminance setting for later experiments on "
                    "this display: at what red luminance does Experiment 1's stimulus stop "
                    "moving, set by adjustment?",
        "varied": "Nothing but the step direction: red ([[param:test_colours]]) against green "
                  "at [[param:spatial_freqs_cpd]] and [[param:rates_hz]], six settings.",
        "paper": ("NOT one of the paper's conditions: Experiment 1's red/green stimulus "
                  "(p. 157: green 13.4 cd/m2, 2.5 c/deg, 5 Hz, yellow 6.25%) set with the "
                  "adjustment procedure of Experiments 2-3 (p. 159), the use the paper "
                  "recommends for TV displays (p. 165)."),
        "assumed": "ASSUMED: start 0.7-1.3 x reference, 1% steps, 60-s deadline, additive "
                   "yellow mixture.",
        "limit": "The setting holds for this stimulus (2.5 c/deg, 5 Hz) on this display; "
                 "use it only for stimuli like it (p. 163).",
    },
}


def motion_task(file: str) -> dict:
    meta = MOTION[file]
    p = load_params(ROOT / file, MotionAdjustParams)
    space = p.colour_space()
    size = p.patch_size_dva
    sf = example_sf(p.spatial_freqs_cpd)
    test, ref = p.test_colours[0], p.reference_colour
    spec = Spec("four_stroke", test, ref, p.reference_cd_m2, p.reference_cd_m2,
                int(round(size * PPD)), period_px(sf), 1, 0, p.interleave_contrast)
    times = sorted({1000.0 * max(1, round(REFRESH / (4 * r))) / REFRESH for r in p.rates_hz})
    timing = (f"{ms_text(times[0])} each" if len(times) == 1 else
              f"{times[0]:.3g}-{times[-1]:.3g} ms each by rate")
    mix = MIXTURE.get((test, ref), "mixture")
    return {
        "taskKey": f"min-motion-adjust@{file}",
        "description": (
            f"**Question.** {meta['question']}\n\n"
            f"**What the observer sees and does.** The four-stroke cycle: test and "
            f"{ref} ([[param:reference_cd_m2]]) bars, then light/dark {mix} mixture bars at "
            f"[[param:interleave_contrast]] a quarter cycle on, then the colours exchanged, "
            f"then the mixture exchanged ({timing} at 60 Hz). The observer turns the test "
            f"bars' luminance (wheel or UP/DOWN, [[param:step_factor]] per step) until the "
            f"motion is least and presses SPACE.\n\n"
            f"**Varied.** {meta['varied']} Each condition is set "
            f"[[param:paradigm.n_per_condition]] times per step direction.\n\n"
            f"**Measured.** The setting (cd/m2), its mean over the readings, and luminous "
            f"efficiency relative to the uniform-field flicker match.\n\n"
            f"**Meaning and limits.** {meta['limit']} {CALIBRATION}"),
        "timeline": {
            "caption": "One setting. The cycle runs until SPACE.",
            "phases": [FIXATE,
                       {"id": "adjust", "label": "Adjust", "timing": {
                           "kind": "event", "until": "SPACE",
                           "max": {"param": "adjust_timeout"}},
                        "start_events": ["ADJUST_START"], "end_events": ["RESPONSE"]}],
            "tracks": [fix_track("adjust"),
                       {"label": f"T1-T4 repeating, {timing}", "role": "stimulus",
                        "from": "adjust", "to": "adjust"},
                       {"label": "Wheel or UP/DOWN, then SPACE", "role": "response",
                        "from": "adjust", "to": "adjust"}],
            "branches": [{"from": "adjust", "kind": "failure", "when": "no SPACE in time",
                          "outcome": "TIMEOUT", "effect": "served again"}],
            "end": {"outcome": "SET", "label": "SET: the test luminance is recorded"},
            "between_trials": ITI},
        "diagram": diagram(
            4 * size + 3 * GAP + 0.4,
            (f"One cycle for {test} against {ref}, both at {p.reference_cd_m2:g} cd/m2 "
             f"(each setting starts at a random 0.7-1.3 x reference), {sf:g} c/deg, steps "
             f"rightward, drawn side by side in time order (same place on screen). "
             f"{'Grey is the display white point. ' if ref == 'grey' else ''}"
             f"Task arrays at 40 px/deg; sRGB inks from the example photometry, illustrative "
             f"and uncalibrated. Ticks: first {test} (T1, T3) or light (T2, T4) bar, a quarter "
             f"cycle further right each stroke."),
            panels(spec, space, size, names4(test, ref, mix), timing)),
        "sourceFiles": ["src/anstiscavanagh1983/stimulus.py", "src/anstiscavanagh1983/adjust.py",
                        file, "scripts/guide_overlay.py"],
        "notes": [meta["paper"], meta["assumed"]],
    }


# --- Minimum flicker -----------------------------------------------------------------
FLICKER = {
    "configs/flicker-uniform.yaml": {
        "paper": ("Paper (p. 159, Fig. 3 legend): the standard flicker match, a 2-deg uniform "
                  "field in square-wave flicker at 15 Hz between the colour and 13.6 cd/m2 "
                  "white; it normalises Fig. 3-4."),
        "sees": "A 2-deg disc alternates between the test colour and grey",
        "limit": "Heterochromatic flicker photometry; not the paper's minimum-motion "
                 "criterion.",
    },
    "configs/flicker-grating.yaml": {
        "paper": ("Paper (p. 159, Fig. 3 filled symbols): square-wave gratings whose bars "
                  "flicker in counterphase between the colour and 13.6 cd/m2 grey, two TV "
                  "frames (33 ms) per state, 0.625-5 c/deg, six readings per point."),
        "sees": "A square-wave grating whose bars swap between the test colour and grey",
        "limit": "Minimum counterphase flicker at each spatial frequency, the comparison for "
                 "Experiment 2's minimum-motion settings.",
    },
}


def flicker_task(file: str) -> dict:
    meta = FLICKER[file]
    p = load_params(ROOT / file, FlickerAdjustParams)
    space = p.colour_space()
    size = p.patch_size_dva
    test, ref = p.test_colours[0], p.reference_colour
    ms = 1000.0 * max(1, round(REFRESH / (2 * p.rates_hz[0]))) / REFRESH
    if p.field == "uniform":
        els = []
        for k, (name, colour) in enumerate([(test, test), (ref, ref)]):
            cx = (k - 0.5) * (size + GAP)
            lin = space.levels(space.gun_luminance(colour, p.reference_cd_m2))
            els.append({"type": "circle", "cx": r3(cx), "cy": 0, "r": r3(size / 2),
                        "role": "stimulus", "color": hexrgb(lin)})
            els += fixation(cx)
            els.append({"type": "text", "x": r3(cx), "y": r3(size / 2 + 0.55),
                        "text": f"T{k + 1}  {name}", "role": "annotation"})
        els.append({"type": "text", "x": r3(-size - GAP / 2), "y": r3(-size / 2 - 0.45),
                    "text": f"{ms_text(ms)} each, alternating, same place",
                    "role": "annotation"})
        width = 2 * size + GAP + 0.6
        caption = (f"The two states of the uniform field, side by side; on the screen they "
                   f"alternate in one place. {test.capitalize()} shown at "
                   f"{p.reference_cd_m2:g} cd/m2 against {ref} {p.reference_cd_m2:g}. "
                   f"sRGB inks from the example photometry, illustrative and uncalibrated.")
        varied = "Colour ([[param:test_colours]]) at [[param:rates_hz]]."
    else:
        sf = example_sf(p.spatial_freqs_cpd)
        spec = Spec("counterphase", test, ref, p.reference_cd_m2, p.reference_cd_m2,
                    int(round(size * PPD)), period_px(sf), 1, 0)
        els = panels(spec, space, size, [f"{test} | {ref}", f"{ref} | {test}"],
                     f"{ms_text(ms)} each")
        width = 2 * size + GAP + 0.6
        caption = (f"The two states of the counterphase grating ({test} vs {ref}, both at "
                   f"{p.reference_cd_m2:g} cd/m2, {sf:g} c/deg), side by side; on the screen "
                   f"they alternate in one place, the bars exchanging colours (half a cycle, "
                   f"no direction). Task arrays at 40 px/deg; sRGB inks from the example "
                   f"photometry, illustrative and uncalibrated.")
        varied = ("Colour ([[param:test_colours]]) x spatial frequency "
                  "([[param:spatial_freqs_cpd]]) at [[param:rates_hz]].")
    return {
        "taskKey": f"min-flicker-adjust@{file}",
        "description": (
            "**Question.** The comparison measure: at what luminance does a colour stop "
            "flickering against grey?\n\n"
            f"**What the observer sees and does.** {meta['sees']} "
            f"([[param:reference_cd_m2]]) at [[param:rates_hz]] ({ms_text(ms)} per state at "
            "60 Hz). The observer turns the colour's luminance until the flicker is least "
            "and presses SPACE.\n\n"
            f"**Varied.** {varied} Each condition is set [[param:paradigm.n_per_condition]] "
            "times per step direction.\n\n"
            "**Measured.** The setting per condition (cd/m2) and its mean.\n\n"
            f"**Meaning and limits.** {meta['limit']} {CALIBRATION}"),
        "timeline": {
            "caption": "One setting. The flicker runs until SPACE.",
            "phases": [FIXATE,
                       {"id": "adjust", "label": "Adjust", "timing": {
                           "kind": "event", "until": "SPACE",
                           "max": {"param": "adjust_timeout"}},
                        "start_events": ["ADJUST_START"], "end_events": ["RESPONSE"]}],
            "tracks": [fix_track("adjust"),
                       {"label": f"Colour and grey alternate, {ms_text(ms)} each",
                        "role": "stimulus", "from": "adjust", "to": "adjust"},
                       {"label": "Wheel or UP/DOWN, then SPACE", "role": "response",
                        "from": "adjust", "to": "adjust"}],
            "branches": [{"from": "adjust", "kind": "failure", "when": "no SPACE in time",
                          "outcome": "TIMEOUT", "effect": "served again"}],
            "end": {"outcome": "SET", "label": "SET: the test luminance is recorded"},
            "between_trials": ITI},
        "diagram": diagram(width, caption, els),
        "sourceFiles": ["src/anstiscavanagh1983/stimulus.py", "src/anstiscavanagh1983/adjust.py",
                        file, "scripts/guide_overlay.py"],
        "notes": [meta["paper"],
                  "ASSUMED: 2 x 2 deg grating size (the uniform field's 2 deg is the paper's), "
                  "start 0.7-1.3 x reference, 1% steps, 60-s deadline."],
    }


SETS = [
    ("min-motion-constant", "configs/task.yaml", constant_task),
    ("min-motion-constant", "configs/task-blue-yellow.yaml", constant_task),
    ("min-motion-adjust", "configs/adjust-spatial.yaml", motion_task),
    ("min-motion-adjust", "configs/adjust-temporal.yaml", motion_task),
    ("min-motion-adjust", "configs/adjust-red-green.yaml", motion_task),
    ("min-flicker-adjust", "configs/flicker-uniform.yaml", flicker_task),
    ("min-flicker-adjust", "configs/flicker-grating.yaml", flicker_task),
]


def overlay() -> dict:
    return {"tasks": [build(file) for _, file, build in SETS]}


def main(argv: list[str]) -> int:
    text = json.dumps(overlay(), indent=1, ensure_ascii=False) + "\n"
    if "--check" in argv:
        same = OUT.is_file() and OUT.read_text(encoding="utf-8") == text
        print("up to date" if same else "docs/guide-overlay.json is out of date")
        return 0 if same else 1
    OUT.write_text(text, encoding="utf-8")
    print(OUT.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
