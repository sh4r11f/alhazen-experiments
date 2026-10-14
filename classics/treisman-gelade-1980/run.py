"""Run Feature vs conjunction search (Treisman & Gelade, 1980), in any of alhazen's modes.

    uv run python run.py --task feature-conjunction-search --mode demo
    uv run python run.py --task feature-conjunction-search --mode simulate --headless --sub sim --ses 1 --seed 1
    uv run python run.py --task feature-conjunction-search --mode test --sub dev --ses 1 --initials DEV
    uv run python run.py --task feature-conjunction-search --rig booth --sub s01 --ses 1 --initials AB \
        --params configs/task-exp1-feature.yaml
    uv run alhazen dashboard --project .

One run is one block of 128 search trials (plus a repeat and a dummy trial for every
error) in ONE condition, the parameter set chosen. Experiment I ran each condition in its
own session, in an ABBAAB order, half the subjects starting with each condition, and
treated the first block of each condition as practice (paper p. 103). See docs/methods.md.

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

from treisman_gelade1980.task import FeatureConjunctionSearchTask

HERE = Path(__file__).parent

# task name -> (Task class, params file it runs with when --params is not given)
TASKS = {
    "feature-conjunction-search": (FeatureConjunctionSearchTask, HERE / "configs" / "task.yaml"),
}

# The dashboard's parameter-set menu: display name -> (task name, params file).
# "(human)" / "(monkey)" names who the file is for (its subject_kind).
PARAMETERS = {
    "Exp. I conjunction: green T (human)": (
        "feature-conjunction-search", HERE / "configs" / "task.yaml"),
    "Exp. I feature: blue letter or S (human)": (
        "feature-conjunction-search", HERE / "configs" / "task-exp1-feature.yaml"),
    "Exp. II easy: red O (human)": (
        "feature-conjunction-search", HERE / "configs" / "task-exp2-easy.yaml"),
    "Exp. II difficult: green T among blue T (human)": (
        "feature-conjunction-search", HERE / "configs" / "task-exp2-difficult.yaml"),
}

# Monkey training ladders: display name -> ladder YAML. Empty: a human-only experiment.
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
