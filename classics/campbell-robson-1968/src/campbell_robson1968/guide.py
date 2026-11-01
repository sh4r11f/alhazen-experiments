"""Build docs/guide-overlay.json: the compact reader drawings for each task, from the
parameter files and this folder's own stimulus geometry.

    uv run python -m campbell_robson1968.guide            # rewrites docs/guide-overlay.json

The stimulus schematic draws the sine grating as narrow vertical strips (``rect``
elements), each at the luminance the task's own formula gives at the strip's centre, so
the picture is a sampled SINE, not the reader's square-wave ``grating`` schematic, and the
field is the paper's square aperture rather than a disc. One example frequency (1 c/deg)
and an illustrative contrast (0.6) are drawn; real threshold contrasts would be invisible.
Uses only elements the released schema already has (rect, line, circle, dimension).
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

import yaml

from campbell_robson1968.common import PROJECT
from campbell_robson1968.stimuli import bracket_segments

EXAMPLE_SF = 1.0
EXAMPLE_CONTRAST = 0.6
STRIPS_PER_CYCLE = 16


def _params(rel: str) -> dict[str, Any]:
    return yaml.safe_load((PROJECT / rel).read_text(encoding="utf-8"))


def _quantised_mean(p: dict[str, Any]) -> float:
    levels = 2 ** int(p["display_bits"]) - 1
    return round(float(p["mean_luminance"]) * levels) / levels


def diagram(params_file: str, *, fixation: bool, sf: float = EXAMPLE_SF,
            waveform: str = "sine") -> dict[str, Any]:
    p = _params(params_file)
    field = float(p["field_dva"])
    mean = _quantised_mean(p)
    n = int(round(field * sf * STRIPS_PER_CYCLE))
    w = field / n
    elements: list[dict[str, Any]] = []
    for i in range(n):
        cx = -field / 2 + (i + 0.5) * w
        c = math.cos(2 * math.pi * sf * cx)
        w_ = c if waveform == "sine" else math.copysign(1.0, c)
        lum = mean * (1 + EXAMPLE_CONTRAST * w_)
        elements.append(
            {
                "type": "rect",
                "cx": round(cx, 4),
                "cy": 0,
                "width": round(w, 4),
                "height": {"param": "field_dva"},
                "luminance": round(lum, 4),
                "role": "stimulus",
            }
        )
    elements.append(
        {
            "type": "rect",
            "cx": 0,
            "cy": 0,
            "width": {"param": "field_dva"},
            "height": {"param": "field_dva"},
            "role": "region",
            "dashed": True,
            "label": f"Field: sine grating, here {EXAMPLE_SF:g} c/deg at contrast "
            f"{EXAMPLE_CONTRAST:g} (illustrative)",
        }
    )
    for j, (a, b) in enumerate(
        bracket_segments(field, float(p["marks_gap_dva"]), float(p["marks_arm_dva"]))
    ):
        el = {
            "type": "line",
            "x1": round(a[0], 4),
            "y1": round(a[1], 4),
            "x2": round(b[0], 4),
            "y2": round(b[1], 4),
            "role": "cue",
            "color": "#000000",
            "stroke_width": {"param": "marks_width_dva"},
        }
        if j == 0:
            el["label"] = (
                "Corner marks (shown only while a look runs)" if fixation else "Corner marks"
            )
        elements.append(el)
    if fixation:
        elements.append(
            {
                "type": "circle",
                "cx": 0,
                "cy": 0,
                "r": {"param": "fix_size_dva", "factor": 0.5},
                "luminance": float(p["fix_luminance"]),
                "role": "target",
                "label": "Fixation point",
            }
        )
    y = -field / 2 - float(p["marks_gap_dva"]) - 0.9
    elements.append(
        {
            "type": "dimension",
            "x1": -field / 2,
            "y1": y,
            "x2": field / 2,
            "y2": y,
            "value": {"param": "field_dva"},
            "text": "field width",
            "role": "annotation",
        }
    )
    span = field + 2 * (float(p["marks_gap_dva"]) + 1.6)
    return {
        "caption": (
            "The display to scale on the mean grey (the rig's linearised mid-level), the stripes "
            f"as one example frequency ({EXAMPLE_SF:g} c/deg) at an illustrative contrast of "
            f"{EXAMPLE_CONTRAST:g}. Greys are display values, not calibrated luminance. The task "
            "uses the frequencies of the parameter set, a random phase per presentation, and "
            "contrasts near threshold, mostly below 1%."
        ),
        "unit": "dva",
        "width": round(span, 2),
        "height": round(span, 2),
        "background": round(mean, 4),
        "elements": elements,
    }


def timeline_2ifc() -> dict[str, Any]:
    return {
        "caption": "One trial. The grating is in interval 1 or 2 at random; the other "
        "interval shows only the mean field. A key pressed before the response "
        "window is ignored.",
        "phases": [
            {
                "id": "fixation",
                "label": "Fixation",
                "timing": {"kind": "parameter", "param": "fixation_duration"},
                "start_events": ["FIX_ON"],
            },
            {
                "id": "interval1",
                "label": "Interval 1",
                "timing": {"kind": "parameter", "param": "interval_duration"},
                "start_events": ["INTERVAL1_ON"],
            },
            {
                "id": "isi",
                "label": "Gap",
                "timing": {"kind": "parameter", "param": "isi"},
                "start_events": ["ISI_ON"],
            },
            {
                "id": "interval2",
                "label": "Interval 2",
                "timing": {"kind": "parameter", "param": "interval_duration"},
                "start_events": ["INTERVAL2_ON"],
            },
            {
                "id": "response",
                "label": "Response",
                "timing": {
                    "kind": "event",
                    "until": "F or J",
                    "max": {"param": "response_timeout"},
                },
                "start_events": ["RESPONSE_CUE"],
                "end_events": ["RESPONSE"],
            },
            {
                "id": "feedback",
                "label": "Feedback",
                "timing": {"kind": "parameter", "param": "feedback_duration"},
            },
        ],
        "tracks": [
            {"label": "Fixation point", "role": "stimulus", "from": "fixation", "to": "feedback"},
            {
                "label": "Corner marks, look 1",
                "role": "annotation",
                "from": "interval1",
                "to": "interval1",
            },
            {
                "label": "Grating (half of trials)",
                "role": "stimulus",
                "from": "interval1",
                "to": "interval1",
            },
            {
                "label": "Corner marks, look 2",
                "role": "annotation",
                "from": "interval2",
                "to": "interval2",
            },
            {
                "label": "Grating (other half)",
                "role": "stimulus",
                "from": "interval2",
                "to": "interval2",
            },
            {
                "label": "F = first, J = second",
                "role": "response",
                "from": "response",
                "to": "response",
            },
        ],
        "branches": [
            {
                "from": "response",
                "kind": "failure",
                "when": "no key in time",
                "outcome": "NO_RESPONSE",
                "effect": "served again",
            }
        ],
        "end": {"outcome": "CORRECT", "label": "CORRECT or WRONG"},
        "between_trials": {
            "label": "Inter-trial interval",
            "timing": {"kind": "parameter", "param": "iti"},
        },
    }


def timeline_adjustment() -> dict[str, Any]:
    return {
        "caption": "One setting. While the observer adjusts, the grating is on for the first "
        "half of every 2-s cycle and off (mean field) for the second, counted in "
        "frames from the first frame of the adjustment.",
        "phases": [
            {
                "id": "ready",
                "label": "Mean field",
                "timing": {"kind": "parameter", "param": "fixation_duration"},
                "start_events": ["FIX_ON"],
            },
            {
                "id": "adjust",
                "label": "Adjust",
                "timing": {"kind": "event", "until": "SPACE", "max": {"param": "adjust_timeout"}},
                "start_events": ["ADJUST_START"],
                "end_events": ["RESPONSE"],
            },
        ],
        "tracks": [
            {"label": "Corner marks", "role": "annotation", "from": "ready", "to": "adjust"},
            {
                "label": "Grating on 1 s, off 1 s",
                "role": "stimulus",
                "from": "adjust",
                "to": "adjust",
            },
            {
                "label": "Up/down arrows or wheel; SPACE sets",
                "role": "response",
                "from": "adjust",
                "to": "adjust",
            },
        ],
        "branches": [
            {
                "from": "adjust",
                "kind": "failure",
                "when": "no SPACE before the limit",
                "outcome": "TIMEOUT",
                "effect": "served again",
            }
        ],
        "end": {"outcome": "SET", "label": "SET"},
        "between_trials": {
            "label": "Inter-trial interval",
            "timing": {"kind": "parameter", "param": "iti"},
        },
    }


DESC_2IFC = (
    "**Which of two looks held the stripes?** Each trial shows the observer two looks in turn, "
    "each [[param:interval_duration]] long and [[param:isi]] apart, marked by four corner marks "
    "around a square field of [[param:field_dva]] on a uniform grey. In one look, chosen at "
    "random, the field holds a stationary vertical sine-wave grating at the same mean "
    "luminance as the grey; in the other it holds nothing. The observer presses F for the first "
    "look or J for the second; the fixation point then turns green or red for "
    "[[param:feedback_duration]].\n\n"
    "**What changes.** The spatial frequency (cycles per degree, one cell each, interleaved) "
    "and, trial by trial, the grating's contrast (Lmax - Lmin) / (Lmax + Lmin), which QUEST+ "
    "chooses on a log scale to home in on each cell's threshold.\n\n"
    "**What is measured.** Proportion correct as a function of contrast in each cell; the "
    "threshold is the contrast for 81% correct in a fitted Weibull function, and the contrast "
    "sensitivity is 1 / threshold. Plotted against spatial frequency, sensitivities form the "
    "contrast-sensitivity function. The record keeps the contrast asked for and the contrast "
    "of the image actually drawn.\n\n"
    "**What it can and cannot show.** A drop in sensitivity at low and high frequencies, with "
    "a peak between, for this observer on this display. Its absolute values depend on the "
    "display's luminance, gamma and bit depth, the field size and the observer's optics; it "
    "is not a clinical test. The paper measured thresholds by adjustment ([[task:csf-adjustment]]); "
    "forced choice is a deliberate change."
)

DESC_ADJ = (
    "**The paper's method.** The grating switches on and off once every "
    "[[param:flicker_period]] (the paper's 0.5 c/s) inside a square field of "
    "[[param:field_dva]], with no change in mean luminance. The observer turns its contrast "
    "down or up (arrow keys or scroll wheel, a factor of 10^[[param:knob_step_log10]] per step) "
    "until the stripes are barely detectable, then presses SPACE. Each spatial frequency gets "
    "[[param:paradigm.n_per_condition]] settings, in random order, each starting from a random "
    "contrast.\n\n"
    "**What is measured.** The settings; a frequency's threshold is their geometric mean and "
    "the sensitivity its reciprocal. Settings depend on the observer's criterion for \"barely "
    'detectable", which forced choice ([[task:csf-2ifc]]) avoids.'
)


DESC_FAR = (
    "**The high-frequency set.** The same two-look trial as the main set: corner marks show two "
    "looks of [[param:interval_duration]], [[param:isi]] apart; a stationary vertical sine "
    "grating is in one, chosen at random; F for the first, J for the second. The field is the "
    "paper's small aperture, [[param:field_dva]] on a side, and the frequencies run from 2 to "
    "22.6 c/deg, the part of Fig. 2 the paper measured from 285 cm.\n\n"
    "**Why it needs its own rig.** A pixel display can only draw a grating with enough pixels per "
    "cycle; this task refuses any frequency with fewer than [[param:min_px_per_cycle]]. At 22.6 "
    "c/deg that means about 90 px/deg: the example booth panel viewed from 150 cm "
    "(configs/rig-booth-far.yaml), not from 57 cm (36 px/deg), where the session stops before "
    "the first trial and names the frequencies it cannot show. Even when allowed, a display's "
    "own blur lowers the contrast it delivers near its limit, which this folder does not "
    "measure.\n\n"
    "**What is measured.** As in the main set: a threshold (81% correct in a fitted Weibull) "
    "and its reciprocal, the sensitivity, per frequency. The paper found that a 2 deg field "
    "lowers sensitivity below about 3 c/deg compared with a 10 deg field (p. 554), so the two "
    "sets are not interchangeable at their overlapping frequencies.")

DESC_SQUARE = (
    "**The paper's Fourier test.** The same two-look trial as the main set in the "
    "[[param:field_dva]] field, but each frequency is measured with two waveforms, interleaved: "
    "a sine-wave grating and a square-wave grating of the same period. A trial shows ONE of "
    "them, in one of the two looks; the drawing shows the square wave, which steps between two "
    "levels at the same mean.\n\n"
    "**Why the ratio is 4/pi.** A square wave of contrast m is a sum of sine waves at f, 3f, "
    "5f, ...; its fundamental has amplitude 4m/pi. If only the fundamental decides whether the "
    "grating is seen, square-wave sensitivity is 4/pi = 1.273 times sine-wave sensitivity; the "
    "paper found that above about 0.8 c/deg and a larger ratio below it (pp. 555-556). Each "
    "trial records the square wave's contrast and its drawn fundamental.\n\n"
    "**Sampling.** A square wave needs its harmonics drawn too, so its frequencies are refused "
    "below [[param:square_min_px_per_cycle]] px per cycle (third harmonic at 4 or more); on the "
    "example booth that caps the set at 3 c/deg. Above that, the display's pixels rather than "
    "the eye would remove the harmonics and the ratio would say nothing about vision.")


def overlay() -> dict[str, Any]:
    src = [
        "classics/campbell-robson-1968/src/campbell_robson1968/" + f
        for f in ("task.py", "adjust.py", "grating.py", "stimuli.py", "phases.py", "common.py")
    ]
    return {
        "tasks": [
            {
                "taskKey": "csf-2ifc@configs/task.yaml",
                "timeline": timeline_2ifc(),
                "diagram": diagram("configs/task.yaml", fixation=True),
                "description": DESC_2IFC,
                "sourceFiles": src
                + [
                    "classics/campbell-robson-1968/configs/task.yaml",
                    "classics/campbell-robson-1968/docs/experiment.json",
                ],
                "notes": [
                    "Paper (p. 553): mean 500 cd/m2, contrast switched on and off at 0.5 c/s, 10 x 10 "
                    "or 2 x 2 cm apertures at 57 or 285 cm (10 or 2 deg), monocular, cycloplegic, "
                    "2.5-mm artificial pupil, threshold by adjustment, 5 or 10 settings.",
                    "Changed here: two-interval forced choice with QUEST+, binocular natural viewing, "
                    "a display's luminance instead of 500 cd/m2.",
                    "ASSUMED: frequencies, vertical stripes, random phase, 1000-ms looks, 500-ms gap, "
                    "corner marks, fixation point, feedback, QUEST+ grids, 60 trials per cell.",
                    "Contrast below one display code step (about 0.8% on 8 bits) exists only through "
                    "dithering; set display_bits and measure gamma before real data.",
                ],
            },
            {
                "taskKey": "csf-2ifc@configs/task-far.yaml",
                "timeline": timeline_2ifc(),
                "diagram": diagram("configs/task-far.yaml", fixation=True, sf=4.0),
                "description": DESC_FAR,
                "sourceFiles": src
                + [
                    "classics/campbell-robson-1968/configs/task-far.yaml",
                    "classics/campbell-robson-1968/configs/rig-booth-far.yaml",
                    "classics/campbell-robson-1968/docs/experiment.json",
                ],
                "notes": [
                    "Paper (pp. 553-554, Fig. 2): the 2 x 2 deg field was a 2 x 2 cm aperture at 57 cm or 10 x 10 cm at 285 cm; the high frequencies came from 285 cm because the tube lost contrast above 10 c/cm.",
                    "Here: 2 deg field at 2, 4, 8, 16 and 22.6 c/deg (ASSUMED levels); refused unless every frequency gets 4 px per cycle on the rig (about 90 px/deg at 22.6 c/deg).",
                    "Drawing: the 2 deg field to scale with one example frequency, 4 c/deg, at an illustrative contrast of 0.6; the timing is the same as the main set's.",
                ],
            },
            {
                "taskKey": "csf-2ifc@configs/sine-square.yaml",
                "timeline": timeline_2ifc(),
                "diagram": diagram("configs/sine-square.yaml", fixation=True, waveform="square"),
                "description": DESC_SQUARE,
                "sourceFiles": src
                + [
                    "classics/campbell-robson-1968/configs/sine-square.yaml",
                    "classics/campbell-robson-1968/src/campbell_robson1968/analysis.py",
                    "classics/campbell-robson-1968/docs/experiment.json",
                ],
                "notes": [
                    "Paper (pp. 555-556, Figs. 3-4): square/sine sensitivity ratio 4/pi = 1.273 above about 0.8 c/deg (1.280 +/- 0.025 for F.W.C. over 1-35 c/deg), larger below; thresholds for the two waveforms measured alternately.",
                    "Here: sine and square interleaved at 0.5, 1, 2 and 3 c/deg (ASSUMED levels); square waves refused below 12 px per cycle; the analysis reports the ratio per frequency beside 4/pi.",
                    "Drawing: the square wave at 1 c/deg, contrast 0.6 (illustrative); sine trials look like the main set's drawing. One waveform per trial, never both.",
                ],
            },
            {
                "taskKey": "csf-adjustment@configs/adjustment.yaml",
                "timeline": timeline_adjustment(),
                "diagram": diagram("configs/adjustment.yaml", fixation=False),
                "description": DESC_ADJ,
                "sourceFiles": src
                + [
                    "classics/campbell-robson-1968/configs/adjustment.yaml",
                    "classics/campbell-robson-1968/docs/experiment.json",
                ],
                "notes": [
                    "Paper (p. 553): on-off at 0.5 c/s, settings until barely detectable, 5 or 10 per "
                    "threshold, standard error under 10%.",
                    "ASSUMED: equal on and off halves, the knob step, start contrasts, no fixation mark, "
                    "5 settings per frequency.",
                ],
            },
        ]
    }


def write(path: Path | None = None) -> Path:
    out = path or PROJECT / "docs" / "guide-overlay.json"
    out.write_text(json.dumps(overlay(), indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return out


if __name__ == "__main__":
    print(write(Path(sys.argv[1]) if len(sys.argv) > 1 else None))
