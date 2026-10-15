"""Shared fixtures: the params files as loaded, and ONE simulated session.

The simulated session runs in real time (alhazen's simulate mode paces its
frames), so it is run once per test session and shared by the tests that read
its files (test_simulate, test_notebook) rather than once per test.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from alhazen.config.loader import load_params

from stroop1935.task import StroopParams

PROJECT = Path(__file__).resolve().parents[1]


def params_with(path: str = "configs/task.yaml", **changes) -> StroopParams:
    """A params file as loaded, with some fields changed and re-validated."""
    base = load_params(PROJECT / path, StroopParams).model_dump()
    return StroopParams.model_validate({**base, **changes})


def write_sim_rig(folder: Path) -> Path:
    rig = folder / "rig-sim.yaml"
    rig.write_text(
        "monitor: {name: sim, width_px: 1920, height_px: 1080, width_cm: 53.0, distance_cm: 57.0,"
        " refresh_rate_hz: 60.0, fullscreen: false}\n"
        "display: {backend: simulated}\n"
        f"devices: {{}}\ndata_root: {folder / 'data'}\nreal_data: false\n",
        encoding="utf-8")
    return rig


@pytest.fixture(scope="session")
def simulated_run(tmp_path_factory) -> Path:
    """Run the colour-naming task once in simulate mode, headless, as
    `run.py --mode simulate --headless` does; return the run folder."""
    folder = tmp_path_factory.mktemp("sim")
    rig = write_sim_rig(folder)
    cmd = [sys.executable, str(PROJECT / "run.py"), "--task", "stroop-color-naming",
           "--mode", "simulate", "--headless", "--rig", str(rig), "--sub", "sim", "--ses", "1",
           "--seed", "1"]
    done = subprocess.run(cmd, cwd=PROJECT, capture_output=True, text=True, timeout=600)
    assert done.returncode == 0, done.stdout[-3000:] + done.stderr[-3000:]
    trials = list(folder.rglob("*_trials.csv"))
    assert trials, "no trials.csv written:\n" + done.stdout[-3000:] + done.stderr[-3000:]
    return trials[0].parent
