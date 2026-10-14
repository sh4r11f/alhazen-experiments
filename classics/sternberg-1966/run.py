"""Run Sternberg memory scanning (experiment 1 varied set, experiment 2 fixed set).

    uv run python run.py --task memory-scanning --mode demo
    uv run python run.py --task memory-scanning-fixed --mode simulate --headless --sub sim
    uv run python run.py --task memory-scanning --mode simulate --headless --sub sim --seed 1
    uv run python run.py --task memory-scanning --mode test --sub dev --ses 1 --initials DEV
    uv run python run.py --task memory-scanning --rig booth --sub s01 --ses 1 --initials AB
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

from sternberg1966.task import FixedSetMemoryScanningTask, MemoryScanningTask

HERE = Path(__file__).parent

# task name -> (Task class, params file it runs with when --params is not given)
TASKS = {
    "memory-scanning": (MemoryScanningTask, HERE / "configs" / "task.yaml"),
    "memory-scanning-fixed": (FixedSetMemoryScanningTask, HERE / "configs" / "task-fixed-set.yaml"),
}

# The dashboard's parameter-set menu: display name -> (task name, params file).
# "(human)" / "(monkey)" names who the file is for (its subject_kind).
PARAMETERS = {
    "Experiment 1, varied set (human)": ("memory-scanning", HERE / "configs" / "task.yaml"),
    "Experiment 2, fixed set (human)": (
        "memory-scanning-fixed",
        HERE / "configs" / "task-fixed-set.yaml",
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
