"""Run the dynamic motion aftereffect experiment (Hiris & Blake, 1992) in any alhazen mode.

    uv run python run.py --task mae-coherence-match --mode demo
    uv run python run.py --task mae-coherence-match --mode simulate --headless \
        --sub sim --ses 1 --seed 1
    uv run python run.py --task mae-coherence-match --params configs/task-control.yaml \
        --mode simulate --headless --sub sim --ses 2 --seed 2
    uv run python run.py --task mae-coherence-match --mode test --sub dev --ses 1 --initials DEV
    uv run python run.py --task mae-coherence-match --rig booth --sub s01 --ses 1 --initials AB
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

from hirisblake1992.task import MaeCoherenceMatchTask

HERE = Path(__file__).parent

# task name -> (Task class, params file it runs with when --params is not given)
TASKS = {
    "mae-coherence-match": (MaeCoherenceMatchTask, HERE / "configs" / "task.yaml"),
}

# The dashboard's parameter-set menu: display name -> (task name, params file).
# "(human)" / "(monkey)" names who the file is for (its subject_kind).
# The main set adapts the left display to upward motion (the paper's experimental curve);
# the control set shows random motion in both displays during adaptation (its unadapted
# curve). Run them as separate sessions: adaptation cannot be mixed within one.
PARAMETERS = {
    "Adapted to upward motion (human)": ("mae-coherence-match", HERE / "configs" / "task.yaml"),
    "No adaptation, control (human)": ("mae-coherence-match",
                                       HERE / "configs" / "task-control.yaml"),
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
