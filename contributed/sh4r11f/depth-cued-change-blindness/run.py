"""Run Depth-cued change blindness, in any of alhazen's modes.

    uv run python run.py --task depth-cued-flicker --mode demo
    uv run python run.py --task depth-cued-flicker --mode simulate --headless \
        --sub sim --ses 1 --seed 1
    uv run python run.py --task depth-cued-flicker --rig booth --sub s01 --ses 1 --initials AB
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

from depthcb.task import DepthCuedFlickerTask

HERE = Path(__file__).parent

# task name -> (Task class, params file it runs with when --params is not given)
TASKS = {
    "depth-cued-flicker": (DepthCuedFlickerTask, HERE / "configs" / "task-photos.yaml"),
}

# The dashboard's parameter-set menu: display name -> (task name, params file).
PARAMETERS = {
    "Practice: 6 photographs (human)": (
        "depth-cued-flicker", HERE / "configs" / "task-photos-practice.yaml"),
    "Main: 48 photographs, 75% valid depth cues (human)": (
        "depth-cued-flicker", HERE / "configs" / "task-photos.yaml"),
    "Drawn scenes, practice: 6 trials (human)": (
        "depth-cued-flicker", HERE / "configs" / "task-practice.yaml"),
    "Drawn scenes: 96 trials, 75% valid (human)": (
        "depth-cued-flicker", HERE / "configs" / "task.yaml"),
    "Drawn scenes with neutral cues (human)": (
        "depth-cued-flicker", HERE / "configs" / "task-neutral.yaml"),
    "Drawn scenes, size-matched planes (human)": (
        "depth-cued-flicker", HERE / "configs" / "task-matched-size.yaml"),
}

# Monkey training ladders: none (a human paradigm: a cue word, a key press, a report).
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
