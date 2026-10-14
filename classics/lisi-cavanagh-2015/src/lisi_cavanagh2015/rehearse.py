"""Simulated sessions on simulated time: a whole session in seconds, for the tests and to
give the analysis notebook something to read.

    uv run python -m lisi_cavanagh2015.rehearse data-sim            # both tasks, full length
    uv run python -m lisi_cavanagh2015.rehearse data-sim --perceived  # saccades to the perceived path

Each flip moves a fake clock on by one frame (alhazen's FakeClock), so nothing waits for
real time. The data go to <root>/data-rehearsal/ like any rehearsal. This is software
verification with a simulated observer (lisi_cavanagh2015.simulate), never participant data.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from alhazen.config.loader import load_params
from alhazen.config.models import (
    DisplayConfig,
    LiveMonitorConfig,
    MonitorConfig,
    RigConfig,
)
from alhazen.modes import Mode
from alhazen.modes.session import build_mode_session
from alhazen.testing import FakeClock

from lisi_cavanagh2015.common import PROJECT
from lisi_cavanagh2015.perception import DoubleDriftPerceptionTask, PerceptionParams
from lisi_cavanagh2015.saccade import DoubleDriftSaccadesTask, SaccadeParams
from lisi_cavanagh2015.simulate import ObserverModel

TASKS = {
    "double-drift-perception": (DoubleDriftPerceptionTask, PerceptionParams,
                                "task-perception.yaml"),
    "double-drift-saccades": (DoubleDriftSaccadesTask, SaccadeParams, "task.yaml"),
}


def simulated_rig(data_root: Path, refresh_hz: float = 120.0) -> RigConfig:
    """A development rig with the paper's viewing distance and refresh rate."""
    return RigConfig(
        monitor=MonitorConfig(width_px=1920, height_px=1080, width_cm=53.0, distance_cm=60.0,
                              refresh_rate_hz=refresh_hz, fullscreen=False, name="sim"),
        display=DisplayConfig(backend="simulated"),
        live_monitor=LiveMonitorConfig(enabled=False),
        data_root=data_root,
        real_data=False,
    )


def run_simulated(task_name: str, root: Path, *, seed: int = 1, full: bool = True,
                  params: object | None = None, model: ObserverModel | None = None,
                  subject: str = "sim", session: int = 1,
                  refresh_hz: float = 120.0) -> Path:
    """Run one simulated session of ``task_name`` and return its run folder.

    ``full`` keeps every trial count (simulate mode otherwise runs alhazen's reduced
    rehearsal); ``params`` replaces the task's params file; ``model`` the observer."""
    task_cls, params_cls, fname = TASKS[task_name]
    if params is None:
        params = load_params(PROJECT / "configs" / fname, params_cls)
    task = task_cls(params)
    task.observer_model = model  # type: ignore[attr-defined]
    big = 10_000 if full else 1
    built = build_mode_session(
        Mode.SIMULATE, rig=simulated_rig(Path(root), refresh_hz), task=task,
        subject=subject, session=session, seed=seed, headless=True, live_monitor=False,
        n_per_condition=big, max_adaptive_trials=big if full else 10, clock=FakeClock())
    built.runner.run()
    runs = sorted(Path(built.data_root).rglob(f"run-*_task-{task_name}"),
                  key=lambda p: p.stat().st_mtime)
    return runs[-1]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("root", type=Path)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--perceived", action="store_true",
                    help="the simulated saccades target the perceived path (hypothesis 2)")
    a = ap.parse_args(argv)
    model = ObserverModel(target="perceived" if a.perceived else "physical")
    for name in TASKS:
        print(run_simulated(name, a.root, seed=a.seed, model=model))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
