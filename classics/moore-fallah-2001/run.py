"""Run Saccade planning and attention (Moore & Fallah), in any of alhazen's modes.

        uv run python run.py --task target-dimming-detection --mode simulate --headless --sub sim --ses 1 --seed 1
    uv run python run.py --task target-dimming-detection --mode test --sub dev --ses 1 --initials DEV
    uv run python run.py --task target-dimming-detection --rig booth --sub s01 --ses 1 --initials AB
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

from moore_fallah2001.task import TargetDimmingDetectionTask

HERE = Path(__file__).parent

# task name -> (Task class, params file it runs with when --params is not given)
TASKS = {
    "target-dimming-detection": (TargetDimmingDetectionTask, HERE / "configs" / "task.yaml"),
}

# The dashboard's parameter-set menu: display name -> (task name, params file).
# "(human)" / "(monkey)" names who the file is for (its subject_kind).
PARAMETERS = {
    "Main (human)": ("target-dimming-detection", HERE / "configs" / "task.yaml"),
    "Inside the movement field (monkey)": (
        "target-dimming-detection", HERE / "configs" / "task-monkey-inside.yaml"),
    "Outside the movement field (monkey)": (
        "target-dimming-detection", HERE / "configs" / "task-monkey-outside.yaml"),
}

# Monkey training ladders: display name -> ladder YAML. None: the paper describes no
# training sequence, and inventing one would be all assumption (docs/methods.md).
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
