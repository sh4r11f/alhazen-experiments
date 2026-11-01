"""Write docs/guide-overlay.json: the Experiment Platform's compact task guides (timeline,
stimulus schematic, description) for this folder, generated from the task's own code.

    uv run python scripts/guide_overlay.py            # rewrites docs/guide-overlay.json
    uv run python scripts/guide_overlay.py --check    # exit 1 if the file is out of date

Every bar in the schematics is a run of identical columns of the arrays the task draws
(stimulus.stroke_luminance) at 40 px/deg, coloured with the sRGB encoding of the linear gun
levels the example photometry gives: illustrative and uncalibrated. Strokes are drawn side by
side in time order; on the screen they occupy the same place one after another. The overlay
uses only element fields the released guide schema accepts (rect, circle, line, text,
dimension, with the color/stroke_width extensions); no new renderer fields are needed.
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


def hexrgb(linear: np.ndarray) -> str:
    x = np.clip(np.asarray(linear, float), 0.0, 1.0)
    s = np.where(x <= 0.0031308, 12.92 * x, 1.055 * x ** (1 / 2.4) - 0.055)
    return "#" + "".join(f"{int(round(v * 255)):02x}" for v in s)


def r3(v: float) -> float:
    return round(float(v), 3)


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


def cycle_panels(spec: Spec, space, size: float, names: list[str], ms: float) -> list[dict]:
    els = []
    nk = spec.strokes
    xs = [(i - (nk - 1) / 2) * (size + GAP) for i in range(nk)]
    q = spec.period_px // 4
    for k, cx in enumerate(xs):
        els += bars(spec, space, k, cx, size)
        els += fixation(cx)
        els.append({"type": "text", "x": r3(cx - size / 2), "y": r3(size / 2 + 0.55),
                    "text": f"T{k + 1}  {names[k]}", "role": "annotation"})
        if spec.layout == "four_stroke":
            edge = cx - size / 2 + ((spec.offset_px + spec.step * k * q) % spec.period_px) / PPD
            els.append({"type": "line", "x1": r3(edge), "y1": r3(size / 2 + 0.05),
                        "x2": r3(edge), "y2": r3(size / 2 + 0.3), "role": "annotation",
                        "color": "#7f1d1d", "stroke_width": 0.06})
    els.append({"type": "dimension", "x1": r3(xs[0] - size / 2), "y1": r3(-size / 2 - 0.35),
                "x2": r3(xs[0] + size / 2), "y2": r3(-size / 2 - 0.35),
                "value": {"param": "patch_size_dva"}, "text": "patch"})
    els.append({"type": "text", "x": r3(xs[1] - size / 2), "y": r3(-size / 2 - 0.45),
                "text": f"{ms:.3g} ms each, in this order, same place", "role": "annotation"})
    return els


def constant_task() -> dict:
    p = load_params(ROOT / "configs" / "task.yaml", ConstantParams)
    space = p.colour_space()
    period = 4 * round(PPD / p.spatial_freq_cpd / 4)
    size = p.patch_size_dva
    spec = Spec("four_stroke", p.test_colour, p.reference_colour, 10.0, p.reference_cd_m2,
                int(round(size * PPD)), period, 1, 0, p.interleave_contrast)
    ms = 1000.0 / (4 * p.cycle_hz)
    width = 4 * size + 3 * GAP + 0.4
    return {
        "taskKey": "min-motion-constant@configs/task.yaml",
        "description": (
            "**Question.** At what luminance is red as bright as green for the visual "
            "system's motion pathway, for this observer?\n\n"
            "**What the observer sees and does.** A [[param:patch_size_dva]] patch of "
            "square-wave stripes at [[param:spatial_freq_cpd]] around a white cross on a blue "
            "square. A red/green grating (T1), a light/dark grating of their yellow mixture "
            "a quarter cycle on (T2), the red/green grating half a cycle on (T3) and the "
            "mixture three quarters on (T4) repeat at [[param:cycle_hz]]. If red is lighter "
            "than green the stripes seem to drift with the steps, if darker against them. "
            "The observer presses LEFT, RIGHT or DOWN (no consistent motion).\n\n"
            "**Varied.** Red luminance ([[param:test_levels_cd_m2]]) against green at "
            "[[param:reference_cd_m2]], and the step direction (left or right), "
            "[[param:paradigm.n_per_condition]] times each.\n\n"
            "**Measured.** Percent left, right and neither per red luminance; the PSE where "
            "neither direction prevails; the width of the neither band.\n\n"
            "**Meaning and limits.** The PSE is this observer's luminance match for this "
            "stimulus on this display. Physical cd/m2 need a measured photometry file; with "
            "the example file the values are nominal and device-specific. It is not a "
            "colour-vision test."),
        "timeline": {
            "caption": "One trial. The cycle T1-T4 repeats until a key; only the key wait "
                       "is event-dependent.",
            "phases": [
                {"id": "fixate", "label": "Fixation cross", "timing": {
                    "kind": "parameter", "param": "fixation_duration"},
                 "start_events": ["FIX_ON"]},
                {"id": "respond", "label": "Cycle runs; report", "timing": {
                    "kind": "event", "until": "LEFT, RIGHT or DOWN",
                    "max": {"param": "response_timeout"}},
                 "start_events": ["RESPONSE_CUE"], "end_events": ["RESPONSE"]}],
            "tracks": [
                {"label": "Fixation cross on blue square", "role": "stimulus",
                 "from": "fixate", "to": "respond"},
                {"label": f"T1 T2 T3 T4 repeating, {ms:.3g} ms each", "role": "stimulus",
                 "from": "respond", "to": "respond"},
                {"label": "Key: left / right / neither", "role": "response",
                 "from": "respond", "to": "respond"}],
            "branches": [{"from": "respond", "kind": "failure", "when": "no key in time",
                          "outcome": "NO_RESPONSE", "effect": "served again"}],
            "end": {"outcome": "NO_MOTION",
                    "label": "MOTION_LEFT, MOTION_RIGHT or NO_MOTION"},
            "between_trials": {"label": "Dark interval",
                               "timing": {"kind": "parameter", "param": "iti"}}},
        "diagram": {
            "width": r3(width), "height": 3.6, "unit": "dva", "background": 0,
            "caption": ("One four-stroke cycle drawn side by side in time order; on the "
                        "screen all four occupy the same place, one after another. Red 10.0 "
                        "vs green 13.4 cd/m2 (red darker), steps rightward. Bars are the "
                        "task's own arrays at 40 px/deg; inks are sRGB renderings of the "
                        "example photometry's gun levels, illustrative and uncalibrated. "
                        "Oxblood ticks mark where the first red (T1, T3) or light (T2, T4) "
                        "bar starts: a quarter cycle further right each stroke."),
            "elements": cycle_panels(spec, space, size, ["red | green", "light | dark",
                                                         "green | red", "dark | light"], ms)},
        "sourceFiles": ["src/anstiscavanagh1983/stimulus.py",
                        "src/anstiscavanagh1983/constant.py",
                        "src/anstiscavanagh1983/color.py", "configs/task.yaml",
                        "scripts/guide_overlay.py"],
        "notes": [
            "Paper (pp. 155-157): square-wave 2.5 c/deg, 2 x 2 deg in a dark surround, "
            "four-stroke cycle at 5 Hz, green 13.4 cd/m2, red 8-12 cd/m2 ten times each, "
            "yellow grating 6.25%, white cross on a blue 6-min square.",
            "ASSUMED: 0.25 cd/m2 level spacing, keys, 500-ms fixation and interval, "
            "10-s deadline, cross size, random start phase; the step direction is "
            "counterbalanced (a deviation).",
            "Mixture bars are drawn as the additive mean of red and green (the paper "
            "dithered raster lines); line_dither reproduces the dither.",
        ],
    }


def adjust_task() -> dict:
    p = load_params(ROOT / "configs" / "adjust-spatial.yaml", MotionAdjustParams)
    space = p.colour_space()
    sf = 2.5
    period = 4 * round(PPD / sf / 4)
    size = p.patch_size_dva
    spec = Spec("four_stroke", "red", p.reference_colour, p.reference_cd_m2,
                p.reference_cd_m2, int(round(size * PPD)), period, 1, 0, p.interleave_contrast)
    ms = 1000.0 / (4 * p.rates_hz[0])
    width = 4 * size + 3 * GAP + 0.4
    return {
        "taskKey": "min-motion-adjust@configs/adjust-spatial.yaml",
        "description": (
            "**Question.** How bright must red, green and blue be to match grey for the "
            "motion pathway, and does that depend on spatial frequency (Experiment 2) or "
            "temporal frequency (Experiment 3)?\n\n"
            "**What the observer sees and does.** The four-stroke cycle with coloured and "
            "grey ([[param:reference_cd_m2]]) bars and light/dark 'pink' mixture bars at "
            "[[param:interleave_contrast]]. The observer turns the coloured bars' luminance "
            "(wheel or UP/DOWN, [[param:step_factor]] per step) until the motion is least "
            "and presses SPACE.\n\n"
            "**Varied.** Colour ([[param:test_colours]]), spatial frequency "
            "([[param:spatial_freqs_cpd]]) at [[param:rates_hz]]; "
            "configs/adjust-temporal.yaml varies the rate instead.\n\n"
            "**Measured.** The setting (cd/m2); its mean over six readings; luminous "
            "efficiency relative to the uniform-field flicker match.\n\n"
            "**Meaning and limits.** A match for this observer, colour, frequency and "
            "display; settings at different spatial frequencies differ (the paper's Fig. 3)."),
        "timeline": {
            "caption": "One setting. The cycle runs until SPACE.",
            "phases": [
                {"id": "fixate", "label": "Fixation cross", "timing": {
                    "kind": "parameter", "param": "fixation_duration"},
                 "start_events": ["FIX_ON"]},
                {"id": "adjust", "label": "Adjust", "timing": {
                    "kind": "event", "until": "SPACE", "max": {"param": "adjust_timeout"}},
                 "start_events": ["ADJUST_START"], "end_events": ["RESPONSE"]}],
            "tracks": [
                {"label": "Fixation cross on blue square", "role": "stimulus",
                 "from": "fixate", "to": "adjust"},
                {"label": "T1-T4 repeating, one frame each at 60 Hz", "role": "stimulus",
                 "from": "adjust", "to": "adjust"},
                {"label": "Wheel or UP/DOWN, then SPACE", "role": "response",
                 "from": "adjust", "to": "adjust"}],
            "branches": [{"from": "adjust", "kind": "failure", "when": "no SPACE in time",
                          "outcome": "TIMEOUT", "effect": "served again"}],
            "end": {"outcome": "SET", "label": "SET: the test luminance is recorded"},
            "between_trials": {"label": "Dark interval",
                               "timing": {"kind": "parameter", "param": "iti"}}},
        "diagram": {
            "width": r3(width), "height": 3.6, "unit": "dva", "background": 0,
            "caption": (f"Example at 2.5 c/deg, red at {p.reference_cd_m2:g} vs grey "
                        f"{p.reference_cd_m2:g} cd/m2, steps rightward, drawn side by side "
                        "in time order (same place on screen). Grey is the display's white "
                        "point. Task arrays at 40 px/deg; sRGB inks from the example "
                        "photometry, illustrative and uncalibrated."),
            "elements": cycle_panels(spec, space, size, ["red | grey", "light | dark",
                                                         "grey | red", "dark | light"], ms)},
        "sourceFiles": ["src/anstiscavanagh1983/stimulus.py", "src/anstiscavanagh1983/adjust.py",
                        "configs/adjust-spatial.yaml", "configs/adjust-temporal.yaml",
                        "scripts/guide_overlay.py"],
        "notes": [
            "Paper (pp. 157-161): grey 13.6 cd/m2, pink 12.5%, 15 Hz (one TV frame per "
            "grating), 0.625-5 c/deg; Experiment 3 0.9375-15 Hz at 2.5 c/deg; joystick; six "
            "readings per point.",
            "ASSUMED: 2 x 2 deg size, start 0.7-1.3 x reference, 1% steps, 60-s deadline.",
        ],
    }


def flicker_task() -> dict:
    p = load_params(ROOT / "configs" / "flicker-uniform.yaml", FlickerAdjustParams)
    space = p.colour_space()
    size = p.patch_size_dva
    ms = 1000.0 / (2 * p.rates_hz[0])
    els = []
    for k, (name, colour) in enumerate([("red", "red"), ("grey", p.reference_colour)]):
        cx = (k - 0.5) * (size + GAP)
        lin = space.levels(space.gun_luminance(colour, p.reference_cd_m2))
        els.append({"type": "circle", "cx": r3(cx), "cy": 0, "r": r3(size / 2),
                    "role": "stimulus", "color": hexrgb(lin)})
        els += fixation(cx)
        els.append({"type": "text", "x": r3(cx - size / 2), "y": r3(size / 2 + 0.55),
                    "text": f"State {k + 1}: {name}", "role": "annotation"})
    els.append({"type": "text", "x": r3(-size - GAP / 2), "y": r3(-size / 2 - 0.45),
                "text": f"{ms:.3g} ms each, alternating, same place", "role": "annotation"})
    return {
        "taskKey": "min-flicker-adjust@configs/flicker-uniform.yaml",
        "description": (
            "**Question.** The standard comparison: at what luminance does a colour stop "
            "flickering against grey?\n\n"
            "**What the observer sees and does.** A 2-deg disc alternates between the test "
            "colour and grey ([[param:reference_cd_m2]]) at [[param:rates_hz]]. The observer "
            "turns the colour's luminance until the flicker is least and presses SPACE. "
            "configs/flicker-grating.yaml uses a counterphase grating instead (Fig. 3's "
            "filled symbols).\n\n"
            "**Measured.** The setting per colour; it normalises the motion settings in "
            "Fig. 3-4.\n\n"
            "**Meaning and limits.** Heterochromatic flicker photometry for this observer "
            "and display; not the paper's minimum-motion criterion."),
        "timeline": {
            "caption": "One setting. The flicker runs until SPACE.",
            "phases": [
                {"id": "fixate", "label": "Fixation cross", "timing": {
                    "kind": "parameter", "param": "fixation_duration"},
                 "start_events": ["FIX_ON"]},
                {"id": "adjust", "label": "Adjust", "timing": {
                    "kind": "event", "until": "SPACE", "max": {"param": "adjust_timeout"}},
                 "start_events": ["ADJUST_START"], "end_events": ["RESPONSE"]}],
            "tracks": [
                {"label": "Fixation cross on blue square", "role": "stimulus",
                 "from": "fixate", "to": "adjust"},
                {"label": f"Colour and grey alternate, {ms:.3g} ms each", "role": "stimulus",
                 "from": "adjust", "to": "adjust"},
                {"label": "Wheel or UP/DOWN, then SPACE", "role": "response",
                 "from": "adjust", "to": "adjust"}],
            "branches": [{"from": "adjust", "kind": "failure", "when": "no SPACE in time",
                          "outcome": "TIMEOUT", "effect": "served again"}],
            "end": {"outcome": "SET", "label": "SET: the test luminance is recorded"},
            "between_trials": {"label": "Dark interval",
                               "timing": {"kind": "parameter", "param": "iti"}}},
        "diagram": {
            "width": r3(2 * size + GAP + 0.6), "height": 3.6, "unit": "dva", "background": 0,
            "caption": ("The two states of the uniform field, side by side; on the screen "
                        "they alternate in one place. Red shown at 13.6 cd/m2. sRGB inks "
                        "from the example photometry, illustrative and uncalibrated."),
            "elements": els},
        "sourceFiles": ["src/anstiscavanagh1983/stimulus.py", "src/anstiscavanagh1983/adjust.py",
                        "configs/flicker-uniform.yaml", "configs/flicker-grating.yaml",
                        "scripts/guide_overlay.py"],
        "notes": ["Paper (p. 159): 2-deg uniform field, square-wave flicker at 15 Hz against "
                  "13.6 cd/m2 white; counterphase gratings two TV frames per state."],
    }


def overlay() -> dict:
    return {"tasks": [constant_task(), adjust_task(), flicker_task()]}


def main(argv: list[str]) -> int:
    text = json.dumps(overlay(), indent=1, ensure_ascii=False) + "\n"
    if "--check" in argv:
        same = OUT.is_file() and OUT.read_text(encoding="utf-8") == text
        print("up to date" if same else "docs/guide-overlay.json is out of date")
        return 0 if same else 1
    OUT.write_text(text, encoding="utf-8")
    print(OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
