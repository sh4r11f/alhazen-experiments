"""A full-length session of a shipped params file, on simulated time, with the simulated subject.

    uv run python scripts/simulate_full.py memory-scanning OUT_DIR
    uv run python scripts/simulate_full.py memory-scanning-fixed OUT_DIR

`run.py --mode simulate` runs a rehearsal (one repetition per cell) in real time. This runs
the whole plan the params file describes (168 trials of experiment 1, 540 of experiment 2)
through alhazen's own session builder and runner, on a clock that advances one frame per
flip, so it takes minutes instead of an hour. The data land under OUT_DIR like any session's
and `notebooks/analysis.ipynb` reads them (ANALYSIS_DATA=OUT_DIR). The subject is
sternberg1966.simulate's: software verification, not a replication.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from alhazen.config.loader import load_params
from alhazen.config.models import DisplayConfig, MonitorConfig, RigConfig
from alhazen.session.builder import build_session
from alhazen.testing import FakeClock

from sternberg1966.simulate import SimulatedObserver
from sternberg1966.task import (
    FixedSetMemoryScanningTask,
    FixedSetParams,
    MemoryScanningTask,
    VariedSetParams,
)

ROOT = Path(__file__).resolve().parents[1]
TASKS = {
    "memory-scanning": (MemoryScanningTask, VariedSetParams, "task.yaml"),
    "memory-scanning-fixed": (FixedSetMemoryScanningTask, FixedSetParams, "task-fixed-set.yaml"),
}


def main(task_name: str, out: Path, seed: int = 1) -> int:
    task_class, model, params_file = TASKS[task_name]
    task = task_class(load_params(ROOT / "configs" / params_file, model))
    clock = FakeClock()
    rig = RigConfig(
        monitor=MonitorConfig(width_px=1920, height_px=1080, width_cm=53.0, distance_cm=57.0,
                              refresh_rate_hz=60.0, fullscreen=False, name="sim"),
        display=DisplayConfig(backend="simulated"), data_root=str(out), real_data=False)
    observer = SimulatedObserver(seed=seed, positive_key=task.params.positive_key,
                                 negative_key=task.params.negative_key, clock=clock.now,
                                 **task.observer_model)
    runner = build_session(rig=rig, subject="sim", session=1, run=1, task=task, seed=seed,
                           iti=task.params.iti, response=observer, clock=clock,
                           live_monitor=False, mode="simulate")
    runner.run()
    trials = next(out.rglob("*_trials.csv"))
    df = pd.read_csv(trials)
    print(f"{task_name}: {len(df)} trials, outcomes {df['outcome'].value_counts().to_dict()}, "
          f"simulated duration {clock.now() / 60:.1f} min")
    print(trials)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1], Path(sys.argv[2]).resolve()))
