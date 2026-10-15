"""Run Lisi & Cavanagh (2015), Experiment 1, in any of alhazen's modes.

    uv run python run.py --task double-drift-perception --mode simulate --headless --sub sim --ses 1
    uv run python run.py --task double-drift-saccades --mode simulate --headless --sub sim --ses 1
    uv run python run.py --task double-drift-perception --rig booth --sub s01 --ses 1 --initials AB
    uv run python -m lisi_cavanagh2015.pse <the perception run folder>   # the two PSEs
    uv run python run.py --task double-drift-saccades --rig booth --sub s01 --ses 1 --initials AB \
        --params configs/task-s01.yaml                                 # a copy with s01's PSEs
    uv run alhazen dashboard --project .

The perceptual task comes first: it finds, for each participant, the physical path
orientations seen as vertical, and the saccade task shows those orientations. Both need an
eye tracker (configs/rig-booth.yaml).

TASKS, PARAMETERS and LADDERS are module-level dict LITERALS on purpose: alhazen's
dashboard reads them out of this file without running it. Each path is anchored to this
file, so a session finds its configs wherever the command is typed.

Without --rig a session starts on alhazen's shared `laptop` rig, a development rig on
which run mode (real data) is refused. A real session names its rig.
"""

from __future__ import annotations

import sys
from pathlib import Path

from alhazen.cli.modes import run_experiment

from lisi_cavanagh2015.task import DoubleDriftPerceptionTask, DoubleDriftSaccadesTask

HERE = Path(__file__).parent

# task name -> (Task class, params file it runs with when --params is not given)
TASKS = {
    "double-drift-perception": (
        DoubleDriftPerceptionTask, HERE / "configs" / "task-perception.yaml"),
    "double-drift-saccades": (DoubleDriftSaccadesTask, HERE / "configs" / "task.yaml"),
}

# The dashboard's parameter-set menu: display name -> (task name, params file).
PARAMETERS = {
    "1. Perceptual task (human)": (
        "double-drift-perception", HERE / "configs" / "task-perception.yaml"),
    "2. Saccade task (human)": ("double-drift-saccades", HERE / "configs" / "task.yaml"),
}

# Monkey training ladders: none (the original is a human experiment).
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
