"""Run Spatial contrast sensitivity (Campbell & Robson, 1968), in any of alhazen's modes.

    uv run python run.py --task csf-2ifc --rig booth --sub s01 --ses 1 --initials AB
    uv run python run.py --task csf-adjustment --rig booth --sub s01 --ses 2 --initials AB
    uv run python run.py --task csf-2ifc --params configs/task-far.yaml --rig booth-far ...
    uv run python run.py --task csf-2ifc --mode simulate --headless --sub sim --ses 1 --seed 1
    uv run python run.py --task csf-2ifc --mode demo
    uv run alhazen dashboard --project .

Before real data: measure the rig (`alhazen calibrate ruler`) and its gamma
(`alhazen calibrate gamma`, with a photometer), and set `display_bits` in the params file
to the display's real depth. Threshold contrasts are below 1%; on an 8-bit display they
exist only through dithering (docs/methods.md, Apparatus).

TASKS, PARAMETERS and LADDERS are module-level dict LITERALS on purpose: alhazen's
dashboard reads them out of this file without running it. Each path is anchored to this
file, so a session finds its configs wherever the command is typed.

Without --rig a session starts on alhazen's shared `laptop` rig, a development rig on
which run mode (real data) is refused. A real session names its rig: copy
configs/rig-booth.yaml (or rig-booth-far.yaml for the 2 deg set), enter the machine's
measured geometry, and pass --rig booth.
"""

from __future__ import annotations

import sys
from pathlib import Path

from alhazen.cli.modes import run_experiment

from campbell_robson1968.adjust import CsfAdjustmentTask
from campbell_robson1968.task import Csf2ifcTask

HERE = Path(__file__).parent

# task name -> (Task class, params file it runs with when --params is not given)
TASKS = {
    "csf-2ifc": (Csf2ifcTask, HERE / "configs" / "task.yaml"),
    "csf-adjustment": (CsfAdjustmentTask, HERE / "configs" / "adjustment.yaml"),
}

# The dashboard's parameter-set menu: display name -> (task name, params file).
# "(human)" / "(monkey)" names who the file is for (its subject_kind).
PARAMETERS = {
    "1. Contrast sensitivity, 2IFC, 10 deg field (human)": (
        "csf-2ifc",
        HERE / "configs" / "task.yaml",
    ),
    "2. High frequencies, 2IFC, 2 deg field (human)": (
        "csf-2ifc",
        HERE / "configs" / "task-far.yaml",
    ),
    "3. Sine vs square waves, 2IFC (human)": ("csf-2ifc", HERE / "configs" / "sine-square.yaml"),
    "4. Adjustment, the paper's method (human)": (
        "csf-adjustment",
        HERE / "configs" / "adjustment.yaml",
    ),
}

# Monkey training ladders: display name -> ladder YAML. Empty when there are none.
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
