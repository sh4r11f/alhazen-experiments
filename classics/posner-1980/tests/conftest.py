"""Shared fixtures: whole simulated sessions of both parameter sets, on a fake clock.

Built by alhazen exactly as ``run.py --mode simulate`` builds one (build_mode_session),
with alhazen's FakeClock: every flip moves time on by one frame, so a full 320-trial
session with its real durations takes seconds rather than twenty minutes. Built once
per test session and shared, read-only, by the tests that read its data.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from alhazen.config.loader import load_params, load_rig
from alhazen.modes import Mode
from alhazen.modes.session import build_mode_session
from alhazen.testing import FakeClock

from posner1980.task import PROJECT, PosnerCueingTask, PosnerCueingTaskParams

PARAMETER_SETS = {"tracker": "task.yaml", "keyboard": "task-keyboard.yaml"}


def sim_rig(tmp: Path) -> Path:
    """A headless 60 Hz rig with no devices, data under ``tmp``."""
    rig = tmp / "rig-sim.yaml"
    rig.write_text(
        "monitor: {name: sim, width_px: 1920, height_px: 1080, width_cm: 53.0, distance_cm: 57.0,"
        " refresh_rate_hz: 60.0, fullscreen: false}\n"
        "display: {backend: simulated}\n"
        f"devices: {{}}\ndata_root: {tmp / 'data'}\nreal_data: false\n",
        encoding="utf-8")
    return rig


def simulated_session(tmp: Path, params_file: Path, seed: int = 1) -> Path:
    """Run one whole simulated session; return its run folder."""
    params = load_params(params_file, PosnerCueingTaskParams)
    built = build_mode_session(Mode.SIMULATE, rig=load_rig(sim_rig(tmp)),
                               task=PosnerCueingTask(params), subject="sim", session=1,
                               seed=seed, headless=True, live_monitor=False, clock=FakeClock())
    built.runner.run()
    return next(built.data_root.rglob("*_trials.csv")).parent


@pytest.fixture(scope="session")
def simulated_runs(tmp_path_factory) -> dict[str, Path]:
    """{"tracker": run folder, "keyboard": run folder}, one full session each."""
    return {name: simulated_session(tmp_path_factory.mktemp(name), PROJECT / "configs" / f)
            for name, f in PARAMETER_SETS.items()}
