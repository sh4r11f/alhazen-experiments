"""Run Minimum-motion equiluminance (Anstis & Cavanagh 1983), in any of alhazen's modes.

    uv run python run.py --task min-motion-constant --mode demo
    uv run python run.py --task min-motion-constant --mode simulate --headless \
        --sub sim --ses 1 --seed 1
    uv run python run.py --task min-motion-constant --rig booth --sub s01 --ses 1 --initials AB
    uv run python run.py --task min-motion-adjust --rig booth --sub s01 --ses 1 --initials AB
    uv run alhazen dashboard --project .

Experiment 1 is min-motion-constant (configs/task.yaml red/green, task-blue-yellow.yaml);
Experiments 2-3 are min-motion-adjust with min-flicker-adjust as their comparison.

TASKS, PARAMETERS and LADDERS are module-level dict LITERALS on purpose: alhazen's
dashboard reads them out of this file without running it. Each path is anchored to this
file, so a session finds its configs wherever the command is typed.

Without --rig a session starts on alhazen's shared `laptop` rig, a development rig on
which run mode (real data) is refused. A real session names its rig: copy
configs/rig-booth.yaml and configs/photometry-booth.yaml, linearise the display, enter the
measured geometry and gun luminances (measured: true), and pass --rig booth.
"""

from __future__ import annotations

import sys
from pathlib import Path

from alhazen.cli.modes import run_experiment

from anstiscavanagh1983.adjust import MinFlickerAdjustTask, MinMotionAdjustTask
from anstiscavanagh1983.constant import MinMotionConstantTask

HERE = Path(__file__).parent

# task name -> (Task class, params file it runs with when --params is not given)
TASKS = {
    "min-motion-constant": (MinMotionConstantTask, HERE / "configs" / "task.yaml"),
    "min-motion-adjust": (MinMotionAdjustTask, HERE / "configs" / "adjust-spatial.yaml"),
    "min-flicker-adjust": (MinFlickerAdjustTask, HERE / "configs" / "flicker-uniform.yaml"),
}

# The dashboard's parameter-set menu: display name -> (task name, params file).
# "(human)" / "(monkey)" names who the file is for (its subject_kind).
PARAMETERS = {
    "1a. Exp. 1 red/green, constant stimuli (human)": (
        "min-motion-constant", HERE / "configs" / "task.yaml"),
    "1b. Exp. 1 blue/yellow, constant stimuli (human)": (
        "min-motion-constant", HERE / "configs" / "task-blue-yellow.yaml"),
    "2a. Exp. 2 minimum motion vs spatial frequency (human)": (
        "min-motion-adjust", HERE / "configs" / "adjust-spatial.yaml"),
    "2b. Exp. 2 minimum flicker, counterphase gratings (human)": (
        "min-flicker-adjust", HERE / "configs" / "flicker-grating.yaml"),
    "2c. Standard flicker match, 2-deg uniform field (human)": (
        "min-flicker-adjust", HERE / "configs" / "flicker-uniform.yaml"),
    "3. Exp. 3 minimum motion vs temporal frequency (human)": (
        "min-motion-adjust", HERE / "configs" / "adjust-temporal.yaml"),
    "4. Red/green setting by adjustment, not in the paper (human)": (
        "min-motion-adjust", HERE / "configs" / "adjust-red-green.yaml"),
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
