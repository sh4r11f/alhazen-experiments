"""Run the oculomotor delayed-response task, in any of alhazen's modes.

    TASK=oculomotor-delayed-response
    uv run python run.py --task $TASK --mode demo
    uv run python run.py --task $TASK --mode simulate --headless --sub sim --ses 1 --seed 1
    uv run python run.py --task $TASK --mode test --sub dev --ses 1 --initials DEV
    uv run python run.py --task $TASK --rig booth --sub s01 --ses 1 --initials AB
    uv run python run.py --task $TASK --params configs/task-monkey.yaml \
        --rig gaze-example --sub m01 --ses 1 --initials MK
    uv run python run.py --mode training --stage fixate --rig gaze-example \
        --sub m01 --ses 1 --initials MK
    uv run alhazen dashboard --project .

TASKS, PARAMETERS and LADDERS are module-level dict LITERALS on purpose: alhazen's
dashboard reads them out of this file without running it. Each path is anchored to this
file, so a session finds its configs wherever the command is typed.

The task is gaze-contingent: a real session needs a rig with an eye tracker
(configs/rig-booth.yaml for a human booth, configs/rig-gaze-example.yaml for a monkey rig
with reward and sync lines; both carry example geometry to replace with your own). Without
--rig a session starts on alhazen's shared `laptop` rig, a development rig on which run mode
(real data) is refused.
"""

from __future__ import annotations

import sys
from pathlib import Path

from alhazen.cli.modes import run_experiment

from funahashi1989.task import OculomotorDelayedResponseTask

HERE = Path(__file__).parent

# task name -> (Task class, params file it runs with when --params is not given)
TASKS = {
    "oculomotor-delayed-response": (OculomotorDelayedResponseTask, HERE / "configs" / "task.yaml"),
}

# The dashboard's parameter-set menu: display name -> (task name, params file).
# "(human)" / "(monkey)" names who the file is for (its subject_kind).
PARAMETERS = {
    "Main (human)": ("oculomotor-delayed-response", HERE / "configs" / "task.yaml"),
    "Main (monkey)": ("oculomotor-delayed-response", HERE / "configs" / "task-monkey.yaml"),
}

# Monkey training ladders: display name -> ladder YAML (alhazen's training mode).
LADDERS = {
    "ODR training (monkey)": HERE / "configs" / "training-odr.yaml",
}


def main(argv: list[str] | None = None) -> int:
    return run_experiment(
        tasks=TASKS,
        ladders=LADDERS,
        default_rig="laptop",
        argv=list(sys.argv[1:] if argv is None else argv),
    )


if __name__ == "__main__":
    raise SystemExit(main())
