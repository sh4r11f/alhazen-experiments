r"""Run FEF microstimulation gating (Moore & Armstrong), in any of alhazen's modes.

    uv run python run.py --task rf-gating-fixation --mode simulate --headless \
        --rig recording-rehearsal --sub sim --ses 1 --seed 1
    uv run python run.py --task rf-gating-fixation --params configs/task-demo-human.yaml \
        --mode test --rig booth --sub dev --ses 1 --initials DEV
    uv run python run.py --task rf-gating-fixation --rig recording-example \
        --sub m01 --ses 1 --initials MK
    uv run alhazen dashboard --project .

The main file (configs/task.yaml) is a MONKEY stimulation session: run mode refuses a rig
whose sync does not map STIM_TRIGGER to a real line (RfGatingFixationTask.params_hook).
configs/task-demo-human.yaml is the same display with no stimulation, for a person to
watch. Neither records the paper's measure, V4 activity: that is the lab's recording
system, aligned through the sync lines (docs/methods.md).

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

from moore_armstrong2003.task import RfGatingFixationTask

HERE = Path(__file__).parent

# task name -> (Task class, params file it runs with when --params is not given)
TASKS = {
    "rf-gating-fixation": (RfGatingFixationTask, HERE / "configs" / "task.yaml"),
}

# The dashboard's parameter-set menu: display name -> (task name, params file).
# "(human)" / "(monkey)" names who the file is for (its subject_kind).
PARAMETERS = {
    "Main: stimulation session (monkey)": ("rf-gating-fixation", HERE / "configs" / "task.yaml"),
    "Demo: no stimulation (human)": (
        "rf-gating-fixation",
        HERE / "configs" / "task-demo-human.yaml",
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
