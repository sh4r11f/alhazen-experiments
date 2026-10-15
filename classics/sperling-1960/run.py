"""Run Sperling partial report, in any of alhazen's modes.

    uv run python run.py --task partial-report --mode demo
    uv run python run.py --task partial-report --mode simulate --headless --sub sim --ses 1 --seed 1
    uv run python run.py --task partial-report --mode test --sub dev --ses 1 --initials DEV
    uv run python run.py --task partial-report --rig booth --sub s01 --ses 1 --initials AB
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

from sperling1960.task import PartialReportTask

HERE = Path(__file__).parent

# task name -> (Task class, params file it runs with when --params is not given)
TASKS = {
    "partial-report": (PartialReportTask, HERE / "configs" / "task.yaml"),
}

# The dashboard's parameter-set menu: display name -> (task name, params file).
# "(human)" / "(monkey)" names who the file is for (its subject_kind).
PARAMETERS = {
    "Exp. 4 decay, 12 letters and numbers (human)": (
        "partial-report", HERE / "configs" / "task.yaml"),
    "Exp. 4 decay, 9 letters (human)": (
        "partial-report", HERE / "configs" / "task-9.yaml"),
    "Exp. 3 partial report at offset, all materials (human)": (
        "partial-report", HERE / "configs" / "task-exp3.yaml"),
    "Exp. 1 whole report, baseline (human)": (
        "partial-report", HERE / "configs" / "task-whole.yaml"),
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
