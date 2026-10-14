"""Run Stroop (1935) color-word interference, in any of alhazen's modes.

    uv run python run.py --task stroop-color-naming --mode demo
    uv run python run.py --task stroop-color-naming --mode simulate --headless \
        --sub sim --ses 1 --seed 1
    uv run python run.py --task stroop-color-naming --mode test --sub dev --ses 1 --initials DEV
    uv run python run.py --task stroop-color-naming --rig booth --sub 01 --ses 1 --initials AB
    uv run python run.py --task stroop-word-reading --rig booth --sub 01 --ses 2 --initials AB
    uv run alhazen dashboard --project .

Two tasks: stroop-color-naming is Experiment 2 (name the ink: squares vs incongruent
words); stroop-word-reading is Experiment 1's comparison (give the word: black vs ink),
answered by key, which is not the same as reading aloud (docs/methods.md says why).

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

from stroop1935.task import StroopColorNamingTask, StroopWordReadingTask

HERE = Path(__file__).parent

# task name -> (Task class, params file it runs with when --params is not given)
TASKS = {
    "stroop-color-naming": (StroopColorNamingTask, HERE / "configs" / "task.yaml"),
    "stroop-word-reading": (StroopWordReadingTask, HERE / "configs" / "task-word-reading.yaml"),
}

# The dashboard's parameter-set menu: display name -> (task name, params file).
# "(human)" / "(monkey)" names who the file is for (its subject_kind).
PARAMETERS = {
    "Experiment 2: colour naming (human)": ("stroop-color-naming", HERE / "configs" / "task.yaml"),
    "Experiment 1: word reading by key (human)": (
        "stroop-word-reading", HERE / "configs" / "task-word-reading.yaml"),
}

# Monkey training ladders: display name -> ladder YAML. None: Stroop is a human task.
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
