"""Run Mental rotation of 3-D objects, in any of alhazen's modes.

    uv run python run.py --task mental-rotation --mode demo
    uv run python run.py --task mental-rotation --mode simulate --headless --sub sim --ses 1 \
        --seed 1 --params configs/task-rehearsal.yaml
    uv run python run.py --task mental-rotation --mode test --sub dev --ses 1 --initials DEV
    uv run python run.py --task mental-rotation --rig booth --sub s01 --ses 1 --initials AB

--ses picks the block: the design has 8 sessions of one 200-trial block each, drawn from
the subject's own 1600-trial plan (docs/methods.md, Design). Run sessions 1 to 8.
    uv run alhazen dashboard --project .

TASKS, PARAMETERS and LADDERS are module-level dict LITERALS on purpose: alhazen's
dashboard reads them out of this file without running it. Each path is anchored to this
file, so a session finds its configs wherever the command is typed.

Without --rig a session starts on alhazen's shared `laptop` rig, a development rig on
which run mode (real data) is refused. A real session names its rig: copy
configs/rig-booth.yaml, enter the machine's measured geometry, and pass --rig booth.
"""

from __future__ import annotations

import sys
from pathlib import Path

from alhazen.cli.modes import run_experiment

from shepard_metzler1971.task import MentalRotationTask

HERE = Path(__file__).parent

# task name -> (Task class, params file it runs with when --params is not given)
TASKS = {
    "mental-rotation": (MentalRotationTask, HERE / "configs" / "task.yaml"),
}

# The dashboard's parameter-set menu: display name -> (task name, params file).
# "(human)" / "(monkey)" names who the file is for (its subject_kind).
PARAMETERS = {
    "Main (human)": ("mental-rotation", HERE / "configs" / "task.yaml"),
    "Rehearsal, 20 trials (human)": ("mental-rotation", HERE / "configs" / "task-rehearsal.yaml"),
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
