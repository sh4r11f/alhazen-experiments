"""Run Attention-based motion (Cavanagh 1992), in any of alhazen's modes.

    uv run python run.py --task equiluminance-speed --rig booth --sub s01 --ses 1 --initials AB
    uv run python run.py --task attentive-tracking --rig booth --sub s01 --ses 1 --initials AB
    uv run python run.py --task attentive-tracking --mode simulate --headless \
        --sub sim --ses 1 --seed 1
    uv run python run.py --task attentive-tracking --mode demo
    uv run alhazen dashboard --project .

A subject's order: equiluminance-speed first (every colour stimulus is drawn at the k it
records), then motion-null, thresholds, and the tracking sessions (colour-bar and
luminance-bar sessions alternating, at least two of each); speed-match is Experiment 2.

TASKS, PARAMETERS and LADDERS are module-level dict LITERALS on purpose: alhazen's
dashboard reads them out of this file without running it. Each path is anchored to this
file, so a session finds its configs wherever the command is typed.

Without --rig a session starts on alhazen's shared `laptop` rig, a development rig on
which run mode (real data) is refused. A real session names its rig: copy
configs/rig-booth.yaml and configs/photometry-booth.yaml, enter the machine's measured
geometry and gun luminances, and pass --rig booth.
"""

from __future__ import annotations

import sys
from pathlib import Path

from alhazen.cli.modes import run_experiment

from cavanagh1992.calibration import EquiluminanceSpeedTask, FlickerPhotometryTask
from cavanagh1992.nulling import MotionNullTask, ThresholdTask
from cavanagh1992.speed_match import SpeedMatchTask
from cavanagh1992.task import AttentiveTrackingTask

HERE = Path(__file__).parent

# task name -> (Task class, params file it runs with when --params is not given)
TASKS = {
    "attentive-tracking": (AttentiveTrackingTask, HERE / "configs" / "task.yaml"),
    "equiluminance-speed": (EquiluminanceSpeedTask, HERE / "configs" / "equiluminance-speed.yaml"),
    "flicker-photometry": (FlickerPhotometryTask, HERE / "configs" / "flicker-photometry.yaml"),
    "motion-null": (MotionNullTask, HERE / "configs" / "motion-null.yaml"),
    "thresholds": (ThresholdTask, HERE / "configs" / "thresholds-presence.yaml"),
    "speed-match": (SpeedMatchTask, HERE / "configs" / "speed-global.yaml"),
}

# The dashboard's parameter-set menu: display name -> (task name, params file).
# "(human)" / "(monkey)" names who the file is for (its subject_kind).
PARAMETERS = {
    "1. Equiluminance, minimum speed (human)": (
        "equiluminance-speed", HERE / "configs" / "equiluminance-speed.yaml"),
    "1b. Equiluminance, flicker photometry (human)": (
        "flicker-photometry", HERE / "configs" / "flicker-photometry.yaml"),
    "2. Motion null (human)": ("motion-null", HERE / "configs" / "motion-null.yaml"),
    "3a. Thresholds, presence (human)": (
        "thresholds", HERE / "configs" / "thresholds-presence.yaml"),
    "3b. Thresholds, direction (human)": (
        "thresholds", HERE / "configs" / "thresholds-direction.yaml"),
    "4a. Tracking, colour bars (human)": ("attentive-tracking", HERE / "configs" / "task.yaml"),
    "4b. Tracking, luminance bars (human)": (
        "attentive-tracking", HERE / "configs" / "task-luminance.yaml"),
    "5a. Speed match, global (human)": ("speed-match", HERE / "configs" / "speed-global.yaml"),
    "5b. Speed match, tracking (human)": ("speed-match", HERE / "configs" / "speed-tracking.yaml"),
}

# Monkey training ladders: display name -> ladder YAML. Empty: the paper's observers were
# human and nothing here is designed for a monkey.
LADDERS: dict[str, Path] = {}


def main(argv: list[str] | None = None) -> int:
    return run_experiment(
        tasks=TASKS,
        ladders=LADDERS or None,
        default_rig="laptop",
        argv=list(sys.argv[1:] if argv is None else argv),
    )


if __name__ == "__main__":
    raise SystemExit(main())
